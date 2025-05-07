"""
Recipe Spider module for crawling websites to find recipes.
"""

import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from urllib.parse import urlparse, urljoin
import re
import logging
import random
from typing import Dict, List, Set, Optional

from ..url_analyzer import URLAnalyzer
from ..recipe_detector import RecipeDetector


class RecipeSpider(CrawlSpider):
    """
    Scrapy spider for crawling websites to find recipes.
    Uses intelligent URL analysis and content detection to find recipe pages.
    """
    
    name = 'recipe_spider'
    
    # Common browser User-Agents
    BROWSER_USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/119.0.6045.109 Mobile/15E148 Safari/604.1'
    ]
    
    # Common browser headers
    BROWSER_HEADERS = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.google.com/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    
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
        '/cuisine/italian',
        '/cuisine/mexican',
        '/cuisine/asian',
        '/cuisine/indian',
        '/course/main-dishes',
        '/course/desserts',
        '/course/appetizers',
        '/course/sides',
        '/course/breakfast',
        '/meal/dinner',
        '/meal/lunch',
        '/meal/breakfast',
        '/meal/snacks'
    ]
    
    def __init__(self, start_url=None, allowed_domains=None, max_recipes=5, 
                 max_depth=3, *args, **kwargs):
        """
        Initialize the recipe spider.
        
        Args:
            start_url: URL to start crawling from
            allowed_domains: List of domains to restrict crawling to
            max_recipes: Maximum number of recipes to find
            max_depth: Maximum depth to crawl
        """
        super(RecipeSpider, self).__init__(*args, **kwargs)
        
        # Set up the start URL and allowed domains
        if start_url:
            self.start_urls = [start_url]
            
            # Extract domain from start_url if allowed_domains not provided
            if not allowed_domains:
                parsed_url = urlparse(start_url)
                domain = parsed_url.netloc
                self.allowed_domains = [domain]
            else:
                self.allowed_domains = allowed_domains
        
        # Initialize URL analyzer and recipe detector
        self.url_analyzer = URLAnalyzer()
        self.recipe_detector = RecipeDetector()
        
        # Set up crawling parameters
        self.max_recipes = int(max_recipes)
        self.max_depth = int(max_depth)
        
        # Track found recipes and visited URLs
        self.found_recipes = []
        self.visited_urls = set()
        self.category_urls = set()
        self.failed_urls = set()
        
        # Set up rules for following links
        self.rules = (
            # Rule for recipe pages - don't follow links from recipe pages
            Rule(
                LinkExtractor(),
                callback='parse_page',
                follow=True,
                process_links='process_links',
                cb_kwargs={'depth': 0}
            ),
        )
        
        # Initialize the rules
        self._compile_rules()
    
    def process_links(self, links):
        """
        Process and filter links before following them.
        
        Args:
            links: List of scrapy.Link objects
            
        Returns:
            List of filtered links
        """
        filtered_links = []
        
        for link in links:
            # Skip already visited URLs
            if link.url in self.visited_urls:
                continue
            
            # Analyze the URL
            analysis = self.url_analyzer.analyze_url(link.url)
            
            # Always include recipe and category URLs
            if analysis['type'] == 'recipe':
                filtered_links.append(link)
            elif analysis['type'] == 'category':
                self.category_urls.add(link.url)
                filtered_links.append(link)
            elif analysis['type'] != 'exclude':
                # For other URLs, include them but with lower priority
                filtered_links.append(link)
            
            # Stop if we've found enough recipes
            if len(self.found_recipes) >= self.max_recipes:
                return []
        
        return filtered_links
    
    def parse_page(self, response, depth=0):
        """
        Parse a page to determine if it's a recipe and extract links.
        
        Args:
            response: Scrapy response object
            depth: Current crawl depth
        """
        url = response.url
        self.visited_urls.add(url)
        
        # Skip if we've found enough recipes
        if len(self.found_recipes) >= self.max_recipes:
            return
        
        # Skip if we've reached max depth
        if depth > self.max_depth:
            return
        
        # Check if we got a 403 or other error status
        if response.status in [403, 429, 500, 502, 503, 504]:
            self.logger.warning(f"Received status {response.status} for {url}")
            self.failed_urls.add(url)
            return
        
        # Analyze the URL
        url_analysis = self.url_analyzer.analyze_url(url)
        
        # If the URL looks like a recipe, check the content
        if url_analysis['type'] == 'recipe' or url in self.category_urls:
            # Analyze the content
            content_analysis = self.recipe_detector.analyze_content(response.text, url)
            
            # If it's a recipe, add it to the found recipes
            if content_analysis['is_recipe']:
                recipe_info = {
                    'url': url,
                    'title': self._extract_title(response),
                    'url_score': url_analysis['score'],
                    'content_score': content_analysis['confidence'],
                    'features': content_analysis['features']
                }
                
                self.found_recipes.append(recipe_info)
                self.logger.info(f"Found recipe: {recipe_info['title']} ({url})")
                
                # Yield the recipe
                yield {
                    'type': 'recipe',
                    'url': url,
                    'title': recipe_info['title'],
                    'confidence': content_analysis['confidence']
                }
                
                # Stop if we've found enough recipes
                if len(self.found_recipes) >= self.max_recipes:
                    return
        
        # Extract and follow links
        links = LinkExtractor().extract_links(response)
        filtered_links = self.process_links(links)
        
        # Follow links with priority based on their type
        for link in filtered_links:
            # Skip if we've found enough recipes
            if len(self.found_recipes) >= self.max_recipes:
                break
                
            # Skip already visited URLs
            if link.url in self.visited_urls or link.url in self.failed_urls:
                continue
                
            # Analyze the URL
            analysis = self.url_analyzer.analyze_url(link.url)
            
            # Select a random User-Agent for each request
            headers = self.BROWSER_HEADERS.copy()
            headers['User-Agent'] = random.choice(self.BROWSER_USER_AGENTS)
            
            # Prioritize recipe and category URLs
            if analysis['type'] == 'recipe':
                yield scrapy.Request(
                    link.url, 
                    headers=headers,
                    callback=self.parse_page,
                    errback=self.handle_error,
                    cb_kwargs={'depth': depth + 1},
                    priority=2,  # Higher priority
                    meta={'dont_redirect': False, 'handle_httpstatus_list': [403, 404, 429, 500, 502, 503, 504]}
                )
            elif analysis['type'] == 'category':
                self.category_urls.add(link.url)
                yield scrapy.Request(
                    link.url, 
                    headers=headers,
                    callback=self.parse_page,
                    errback=self.handle_error,
                    cb_kwargs={'depth': depth + 1},
                    priority=1,  # Medium priority
                    meta={'dont_redirect': False, 'handle_httpstatus_list': [403, 404, 429, 500, 502, 503, 504]}
                )
            elif analysis['type'] != 'exclude':
                # Follow other URLs with lower priority
                yield scrapy.Request(
                    link.url, 
                    headers=headers,
                    callback=self.parse_page,
                    errback=self.handle_error,
                    cb_kwargs={'depth': depth + 1},
                    priority=0,  # Lower priority
                    meta={'dont_redirect': False, 'handle_httpstatus_list': [403, 404, 429, 500, 502, 503, 504]}
                )
    
    def start_requests(self):
        """
        Start requests with browser-like headers and handle potential 403 errors
        by trying alternative entry points.
        """
        # Select a random User-Agent
        user_agent = random.choice(self.BROWSER_USER_AGENTS)
        headers = self.BROWSER_HEADERS.copy()
        headers['User-Agent'] = user_agent
        
        # Try the main URL first
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                headers=headers,
                callback=self.parse,
                errback=self.handle_error,
                meta={'dont_redirect': False, 'handle_httpstatus_list': [403, 404, 429, 500, 502, 503, 504]}
            )
    
    def handle_error(self, failure):
        """
        Handle request errors, particularly 403 Forbidden errors,
        by trying alternative entry points.
        """
        # Get the original request
        request = failure.request
        
        # Log the error
        self.logger.error(f"Request to {request.url} failed: {failure.value}")
        
        # Add to failed URLs
        self.failed_urls.add(request.url)
        
        # If this is the main domain and we haven't tried alternative entry points yet
        if request.url in self.start_urls:
            # Extract the base URL
            parsed_url = urlparse(request.url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Try alternative category paths
            self.logger.info(f"Trying alternative entry points for {base_url}")
            
            # Select a random User-Agent for each request to avoid detection
            headers = self.BROWSER_HEADERS.copy()
            
            # Try each common category path
            for path in self.COMMON_CATEGORY_PATHS:
                # Skip if we've found enough recipes
                if len(self.found_recipes) >= self.max_recipes:
                    break
                    
                # Create the full URL
                category_url = urljoin(base_url, path)
                
                # Skip if we've already tried this URL
                if category_url in self.failed_urls or category_url in self.visited_urls:
                    continue
                
                # Use a new random User-Agent for each request
                headers['User-Agent'] = random.choice(self.BROWSER_USER_AGENTS)
                
                # Try the category URL
                yield scrapy.Request(
                    url=category_url,
                    headers=headers,
                    callback=self.parse,
                    errback=self.handle_error,
                    meta={'dont_redirect': False, 'handle_httpstatus_list': [403, 404, 429, 500, 502, 503, 504]},
                    dont_filter=True  # Important to bypass the duplicate filter
                )
    
    def parse(self, response):
        """
        Default parse method required by CrawlSpider.
        
        This will be called for the initial response if no rule matches.
        """
        # Just delegate to parse_page with depth=0
        yield from self.parse_page(response, depth=0)
    
    def _extract_title(self, response):
        """Extract the title from a page."""
        # Try to get the title from the og:title meta tag
        og_title = response.css('meta[property="og:title"]::attr(content)').get()
        if og_title:
            return og_title.strip()
        
        # Try to get the title from the title tag
        title = response.css('title::text').get()
        if title:
            return title.strip()
        
        # Try to get the title from the first h1 tag
        h1 = response.css('h1::text').get()
        if h1:
            return h1.strip()
        
        # Default to the URL
        return urlparse(response.url).path