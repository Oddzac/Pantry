"""
This module contains direct recipe URLs for popular recipe sites.
These are known good recipe URLs that can be used as fallbacks when
the automatic recipe finder fails to find valid recipe pages.
"""

DIRECT_RECIPE_URLS = {
    # AllRecipes
    "allrecipes.com": [
        "https://www.allrecipes.com/recipe/8372/black-magic-cake/",
        "https://www.allrecipes.com/recipe/8538/perfect-pumpkin-pie/",
        "https://www.allrecipes.com/recipe/10813/best-chocolate-chip-cookies/",
        "https://www.allrecipes.com/recipe/219164/simple-beef-pot-roast/"
    ],
    
    # Food Network
    "foodnetwork.com": [
        "https://www.foodnetwork.com/recipes/food-network-kitchen/classic-deviled-eggs-recipe-2112224",
        "https://www.foodnetwork.com/recipes/ina-garten/perfect-roast-chicken-recipe-1940592",
        "https://www.foodnetwork.com/recipes/alton-brown/the-chewy-recipe-1909046"
    ],
    
    # Epicurious
    "epicurious.com": [
        "https://www.epicurious.com/recipes/food/views/our-favorite-spaghetti-and-meatballs-56389489",
        "https://www.epicurious.com/recipes/food/views/classic-chocolate-mousse-107312",
        "https://www.epicurious.com/recipes/food/views/ba-best-chocolate-chip-cookies-56389969"
    ],
    
    # Bon Appetit
    "bonappetit.com": [
        "https://www.bonappetit.com/recipe/classic-caesar-salad",
        "https://www.bonappetit.com/recipe/bas-best-chocolate-chip-cookies",
        "https://www.bonappetit.com/recipe/simple-roast-chicken"
    ],
    
    # Serious Eats
    "seriouseats.com": [
        "https://www.seriouseats.com/the-best-chocolate-chip-cookies-recipe",
        "https://www.seriouseats.com/classic-potato-salad-recipe",
        "https://www.seriouseats.com/new-york-style-pizza-sauce"
    ],
    
    # Simply Recipes
    "simplyrecipes.com": [
        "https://www.simplyrecipes.com/recipes/perfect_guacamole/",
        "https://www.simplyrecipes.com/recipes/homemade_pizza/",
        "https://www.simplyrecipes.com/recipes/banana_bread/"
    ],
    
    # Taste of Home
    "tasteofhome.com": [
        "https://www.tasteofhome.com/recipes/the-best-ever-lasagna/",
        "https://www.tasteofhome.com/recipes/apple-pie/",
        "https://www.tasteofhome.com/recipes/basic-homemade-bread/"
    ],
    
    # King Arthur Flour
    "kingarthurbaking.com": [
        "https://www.kingarthurbaking.com/recipes/classic-sandwich-bread-recipe",
        "https://www.kingarthurbaking.com/recipes/chocolate-chip-cookies-recipe",
        "https://www.kingarthurbaking.com/recipes/classic-sourdough-bread-recipe"
    ],
    
    # BBC Good Food
    "bbcgoodfood.com": [
        "https://www.bbcgoodfood.com/recipes/best-ever-chocolate-brownies-recipe",
        "https://www.bbcgoodfood.com/recipes/classic-victoria-sandwich-recipe",
        "https://www.bbcgoodfood.com/recipes/easy-pancakes"
    ],
    
    # Delish
    "delish.com": [
        "https://www.delish.com/cooking/recipe-ideas/a20720076/best-chocolate-chip-cookies-recipe/",
        "https://www.delish.com/cooking/recipe-ideas/a25621572/pico-de-gallo-recipe/",
        "https://www.delish.com/cooking/recipe-ideas/a23365368/how-to-cook-a-medium-rare-steak/"
    ]
}

def get_direct_recipe_urls(domain):
    """
    Get direct recipe URLs for a specific domain.
    
    Args:
        domain: Domain to get recipe URLs for
        
    Returns:
        List[str]: List of recipe URLs for the domain, or empty list if none found
    """
    # Clean up the domain to match our keys
    domain = domain.lower()
    if domain.startswith('http://'):
        domain = domain[7:]
    if domain.startswith('https://'):
        domain = domain[8:]
    if domain.startswith('www.'):
        domain = domain[4:]
    
    # Remove any trailing path or query string
    domain = domain.split('/')[0]
    
    # Check if we have direct URLs for this domain
    for key in DIRECT_RECIPE_URLS:
        if key in domain or domain in key:
            return DIRECT_RECIPE_URLS[key]
    
    return []