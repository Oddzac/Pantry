import sqlite3
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from .models import Recipe, Ingredient


class RecipeDatabase:
    """
    Database manager for recipe storage and retrieval using SQLite.
    """
    
    def __init__(self, db_path: Union[str, Path]):
        """
        Initialize the database connection.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self.conn = None
        self.cursor = None
        
        # Create the database directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialize the database
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize the database with required tables if they don't exist."""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # Enable foreign keys
        self.cursor.execute("PRAGMA foreign_keys = ON")
        
        # Create recipes table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            total_time INTEGER,
            yields TEXT,
            instructions TEXT NOT NULL,
            image TEXT,
            host TEXT NOT NULL,
            nutrients TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create ingredients table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            measurement TEXT,
            unit_type TEXT,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
        ''')
        
        # Create indexes for faster searching
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_recipes_title ON recipes(title)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_recipes_host ON recipes(host)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_recipes_total_time ON recipes(total_time)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_ingredients_name ON ingredients(name)')
        
        # Create a virtual table for full-text search on recipes
        self.cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS recipes_fts USING fts5(
            title, instructions, content='recipes', content_rowid='id'
        )
        ''')
        
        # Create a trigger to keep the FTS table in sync with the recipes table
        self.cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS recipes_ai AFTER INSERT ON recipes BEGIN
            INSERT INTO recipes_fts(rowid, title, instructions) VALUES (new.id, new.title, new.instructions);
        END
        ''')
        
        self.cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS recipes_ad AFTER DELETE ON recipes BEGIN
            INSERT INTO recipes_fts(recipes_fts, rowid, title, instructions) VALUES('delete', old.id, old.title, old.instructions);
        END
        ''')
        
        self.cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS recipes_au AFTER UPDATE ON recipes BEGIN
            INSERT INTO recipes_fts(recipes_fts, rowid, title, instructions) VALUES('delete', old.id, old.title, old.instructions);
            INSERT INTO recipes_fts(rowid, title, instructions) VALUES (new.id, new.title, new.instructions);
        END
        ''')
        
        self.conn.commit()
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def add_recipe(self, recipe: Recipe) -> int:
        """
        Add a recipe to the database.
        
        Args:
            recipe: Recipe object to add
            
        Returns:
            int: ID of the added recipe
        """
        try:
            # Convert recipe to dictionary
            recipe_dict = recipe.dict()
            
            # Extract ingredients
            ingredients = recipe_dict.pop('ingredients')
            
            # Convert nutrients and notes to JSON
            nutrients_json = json.dumps(recipe_dict.pop('nutrients'))
            notes_json = json.dumps(recipe_dict.pop('notes'))
            
            # Insert recipe
            self.cursor.execute('''
            INSERT OR REPLACE INTO recipes 
            (url, title, total_time, yields, instructions, image, host, nutrients, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                recipe_dict['url'],
                recipe_dict['title'],
                recipe_dict['total_time'],
                recipe_dict['yields'],
                recipe_dict['instructions'],
                recipe_dict['image'],
                recipe_dict['host'],
                nutrients_json,
                notes_json
            ))
            
            # Get the recipe ID
            recipe_id = self.cursor.lastrowid
            
            # Insert ingredients
            for ingredient in ingredients:
                self.cursor.execute('''
                INSERT INTO ingredients (recipe_id, name, measurement, unit_type)
                VALUES (?, ?, ?, ?)
                ''', (
                    recipe_id,
                    ingredient['name'],
                    ingredient['measurement'],
                    ingredient['unit_type']
                ))
            
            self.conn.commit()
            return recipe_id
        
        except Exception as e:
            self.conn.rollback()
            raise e
    
    def add_recipes(self, recipes: List[Recipe]) -> int:
        """
        Add multiple recipes to the database.
        
        Args:
            recipes: List of Recipe objects to add
            
        Returns:
            int: Number of recipes added
        """
        count = 0
        for recipe in recipes:
            try:
                self.add_recipe(recipe)
                count += 1
            except Exception as e:
                print(f"Error adding recipe {recipe.title}: {str(e)}")
        
        return count
    
    def get_recipe(self, recipe_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a recipe by ID.
        
        Args:
            recipe_id: ID of the recipe to get
            
        Returns:
            Optional[Dict[str, Any]]: Recipe data or None if not found
        """
        # Get recipe data
        self.cursor.execute('''
        SELECT id, url, title, total_time, yields, instructions, image, host, nutrients, notes
        FROM recipes WHERE id = ?
        ''', (recipe_id,))
        
        recipe_data = self.cursor.fetchone()
        if not recipe_data:
            return None
        
        # Get ingredients
        self.cursor.execute('''
        SELECT name, measurement, unit_type FROM ingredients WHERE recipe_id = ?
        ''', (recipe_id,))
        
        ingredients = []
        for row in self.cursor.fetchall():
            ingredients.append({
                'name': row[0],
                'measurement': row[1],
                'unit_type': row[2]
            })
        
        # Construct recipe dictionary
        recipe = {
            'id': recipe_data[0],
            'url': recipe_data[1],
            'title': recipe_data[2],
            'total_time': recipe_data[3],
            'yields': recipe_data[4],
            'instructions': recipe_data[5],
            'image': recipe_data[6],
            'host': recipe_data[7],
            'nutrients': json.loads(recipe_data[8]),
            'notes': json.loads(recipe_data[9]),
            'ingredients': ingredients
        }
        
        return recipe
    
    def search_by_title(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search recipes by title.
        
        Args:
            query: Search query
            limit: Maximum number of results to return
            
        Returns:
            List[Dict[str, Any]]: List of matching recipes
        """
        self.cursor.execute('''
        SELECT id FROM recipes_fts WHERE title MATCH ? LIMIT ?
        ''', (query, limit))
        
        recipe_ids = [row[0] for row in self.cursor.fetchall()]
        return [self.get_recipe(recipe_id) for recipe_id in recipe_ids]
    
    def search_by_ingredient(self, ingredient: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search recipes by ingredient.
        
        Args:
            ingredient: Ingredient to search for
            limit: Maximum number of results to return
            
        Returns:
            List[Dict[str, Any]]: List of matching recipes
        """
        self.cursor.execute('''
        SELECT DISTINCT recipe_id FROM ingredients 
        WHERE name LIKE ? LIMIT ?
        ''', (f'%{ingredient}%', limit))
        
        recipe_ids = [row[0] for row in self.cursor.fetchall()]
        return [self.get_recipe(recipe_id) for recipe_id in recipe_ids]
    
    def search_by_time(self, max_time: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search recipes by maximum preparation time.
        
        Args:
            max_time: Maximum preparation time in minutes
            limit: Maximum number of results to return
            
        Returns:
            List[Dict[str, Any]]: List of matching recipes
        """
        self.cursor.execute('''
        SELECT id FROM recipes 
        WHERE total_time <= ? AND total_time > 0
        ORDER BY total_time ASC
        LIMIT ?
        ''', (max_time, limit))
        
        recipe_ids = [row[0] for row in self.cursor.fetchall()]
        return [self.get_recipe(recipe_id) for recipe_id in recipe_ids]
    
    def get_recipe_count(self) -> int:
        """
        Get the total number of recipes in the database.
        
        Returns:
            int: Number of recipes
        """
        self.cursor.execute('SELECT COUNT(*) FROM recipes')
        return self.cursor.fetchone()[0]
    
    def get_ingredient_count(self) -> int:
        """
        Get the total number of ingredients in the database.
        
        Returns:
            int: Number of ingredients
        """
        self.cursor.execute('SELECT COUNT(*) FROM ingredients')
        return self.cursor.fetchone()[0]
    
    def import_from_json(self, json_path: Union[str, Path]) -> int:
        """
        Import recipes from a JSON file.
        
        Args:
            json_path: Path to the JSON file
            
        Returns:
            int: Number of recipes imported
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                recipes_data = json.load(f)
            
            count = 0
            for recipe_data in recipes_data:
                try:
                    recipe = Recipe(**recipe_data)
                    self.add_recipe(recipe)
                    count += 1
                except Exception as e:
                    print(f"Error importing recipe {recipe_data.get('title', 'Unknown')}: {str(e)}")
            
            return count
        
        except Exception as e:
            print(f"Error importing recipes from {json_path}: {str(e)}")
            return 0
    
    def export_to_json(self, json_path: Union[str, Path], limit: Optional[int] = None) -> int:
        """
        Export recipes to a JSON file.
        
        Args:
            json_path: Path to the JSON file
            limit: Maximum number of recipes to export (None for all)
            
        Returns:
            int: Number of recipes exported
        """
        try:
            # Get all recipe IDs
            if limit:
                self.cursor.execute('SELECT id FROM recipes LIMIT ?', (limit,))
            else:
                self.cursor.execute('SELECT id FROM recipes')
            
            recipe_ids = [row[0] for row in self.cursor.fetchall()]
            recipes = [self.get_recipe(recipe_id) for recipe_id in recipe_ids]
            
            # Remove the ID field from each recipe
            for recipe in recipes:
                recipe.pop('id', None)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(recipes, f, indent=2, ensure_ascii=False)
            
            return len(recipes)
        
        except Exception as e:
            print(f"Error exporting recipes to {json_path}: {str(e)}")
            return 0


def main():
    """Test the database functionality."""
    db_path = Path('recipe_library.db')
    
    with RecipeDatabase(db_path) as db:
        # Import recipes from JSON
        json_path = Path('recipe_library.json')
        if json_path.exists():
            print(f"Importing recipes from {json_path}...")
            count = db.import_from_json(json_path)
            print(f"Imported {count} recipes")
        
        # Print database stats
        print(f"Database contains {db.get_recipe_count()} recipes and {db.get_ingredient_count()} ingredients")
        
        # Search for recipes
        print("\nSearching for recipes with 'chicken'...")
        chicken_recipes = db.search_by_title('chicken', limit=3)
        for recipe in chicken_recipes:
            print(f"- {recipe['title']} ({recipe['total_time']} minutes)")
        
        print("\nSearching for recipes with 'garlic'...")
        garlic_recipes = db.search_by_ingredient('garlic', limit=3)
        for recipe in garlic_recipes:
            print(f"- {recipe['title']} ({recipe['total_time']} minutes)")
        
        print("\nSearching for recipes under 30 minutes...")
        quick_recipes = db.search_by_time(30, limit=3)
        for recipe in quick_recipes:
            print(f"- {recipe['title']} ({recipe['total_time']} minutes)")


if __name__ == "__main__":
    main()