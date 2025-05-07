import re
from typing import Dict, Tuple, Optional, List
from fractions import Fraction
import unicodedata


class IngredientParser:
    """
    Parser for recipe ingredients with improved measurement extraction
    and unit standardization.
    """
    
    # Mapping of unit variations to standard units
    UNIT_MAPPING = {
        # Volume measurements
        'tsp': 'teaspoon',
        'tsps': 'teaspoon',
        'teaspoon': 'teaspoon',
        'teaspoons': 'teaspoon',
        't': 'teaspoon',
        'tbsp': 'tablespoon',
        'tbsps': 'tablespoon',
        'tablespoon': 'tablespoon',
        'tablespoons': 'tablespoon',
        'tbs': 'tablespoon',
        'tb': 'tablespoon',
        'T': 'tablespoon',
        'cup': 'cup',
        'cups': 'cup',
        'c': 'cup',
        'C': 'cup',
        'fl oz': 'fluid ounce',
        'fluid ounce': 'fluid ounce',
        'fluid ounces': 'fluid ounce',
        'oz fl': 'fluid ounce',
        'pint': 'pint',
        'pints': 'pint',
        'pt': 'pint',
        'quart': 'quart',
        'quarts': 'quart',
        'qt': 'quart',
        'gallon': 'gallon',
        'gallons': 'gallon',
        'gal': 'gallon',
        'ml': 'milliliter',
        'milliliter': 'milliliter',
        'milliliters': 'milliliter',
        'millilitre': 'milliliter',
        'millilitres': 'milliliter',
        'cc': 'milliliter',
        'l': 'liter',
        'liter': 'liter',
        'liters': 'liter',
        'litre': 'liter',
        'litres': 'liter',
        
        # Weight measurements
        'lb': 'pound',
        'lbs': 'pound',
        'pound': 'pound',
        'pounds': 'pound',
        '#': 'pound',
        'oz': 'ounce',
        'ounce': 'ounce',
        'ounces': 'ounce',
        'g': 'gram',
        'gram': 'gram',
        'grams': 'gram',
        'gr': 'gram',
        'kg': 'kilogram',
        'kilogram': 'kilogram',
        'kilograms': 'kilogram',
        'kilo': 'kilogram',
        'kilos': 'kilogram',
        
        # Other common units
        'pinch': 'pinch',
        'pinches': 'pinch',
        'pn': 'pinch',
        'dash': 'dash',
        'dashes': 'dash',
        'handful': 'handful',
        'handfuls': 'handful',
        'slice': 'slice',
        'slices': 'slice',
        'piece': 'piece',
        'pieces': 'piece',
        'clove': 'clove',
        'cloves': 'clove',
        'bunch': 'bunch',
        'bunches': 'bunch',
        'sprig': 'sprig',
        'sprigs': 'sprig',
        'stalk': 'stalk',
        'stalks': 'stalk',
        'head': 'head',
        'heads': 'head',
        'can': 'can',
        'cans': 'can',
        'jar': 'jar',
        'jars': 'jar',
        'package': 'package',
        'packages': 'package',
        'pkg': 'package',
        'box': 'box',
        'boxes': 'box',
        'stick': 'stick',
        'sticks': 'stick',
    }
    
    def __init__(self):
        # Build the unit pattern for regex
        self.unit_pattern = '|'.join(self.UNIT_MAPPING.keys())
    
    def unicode_fraction_to_float(self, fraction_str):
        """Convert a unicode fraction character to a float."""
        try:
            return unicodedata.numeric(fraction_str)
        except (ValueError, TypeError):
            return None
    
    def float_to_fraction_string(self, value):
        """Convert a float to a fraction string."""
        try:
            fraction = Fraction(value).limit_denominator()
            return str(fraction)
        except (ValueError, TypeError):
            return str(value)
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text by replacing unicode fractions and standardizing format.
        
        Args:
            text: Text to normalize
            
        Returns:
            str: Normalized text
        """
        # Replace unicode fractions with their decimal equivalents
        fraction_pattern = r'[\u00BC-\u00BE\u2150-\u215E]'
        text = re.sub(fraction_pattern, 
                     lambda m: str(self.unicode_fraction_to_float(m.group())), 
                     text)
        
        # Convert decimals to fraction strings
        decimal_pattern = r'\b\d+\.\d+\b'
        text = re.sub(decimal_pattern, 
                     lambda m: self.float_to_fraction_string(float(m.group())), 
                     text)
        
        # Normalize spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def parse_ingredient(self, ingredient_text: str) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Parse an ingredient string into name, measurement, and unit type.
        
        Args:
            ingredient_text: Raw ingredient text
            
        Returns:
            Tuple[str, Optional[str], Optional[str]]: (name, measurement, unit_type)
        """
        try:
            # Normalize the text
            text = self.normalize_text(ingredient_text)
            
            # Pattern to match measurement and unit
            # This matches:
            # - Fractions like 1/2, 1 1/2
            # - Decimals like 1.5
            # - Whole numbers like 1, 2, 3
            # - Followed by optional units
            pattern = rf'^\s*(\d+(?:/\d+|\s+\d+/\d+|\.\d+)?)\s*({self.unit_pattern})?\b'
            
            match = re.search(pattern, text, re.IGNORECASE)
            
            if match:
                # Extract measurement and unit
                measurement = match.group(1).strip() if match.group(1) else None
                unit_raw = match.group(2).strip() if match.group(2) else None
                
                # Standardize unit
                unit_type = self.UNIT_MAPPING.get(unit_raw.lower(), unit_raw) if unit_raw else None
                
                # Remove the matched part from the ingredient text to get the name
                name = text[match.end():].strip()
                name = re.sub(r'^[,\s]+', '', name)  # Remove leading commas and spaces
                
                return name, measurement, unit_type
            
            # Try another pattern for cases like "Cup yellow onion"
            # where the unit comes first
            pattern = rf'^\s*({self.unit_pattern})\s+(\d+(?:/\d+|\s+\d+/\d+|\.\d+)?)\b'
            
            match = re.search(pattern, text, re.IGNORECASE)
            
            if match:
                # Extract unit and measurement
                unit_raw = match.group(1).strip() if match.group(1) else None
                measurement = match.group(2).strip() if match.group(2) else None
                
                # Standardize unit
                unit_type = self.UNIT_MAPPING.get(unit_raw.lower(), unit_raw) if unit_raw else None
                
                # Remove the matched part from the ingredient text to get the name
                name = text[match.end():].strip()
                name = re.sub(r'^[,\s]+', '', name)  # Remove leading commas and spaces
                
                return name, measurement, unit_type
            
            # If no match, return the original text as the name
            return text, None, None
            
        except Exception as e:
            print(f"Error parsing ingredient '{ingredient_text}': {str(e)}")
            return ingredient_text, None, None
    
    def parse_ingredients(self, ingredients: List[str]) -> List[Dict[str, Optional[str]]]:
        """
        Parse a list of ingredient strings into structured ingredients.
        
        Args:
            ingredients: List of ingredient strings
            
        Returns:
            List[Dict[str, Optional[str]]]: List of parsed ingredients
        """
        parsed_ingredients = []
        
        for ingredient_text in ingredients:
            name, measurement, unit_type = self.parse_ingredient(ingredient_text)
            parsed_ingredients.append({
                'name': name,
                'measurement': measurement,
                'unit_type': unit_type
            })
        
        return parsed_ingredients


