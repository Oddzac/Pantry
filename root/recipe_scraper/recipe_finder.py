import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from typing import List, Optional, Tuple
import random
import time

SSL_PROBLEM_SITES = [
    'afghankitchenrecipes.com',
    # Add other problematic sites here
]

class RecipeFinder:
    """
    Utility for finding recipe URLs on supported sites.
    """
    


    def __init__(self, user_agent=None):
        """
        Initialize the RecipeFinder.
        
        Args:
            user_agent: Optional user agent string to use for requests
        """
        self.user_agent = user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        self.headers = {'User-Agent': self.user_agent}
        
        # Cache for pages we've already checked
        self.page_cache = {}
    
    def find_recipe_urls(self, domain: str, max_urls: int = 5) -> List[str]:
        """
        Find recipe URLs on a given domain.
        
        Args:
            domain: Domain to search for recipes
            max_urls: Maximum number of recipe URLs to return
            
        Returns:
            List[str]: List of recipe URLs
        """
        if domain in SSL_PROBLEM_SITES:
            print(f"Skipping {domain} due to known SSL certificate issues")
            return []
        try:
            # Import direct recipe URLs as a fallback
            from .direct_recipe_urls import get_direct_recipe_urls
            direct_urls = get_direct_recipe_urls(domain)
            
            # Ensure the domain is a valid URL
            if not domain.startswith('http'):
                domain = f"https://{domain}"
            
            # Parse the domain to get the base URL
            parsed_url = urlparse(domain)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            domain_name = parsed_url.netloc.lower()
            
            # First try to find a recipes section
            recipe_urls = []
            
            # Special handling for 101cookbooks.com
            if '101cookbooks.com' in domain_name:
                # 101cookbooks.com has a unique structure with category pages that contain recipes
                category_urls = [
                    f"{base_url}/whole_grain_recipes",
                    f"{base_url}/sides",
                    f"{base_url}/breakfast_brunch",
                    f"{base_url}/vegetarian_recipes",
                    f"{base_url}/vegan-recipes",
                    f"{base_url}/gluten_free_recipes",
                    f"{base_url}/dinner_ideas",
                    f"{base_url}/baked_goods"
                ]
                
                # Try each category page
                for category_url in category_urls:
                    if len(recipe_urls) >= max_urls:
                        break
                    
                    try:
                        print(f"Fetching category: {category_url}...")
                        soup, status_code = self._fetch_and_parse(category_url)
                        if soup:
                            # Find links to individual recipes
                            for link in soup.find_all('a', href=True):
                                url = link['href']
                                
                                # Resolve relative URLs
                                if not url.startswith('http'):
                                    url = urljoin(base_url, url)
                                
                                # Skip URLs that are not from the same domain
                                if not url.startswith(base_url):
                                    continue
                                
                                # Skip category pages
                                if url in category_urls or url == base_url:
                                    continue
                                
                                # Add the URL if it's not already in the list
                                if url not in recipe_urls:
                                    recipe_urls.append(url)
                                    
                                # Stop if we have enough recipes
                                if len(recipe_urls) >= max_urls:
                                    break
                    except Exception as e:
                        print(f"Error fetching category {category_url}: {str(e)}")
            
            # Try common recipe section URLs for all sites
            recipe_sections = [
                f"{base_url}/recipes",
                f"{base_url}/recipe",
                f"{base_url}/popular-recipes",
                f"{base_url}/all-recipes",
                f"{base_url}/featured-recipes",
                domain  # Fall back to the homepage if needed
            ]
            
            for section_url in recipe_sections:
                if len(recipe_urls) >= max_urls:
                    break  # Stop if we've found enough recipes
                    
                try:
                    print(f"Fetching {section_url}...")
                    soup, status_code = self._fetch_and_parse(section_url)
                    if soup:
                        # Find links that might be recipes
                        section_recipes = self._extract_recipe_links(soup, base_url)
                        if section_recipes:
                            recipe_urls.extend(section_recipes)
                except Exception as e:
                    print(f"Error fetching {section_url}: {str(e)}")
            
            # If we still don't have enough recipes, try the homepage and look for a recipes section
            if len(recipe_urls) < max_urls:
                try:
                    print(f"Fetching {domain}...")
                    soup, status_code = self._fetch_and_parse(domain)
                    if soup:
                        # Find links that might be recipes
                        homepage_recipes = self._extract_recipe_links(soup, base_url)
                        if homepage_recipes:
                            recipe_urls.extend(homepage_recipes)
                        
                        # Try to find a recipes section
                        recipe_section_url = self._find_recipe_section(soup, base_url)
                        if recipe_section_url and recipe_section_url not in recipe_sections:
                            print(f"Found recipe section: {recipe_section_url}")
                            soup, status_code = self._fetch_and_parse(recipe_section_url)
                            if soup:
                                section_recipes = self._extract_recipe_links(soup, base_url)
                                if section_recipes:
                                    recipe_urls.extend(section_recipes)
                except Exception as e:
                    print(f"Error fetching homepage: {str(e)}")
            
            # If we still don't have enough recipes, use direct URLs as a fallback
            if len(recipe_urls) < max_urls and direct_urls:
                print(f"Using {len(direct_urls)} direct recipe URLs as fallback")
                recipe_urls.extend(direct_urls)
            
            # Remove duplicates while preserving order
            unique_urls = []
            seen = set()
            for url in recipe_urls:
                if url not in seen:
                    seen.add(url)
                    unique_urls.append(url)
            
            recipe_urls = unique_urls
            
            # For now, skip verification as it's causing issues
            # Just return the first max_urls recipes
            if recipe_urls:
                # Shuffle the URLs to get a random selection
                random.shuffle(recipe_urls)
                result_urls = recipe_urls[:max_urls]
                print(f"Found {len(result_urls)} recipe URLs on {domain}")
                return result_urls
            else:
                print(f"No recipe URLs found on {domain}")
                # Return direct URLs as a last resort
                if direct_urls:
                    return direct_urls[:max_urls]
                return []

        except requests.exceptions.SSLError as e:
            print(f"SSL certificate error for {domain}: {str(e)}")
            self.failed_sites.add(domain)
            return []    
        except Exception as e:
            print(f"Error finding recipe URLs on {domain}: {str(e)}")
            
            # As a last resort, try to use direct URLs
            if direct_urls:
                print(f"Using {len(direct_urls)} direct recipe URLs as fallback after error")
                return direct_urls[:max_urls]
                
            return []
    
    def _fetch_and_parse(self, url: str) -> Tuple[Optional[BeautifulSoup], int]:
        """
        Fetch a URL and parse it with BeautifulSoup.
        
        Args:
            url: URL to fetch
            
        Returns:
            Tuple[Optional[BeautifulSoup], int]: BeautifulSoup object and status code
        """
        # Check if we've already fetched this URL
        if url in self.page_cache:
            return self.page_cache[url]
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            status_code = response.status_code
            
            if status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                result = (soup, status_code)
                self.page_cache[url] = result
                return result
            else:
                return None, status_code
        except Exception as e:
            print(f"Error fetching {url}: {str(e)}")
            return None, 0
    
    def _extract_recipe_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Extract recipe links from a BeautifulSoup object.
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative links
            
        Returns:
            List[str]: List of recipe URLs
        """
        recipe_urls = set()
        
        # First, look for links within elements that are likely to contain recipes
        recipe_containers = []
        
        # Look for common recipe container elements
        for selector in [
            'div.recipes', 'div.recipe-list', 'div.recipe-grid', 
            'section.recipes', 'ul.recipes', 'div.recipe-card',
            'div[class*="recipe"]', 'section[class*="recipe"]',
            'div.post', 'article.post', 'div.entry', 'article.entry'
        ]:
            containers = soup.select(selector)
            if containers:
                recipe_containers.extend(containers)
        
        # If we found recipe containers, extract links from them first
        container_links = []
        if recipe_containers:
            for container in recipe_containers:
                for link in container.find_all('a', href=True):
                    url = link['href']
                    
                    # Resolve relative URLs
                    if not url.startswith('http'):
                        url = urljoin(base_url, url)
                    
                    # Skip URLs that are not from the same domain
                    if not url.startswith(base_url):
                        continue
                    
                    container_links.append(url)
        
        # Process container links first as they're more likely to be recipes
        for url in container_links:
            if self._is_likely_recipe_url(url):
                recipe_urls.add(url)
        
        # If we didn't find enough recipes in containers, look at all links
        if len(recipe_urls) < 5:
            # Look for links that might be recipes
            for link in soup.find_all('a', href=True):
                url = link['href']
                
                # Resolve relative URLs
                if not url.startswith('http'):
                    url = urljoin(base_url, url)
                
                # Skip URLs that are not from the same domain
                if not url.startswith(base_url):
                    continue
                
                # Check if the URL looks like a recipe
                if self._is_likely_recipe_url(url):
                    recipe_urls.add(url)
        
        return list(recipe_urls)
    
    def _is_likely_recipe_url(self, url: str) -> bool:
        """
        Check if a URL is likely to be a recipe based on its pattern.
        
        Args:
            url: URL to check
            
        Returns:
            bool: True if the URL is likely a recipe, False otherwise
        """
        # Extract the path from the URL
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        
        # Check for special case domains with unique URL structures
        domain = parsed_url.netloc.lower()
        
        # Special handling for 101cookbooks.com
        if '101cookbooks.com' in domain:
            # For 101cookbooks.com, we need to be more lenient
            # Their recipes are often directly under category paths
            return True
        
        # Skip URLs that are likely category, tag, or archive pages
        negative_patterns = [
            # Category and archive pages
            r'/category/', r'/categories/', r'/tag/', r'/tags/', 
            r'/author/', r'/about/', r'/contact/', r'/privacy/', 
            r'/terms/', r'/search/', r'/page/', r'/comment/',
            r'/archive/', r'/index/', r'/blog/', r'/feed/',
            r'/wp-content/', r'/wp-admin/', r'/wp-includes/',
            
            # Common recipe collection pages
            r'/recipes?/?$',  # /recipe/ or /recipes/ as standalone paths
            r'/[a-z]+-recipes/?$',  # e.g., /soup-recipes/, /vegan-recipes/
            r'/-recipes?/?',  # e.g., /dinner-recipes/
            r'/_recipes?/?',  # e.g., /dinner_recipes/
            r'/recipes?-[a-z]+/?$',  # e.g., /recipes-category/
            r'/recipes?_[a-z]+/?$',  # e.g., /recipes_category/
            r'/recipes?/[a-z]+/?$',  # e.g., /recipes/breakfast/
            r'/recipes?/season/',  # e.g., /recipes/season/summer/
            r'/recipes?/method/',  # e.g., /recipes/method/grilling/
            r'/recipes?/course/',  # e.g., /recipes/course/dessert/
            r'/recipes?/cuisine/',  # e.g., /recipes/cuisine/italian/
            r'/recipes?/diet/',  # e.g., /recipes/diet/vegetarian/
            r'/recipes?/holiday/',  # e.g., /recipes/holiday/christmas/
            r'/artikelen/',  # Dutch articles
            
            # Media files
            r'\.jpg$', r'\.jpeg$', r'\.png$', r'\.gif$',  # Skip direct image links
            
            # Other non-recipe pages
            r'/collection', r'/collections', r'/cookiebeleid',
            r'/artikelen/', r'/recepten/?$',  # Non-English recipe collections
            
            # Non-English language patterns
            r'/recettes/?$', r'/rezepte/?$', r'/ricette/?$', r'/receitas/?$',
            
            # Policy and terms pages
            r'/policy/?', r'/policies/?', r'/terms/?', r'/terms-of-use/?', 
            r'/terms-and-conditions/?', r'/privacy/?', r'/privacy-policy/?',
            r'/disclaimer/?', r'/legal/?', r'/copyright/?', r'/cookies/?',
            
            # Common category patterns with hyphens and underscores
            r'/easy-dinner-recipes/?', r'/quick-recipes/?', r'/healthy-recipes/?',
            r'/easy_dinner_recipes/?', r'/quick_recipes/?', r'/healthy_recipes/?',
        ]
        
        for pattern in negative_patterns:
            if re.search(pattern, path):
                return False
        
        # Check for positive indicators that this is a specific recipe
        # Look for patterns like /recipe-name/ or /year/month/recipe-name/
        positive_patterns = [
            # Pattern for recipe name with hyphens (e.g., /chicken-parmesan/)
            r'/[a-z0-9]+-[a-z0-9-]+-[a-z0-9-]+/?$',
            
            # Pattern for dated recipes (e.g., /2020/01/chicken-parmesan/)
            r'/\d{4}/\d{2}/[a-z0-9-]+/?$',
            
            # Pattern for recipe with ID (e.g., /recipes/12345/chicken-parmesan)
            r'/recipes?/\d+/[a-z0-9-]+/?$',
            
            # Pattern for recipe with category (e.g., /dinner/chicken-parmesan/)
            r'/[a-z0-9-]+/[a-z0-9]+-[a-z0-9-]+-[a-z0-9-]+/?$',
            
            # Pattern for specific recipe paths
            r'/[a-z0-9-]+/[a-z0-9-]+-[a-z0-9-]+-[a-z0-9-]+/?$'
        ]
        
        for pattern in positive_patterns:
            if re.search(pattern, path):
                return True
        
        # Check if the URL contains specific recipe-related keywords in the right context
        # We want to avoid category pages like /recipes/ but include specific recipes
        recipe_indicators = [
            # These are more specific recipe indicators
            r'/recipe/[a-z0-9-]+', r'/recipes/[a-z0-9-]+',
            r'/how-to-make-', r'/how-to-cook-',
            r'/homemade-', r'/best-ever-',
            r'/easy-', r'/quick-', r'/simple-'
        ]
        
        for indicator in recipe_indicators:
            if re.search(indicator, path):
                return True
        
        # If the path is very short, it's likely not a specific recipe
        if len(path.strip('/').split('/')) <= 1 and len(path.strip('/')) < 10:
            return False
        
        # As a last resort, check for common recipe-related terms, but be more strict
        recipe_keywords = ['recipe', 'dish', 'meal', 'cake', 'bread', 'stew', 'roast', 'bake']
        
        # Avoid certain keywords that are commonly used in category pages
        category_keywords = ['soup', 'vegan', 'vegetarian', 'dessert', 'breakfast', 'lunch', 'dinner']
        
        # Only consider it a recipe if the keyword is part of the final path segment
        # AND it's not a common category keyword
        path_segments = path.strip('/').split('/')
        if path_segments and any(keyword in path_segments[-1] for keyword in recipe_keywords):
            # Make sure it's not a category page
            if not any(keyword in path_segments[-1] for keyword in category_keywords):
                return True
        
        return False
    
    def _find_recipe_section(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """
        Find a link to a recipes section on the site.
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative links
            
        Returns:
            Optional[str]: URL of the recipes section, or None if not found
        """
        # Look for links to a recipes section
        recipe_section_keywords = [
            'recipes', 'recipe index', 'all recipes', 'recipe collection',
            'recipe library', 'popular recipes', 'featured recipes',
            'our recipes', 'recipe archive', 'recipe finder'
        ]
        
        # First, look for links in the navigation menu
        nav_elements = soup.select('nav, header, .menu, .navigation, .nav, #menu, #nav')
        
        for nav in nav_elements:
            for link in nav.find_all('a', href=True):
                link_text = link.get_text().lower().strip()
                
                if any(keyword in link_text for keyword in recipe_section_keywords):
                    url = link['href']
                    
                    # Resolve relative URLs
                    if not url.startswith('http'):
                        url = urljoin(base_url, url)
                    
                    # Skip URLs that are not from the same domain
                    if not url.startswith(base_url):
                        continue
                    
                    return url
        
        # If not found in navigation, look at all links
        for link in soup.find_all('a', href=True):
            link_text = link.get_text().lower().strip()
            
            if any(keyword in link_text for keyword in recipe_section_keywords):
                url = link['href']
                
                # Resolve relative URLs
                if not url.startswith('http'):
                    url = urljoin(base_url, url)
                
                # Skip URLs that are not from the same domain
                if not url.startswith(base_url):
                    continue
                
                return url
        
        # Look for common recipe section paths in href attributes
        common_recipe_paths = ['/recipes', '/recipe', '/all-recipes', '/popular-recipes']
        
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            
            if any(path in href for path in common_recipe_paths):
                url = link['href']
                
                # Resolve relative URLs
                if not url.startswith('http'):
                    url = urljoin(base_url, url)
                
                # Skip URLs that are not from the same domain
                if not url.startswith(base_url):
                    continue
                
                return url
        
        return None


def main():
    """Main function to demonstrate the recipe finder."""
    finder = RecipeFinder()
    
    # Example domains
    domains = [
        'allrecipes.com',
        'foodnetwork.com',
        'epicurious.com'
    ]
    
    for domain in domains:
        print(f"\nSearching for recipes on {domain}...")
        recipe_urls = finder.find_recipe_urls(domain, max_urls=3)
        
        for i, url in enumerate(recipe_urls, 1):
            print(f"{i}. {url}")


if __name__ == '__main__':
    main()