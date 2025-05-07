"""
Simple test script for the browser crawler.
This script directly uses the BrowserCrawler class without dependencies on other modules.
"""

import os
import time
import random
import logging
import re
from typing import List, Dict, Set, Optional
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

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
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0'
    ]
    
    # Common category paths to try as alternative entry points
    COMMON_CATEGORY_PATHS = [
        '/diet/gluten-free',
        '/diet/dairy-free',
        '/diet/vegan',
        '/diet/refined-sugar-free',
        '/category/cakes-mini-cakes'
    ]
    
    def __init__(self):
        """Initialize the browser crawler."""
        self.visited_urls = set()
        self.found_recipes = []
    
    def find_recipe_urls(self, start_url: str, max_urls: int = 5) -> List[str]:
        """
        Find recipe URLs on a website using a headless browser.
        
        Args:
            start_url: URL to start crawling from
            max_urls: Maximum number of recipe URLs to return
            
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
            
            # Create a list of URLs to try
            urls_to_try = []
            
            # Add category paths
            for path in self.COMMON_CATEGORY_PATHS:
                category_url = urljoin(base_url, path)
                urls_to_try.append(category_url)
            
            # Add the original URL as a fallback
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
                    
                    # If we've found enough recipes, stop trying more URLs
                    if len(recipe_urls) >= max_urls:
                        break
                
                except Exception as e:
                    logger.warning(f"Error accessing {url} with headless browser: {str(e)}")
            
            return recipe_urls
        
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

# Run the test
if __name__ == "__main__":
    crawler = BrowserCrawler()
    recipes = crawler.find_recipe_urls('https://theloopywhisk.com', max_urls=3)
    print(f'Found recipes: {recipes}')