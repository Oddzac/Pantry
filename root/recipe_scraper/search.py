from typing import List, Dict, Any, Optional
import json
from pathlib import Path


class RecipeSearch:
    """
    Search functionality for the recipe library.
    """
    
    def __init__(self, library_file=None):
        """
        Initialize the RecipeSearch.
        
        Args:
            library_file: Path to the recipe library file
        """
        if library_file is None:
            # Default to the recipes directory in the main application
            from pathlib import Path
            import sys
            sys.path.append(str(Path(__file__).resolve().parents[2]))
            from root.src.main.main import RecipeManager
            manager = RecipeManager()
            self.library_file = manager.storage_dir / 'recipe_library.json'
        else:
            self.library_file = Path(library_file)
    
    def load_recipes(self) -> List[Dict[str, Any]]:
        """
        Load all recipes from the library file.
        
        Returns:
            List[Dict[str, Any]]: List of recipe dictionaries
        """
        if not self.library_file.exists():
            print(f"Recipe library file not found: {self.library_file}")
            return []
        
        try:
            with open(self.library_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading recipes from library: {str(e)}")
            return []
    
    def search_by_ingredient(self, ingredient: str) -> List[Dict[str, Any]]:
        """
        Search for recipes containing a specific ingredient.
        
        Args:
            ingredient: Ingredient to search for
            
        Returns:
            List[Dict[str, Any]]: List of matching recipe dictionaries
        """
        recipes = self.load_recipes()
        ingredient = ingredient.lower()
        
        matching_recipes = []
        for recipe in recipes:
            # Check if any ingredient contains the search term
            if any(ingredient in ing.get('name', '').lower() for ing in recipe.get('ingredients', [])):
                matching_recipes.append(recipe)
        
        return matching_recipes
    
    def search_by_title(self, title: str) -> List[Dict[str, Any]]:
        """
        Search for recipes with a title containing the search term.
        
        Args:
            title: Title search term
            
        Returns:
            List[Dict[str, Any]]: List of matching recipe dictionaries
        """
        recipes = self.load_recipes()
        title = title.lower()
        
        matching_recipes = []
        for recipe in recipes:
            if title in recipe.get('title', '').lower():
                matching_recipes.append(recipe)
        
        return matching_recipes
    
    def search_by_time(self, max_time: int) -> List[Dict[str, Any]]:
        """
        Search for recipes that can be prepared within a specific time.
        
        Args:
            max_time: Maximum preparation time in minutes
            
        Returns:
            List[Dict[str, Any]]: List of matching recipe dictionaries
        """
        recipes = self.load_recipes()
        
        matching_recipes = []
        for recipe in recipes:
            total_time = recipe.get('total_time')
            if total_time is not None and total_time <= max_time:
                matching_recipes.append(recipe)
        
        return matching_recipes
    
    def advanced_search(self, 
                       ingredients: Optional[List[str]] = None, 
                       exclude_ingredients: Optional[List[str]] = None,
                       max_time: Optional[int] = None,
                       title_keywords: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Perform an advanced search with multiple criteria.
        
        Args:
            ingredients: List of ingredients that must be included
            exclude_ingredients: List of ingredients that must not be included
            max_time: Maximum preparation time in minutes
            title_keywords: Keywords that must appear in the title
            
        Returns:
            List[Dict[str, Any]]: List of matching recipe dictionaries
        """
        recipes = self.load_recipes()
        
        # Convert search terms to lowercase for case-insensitive matching
        if ingredients:
            ingredients = [ing.lower() for ing in ingredients]
        if exclude_ingredients:
            exclude_ingredients = [ing.lower() for ing in exclude_ingredients]
        if title_keywords:
            title_keywords = [kw.lower() for kw in title_keywords]
        
        matching_recipes = []
        for recipe in recipes:
            # Start by assuming the recipe matches
            matches = True
            
            # Check required ingredients
            if ingredients:
                recipe_ingredients = [ing.get('name', '').lower() for ing in recipe.get('ingredients', [])]
                if not all(any(req_ing in ing for ing in recipe_ingredients) for req_ing in ingredients):
                    matches = False
            
            # Check excluded ingredients
            if exclude_ingredients and matches:
                recipe_ingredients = [ing.get('name', '').lower() for ing in recipe.get('ingredients', [])]
                if any(any(excl_ing in ing for ing in recipe_ingredients) for excl_ing in exclude_ingredients):
                    matches = False
            
            # Check maximum time
            if max_time is not None and matches:
                total_time = recipe.get('total_time')
                if total_time is None or total_time > max_time:
                    matches = False
            
            # Check title keywords
            if title_keywords and matches:
                recipe_title = recipe.get('title', '').lower()
                if not all(kw in recipe_title for kw in title_keywords):
                    matches = False
            
            # Add the recipe to the results if it matches all criteria
            if matches:
                matching_recipes.append(recipe)
        
        return matching_recipes


def main():
    """Main function to demonstrate the recipe search functionality."""
    import sys
    
    search = RecipeSearch()
    
    if len(sys.argv) > 2:
        search_type = sys.argv[1]
        search_term = sys.argv[2]
        
        if search_type == "--ingredient":
            results = search.search_by_ingredient(search_term)
            print(f"Found {len(results)} recipes with ingredient '{search_term}':")
        elif search_type == "--title":
            results = search.search_by_title(search_term)
            print(f"Found {len(results)} recipes with title containing '{search_term}':")
        elif search_type == "--time":
            try:
                max_time = int(search_term)
                results = search.search_by_time(max_time)
                print(f"Found {len(results)} recipes that can be prepared in {max_time} minutes or less:")
            except ValueError:
                print(f"Invalid time value: {search_term}")
                return
        else:
            print(f"Unknown search type: {search_type}")
            print("Usage: python search.py --ingredient|--title|--time <search_term>")
            return
        
        # Display the results
        for i, recipe in enumerate(results[:10], 1):
            print(f"{i}. {recipe.get('title')} ({recipe.get('total_time')} minutes)")
        
        if len(results) > 10:
            print(f"... and {len(results) - 10} more.")
    else:
        print("Usage: python search.py --ingredient|--title|--time <search_term>")


if __name__ == "__main__":
    main()