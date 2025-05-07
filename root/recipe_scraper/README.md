# Pantree Recipe Scraper

A Python application for scraping recipes from various websites and storing them in a standardized format.

## Features

- Scrape recipes from a wide variety of websites
- Convert metric measurements to US standard measurements
- Store recipes in a standardized JSON format
- Command-line interface for easy usage
- Crawl websites for recipes

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd Pantree
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Command-line Interface

The recipe scraper can be used from the command line:

```bash
# Scrape a single recipe
python main.py scrape https://example.com/recipe

# Build a recipe library
# Basic usage (scrapes 2 recipes from each of the first 10 sites)
python main.py build-library --limit 10

# Advanced usage with parallel processing
python main.py build-library --limit 100 --recipes-per-site 5 --workers 8 --batch-size 20

# Options:
#   --limit N              Maximum number of sites to scrape from
#   --recipes-per-site N   Number of recipes to scrape from each site (default: 2)
#   --delay N              Delay between requests in seconds (default: 1.0)
#   --no-english-only      Include non-English sites
#   --no-parallel          Disable parallel scraping
#   --workers N            Number of worker threads/processes (default: 4)
#   --batch-size N         Number of sites to process in each batch (default: 20)


# List Supported Sites
python main.py list-sites

# Options:
#   --no-english-only      Include non-English sites
#   --limit N              Maximum number of sites to list

# Find Recipe URLS on a Site
python main.py find-recipes allrecipes.com --max-urls 10


# List Recipes in Your Library
python main.py list-recipes --limit 20

#Recipe library contains 74 recipes:
#1. [1] Spinach Noodles with Citrus-Nori Oil (20 min, 4 servings)
#2. [2] Chick-fil-A Southwest Salad Recipe (95 min, 2 servings)
#3. [3] Air Fryer Frozen French Fries (20 min, 6 servings)
#4. [4] Marry Me Chicken (45 min, 6 servings)
#5. [5] Avocado Ranch Dressing (10 min, 8 servings)



# Search for Recipes
# Search by title
python main.py search title "chicken"

# Search by ingredient
python main.py search ingredient "garlic"

# Search by maximum cooking time (in minutes)
python main.py search time 30

# Options:
#   --limit N              Maximum number of results to return (default: 10)


# View a Specific Recipe
python main.py view-recipe 123  # Where 123 is the recipe ID

```
================================================================================
Recipe ID: 1
Title: Spinach Noodles with Citrus-Nori Oil
Source: https://101cookbooks.com/pasta-recipes/
Host: 101cookbooks.com
--------------------------------------------------------------------------------
Total Time: 20 minutes
Yields: 4 servings
--------------------------------------------------------------------------------
Ingredients:
- 1 (8-inch) sheet nori, toasted*
- 1/2 cup extra-virgin olive oil
- 1/4 teaspoon fine-grain sea salt
- Zest of 2 lemons, oranges, limes (or combo)
- 4 teaspoon toasted sesame seeds
- 1/4 teaspoon cayenne pepper
- 1/2 teaspoon ground cumin
- 1 bunch chives, minced
- 1 pound dried spinach noodles
- 1/2 cup grated Parmesan or Pecorino cheese
--------------------------------------------------------------------------------
Instructions:
1. Crush or cut the toasted nori into the smallest flecks you can manage. In a small bowl, combine most of the nori, the oil, salt, lemon zest, sesame seeds, cayenne, cumin, and most of the chives and set aside.
2. Bring a large pot of salted water to a boil. Add the noodles and cook according to the package instructions. Drain well, reserving 1 cup of the noodle water. Return the noodles to the pot and place it over low heat. Stir in a little of the reserved noodle water, most of the nori oil, and the cheese and stir well. Add more noodle water, a splash at a time, to loosen up the noodles as needed.
3. Serve immediately topped with the remaining nori pieces, the chives, and the remaining nori oil.
4. *To toast nori, gently wave it over the flame of a gas burner or bake it on a baking sheet in a 350°F oven until crisped. Cool, then crumble.
--------------------------------------------------------------------------------
Nutrition Information:
- calories: 503 kcal
- carbohydrateContent: 70 g
- proteinContent: 14 g
- fatContent: 21 g
- fiberContent: 4 g
- servingSize: 1 serving
--------------------------------------------------------------------------------
Image: https://images.101cookbooks.com/best-pasta-recipes.jpg?w=1200&auto=format
================================================================================
```bash

# Import recipes from a JSON file
python main.py import recipes.json

# Export recipes to a JSON file
python main.py export recipes.json --limit 100
```

## Web Access to Recipe Database

The recipe database is available for browsing and searching online at:
https://oddzac.github.io/Pantree/

### API Access

You can also access the database programmatically using SQL.js-httpvfs:

```javascript
// Example JavaScript code to query the database
async function queryRecipes() {
  const sqlPromise = initSqlJs({
    locateFile: file => `https://cdn.jsdelivr.net/npm/sql.js@1.8.0/dist/sql-wasm.wasm`
  });
  
  const [SQL, buf] = await Promise.all([
    sqlPromise,
    fetch('https://oddzac.github.io/recipe_library.db').then(res => res.arrayBuffer())
  ]);
  
  const db = new SQL.Database(new Uint8Array(buf));
  
  // Query recipes with chicken in the title
  const results = db.exec(`
    SELECT r.id, r.title, r.total_time, r.yields 
    FROM recipes r 
    WHERE r.title LIKE '%chicken%'
    LIMIT 10
  `);
  
  return results[0].values.map((row, i) => {
    return {
      id: row[0],
      title: row[1],
      total_time: row[2],
      yields: row[3]
    };
  });
}


```

### Python API

You can also use the recipe scraper in your Python code:

```python
from recipe_scraper import RecipeParser

# Initialize the parser
parser = RecipeParser()

# Parse a recipe from a URL
recipe = parser.parse_url("https://example.com/recipe")

# Access recipe data
print(f"Recipe: {recipe.title}")
print(f"Total Time: {recipe.total_time} minutes")
print(f"Yields: {recipe.yields}")
print("\nIngredients:")
for ingredient in recipe.ingredients:
    if ingredient.measurement and ingredient.unit_type:
        print(f"- {ingredient.measurement} {ingredient.unit_type} of {ingredient.name}")
    else:
        print(f"- {ingredient.name}")
```

### Main Application

The main application provides a simple interface for scraping and managing recipes:

```bash
python root/src/main/main.py https://example.com/recipe
```

## Recipe JSON Format

Recipes are stored in a standardized JSON format:

```json
{
  "url": "https://example.com/recipe",
  "title": "Example Recipe",
  "total_time": 30,
  "yields": "4 servings",
  "ingredients": [
    {
      "name": "ingredient name",
      "measurement": "1",
      "unit_type": "cup"
    }
  ],
  "instructions": "Step-by-step instructions...",
  "image": "https://example.com/image.jpg",
  "host": "example.com",
  "nutrients": {}
}
```

## License

[MIT License](LICENSE)