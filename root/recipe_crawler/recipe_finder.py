"""
Recipe Finder module for finding recipe URLs on websites.
"""

import os
import tempfile
import json
import logging
from typing import Dict, List, Set, Optional
from urllib.parse import urlparse, urljoin
import random
import time
import requests
from bs4 import BeautifulSoup
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from .url_analyzer import URLAnalyzer
from .recipe_detector import RecipeDetector
from .spiders.recipe_spider import RecipeSpider


class RecipeFinder:
    """
    Utility for finding recipe URLs on websites using intelligent crawling.
    """

    def __init__(self, user_agent=None):
        """
        Initialize the RecipeFinder.
        
        Args:
            user_agent: Optional user agent string to use for requests
        """
        self.user_agent = user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        self.headers = {'User-Agent': self.user_agent}
        
        # Initialize URL analyzer and recipe detector
        self.url_analyzer = URLAnalyzer()
        self.recipe_detector = RecipeDetector()
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)

    def find_recipe_urls(self, domain: str, max_urls: int = 5, max_depth: int = 3) -> List[str]:
        """
        Find recipe URLs on a given domain using intelligent crawling.
        
        Args:
            domain: Domain or URL to search for recipes
            max_urls: Maximum number of recipe URLs to return
            max_depth: Maximum depth to crawl
            
        Returns:
            List[str]: List of recipe URLs
        """
        # Ensure the domain is a valid URL
        if not domain.startswith('http'):
            domain = f"https://{domain}"
        
        # Parse the domain to get the base URL
        parsed_url = urlparse(domain)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        domain_name = parsed_url.netloc.lower()
        
        self.logger.info(f"Finding recipe URLs on {domain_name}...")
        
        # First, try to find recipes using the Scrapy crawler
        recipe_urls = self._find_recipes_with_crawler(domain, max_urls, max_depth)
        
        # If we found enough recipes, return them
        if len(recipe_urls) >= max_urls:
            return recipe_urls[:max_urls]
        
        # If we didn't find enough recipes with the crawler, try a simpler approach
        if len(recipe_urls) < max_urls:
            self.logger.info(f"Found {len(recipe_urls)} recipes with crawler, trying simpler approach...")
            additional_urls = self._find_recipes_simple(domain, max_urls - len(recipe_urls))
            recipe_urls.extend(additional_urls)
        
        # Remove duplicates while preserving order
        unique_urls = []
        seen = set()
        for url in recipe_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        self.logger.info(f"Found {len(unique_urls)} unique recipe URLs on {domain_name}")
        return unique_urls[:max_urls]

    def _find_recipes_with_crawler(self, start_url: str, max_recipes: int, max_depth: int) -> List[str]:
        """
        Find recipe URLs using a Scrapy crawler.
        
        Args:
            start_url: URL to start crawling from
            max_recipes: Maximum number of recipes to find
            max_depth: Maximum depth to crawl
            
        Returns:
            List[str]: List of recipe URLs
        """
        # First try with the headless browser approach for sites that block traditional crawlers
        try:
            from .browser_crawler import BrowserCrawler
            self.logger.info("Trying to find recipes using headless browser...")
            browser_crawler = BrowserCrawler()
            browser_recipes = browser_crawler.find_recipe_urls(start_url, max_urls=max_recipes, max_depth=max_depth)
            
            if browser_recipes:
                self.logger.info(f"Found {len(browser_recipes)} recipes using headless browser")
                return browser_recipes
            else:
                self.logger.info("No recipes found with headless browser, falling back to traditional crawler")
        except ImportError:
            self.logger.warning("Selenium not installed, skipping headless browser approach")
            self.logger.warning("To enable browser-based crawling, install: pip install selenium webdriver-manager")
        except Exception as e:
            self.logger.error(f"Error using headless browser: {str(e)}")
        
        # Fall back to the traditional crawler approach
        # Create a temporary file to store the crawler results
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as tmp_file:
            output_file = tmp_file.name
        
        try:
            # Set up the crawler process with anti-blocking settings
            settings = get_project_settings()
            settings.update({
                'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'ROBOTSTXT_OBEY': False,  # Don't strictly obey robots.txt
                'CONCURRENT_REQUESTS': 2,  # Reduce concurrent requests
                'DOWNLOAD_DELAY': 3,  # Increase delay between requests
                'RANDOMIZE_DOWNLOAD_DELAY': True,  # Add randomness to delay
                'COOKIES_ENABLED': False,  # Disable cookies
                'FEED_FORMAT': 'json',
                'FEED_URI': f"file://{output_file}",
                'LOG_LEVEL': 'INFO',
                'RETRY_ENABLED': True,
                'RETRY_TIMES': 5,  # Increase retry attempts
                'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429, 403],  # Add 403 to retry codes
                'HTTPCACHE_ENABLED': True,  # Enable HTTP caching
                'HTTPCACHE_EXPIRATION_SECS': 86400,  # 24 hours
                'HTTPCACHE_DIR': 'httpcache',
                'HTTPCACHE_IGNORE_HTTP_CODES': [403, 404, 500, 502, 503, 504],
                'DEFAULT_REQUEST_HEADERS': {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0',
                    'DNT': '1',
                    'Referer': 'https://www.google.com/'
                }
            })
            
            process = CrawlerProcess(settings)
            
            # Parse the domain from the start URL
            parsed_url = urlparse(start_url)
            allowed_domain = parsed_url.netloc
            
            # Try to find category pages first as alternative entry points
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Create a list of URLs to try, starting with category pages
            urls_to_try = []
            
            # Add common category paths
            for path in RecipeSpider.COMMON_CATEGORY_PATHS:
                category_url = urljoin(base_url, path)
                urls_to_try.append(category_url)
            
            # Add the original URL as a fallback
            urls_to_try.append(start_url)
            
            # Set up and run the spider with multiple starting points
            process.crawl(
                RecipeSpider,
                start_url=start_url,  # Main starting point
                allowed_domains=[allowed_domain],
                max_recipes=max_recipes,
                max_depth=max_depth
            )
            process.start()  # This will block until the crawl is complete
            
            # Read the results from the output file
            with open(output_file, 'r') as f:
                try:
                    results = json.load(f)
                except json.JSONDecodeError:
                    results = []
            
            # Extract recipe URLs from the results
            recipe_urls = [item['url'] for item in results if item.get('type') == 'recipe']
            
            # If we didn't find any recipes with the crawler, try a simpler approach
            if not recipe_urls:
                self.logger.info("No recipes found with crawler, trying direct category page access...")
                
                # Try each category URL directly
                for category_url in urls_to_try[:5]:  # Limit to first 5 category URLs
                    try:
                        # Use a browser-like User-Agent
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                            'Accept-Language': 'en-US,en;q=0.9',
                            'Referer': 'https://www.google.com/'
                        }
                        
                        response = requests.get(category_url, headers=headers, timeout=10)
                        if response.status_code == 200:
                            # Parse the page
                            soup = BeautifulSoup(response.text, 'html.parser')
                            
                            # Extract links
                            for link in soup.find_all('a', href=True):
                                href = link['href']
                                
                                # Resolve relative URLs
                                if not href.startswith('http'):
                                    href = urljoin(category_url, href)
                                
                                # Skip URLs that are not from the same domain
                                if allowed_domain not in href:
                                    continue
                                
                                # Check if the URL looks like a recipe
                                if self.url_analyzer.is_likely_recipe_url(href):
                                    recipe_urls.append(href)
                                    
                                    # Stop if we've found enough recipes
                                    if len(recipe_urls) >= max_recipes:
                                        break
                            
                            # If we found recipes, stop trying more category URLs
                            if recipe_urls:
                                break
                                
                    except Exception as e:
                        self.logger.warning(f"Error accessing category URL {category_url}: {str(e)}")
            
            return recipe_urls
            
        except Exception as e:
            self.logger.error(f"Error using crawler: {str(e)}")
            return []
            
        finally:
            # Clean up the temporary file
            if os.path.exists(output_file):
                os.unlink(output_file)

    def _find_recipes_simple(self, url: str, max_urls: int) -> List[str]:
        """
        Find recipe URLs using a simpler approach (without Scrapy).
        
        Args:
            url: URL to search for recipes
            max_urls: Maximum number of recipe URLs to return
            
        Returns:
            List[str]: List of recipe URLs
        """
        recipe_urls = set()
        visited_urls = set()
        
        # Parse the domain from the URL
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        domain = parsed_url.netloc
        
        # List of browser-like User-Agents to rotate
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/119.0.6045.109 Mobile/15E148 Safari/604.1'
        ]
        
        # Try common category paths first
        category_paths = [
            '/recipes',
            '/recipe-index',
            '/diet/gluten-free',
            '/diet/dairy-free',
            '/diet/vegan',
            '/category/desserts',
            '/category/main-dishes',
            '/category/breakfast'
        ]
        
        # List of URLs to try
        urls_to_try = [urljoin(base_url, path) for path in category_paths]
        urls_to_try.append(url)  # Add the original URL as a fallback
        
        for try_url in urls_to_try:
            # Skip if we've already visited this URL
            if try_url in visited_urls:
                continue
                
            visited_urls.add(try_url)
            
            try:
                # Use a random User-Agent and browser-like headers
                headers = {
                    'User-Agent': random.choice(user_agents),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Referer': 'https://www.google.com/',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Cache-Control': 'max-age=0'
                }
                
                # Fetch the page with a timeout
                response = requests.get(try_url, headers=headers, timeout=15)
                
                # If we got a 403 or other error, continue to the next URL
                if response.status_code != 200:
                    self.logger.warning(f"Failed to fetch {try_url}: HTTP {response.status_code}")
                    continue
                
                # Parse the page
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract all links
                links = []
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    
                    # Resolve relative URLs
                    if not href.startswith('http'):
                        href = urljoin(try_url, href)
                    
                    # Skip URLs that are not from the same domain
                    parsed_href = urlparse(href)
                    if parsed_href.netloc != domain:
                        continue
                    
                    links.append(href)
                
                # Analyze the URLs
                for link in links:
                    # Skip if we've found enough recipes
                    if len(recipe_urls) >= max_urls:
                        break
                    
                    # Check if the URL looks like a recipe
                    if self.url_analyzer.is_likely_recipe_url(link):
                        recipe_urls.add(link)
                
                # If we found recipes, we can stop trying more URLs
                if len(recipe_urls) >= max_urls:
                    break
                
                # If we didn't find enough recipes, look for category pages
                if len(recipe_urls) < max_urls:
                    category_urls = [link for link in links if self.url_analyzer.is_likely_category_url(link)]
                    
                    for category_url in category_urls[:5]:  # Limit to 5 category pages
                        # Skip if we've already visited this URL
                        if category_url in visited_urls:
                            continue
                            
                        visited_urls.add(category_url)
                        
                        # Skip if we've found enough recipes
                        if len(recipe_urls) >= max_urls:
                            break
                        
                        try:
                            # Add a delay to avoid triggering rate limits
                            time.sleep(random.uniform(2, 4))
                            
                            # Use a different User-Agent for each request
                            cat_headers = headers.copy()
                            cat_headers['User-Agent'] = random.choice(user_agents)
                            
                            # Fetch the category page
                            cat_response = requests.get(category_url, headers=cat_headers, timeout=15)
                            if cat_response.status_code != 200:
                                continue
                            
                            # Parse the category page
                            cat_soup = BeautifulSoup(cat_response.text, 'html.parser')
                            
                            # Extract links from the category page
                            for cat_link in cat_soup.find_all('a', href=True):
                                cat_href = cat_link['href']
                                
                                # Resolve relative URLs
                                if not cat_href.startswith('http'):
                                    cat_href = urljoin(category_url, cat_href)
                                
                                # Skip URLs that are not from the same domain
                                parsed_cat_href = urlparse(cat_href)
                                if parsed_cat_href.netloc != domain:
                                    continue
                                
                                # Check if the URL looks like a recipe
                                if self.url_analyzer.is_likely_recipe_url(cat_href):
                                    recipe_urls.add(cat_href)
                                    
                                    # Stop if we've found enough recipes
                                    if len(recipe_urls) >= max_urls:
                                        break
                        except Exception as e:
                            self.logger.warning(f"Error fetching category page {category_url}: {str(e)}")
                
                # If we found recipes, we can stop trying more URLs
                if len(recipe_urls) >= max_urls:
                    break
                    
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Request error for {try_url}: {str(e)}")
                continue
            except Exception as e:
                self.logger.error(f"Error processing {try_url}: {str(e)}")
                continue
        
        return list(recipe_urls)[:max_urls]

    def verify_recipe_page(self, url: str) -> bool:
        """
        Verify that a URL is actually a recipe page by analyzing its content.
        
        Args:
            url: URL to verify
            
        Returns:
            bool: True if the URL is a recipe page, False otherwise
        """
        try:
            # Fetch the page
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return False
            
            # Analyze the content
            return self.recipe_detector.is_recipe_page(response.text, url)
            
        except Exception as e:
            self.logger.error(f"Error verifying recipe page {url}: {str(e)}")
            return False