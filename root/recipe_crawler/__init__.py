"""
Recipe Crawler package for finding and extracting recipes from websites.
"""

from .recipe_finder import RecipeFinder
from .recipe_detector import RecipeDetector
from .url_analyzer import URLAnalyzer
try:
    from .browser_crawler import BrowserCrawler
    __all__ = ['RecipeFinder', 'RecipeDetector', 'URLAnalyzer', 'BrowserCrawler']
except ImportError:
    # Selenium not installed
    __all__ = ['RecipeFinder', 'RecipeDetector', 'URLAnalyzer']