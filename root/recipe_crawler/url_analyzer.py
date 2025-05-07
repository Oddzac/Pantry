"""
URL Analyzer module for analyzing and categorizing URLs in recipe websites.
"""

import re
from urllib.parse import urlparse, urljoin
from typing import Dict, List, Set, Tuple, Optional


class URLAnalyzer:
    """
    Analyzes URLs to determine if they are likely recipe pages, category pages, or other types.
    Provides pattern recognition for different URL structures commonly found in recipe websites.
    """

    def __init__(self):
        """Initialize the URL analyzer with pattern definitions."""
        # Patterns that indicate a URL is likely a recipe page
        self.recipe_patterns = [
            # Date-based patterns (common in blogs)
            r'/\d{4}/\d{2}/\d{2}/[a-z0-9-]+/?$',  # /2023/05/15/recipe-name/
            r'/\d{4}/\d{2}/[a-z0-9-]+/?$',        # /2023/05/recipe-name/
            r'/\d{4}/[a-z0-9-]+/?$',              # /2023/recipe-name/
            
            # Recipe name patterns with multiple segments
            r'/[a-z0-9-]+-[a-z0-9-]+-[a-z0-9-]+/?$',  # /chicken-parmesan-recipe/
            
            # Recipe with ID patterns
            r'/recipes?/\d+/[a-z0-9-]+/?$',       # /recipe/12345/recipe-name/
            r'/recipes?/[a-z0-9-]+/\d+/?$',       # /recipe/recipe-name/12345/
            
            # Common recipe path patterns
            r'/recipes?/[a-z0-9-]+/?$',           # /recipe/recipe-name/
            r'/[a-z0-9-]+/recipes?/[a-z0-9-]+/?$', # /category/recipe/recipe-name/
        ]
        
        # Keywords that suggest a URL points to a recipe
        self.recipe_keywords = [
            'recipe', 'dish', 'meal', 'cake', 'bread', 'stew', 'roast', 'bake',
            'cook', 'food', 'dinner', 'lunch', 'breakfast', 'dessert', 'appetizer',
            'snack', 'drink', 'cocktail', 'smoothie', 'soup', 'salad', 'sandwich',
            'pasta', 'pizza', 'pie', 'cookie', 'muffin', 'brownie', 'chicken', 'beef',
            'pork', 'fish', 'vegetarian', 'vegan', 'gluten-free', 'dairy-free', 'low-carb',
            'nut-free', 'sugar-free', 'healthy', 'quick', 'easy', 'simple', 'traditional',
            'authentic', 'homemade', 'from-scratch', 'slow-cooker', 'instant-pot',
            'pressure-cooker', 'grill', 'barbecue', 'smoke', 'roast', 'fry', 'sauté',
            'steam', 'boil', 'bake', 'broil', 'microwave', 'oven', 'stovetop',
            'casserole', 'stew', 'soup', 'salad', 'sandwich', 'wrap', 'taco', 'burrito',
            'sushi', 'sashimi', 'poke', 'ceviche', 'tartare', 'carpaccio', 'charcuterie',
            'platter', 'board', 'dip', 'spread', 'sauce', 'condiment', 'marinade'
        ]
        
        # Patterns that indicate a URL is likely a category page
        self.category_patterns = [
            # Common category page patterns
            r'/category/[a-z0-9-]+/?$',           # /category/desserts/
            r'/categories/[a-z0-9-]+/?$',         # /categories/desserts/
            r'/recipes/category/[a-z0-9-]+/?$',   # /recipes/category/desserts/
            r'/[a-z0-9-]+-recipes/?$',            # /dessert-recipes/
            r'/diet/[a-z0-9-]+/?$',               # /diet/gluten-free/
            r'/cuisine/[a-z0-9-]+/?$',            # /cuisine/italian/
            r'/course/[a-z0-9-]+/?$',             # /course/main-dishes/
            r'/meal/[a-z0-9-]+/?$',               # /meal/dinner/
            r'/recipes/?$',                        # /recipes/
            r'/recipe-index/?$',                   # /recipe-index/
        ]
        
        # Patterns that indicate a URL should be excluded
        self.exclude_patterns = [
            # Media files
            r'\.(jpg|jpeg|png|gif|pdf|zip|mp3|mp4)$',
            
            # Common non-recipe pages
            r'/about/?$', r'/contact/?$', r'/privacy/?$', r'/terms/?$',
            r'/search/?$', r'/tag/[a-z0-9-]+/?$', r'/author/[a-z0-9-]+/?$',
            r'/page/\d+/?$', r'/comment-page-\d+/?$', r'/trackback/?$',
            r'/feed/?$', r'/wp-content/', r'/wp-admin/', r'/wp-includes/',
            r'/cdn-cgi/', r'/wp-json/', r'/xmlrpc.php', r'/wp-login.php',
            
            # Shopping and account pages
            r'/cart/?$', r'/checkout/?$', r'/account/?$', r'/login/?$',
            r'/register/?$', r'/my-account/?$', r'/shop/?$', r'/store/?$',
            
            # Social media and sharing
            r'/share/?$', r'/print/?$', r'/email/?$', r'/subscribe/?$',
            r'/newsletter/?$', r'/follow/?$',
            
            # Archive pages
            r'/\d{4}/\d{2}/?$',  # /2023/05/
            r'/\d{4}/?$',        # /2023/
        ]

    def analyze_url(self, url: str) -> Dict[str, any]:
        """
        Analyze a URL to determine its type and characteristics.
        
        Args:
            url: The URL to analyze
            
        Returns:
            Dict with analysis results including:
                - type: 'recipe', 'category', 'exclude', or 'unknown'
                - score: Confidence score (0-100)
                - features: List of detected features
        """
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        
        # Initialize result
        result = {
            'url': url,
            'type': 'unknown',
            'score': 0,
            'features': []
        }
        
        # Check exclude patterns first
        for pattern in self.exclude_patterns:
            if re.search(pattern, path):
                result['type'] = 'exclude'
                result['score'] = 100
                result['features'].append(f"matched_exclude_pattern:{pattern}")
                return result
        
        # Check recipe patterns
        recipe_score = 0
        for pattern in self.recipe_patterns:
            if re.search(pattern, path):
                recipe_score += 40
                result['features'].append(f"matched_recipe_pattern:{pattern}")
                break
        
        # Check for recipe keywords in the path
        path_segments = path.strip('/').split('/')
        if path_segments:
            last_segment = path_segments[-1]
            keyword_count = 0
            for keyword in self.recipe_keywords:
                if keyword in last_segment:
                    keyword_count += 1
                    result['features'].append(f"recipe_keyword:{keyword}")
            
            if keyword_count > 0:
                recipe_score += min(30, keyword_count * 10)
        
        # Check category patterns
        category_score = 0
        for pattern in self.category_patterns:
            if re.search(pattern, path):
                category_score += 40
                result['features'].append(f"matched_category_pattern:{pattern}")
                break
        
        # Determine the URL type based on scores
        if recipe_score > category_score and recipe_score >= 30:
            result['type'] = 'recipe'
            result['score'] = recipe_score
        elif category_score > 0:
            result['type'] = 'category'
            result['score'] = category_score
        
        # Additional heuristics for date-based blog URLs
        date_pattern = r'/(\d{4})/(\d{2})(?:/(\d{2}))?/[a-z0-9-]+/?$'
        date_match = re.search(date_pattern, path)
        if date_match:
            result['type'] = 'recipe'  # Date-based URLs are very likely to be recipes
            result['score'] = max(result['score'], 70)
            result['features'].append("date_based_url")
            
            # Extract date components
            year = date_match.group(1)
            month = date_match.group(2)
            day = date_match.group(3) if date_match.group(3) else None
            
            result['date'] = {
                'year': year,
                'month': month,
                'day': day
            }
        
        return result

    def is_likely_recipe_url(self, url: str) -> bool:
        """
        Check if a URL is likely to be a recipe.
        
        Args:
            url: URL to check
            
        Returns:
            bool: True if the URL is likely a recipe, False otherwise
        """
        analysis = self.analyze_url(url)
        return analysis['type'] == 'recipe' and analysis['score'] >= 30

    def is_likely_category_url(self, url: str) -> bool:
        """
        Check if a URL is likely to be a category page.
        
        Args:
            url: URL to check
            
        Returns:
            bool: True if the URL is likely a category page, False otherwise
        """
        analysis = self.analyze_url(url)
        return analysis['type'] == 'category' and analysis['score'] >= 30

    def should_exclude_url(self, url: str) -> bool:
        """
        Check if a URL should be excluded from crawling.
        
        Args:
            url: URL to check
            
        Returns:
            bool: True if the URL should be excluded, False otherwise
        """
        analysis = self.analyze_url(url)
        return analysis['type'] == 'exclude'

    def categorize_urls(self, urls: List[str]) -> Dict[str, List[str]]:
        """
        Categorize a list of URLs into recipe, category, and other types.
        
        Args:
            urls: List of URLs to categorize
            
        Returns:
            Dict with categorized URLs:
                - recipe_urls: List of likely recipe URLs
                - category_urls: List of likely category URLs
                - other_urls: List of other URLs
        """
        result = {
            'recipe_urls': [],
            'category_urls': [],
            'other_urls': []
        }
        
        for url in urls:
            analysis = self.analyze_url(url)
            if analysis['type'] == 'recipe':
                result['recipe_urls'].append(url)
            elif analysis['type'] == 'category':
                result['category_urls'].append(url)
            elif analysis['type'] != 'exclude':
                result['other_urls'].append(url)
        
        return result