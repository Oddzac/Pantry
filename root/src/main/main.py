#!/usr/bin/env python3
import sys
import os
import time
import random
import sqlite3
import json
from pathlib import Path
import argparse

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from recipe_scraper.models import Recipe
from recipe_scraper.parser import RecipeParser
from recipe_scraper.site_scraper import SiteScraper
from recipe_scraper.site_filter import SiteFilter
from recipe_scraper.db_manager import RecipeDatabase
from recipe_scraper.parallel_scraper import ParallelScraper

# Import the new RecipeFinder from recipe_crawler
from recipe_crawler.recipe_finder import RecipeFinder


class RecipeManager:
    """
    Manager for recipe scraping, storage, and retrieval.
    """
    
    def __init__(self, storage_dir=None, db_name='recipe_library.db'):
        """
        Initialize the RecipeManager.
        
        Args:
            storage_dir: Directory to store recipe data
            db_name: Name of the SQLite database file
        """
        # Set up storage directory
        if storage_dir is None:
            self.storage_dir = Path.home() / '.pantree' / 'recipes'
        else:
            self.storage_dir = Path(storage_dir)
        
        # Create the storage directory if it doesn't exist
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # Initialize components
        self.parser = RecipeParser()
        self.site_scraper = SiteScraper()
        self.recipe_finder = RecipeFinder()  # Use the new RecipeFinder
        self.site_filter = SiteFilter()
        
        # Initialize database
        self.db_path = self.storage_dir / db_name
        self.db = RecipeDatabase(self.db_path)
    
    def close(self):
        """Close the database connection."""
        self.db.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def scrape_recipe(self, url: str) -> Recipe:
        """
        Scrape a recipe from a URL.
        
        Args:
            url: URL of the recipe to scrape
            
        Returns:
            Recipe: Scraped recipe
        """
        recipe = self.parser.parse_url(url)
        return recipe
    
    def save_recipe(self, recipe: Recipe) -> int:
        """
        Save a recipe to the database.
        
        Args:
            recipe: Recipe to save
            
        Returns:
            int: ID of the saved recipe
        """
        return self.db.add_recipe(recipe)
    
    def get_recipe(self, recipe_id: int):
        """
        Get a recipe from the database.
        
        Args:
            recipe_id: ID of the recipe to get
            
        Returns:
            Dict: Recipe data
        """
        return self.db.get_recipe(recipe_id)
    
    def list_recipes(self, limit=None):
        """
        List all recipes in the database.
        
        Args:
            limit: Maximum number of recipes to return
            
        Returns:
            List[Tuple[int, str, int, str]]: List of recipe IDs, titles, times, and yields
        """
        try:
            # Get recipe IDs
            conn, cursor = self.db._get_connection()
            if limit:
                cursor.execute('SELECT id, title, total_time, yields FROM recipes LIMIT ?', (limit,))
            else:
                cursor.execute('SELECT id, title, total_time, yields FROM recipes')
            
            return [(row[0], row[1], row[2], row[3]) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error listing recipes: {str(e)}")
            return []
    
    def get_recipe_count(self):
        """
        Get the number of recipes in the database.
        
        Returns:
            int: Number of recipes
        """
        return self.db.get_recipe_count()
    
    def get_supported_sites(self, use_cache=True, english_only=True):
        """
        Get the list of supported sites from the recipe-scrapers documentation.
        
        Args:
            use_cache: Whether to use the cached list if available
            english_only: Whether to include only English language sites
            
        Returns:
            List[Dict[str, str]]: List of supported sites with their names and domains
        """
        sites = self.site_scraper.get_supported_sites(use_cache=use_cache)
        
        # Filter out non-English sites if requested
        if english_only:
            sites = self.site_filter.filter_sites(sites)
            print(f"Filtered to {len(sites)} English language sites")
        
        return sites
    
    def build_recipe_library(self, limit=None, recipes_per_site=2, use_cache=True, 
                            delay=1, english_only=True, parallel=True, 
                            max_workers=4, batch_size=20, use_browser_crawler=True):
        """
        Build a library of recipes by scraping from supported sites.
        
        Args:
            limit: Maximum number of sites to scrape from
            recipes_per_site: Number of recipes to scrape from each site
            use_cache: Whether to use the cached list of supported sites
            delay: Delay between requests in seconds to avoid overloading servers
            english_only: Whether to include only English language sites
            parallel: Whether to use parallel scraping
            max_workers: Maximum number of worker threads/processes for parallel scraping
            batch_size: Number of sites to process in each batch for parallel scraping
            use_browser_crawler: Whether to use the browser crawler for sites with anti-scraping measures
            
        Returns:
            Dict: Statistics about the scraping process
        """
        # Get the list of supported sites
        sites = self.get_supported_sites(use_cache=use_cache, english_only=english_only)
        
        if limit:
            sites = sites[:limit]
        
        if parallel:
            # Use parallel scraping
            scraper = ParallelScraper(
                db_path=self.db_path,
                max_workers=max_workers,
                delay_range=(delay, delay * 2),
                use_browser_crawler=use_browser_crawler
            )
            
            stats = scraper.build_recipe_library(
                sites=sites,
                limit=limit,
                recipes_per_site=recipes_per_site,
                batch_size=batch_size
            )
            
            # Save statistics
            stats_path = self.storage_dir / 'scraping_stats.json'
            scraper.save_stats(stats, stats_path)
            
            return stats
        else:
            # Use sequential scraping
            print(f"Building recipe library from {len(sites)} supported sites...")
            print(f"Attempting to scrape up to {recipes_per_site} recipes per site")
            
            # Track successful scrapes
            successful = 0
            total_attempts = 0
            
            # Track timing
            start_time = time.time()
            
            # Scrape recipes from each site
            for site in sites:
                try:
                    print(f"\nProcessing {site['name']} ({site['domain']})...")
                    
                    # Find recipe URLs on the site
                    recipe_urls = self.recipe_finder.find_recipe_urls(site['domain'], max_urls=recipes_per_site)
                    
                    if not recipe_urls:
                        print(f"No recipe URLs found on {site['domain']}")
                        continue
                    
                    # Scrape each recipe URL
                    site_successful = 0
                    for url in recipe_urls:
                        try:
                            print(f"Scraping recipe from {url}...")
                            total_attempts += 1
                            
                            # Add a delay to avoid overloading servers
                            if total_attempts > 1:
                                time_to_sleep = delay + random.uniform(0, 1)  # Add some randomness
                                print(f"Waiting {time_to_sleep:.2f} seconds before next request...")
                                time.sleep(time_to_sleep)
                            
                            # Parse the recipe
                            try:
                                recipe = self.parser.parse_url(url)
                                
                                # Save the recipe to the database
                                self.save_recipe(recipe)
                                successful += 1
                                site_successful += 1
                                print(f"Successfully scraped recipe: {recipe.title}")
                            
                            except Exception as e:
                                print(f"Error parsing recipe from {url}: {str(e)}")
                                
                        except Exception as e:
                            print(f"Error scraping recipe from {url}: {str(e)}")
                    
                    print(f"Successfully scraped {site_successful} out of {len(recipe_urls)} recipes from {site['name']}")
                    
                except Exception as e:
                    print(f"Error processing {site['domain']}: {str(e)}")
            
            # Calculate statistics
            end_time = time.time()
            elapsed_time = end_time - start_time
            
            stats = {
                'total_sites': len(sites),
                'total_recipes': successful,
                'total_attempts': total_attempts,
                'success_rate': successful / total_attempts if total_attempts > 0 else 0,
                'elapsed_time': elapsed_time,
                'recipes_per_minute': successful / (elapsed_time / 60) if elapsed_time > 0 else 0
            }
            
            print(f"\nSummary: Successfully scraped {successful} recipes from {len(sites)} sites.")
            print(f"Success rate: {stats['success_rate']:.2%}")
            print(f"Total time: {elapsed_time:.2f} seconds ({stats['recipes_per_minute']:.2f} recipes/minute)")
            
            return stats
    
    def import_from_json(self, json_path):
        """
        Import recipes from a JSON file.
        
        Args:
            json_path: Path to the JSON file
            
        Returns:
            int: Number of recipes imported
        """
        return self.db.import_from_json(json_path)
    
    def export_to_json(self, json_path, limit=None):
        """
        Export recipes to a JSON file.
        
        Args:
            json_path: Path to the JSON file
            limit: Maximum number of recipes to export
            
        Returns:
            int: Number of recipes exported
        """
        return self.db.export_to_json(json_path, limit)
    
    def search_by_title(self, query, limit=10):
        """
        Search recipes by title.
        
        Args:
            query: Search query
            limit: Maximum number of results to return
            
        Returns:
            List[Dict]: List of matching recipes
        """
        return self.db.search_by_title(query, limit)
    
    def search_by_ingredient(self, ingredient, limit=10):
        """
        Search recipes by ingredient.
        
        Args:
            ingredient: Ingredient to search for
            limit: Maximum number of results to return
            
        Returns:
            List[Dict]: List of matching recipes
        """
        return self.db.search_by_ingredient(ingredient, limit)
    
    def search_by_time(self, max_time, limit=10):
        """
        Search recipes by maximum preparation time.
        
        Args:
            max_time: Maximum preparation time in minutes
            limit: Maximum number of results to return
            
        Returns:
            List[Dict]: List of matching recipes
        """
        return self.db.search_by_time(max_time, limit)
    

    def optimize_for_web(self, output_path):
        """
        Optimize the database for web access.
        
        Args:
            output_path: Path to save the optimized database
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Create a new connection to the output database
            conn = sqlite3.connect(output_path)
            
            # Copy the database structure and data
            with sqlite3.connect(self.db_path) as src_conn:
                src_conn.backup(conn)
            
            # Optimize the database
            cursor = conn.cursor()
            
            # Enable WAL mode for better concurrent access
            cursor.execute("PRAGMA journal_mode=WAL")
            
            # Create additional indexes for web queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_recipes_host_title ON recipes(host, title)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ingredients_name_recipe ON ingredients(name, recipe_id)")
            
            # Vacuum the database to optimize storage
            cursor.execute("VACUUM")
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            print(f"Error optimizing database for web: {str(e)}")
            return False




def main():
    """Main function to demonstrate recipe scraping functionality."""
    parser = argparse.ArgumentParser(description='Recipe Manager')
    
    # Add subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Scrape command
    scrape_parser = subparsers.add_parser('scrape', help='Scrape a recipe from a URL')
    scrape_parser.add_argument('url', help='URL of the recipe to scrape')
    
    # Build library command
    build_parser = subparsers.add_parser('build-library', help='Build a library of recipes')
    build_parser.add_argument('--limit', type=int, help='Maximum number of sites to scrape from')
    build_parser.add_argument('--recipes-per-site', type=int, default=2, help='Number of recipes to scrape from each site')
    build_parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests in seconds')
    build_parser.add_argument('--no-english-only', action='store_true', help='Include non-English sites')
    build_parser.add_argument('--no-parallel', action='store_true', help='Disable parallel scraping')
    build_parser.add_argument('--workers', type=int, default=4, help='Number of worker threads/processes')
    build_parser.add_argument('--batch-size', type=int, default=20, help='Number of sites to process in each batch')
    build_parser.add_argument('--no-browser-crawler', action='store_true', help='Disable browser crawler for sites with anti-scraping measures')
    
    # List sites command
    sites_parser = subparsers.add_parser('list-sites', help='List supported sites')
    sites_parser.add_argument('--no-english-only', action='store_true', help='Include non-English sites')
    sites_parser.add_argument('--limit', type=int, help='Maximum number of sites to list')
    
    # Find recipes command
    find_parser = subparsers.add_parser('find-recipes', help='Find recipe URLs on a site')
    find_parser.add_argument('domain', help='Domain to search for recipes')
    find_parser.add_argument('--max-urls', type=int, default=5, help='Maximum number of URLs to find')
    find_parser.add_argument('--max-depth', type=int, default=3, help='Maximum depth to crawl')
    
    # List recipes command
    list_parser = subparsers.add_parser('list-recipes', help='List all recipes in the library')
    list_parser.add_argument('--limit', type=int, help='Maximum number of recipes to list')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search for recipes')
    search_parser.add_argument('type', choices=['title', 'ingredient', 'time'], help='Type of search')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--limit', type=int, default=10, help='Maximum number of results to return')
    
    # View recipe command
    view_parser = subparsers.add_parser('view-recipe', help='View details of a specific recipe')
    view_parser.add_argument('id', type=int, help='ID of the recipe to view')

    # Import command
    import_parser = subparsers.add_parser('import', help='Import recipes from a JSON file')
    import_parser.add_argument('file', help='Path to the JSON file')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export recipes to a JSON file')
    export_parser.add_argument('file', help='Path to the JSON file')
    export_parser.add_argument('--limit', type=int, help='Maximum number of recipes to export')
    
    # Export web database command
    web_db_parser = subparsers.add_parser('export-web-db', help='Optimize database for web access')
    web_db_parser.add_argument('--output', default='docs/recipe_library.db', help='Output path for the web-optimized database')


    # Parse arguments
    args = parser.parse_args()


    def print_recipe_details(recipe):
        """Print detailed information about a recipe."""
        print("\n" + "=" * 80)
        print(f"Recipe ID: {recipe['id']}")
        print(f"Title: {recipe['title']}")
        print(f"Source: {recipe['url']}")
        print(f"Host: {recipe['host']}")
        print("-" * 80)
        print(f"Total Time: {recipe['total_time']} minutes")
        print(f"Yields: {recipe['yields']}")
        print("-" * 80)
        
        print("Ingredients:")
        for ingredient in recipe['ingredients']:
            if ingredient['measurement'] and ingredient['unit_type']:
                print(f"- {ingredient['measurement']} {ingredient['unit_type']} {ingredient['name']}")
            elif ingredient['measurement']:
                print(f"- {ingredient['measurement']} {ingredient['name']}")
            else:
                print(f"- {ingredient['name']}")
        
        print("-" * 80)
        print("Instructions:")
        # Format instructions with line breaks
        instructions = recipe['instructions'].split('\n')
        for i, step in enumerate(instructions, 1):
            if step.strip():  # Skip empty lines
                print(f"{i}. {step.strip()}")
        
        print("-" * 80)
        
        # Print nutrition information if available
        if recipe['nutrients'] and any(recipe['nutrients'].values()):
            print("Nutrition Information:")
            for nutrient, value in recipe['nutrients'].items():
                if value:  # Only print non-empty values
                    print(f"- {nutrient}: {value}")
            print("-" * 80)
        
        # Print image URL if available
        if recipe['image']:
            print(f"Image: {recipe['image']}")
        
        print("=" * 80)

    # Create the recipe manager
    with RecipeManager() as recipe_manager:
        if args.command == 'scrape':
            # Scrape a single recipe
            recipe = recipe_manager.scrape_recipe(args.url)
            if recipe:
                recipe_id = recipe_manager.save_recipe(recipe)
                print(f"Recipe saved with ID {recipe_id}: {recipe.title}")
                print(f"Total Time: {recipe.total_time} minutes")
                print(f"Yields: {recipe.yields}")
                print("\nIngredients:")
                for ingredient in recipe.ingredients:
                    if ingredient.measurement and ingredient.unit_type:
                        print(f"- {ingredient.measurement} {ingredient.unit_type} of {ingredient.name}")
                    elif ingredient.measurement:
                        print(f"- {ingredient.measurement} {ingredient.name}")
                    else:
                        print(f"- {ingredient.name}")
        
        elif args.command == 'build-library':
            # Build a library of recipes
            stats = recipe_manager.build_recipe_library(
                limit=args.limit,
                recipes_per_site=args.recipes_per_site,
                delay=args.delay,
                english_only=not args.no_english_only,
                parallel=not args.no_parallel,
                max_workers=args.workers,
                batch_size=args.batch_size,
                use_browser_crawler=not args.no_browser_crawler
            )
            
            # Print summary
            print("\nLibrary building complete!")
            print(f"Total recipes: {recipe_manager.get_recipe_count()}")
            print(f"Success rate: {stats.get('success_rate', 0):.2%}")
            print(f"Total time: {stats.get('elapsed_time', 0):.2f} seconds")
            print(f"Speed: {stats.get('recipes_per_minute', 0):.2f} recipes/minute")
        
        elif args.command == 'list-sites':
            # List supported sites
            sites = recipe_manager.get_supported_sites(english_only=not args.no_english_only)
            
            if args.limit:
                sites = sites[:args.limit]
            
            print(f"Found {len(sites)} supported sites:")
            for i, site in enumerate(sites, 1):
                print(f"{i}. {site['name']} ({site['domain']})")
        
        elif args.command == 'find-recipes':
            # Find recipe URLs on a specific site
            recipe_urls = recipe_manager.recipe_finder.find_recipe_urls(
                args.domain, 
                max_urls=args.max_urls,
                max_depth=args.max_depth
            )
            
            print(f"Found {len(recipe_urls)} recipe URLs on {args.domain}:")
            for i, url in enumerate(recipe_urls, 1):
                print(f"{i}. {url}")
        
        elif args.command == 'list-recipes':
            # List all recipes in the library
            recipes = recipe_manager.list_recipes(limit=args.limit)
            count = recipe_manager.get_recipe_count()
            
            print(f"Recipe library contains {count} recipes:")
            for i, (recipe_id, title, time, yields) in enumerate(recipes, 1):
                print(f"{i}. [{recipe_id}] {title} ({time} min, {yields})")

        
        elif args.command == 'search':
            # Search for recipes
            if args.type == 'title':
                results = recipe_manager.search_by_title(args.query, limit=args.limit)
                print(f"Found {len(results)} recipes with title containing '{args.query}':")
            
            elif args.type == 'ingredient':
                results = recipe_manager.search_by_ingredient(args.query, limit=args.limit)
                print(f"Found {len(results)} recipes with ingredient '{args.query}':")
            
            elif args.type == 'time':
                try:
                    max_time = int(args.query)
                    results = recipe_manager.search_by_time(max_time, limit=args.limit)
                    print(f"Found {len(results)} recipes that can be prepared in {max_time} minutes or less:")
                except ValueError:
                    print(f"Invalid time value: {args.query}")
                    return
            
            # Display the results
            for i, recipe in enumerate(results, 1):
                print(f"{i}. [{recipe['id']}] {recipe['title']} ({recipe['total_time']} minutes)")
        
        elif args.command == 'view-recipe':
            # View a specific recipe
            recipe = recipe_manager.get_recipe(args.id)
            if recipe:
                print_recipe_details(recipe)
            else:
                print(f"Recipe with ID {args.id} not found")

        elif args.command == 'import':
            # Import recipes from a JSON file
            count = recipe_manager.import_from_json(args.file)
            print(f"Imported {count} recipes from {args.file}")
            print(f"Recipe library now contains {recipe_manager.get_recipe_count()} recipes")
        
        elif args.command == 'export':
            # Export recipes to a JSON file
            count = recipe_manager.export_to_json(args.file, limit=args.limit)
            print(f"Exported {count} recipes to {args.file}")
        
        elif args.command == 'export-web-db':
            # Optimize database for web access
            success = recipe_manager.optimize_for_web(args.output)
            if success:
                print(f"Database optimized for web access and saved to {args.output}")
            else:
                print("Failed to optimize database for web access")


        else:
            # Show usage
            parser.print_help()


if __name__ == "__main__":
    main()