def main():
    """Test the ingredient parser with some examples."""
    parser = IngredientParser()
    
    test_ingredients = [
        "1 cup flour",
        "2 tablespoons olive oil",
        "1/2 teaspoon salt",
        "3 large eggs",
        "1 1/2 cups milk",
        "2 cloves garlic, minced",
        "1 lemon, juiced",
        "salt and pepper to taste",
        "4 teaspoons toasted sesame seeds",
        "2 lemons, zested",
        "1/4 teaspoon fine-grain sea salt",
        "500 gr voorgesneden frieten",
        "2 el ketchup",
        "1 pound boneless skinless chicken breasts, cut into bite size pieces",
        "Cup yellow onion, diced",
        "Tablespoons olive oil",
        "1 head broccoli, cut into florets (about 3 cups)",
        "(15.25- ounce) box yellow cake mix",
        "1 tablespoon avocado oil",
        "½ teaspoon cumin",
        "1 clove fresh garlic",
        "1 ½ teaspoons garlic powder",
        "⅓ cup sour cream (or plain Greek yogurt)"
    ]
    
    for ingredient in test_ingredients:
        name, measurement, unit_type = parser.parse_ingredient(ingredient)
        print(f"Original: {ingredient}")
        print(f"  Name: {name}")
        print(f"  Measurement: {measurement}")
        print(f"  Unit: {unit_type}")
        print()


if __name__ == "__main__":
    main()