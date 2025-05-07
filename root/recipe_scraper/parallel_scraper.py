import concurrent.futures
import time
import random
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import json
from tqdm import tqdm

from .recipe_finder import RecipeFinder
from .parser import RecipeParser
from .db_manager import RecipeDatabase
from .models import Recipe

# Import the browser crawler if available
try:
    from root.recipe_crawler.browser_crawler import BrowserCrawler
    BROWSER_CRAWLER_AVAILABLE = True
except ImportError:
    BROWSER_CRAWLER_AVAILABLE = False


class ParallelScraper:
    """
    Parallel scraper for building a recipe library more efficiently.
    Thread-safe implementation with per-thread database connections.
    """
    
    def __init__(self, db_path: Path, max_workers: int = 4, delay_range: Tuple[float, float] = (1.0, 3.0), 
                 use_browser_crawler: bool = True):
        """
        Initialize the parallel scraper.
        
        Args:
            db_path: Path to the SQLite database
            max_workers: Maximum number of worker threads/processes
            delay_range: Range of delay between requests (min, max) in seconds
            use_browser_crawler: Whether to use the browser crawler for sites with anti-scraping measures
        """
        self.db_path = db_path
        self.max_workers = max_workers
        self.delay_range = delay_range
        self.recipe_finder = RecipeFinder()
        self.parser = RecipeParser()
        self.use_browser_crawler = use_browser_crawler and BROWSER_CRAWLER_AVAILABLE
        
        # Initialize browser crawler if available and enabled
        if self.use_browser_crawler:
            try:
                self.browser_crawler = BrowserCrawler()
                print("Browser crawler initialized and ready for sites with anti-scraping measures")
            except Exception as e:
                print(f"Failed to initialize browser crawler: {str(e)}")
                self.use_browser_crawler = False
        
        # Don't create a shared database connection here
        # Instead, each thread will create its own connection
        
        # Track successful and failed sites
        self.successful_sites = set()
        self.failed_sites = set()
        self.site_stats = {}
        
        # Track sites that required browser crawler
        self.browser_crawler_sites = set()
    
    def close(self):
        """Clean up resources."""
        # Nothing to close since we don't have a shared database connection
        pass
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def _scrape_site(self, site: Dict[str, str], recipes_per_site: int = 2) -> Tuple[str, int, int]:
        """
        Scrape recipes from a single site.
        
        Args:
            site: Site dictionary with 'name' and 'domain' keys
            recipes_per_site: Number of recipes to scrape from the site
            
        Returns:
            Tuple[str, int, int]: Site name, number of successful scrapes, number of attempts
        """
        domain = site['domain']
        site_name = site['name']
        
        # Create a thread-local database connection
        thread_db = RecipeDatabase(self.db_path)
        
        try:
            # First try with the standard recipe finder
            recipe_urls = []
            browser_crawler_used = False
            
            try:
                print(f"Finding recipe URLs on {domain} using standard crawler...")
                recipe_urls = self.recipe_finder.find_recipe_urls(domain, max_urls=recipes_per_site)
            except Exception as e:
                print(f"Standard crawler failed for {domain}: {str(e)}")
                recipe_urls = []
            
            # If standard crawler failed or found no recipes, try with browser crawler
            if not recipe_urls and self.use_browser_crawler:
                # Check if this is a site that might need browser crawler
                # Common sites with anti-scraping measures
                anti_scraping_domains = [
                    'theloopywhisk.com',
                    'nytimes.com',
                    'cooking.nytimes.com',
                    'bonappetit.com',
                    'epicurious.com',
                    'foodandwine.com',
                    'seriouseats.com',
                    'smittenkitchen.com',
                    'thekitchn.com'
                ]
                
                # Check if the domain matches any known anti-scraping site
                needs_browser = any(anti_domain in domain for anti_domain in anti_scraping_domains)
                
                # Also check if the domain has failed before with standard crawler
                if domain in self.failed_sites:
                    needs_browser = True
                
                if needs_browser:
                    try:
                        print(f"Trying browser crawler for {domain}...")
                        recipe_urls = self.browser_crawler.find_recipe_urls(f"https://{domain}", max_urls=recipes_per_site)
                        if recipe_urls:
                            print(f"Browser crawler found {len(recipe_urls)} recipes on {domain}")
                            browser_crawler_used = True
                            self.browser_crawler_sites.add(domain)
                    except Exception as e:
                        print(f"Browser crawler failed for {domain}: {str(e)}")
            
            if not recipe_urls:
                print(f"No recipe URLs found on {domain}")
                self.failed_sites.add(domain)
                return site_name, 0, 0
            
            # Track statistics
            successful = 0
            attempts = 0
            
            # Scrape each recipe URL
            for url in recipe_urls:
                try:
                    attempts += 1
                    
                    # Add a delay to avoid overloading servers
                    time.sleep(random.uniform(*self.delay_range))
                    
                    # Parse the recipe
                    recipe = self.parser.parse_url(url)
                    
                    # Save the recipe to the thread-local database
                    thread_db.add_recipe(recipe)
                    successful += 1
                    print(f"Successfully scraped recipe: {recipe.title} from {url}")
                    
                except Exception as e:
                    print(f"Error parsing recipe from {url}: {str(e)}")
            
            # Update tracking
            if successful > 0:
                self.successful_sites.add(domain)
            else:
                self.failed_sites.add(domain)
            
            return site_name, successful, attempts
            
        except Exception as e:
            print(f"Error processing {domain}: {str(e)}")
            self.failed_sites.add(domain)
            return site_name, 0, 0
        finally:
            # Close the thread-local database connection
            thread_db.close()
    
    def build_recipe_library(self, sites: List[Dict[str, str]], 
                            limit: Optional[int] = None, 
                            recipes_per_site: int = 2,
                            batch_size: int = 20) -> Dict[str, Any]:
        """
        Build a library of recipes by scraping from supported sites in parallel.
        
        Args:
            sites: List of site dictionaries with 'name' and 'domain' keys
            limit: Maximum number of sites to scrape from
            recipes_per_site: Number of recipes to scrape from each site
            batch_size: Number of sites to process in each batch
            
        Returns:
            Dict[str, Any]: Statistics about the scraping process
        """
        # Limit the number of sites if specified
        if limit:
            sites = sites[:limit]
        
        print(f"Building recipe library from {len(sites)} supported sites...")
        print(f"Using {self.max_workers} workers, processing in batches of {batch_size}")
        print(f"Attempting to scrape up to {recipes_per_site} recipes per site")
        
        if self.use_browser_crawler:
            print("Browser crawler is enabled for sites with anti-scraping measures")
        else:
            print("Browser crawler is disabled")
        
        # Track statistics
        start_time = time.time()
        total_successful = 0
        total_attempts = 0
        site_results = {}
        
        # Process sites in batches to avoid overwhelming the system
        for i in range(0, len(sites), batch_size):
            batch = sites[i:i+batch_size]
            print(f"\nProcessing batch {i//batch_size + 1}/{(len(sites) + batch_size - 1)//batch_size}...")
            
            # Use a progress bar for the batch
            with tqdm(total=len(batch), desc="Sites processed", unit="site") as pbar:
                # Process the batch in parallel
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    # Submit tasks
                    future_to_site = {
                        executor.submit(self._scrape_site, site, recipes_per_site): site['domain']
                        for site in batch
                    }
                    
                    # Process results as they complete
                    for future in concurrent.futures.as_completed(future_to_site):
                        site_domain = future_to_site[future]
                        try:
                            site_name, successful, attempts = future.result()
                            site_results[site_domain] = {
                                'name': site_name,
                                'successful': successful,
                                'attempts': attempts,
                                'browser_crawler_used': site_domain in self.browser_crawler_sites
                            }
                            total_successful += successful
                            total_attempts += attempts
                            pbar.update(1)
                        except Exception as e:
                            print(f"Error processing {site_domain}: {str(e)}")
                            self.failed_sites.add(site_domain)
                            pbar.update(1)
        
        # Calculate statistics
        end_time = time.time()
        elapsed_time = end_time - start_time
        success_rate = total_successful / total_attempts if total_attempts > 0 else 0
        
        stats = {
            'total_sites': len(sites),
            'successful_sites': len(self.successful_sites),
            'failed_sites': len(self.failed_sites),
            'browser_crawler_sites': len(self.browser_crawler_sites),
            'total_recipes': total_successful,
            'total_attempts': total_attempts,
            'success_rate': success_rate,
            'elapsed_time': elapsed_time,
            'recipes_per_minute': total_successful / (elapsed_time / 60) if elapsed_time > 0 else 0,
            'site_results': site_results
        }
        
        print(f"\nSummary: Successfully scraped {total_successful} recipes from {len(self.successful_sites)} sites.")
        if self.browser_crawler_sites:
            print(f"Browser crawler was used for {len(self.browser_crawler_sites)} sites with anti-scraping measures.")
        print(f"Success rate: {success_rate:.2%}")
        print(f"Total time: {elapsed_time:.2f} seconds ({stats['recipes_per_minute']:.2f} recipes/minute)")
        
        return stats
    
    def save_stats(self, stats: Dict[str, Any], path: Path):
        """
        Save scraping statistics to a JSON file.
        
        Args:
            stats: Statistics dictionary
            path: Path to save the JSON file
        """
        # Convert sets to lists for JSON serialization
        stats_copy = stats.copy()
        stats_copy['successful_sites'] = list(self.successful_sites)
        stats_copy['failed_sites'] = list(self.failed_sites)
        stats_copy['browser_crawler_sites'] = list(self.browser_crawler_sites)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(stats_copy, f, indent=2)
    
    def get_recipe_count(self) -> int:
        """
        Get the total number of recipes in the database.
        
        Returns:
            int: Number of recipes
        """
        # Create a temporary database connection
        with RecipeDatabase(self.db_path) as db:
            return db.get_recipe_count()


def main():
    """Test the parallel scraper."""
    from .site_scraper import SiteScraper
    from .site_filter import SiteFilter
    
    # Get supported sites
    site_scraper = SiteScraper()
    sites = site_scraper.get_supported_sites(use_cache=True)
    
    # Filter to English sites
    site_filter = SiteFilter()
    sites = site_filter.filter_sites(sites)
    
    print(f"Found {len(sites)} supported English sites")
    
    # Initialize the parallel scraper
    db_path = Path('recipe_library.db')
    scraper = ParallelScraper(db_path, max_workers=4, delay_range=(1.0, 2.0))
    
    # Build the recipe library
    stats = scraper.build_recipe_library(
        sites=sites,
        limit=10,  # Limit to 10 sites for testing
        recipes_per_site=2,
        batch_size=5
    )
    
    # Save statistics
    scraper.save_stats(stats, Path('scraping_stats.json'))
    
    # Print database stats
    print(f"\nDatabase contains {scraper.get_recipe_count()} recipes")


if __name__ == "__main__":
    main()
