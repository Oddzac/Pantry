import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from urllib.parse import urlparse
import re
from .parser import RecipeParser


class RecipeSpider(CrawlSpider):
    """
    Scrapy spider for crawling recipe websites and extracting recipe information.
    """
    name = 'recipe_spider'
    
    # These rules can be customized based on the specific websites you want to crawl
    rules = (
        # Follow links that look like recipe pages
        Rule(LinkExtractor(allow=r'recipe|recipes|cook|bake|food'), callback='parse_recipe', follow=True),
    )
    
    def __init__(self, *args, **kwargs):
        """Initialize the spider with a RecipeParser."""
        super(RecipeSpider, self).__init__(*args, **kwargs)
        self.parser = RecipeParser()
        
        # Default allowed domains if none provided
        if not hasattr(self, 'allowed_domains'):
            self.allowed_domains = []
        
        # Default start URLs if none provided
        if not hasattr(self, 'start_urls'):
            self.start_urls = []
    
    def start_requests(self):
        """Generate initial requests for the spider."""
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.parse)
    
    def parse_recipe(self, response):
        """
        Parse a potential recipe page.
        
        Args:
            response: Scrapy response object
            
        Returns:
            dict: Recipe data if the page contains a recipe, None otherwise
        """
        url = response.url
        
        # Check if the page is likely to contain a recipe
        if self._is_recipe_page(response):
            try:
                recipe = self.parser.parse_url(url)
                return recipe.dict()
            except Exception as e:
                self.logger.error(f"Failed to parse recipe from {url}: {str(e)}")
        
        return None
    
    def _is_recipe_page(self, response):
        """
        Determine if a page is likely to contain a recipe.
        
        Args:
            response: Scrapy response object
            
        Returns:
            bool: True if the page likely contains a recipe, False otherwise
        """
        # Check for common recipe page indicators
        indicators = [
            # Check for recipe schema markup
            response.xpath('//script[@type="application/ld+json"][contains(text(), "Recipe")]'),
            
            # Check for common recipe page elements
            response.xpath('//h1[contains(@class, "recipe-title")]'),
            response.xpath('//div[contains(@class, "recipe")]'),
            response.xpath('//div[contains(@class, "ingredients")]'),
            response.xpath('//div[contains(@class, "instructions")]'),
            
            # Check for common recipe terms in the title
            response.xpath('//title[contains(text(), "recipe") or contains(text(), "Recipe")]'),
            
            # Check for ingredient lists
            response.css('ul.ingredients'),
            response.css('ol.instructions'),
        ]
        
        # If any indicators are found, consider it a recipe page
        return any(indicators)