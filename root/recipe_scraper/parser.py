from typing import Dict, List, Optional, Tuple, Any
from recipe_scrapers import scrape_me
from urllib.parse import urlparse
import re
from .models import Recipe, Ingredient
from .ingredient_parser import IngredientParser


class RecipeParser:
    """
    Parser for extracting recipe information from websites using recipe_scrapers library
    and converting it to our standardized Recipe model.
    """
    
    def __init__(self):
        # Initialize the ingredient parser with the new implementation
        self.ingredient_parser = IngredientParser()
        
        # List of non-English language domains to skip
        self.non_english_domains = [
            # Dutch
            '.nl', '.be', 
            # German
            '.de', '.at', '.ch',
            # French
            '.fr',
            # Spanish
            '.es', '.mx', '.ar', '.co',
            # Italian
            '.it',
            # Portuguese
            '.pt', '.br',
            # Swedish
            '.se',
            # Norwegian
            '.no',
            # Danish
            '.dk',
            # Finnish
            '.fi',
            # Polish
            '.pl',
            # Czech
            '.cz',
            # Hungarian
            '.hu',
            # Russian
            '.ru',
            # Turkish
            '.tr',
            # Greek
            '.gr',
            # Japanese
            '.jp',
            # Korean
            '.kr',
            # Chinese
            '.cn', '.tw', '.hk',
            # Thai
            '.th',
            # Vietnamese
            '.vn'
        ]
        
        # List of non-English language keywords in URLs
        self.non_english_keywords = [
            # Dutch
            'recepten', 'koken', 'eten',
            # German
            'rezepte', 'kochen', 'essen',
            # French
            'recettes', 'cuisine', 'manger',
            # Spanish
            'recetas', 'cocina', 'comer',
            # Italian
            'ricette', 'cucina', 'mangiare',
            # Portuguese
            'receitas', 'cozinha', 'comer'
        ]
    
    def is_english_site(self, url: str) -> bool:
        """
        Check if a URL is likely to be an English language site.
        
        Args:
            url: URL to check
            
        Returns:
            bool: True if the site is likely in English, False otherwise
        """
        # Parse the URL to get the domain
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        path = parsed_url.path.lower()
        
        # Check for non-English TLDs
        for tld in self.non_english_domains:
            if domain.endswith(tld):
                return False
        
        # Check for non-English keywords in the domain or path
        for keyword in self.non_english_keywords:
            if keyword in domain or keyword in path:
                return False
        
        # Default to assuming it's English
        return True
    
    def parse_url(self, url: str) -> Recipe:
        """
        Parse a recipe from a URL using recipe_scrapers library.
        
        Args:
            url: URL of the recipe to parse
            
        Returns:
            Recipe: Standardized recipe object
        """
        # Skip non-English sites
        if not self.is_english_site(url):
            raise ValueError(f"Skipping non-English site: {url}")
        
        try:
            scraper = scrape_me(url)
            
            # Extract ingredients and parse them into our format
            raw_ingredients = scraper.ingredients()
            parsed_ingredients = [self._parse_ingredient(ing) for ing in raw_ingredients]
            
            # Create the recipe object
            recipe = Recipe(
                url=url,
                title=scraper.title(),
                total_time=scraper.total_time(),
                yields=scraper.yields(),
                ingredients=parsed_ingredients,
                instructions=scraper.instructions(),
                image=scraper.image() if scraper.image() else None,
                host=urlparse(url).netloc,
                nutrients=scraper.nutrients()
            )
            
            return recipe
        except Exception as e:
            raise ValueError(f"Failed to parse recipe from {url}: {str(e)}")
    
    def _parse_ingredient(self, ingredient_text: str) -> Ingredient:
        """
        Parse an ingredient string into our standardized Ingredient model.
        
        Args:
            ingredient_text: Raw ingredient text from the recipe
            
        Returns:
            Ingredient: Parsed ingredient with name, measurement, and unit type
        """
        try:
            # Use the advanced ingredient parser
            name, measurement, unit_type = self.ingredient_parser.parse_ingredient(ingredient_text)
            
            return Ingredient(
                name=name,
                measurement=measurement,
                unit_type=unit_type
            )
        except Exception as e:
            # Fallback to a simple parsing if the advanced parser fails
            print(f"Warning: Advanced ingredient parsing failed for '{ingredient_text}': {str(e)}")
            return Ingredient(
                name=ingredient_text,
                measurement=None,
                unit_type=None
            )