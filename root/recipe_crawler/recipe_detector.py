"""
Recipe Detector module for analyzing page content to determine if it contains a recipe.
"""

import re
from typing import Dict, List, Set, Tuple, Optional
from bs4 import BeautifulSoup


class RecipeDetector:
    """
    Analyzes page content to determine if it contains a recipe.
    Uses multiple heuristics to identify recipe pages based on their content.
    """

    def __init__(self):
        """Initialize the recipe detector with content patterns."""
        # Common recipe section headings
        self.recipe_headings = [
            'ingredients', 'directions', 'instructions', 'method', 'preparation',
            'steps', 'how to make', 'what you need', 'recipe', 'nutrition',
            'cook time', 'prep time', 'total time', 'servings', 'yield'
        ]
        
        # Common ingredient list markers
        self.ingredient_markers = [
            'cup', 'cups', 'tablespoon', 'tablespoons', 'tbsp', 'teaspoon', 'teaspoons', 'tsp',
            'ounce', 'ounces', 'oz', 'pound', 'pounds', 'lb', 'gram', 'grams', 'g',
            'kilogram', 'kilograms', 'kg', 'ml', 'milliliter', 'milliliters', 'liter', 'liters',
            'pinch', 'dash', 'to taste', 'clove', 'cloves', 'bunch', 'bunches', 'sprig', 'sprigs'
        ]
        
        # Common recipe schema types
        self.recipe_schema_types = [
            'Recipe', 'recipeIngredient', 'recipeInstructions', 'recipeYield',
            'cookTime', 'prepTime', 'totalTime', 'nutrition'
        ]
        
        # Common recipe microdata/RDFa properties
        self.recipe_properties = [
            'recipe', 'ingredients', 'recipeIngredient', 'recipeInstructions',
            'cookTime', 'prepTime', 'totalTime', 'recipeYield', 'nutrition'
        ]

    def analyze_content(self, html_content: str, url: str = None) -> Dict[str, any]:
        """
        Analyze HTML content to determine if it contains a recipe.
        
        Args:
            html_content: HTML content to analyze
            url: Optional URL for context
            
        Returns:
            Dict with analysis results including:
                - is_recipe: Boolean indicating if the page contains a recipe
                - confidence: Confidence score (0-100)
                - features: List of detected recipe features
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Initialize result
        result = {
            'is_recipe': False,
            'confidence': 0,
            'features': []
        }
        
        # Check for recipe structured data (JSON-LD, microdata, RDFa)
        structured_data_score = self._check_structured_data(soup)
        if structured_data_score > 0:
            result['features'].append(f"structured_data_score:{structured_data_score}")
        
        # Check for recipe headings
        heading_score = self._check_recipe_headings(soup)
        if heading_score > 0:
            result['features'].append(f"heading_score:{heading_score}")
        
        # Check for ingredient lists
        ingredient_score = self._check_ingredient_lists(soup)
        if ingredient_score > 0:
            result['features'].append(f"ingredient_score:{ingredient_score}")
        
        # Check for instruction lists
        instruction_score = self._check_instruction_lists(soup)
        if instruction_score > 0:
            result['features'].append(f"instruction_score:{instruction_score}")
        
        # Check for recipe metadata (cook time, prep time, etc.)
        metadata_score = self._check_recipe_metadata(soup)
        if metadata_score > 0:
            result['features'].append(f"metadata_score:{metadata_score}")
        
        # Calculate overall confidence score
        confidence = (
            structured_data_score * 0.4 +  # Structured data is a strong signal
            heading_score * 0.2 +
            ingredient_score * 0.2 +
            instruction_score * 0.15 +
            metadata_score * 0.05
        )
        
        result['confidence'] = min(100, round(confidence))
        result['is_recipe'] = result['confidence'] >= 60  # Threshold for considering it a recipe
        
        return result

    def _check_structured_data(self, soup: BeautifulSoup) -> int:
        """Check for recipe structured data in the page."""
        score = 0
        
        # Check for JSON-LD
        script_tags = soup.find_all('script', type='application/ld+json')
        for script in script_tags:
            try:
                script_text = script.string
                if script_text and any(schema_type in script_text for schema_type in self.recipe_schema_types):
                    # Strong indicator if multiple recipe schema types are present
                    matches = sum(1 for schema_type in self.recipe_schema_types if schema_type in script_text)
                    score += min(100, matches * 25)
            except:
                pass
        
        # Check for microdata and RDFa
        elements_with_props = soup.find_all(attrs={"itemprop": True}) + soup.find_all(attrs={"property": True})
        recipe_props_count = 0
        
        for element in elements_with_props:
            prop = element.get('itemprop') or element.get('property')
            if prop and any(recipe_prop in prop for recipe_prop in self.recipe_properties):
                recipe_props_count += 1
        
        if recipe_props_count > 0:
            score += min(100, recipe_props_count * 15)
        
        return min(100, score)

    def _check_recipe_headings(self, soup: BeautifulSoup) -> int:
        """Check for recipe-related headings in the page."""
        score = 0
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        recipe_heading_count = 0
        for heading in headings:
            heading_text = heading.get_text().lower()
            if any(recipe_heading in heading_text for recipe_heading in self.recipe_headings):
                recipe_heading_count += 1
        
        if recipe_heading_count >= 3:
            score = 100  # Strong signal if multiple recipe headings are present
        elif recipe_heading_count > 0:
            score = recipe_heading_count * 30
        
        return score

    def _check_ingredient_lists(self, soup: BeautifulSoup) -> int:
        """Check for ingredient lists in the page."""
        score = 0
        
        # Look for lists (ul/ol) that might contain ingredients
        lists = soup.find_all(['ul', 'ol'])
        
        ingredient_list_count = 0
        for list_elem in lists:
            list_items = list_elem.find_all('li')
            if not list_items:
                continue
                
            # Count items that look like ingredients
            ingredient_like_items = 0
            for item in list_items:
                item_text = item.get_text().lower()
                if any(marker in item_text for marker in self.ingredient_markers):
                    ingredient_like_items += 1
            
            # If more than half the items look like ingredients, count it as an ingredient list
            if ingredient_like_items >= len(list_items) / 2:
                ingredient_list_count += 1
        
        # Also check for divs with ingredient-related classes or IDs
        ingredient_divs = soup.find_all(['div', 'section'], class_=lambda c: c and 'ingredient' in c.lower())
        ingredient_divs += soup.find_all(['div', 'section'], id=lambda i: i and 'ingredient' in i.lower())
        
        if ingredient_divs:
            ingredient_list_count += len(ingredient_divs)
        
        if ingredient_list_count > 0:
            score = min(100, ingredient_list_count * 50)
        
        return score

    def _check_instruction_lists(self, soup: BeautifulSoup) -> int:
        """Check for instruction lists in the page."""
        score = 0
        
        # Look for ordered lists that might contain instructions
        instruction_lists = soup.find_all('ol')
        
        # Also check for divs with instruction-related classes or IDs
        instruction_divs = soup.find_all(['div', 'section'], class_=lambda c: c and any(x in c.lower() for x in ['instruction', 'direction', 'method', 'step']))
        instruction_divs += soup.find_all(['div', 'section'], id=lambda i: i and any(x in i.lower() for x in ['instruction', 'direction', 'method', 'step']))
        
        instruction_list_count = len(instruction_lists) + len(instruction_divs)
        
        if instruction_list_count > 0:
            score = min(100, instruction_list_count * 50)
        
        return score

    def _check_recipe_metadata(self, soup: BeautifulSoup) -> int:
        """Check for recipe metadata like cook time, prep time, etc."""
        score = 0
        
        metadata_terms = ['cook time', 'prep time', 'preparation time', 'total time', 
                         'servings', 'yield', 'serves', 'difficulty', 'cuisine']
        
        # Look for spans, divs, or paragraphs containing metadata terms
        metadata_count = 0
        for term in metadata_terms:
            elements = soup.find_all(string=lambda text: text and term in text.lower())
            if elements:
                metadata_count += 1
        
        if metadata_count > 0:
            score = min(100, metadata_count * 20)
        
        return score

    def is_recipe_page(self, html_content: str, url: str = None, threshold: int = 60) -> bool:
        """
        Determine if a page contains a recipe based on its content.
        
        Args:
            html_content: HTML content to analyze
            url: Optional URL for context
            threshold: Confidence threshold (0-100) for considering it a recipe
            
        Returns:
            bool: True if the page contains a recipe, False otherwise
        """
        # Special case for theloopywhisk.com - their recipe pages have a specific pattern
        if url and 'theloopywhisk.com' in url:
            from urllib.parse import urlparse
            import re
            
            # Check for date-based URL pattern which is common for their recipes
            parsed_url = urlparse(url)
            path = parsed_url.path.lower()
            
            # Their recipe URLs typically follow the pattern /YYYY/MM/DD/recipe-name/
            date_pattern = r'/\d{4}/\d{2}/\d{2}/[a-z0-9-]+/?'
            if re.search(date_pattern, path):
                return True
            
            # Also check for recipe schema in the HTML
            if 'application/ld+json' in html_content and '"@type":"Recipe"' in html_content:
                return True
        
        # For all other sites, use the standard analysis
        analysis = self.analyze_content(html_content, url)
        return analysis['confidence'] >= threshold