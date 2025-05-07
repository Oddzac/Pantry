"""
Browser-based crawler for accessing websites that block traditional crawlers.
Uses a headless browser to emulate a real user browsing the site.
"""

import os
import time
import random
import logging
import re
from typing import List, Dict, Set, Optional
from urllib.parse import urlparse, urljoin

from .url_analyzer import URLAnalyzer
from .recipe_detector import RecipeDetector

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class BrowserCrawler:
    """
    Browser-based crawler for accessing websites that block traditional crawlers.
    Uses Selenium with a headless browser to emulate a real user.
    """
    
    # Common browser User-Agents
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/119.0.6045.109 Mobile/15E148 Safari/604.1'
    ]
    
    # Common category paths to try as alternative entry points
    COMMON_CATEGORY_PATHS = [
        '/recipes',
        '/recipe-index',
        '/diet/gluten-free',
        '/diet/dairy-free',
        '/diet/vegan',
        '/diet/vegetarian',
        '/category/desserts',
        '/category/main-dishes',
        '/category/breakfast',
        '/category/dinner',
        '/category/lunch',
        '/category/appetizers',
        '/category/snacks',
        '/category/drinks',
        '/category/baking',
        '/category/cakes-mini-cakes',  # Added for theloopywhisk.com
        '/diet/refined-sugar-free'      # Added for theloopywhisk.com
    ]
    
    def __init__(self):
        """Initialize the browser crawler."""
        self.url_analyzer = URLAnalyzer()
        self.recipe_detector = RecipeDetector()
        self.visited_urls = set()
        self.found_recipes = []
    
    def find_recipe_urls(self, start_url: str, max_urls: int = 5, max_depth: int = 2) -> List[str]:
        """
        Find recipe URLs on a website using a headless browser.
        
        Args:
            start_url: URL to start crawling from
            max_urls: Maximum number of recipe URLs to return
            max_depth: Maximum depth to crawl
            
        Returns:
            List[str]: List of recipe URLs
        """
        try:
            # Import Selenium components
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # Try to use webdriver_manager if available
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                driver_path = ChromeDriverManager().install()
            except ImportError:
                # Fall back to expecting chromedriver in PATH
                driver_path = None
                logger.warning("webdriver_manager not installed, using system chromedriver")
            
            # Set up Chrome options
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            # Set a random user agent
            user_agent = random.choice(self.USER_AGENTS)
            options.add_argument(f"user-agent={user_agent}")
            
            # Add fingerprint evasion options
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Initialize the Chrome driver
            if driver_path:
                service = Service(driver_path)
                driver = webdriver.Chrome(service=service, options=options)
            else:
                driver = webdriver.Chrome(options=options)
            
            # Set window size to a common desktop resolution
            driver.set_window_size(1920, 1080)
            
            # Parse the domain from the start URL
            parsed_url = urlparse(start_url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            domain = parsed_url.netloc
            
            # Special handling for theloopywhisk.com
            is_loopywhisk = 'theloopywhisk.com' in domain
            
            # Create a list of URLs to try
            urls_to_try = []
            
            # For theloopywhisk.com, prioritize category pages
            if is_loopywhisk:
                logger.info("Detected theloopywhisk.com, using specialized approach")
                # Add category paths that are known to work for this site
                for path in ['/diet/gluten-free', '/diet/dairy-free', '/diet/vegan', 
                             '/diet/refined-sugar-free', '/category/cakes-mini-cakes']:
                    category_url = urljoin(base_url, path)
                    urls_to_try.append(category_url)
            
            # Add common category paths for all sites
            for path in self.COMMON_CATEGORY_PATHS:
                category_url = urljoin(base_url, path)
                if category_url not in urls_to_try:  # Avoid duplicates
                    urls_to_try.append(category_url)
            
            # Add the original URL as a fallback
            if start_url not in urls_to_try:
                urls_to_try.append(start_url)
            
            # Try each URL until we find recipes
            recipe_urls = []
            
            for url in urls_to_try:
                if len(recipe_urls) >= max_urls:
                    break
                
                try:
                    logger.info(f"Trying to access {url} with headless browser")
                    
                    # Navigate to the URL
                    driver.get(url)
                    
                    # Wait for the page to load
                    time.sleep(3)
                    
                    # Execute JavaScript to scroll down the page
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 3);")
                    time.sleep(1)
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
                    time.sleep(1)
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
                    
                    # Get the page source
                    page_source = driver.page_source
                    
                    # Check if the page contains a recipe
                    if self.recipe_detector.is_recipe_page(page_source, url):
                        logger.info(f"Found recipe page: {url}")
                        recipe_urls.append(url)
                    
                    # Special handling for category pages
                    if '/category/' in url or '/diet/' in url:
                        logger.info(f"Processing category page: {url}")
                        
                        # For theloopywhisk.com, look for specific patterns in links
                        if is_loopywhisk:
                            # Extract all links
                            all_links = []
                            elements = driver.find_elements(By.TAG_NAME, "a")
                            for element in elements:
                                try:
                                    href = element.get_attribute("href")
                                    if href and href.startswith("http"):
                                        # Only include links from the same domain
                                        parsed_href = urlparse(href)
                                        if parsed_href.netloc == domain:
                                            all_links.append(href)
                                except Exception as e:
                                    logger.debug(f"Error extracting link: {str(e)}")
                            
                            # Look for date-based URLs which are typical for theloopywhisk.com recipes
                            for link in all_links:
                                parsed_link = urlparse(link)
                                path = parsed_link.path.lower()
                                
                                # Their recipe URLs typically follow the pattern /YYYY/MM/DD/recipe-name/
                                date_pattern = r'/\d{4}/\d{2}/\d{2}/[a-z0-9-]+/?$'
                                if re.search(date_pattern, path) and link not in recipe_urls:
                                    logger.info(f"Found recipe with date pattern: {link}")
                                    recipe_urls.append(link)
                                    if len(recipe_urls) >= max_urls:
                                        break
                            
                            # If we still need more recipes, look for article elements
                            if len(recipe_urls) < max_urls:
                                # Look for article elements which typically contain recipes
                                articles = driver.find_elements(By.TAG_NAME, "article")
                                for article in articles:
                                    try:
                                        # Find the link within this article
                                        link_element = article.find_element(By.TAG_NAME, "a")
                                        href = link_element.get_attribute("href")
                                        if href and href.startswith("http"):
                                            parsed_href = urlparse(href)
                                            if parsed_href.netloc == domain and href not in recipe_urls:
                                                logger.info(f"Found recipe link in article: {href}")
                                                recipe_urls.append(href)
                                                if len(recipe_urls) >= max_urls:
                                                    break
                                    except Exception as e:
                                        logger.debug(f"Error extracting article link: {str(e)}")
                        else:
                            # Standard approach for other sites
                            # Extract all links
                            links = []
                            elements = driver.find_elements(By.TAG_NAME, "a")
                            for element in elements:
                                try:
                                    href = element.get_attribute("href")
                                    if href and href.startswith("http"):
                                        # Only include links from the same domain
                                        parsed_href = urlparse(href)
                                        if parsed_href.netloc == domain:
                                            links.append(href)
                                except Exception as e:
                                    logger.debug(f"Error extracting link: {str(e)}")
                            
                            # Analyze the links
                            categorized_links = self.url_analyzer.categorize_urls(links)
                            
                            # Add recipe URLs
                            for recipe_url in categorized_links['recipe_urls']:
                                if recipe_url not in recipe_urls:
                                    recipe_urls.append(recipe_url)
                                    logger.info(f"Added recipe URL: {recipe_url}")
                                    if len(recipe_urls) >= max_urls:
                                        break
                    
                    # If we've found enough recipes, stop trying more URLs
                    if len(recipe_urls) >= max_urls:
                        break
                
                except Exception as e:
                    logger.warning(f"Error accessing {url} with headless browser: {str(e)}")
            
            # Verify each recipe URL by visiting the page
            verified_recipes = []
            for url in recipe_urls[:max_urls]:
                try:
                    logger.info(f"Verifying recipe page: {url}")
                    
                    # For theloopywhisk.com, trust the URL pattern without verification
                    if is_loopywhisk and re.search(r'/\d{4}/\d{2}/\d{2}/[a-z0-9-]+/?$', urlparse(url).path.lower()):
                        logger.info(f"Accepting theloopywhisk.com recipe based on URL pattern: {url}")
                        verified_recipes.append(url)
                        continue
                    
                    # Navigate to the URL
                    driver.get(url)
                    
                    # Wait for the page to load
                    time.sleep(3)
                    
                    # Get the page source
                    page_source = driver.page_source
                    
                    # Check if the page contains a recipe
                    if self.recipe_detector.is_recipe_page(page_source, url):
                        logger.info(f"Verified recipe page: {url}")
                        verified_recipes.append(url)
                    else:
                        logger.info(f"Not a recipe page: {url}")
                
                except Exception as e:
                    logger.warning(f"Error verifying recipe page {url}: {str(e)}")
            
            return verified_recipes
        
        except ImportError as e:
            logger.error(f"Selenium not installed or missing dependencies: {str(e)}")
            logger.error("Please install Selenium: pip install selenium webdriver-manager")
            return []
        
        except Exception as e:
            logger.error(f"Error using headless browser: {str(e)}")
            return []
        
        finally:
            # Close the browser
            if 'driver' in locals():
                driver.quit()
    
    def get_recipe_content(self, url: str) -> Optional[Dict]:
        """
        Get the content of a recipe page using a headless browser.
        
        Args:
            url: URL of the recipe page
            
        Returns:
            Optional[Dict]: Recipe content or None if not found
        """
        try:
            # Import Selenium components
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            
            # Try to use webdriver_manager if available
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                driver_path = ChromeDriverManager().install()
            except ImportError:
                # Fall back to expecting chromedriver in PATH
                driver_path = None
            
            # Set up Chrome options
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            # Set a random user agent
            user_agent = random.choice(self.USER_AGENTS)
            options.add_argument(f"user-agent={user_agent}")
            
            # Add fingerprint evasion options
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Initialize the Chrome driver
            if driver_path:
                service = Service(driver_path)
                driver = webdriver.Chrome(service=service, options=options)
            else:
                driver = webdriver.Chrome(options=options)
            
            # Set window size to a common desktop resolution
            driver.set_window_size(1920, 1080)
            
            try:
                logger.info(f"Accessing recipe page: {url}")
                
                # Navigate to the URL
                driver.get(url)
                
                # Wait for the page to load
                time.sleep(3)
                
                # Get the page source
                page_source = driver.page_source
                
                # Extract recipe information
                # This is a simplified version - you would need to implement
                # more sophisticated extraction based on your needs
                title = driver.title
                
                # Look for recipe structured data
                structured_data = driver.execute_script("""
                    var jsonld = document.querySelector('script[type="application/ld+json"]');
                    if (jsonld) {
                        try {
                            return JSON.parse(jsonld.textContent);
                        } catch (e) {
                            return null;
                        }
                    }
                    return null;
                """)
                
                # Return the recipe content
                return {
                    'url': url,
                    'title': title,
                    'structured_data': structured_data,
                    'html': page_source
                }
            
            except Exception as e:
                logger.error(f"Error accessing recipe page {url}: {str(e)}")
                return None
            
        except ImportError:
            logger.error("Selenium not installed or missing dependencies")
            logger.error("Please install Selenium: pip install selenium webdriver-manager")
            return None
        
        except Exception as e:
            logger.error(f"Error using headless browser: {str(e)}")
            return None
        
        finally:
            # Close the browser
            if 'driver' in locals():
                driver.quit()