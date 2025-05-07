import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional
import json
from pathlib import Path


class SiteScraper:
    """
    Scraper for collecting the list of supported sites from the recipe-scrapers documentation.
    """
    
    DOCS_URL = "https://docs.recipe-scrapers.com/getting-started/supported-sites/#exec-2--supported-sites-list"
    
    def __init__(self, cache_file=None):
        """
        Initialize the SiteScraper.
        
        Args:
            cache_file: Optional file path to cache the supported sites list
        """
        if cache_file is None:
            self.cache_file = Path(__file__).resolve().parent / 'supported_sites.json'
        else:
            self.cache_file = Path(cache_file)
    
    def get_supported_sites(self, use_cache=True) -> List[Dict[str, str]]:
        """
        Get the list of supported sites from the recipe-scrapers documentation.
        
        Args:
            use_cache: Whether to use the cached list if available
            
        Returns:
            List[Dict[str, str]]: List of supported sites with their names and domains
        """
        # Check if we have a cached list
        if use_cache and self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    sites = json.load(f)
                print(f"Loaded {len(sites)} supported sites from cache.")
                return sites
            except Exception as e:
                print(f"Error loading cached sites: {str(e)}")
        
        # Fetch the list from the documentation
        print(f"Fetching supported sites from {self.DOCS_URL}...")
        sites = self._scrape_supported_sites()
        
        # Cache the list for future use
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(sites, f, indent=2, ensure_ascii=False)
            print(f"Cached {len(sites)} supported sites to {self.cache_file}")
        except Exception as e:
            print(f"Error caching supported sites: {str(e)}")
        
        return sites
    
    def _scrape_supported_sites(self) -> List[Dict[str, str]]:
        """
        Scrape the list of supported sites from the recipe-scrapers documentation.
        
        Returns:
            List[Dict[str, str]]: List of supported sites with their names and domains
        """
        try:
            # Fetch the documentation page
            response = requests.get(self.DOCS_URL)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the section with the supported sites list
            sites_section = soup.find('h2', id='exec-2--supported-sites-list')
            
            if not sites_section:
                print("Could not find the supported sites section in the documentation.")
                return []
            
            # Find the list of supported sites - it's in a ul element after the h2
            site_list = []
            ul_element = sites_section.find_next('ul')
            if ul_element:
                site_list = ul_element.find_all('li')
            
            if not site_list:
                print("Could not find the list of supported sites in the documentation.")
                return []
            
            sites = []
            for site_item in site_list:
                # Each list item should contain an anchor tag with the site URL
                anchor = site_item.find('a')
                if anchor and anchor.has_attr('href'):
                    site_url = anchor['href']
                    site_name = anchor.get_text().strip()
                    
                    # Extract the domain from the URL
                    from urllib.parse import urlparse
                    parsed_url = urlparse(site_url)
                    domain = parsed_url.netloc
                    
                    if not domain:
                        # If the URL doesn't have a netloc, use the path
                        domain = parsed_url.path.strip('/')
                    
                    # Use the site URL as provided in the documentation
                    sites.append({
                        'name': site_name,
                        'domain': site_url
                    })
            
            print(f"Found {len(sites)} supported sites.")
            return sites
        
        except Exception as e:
            print(f"Error scraping supported sites: {str(e)}")
            return []
    
    def get_example_recipes(self, sites: List[Dict[str, str]], limit: Optional[int] = None) -> List[str]:
        """
        Generate example recipe URLs from the supported sites.
        
        Args:
            sites: List of supported sites
            limit: Maximum number of sites to include
            
        Returns:
            List[str]: List of example recipe URLs
        """
        if limit:
            sites = sites[:limit]
        
        # For now, just return the domain URLs
        # In a real implementation, you might want to crawl each site to find actual recipe URLs
        return [site['domain'] for site in sites]


def main():
    """Main function to demonstrate the site scraper."""
    scraper = SiteScraper()
    sites = scraper.get_supported_sites(use_cache=False)
    
    print(f"Found {len(sites)} supported sites:")
    for i, site in enumerate(sites[:10], 1):
        print(f"{i}. {site['name']} ({site['domain']})")
    
    if len(sites) > 10:
        print(f"... and {len(sites) - 10} more.")


if __name__ == '__main__':
    main()