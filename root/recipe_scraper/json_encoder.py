import json
from pydantic import HttpUrl
from typing import Any


class RecipeJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that can handle Pydantic's HttpUrl type.
    """
    
    def default(self, obj: Any) -> Any:
        """
        Convert objects to JSON serializable types.
        
        Args:
            obj: Object to convert
            
        Returns:
            JSON serializable representation of the object
        """
        if isinstance(obj, HttpUrl):
            # Convert HttpUrl to string
            return str(obj)
        
        # Let the base class handle other types
        return super().default(obj)


def recipe_json_dumps(obj: Any, **kwargs) -> str:
    """
    Serialize object to JSON string with custom encoder.
    
    Args:
        obj: Object to serialize
        **kwargs: Additional arguments to pass to json.dumps
        
    Returns:
        str: JSON string
    """
    return json.dumps(obj, cls=RecipeJSONEncoder, **kwargs)


def recipe_dict_to_json(recipe_dict: dict) -> dict:
    """
    Convert a recipe dictionary to a JSON-serializable dictionary.
    
    Args:
        recipe_dict: Recipe dictionary from Recipe.dict()
        
    Returns:
        dict: JSON-serializable dictionary
    """
    # Create a copy of the dictionary
    result = {}
    
    # Convert each field
    for key, value in recipe_dict.items():
        if isinstance(value, HttpUrl):
            # Convert HttpUrl to string
            result[key] = str(value)
        elif isinstance(value, list):
            # Handle lists (like ingredients)
            result[key] = [
                recipe_dict_to_json(item) if isinstance(item, dict) else item
                for item in value
            ]
        elif isinstance(value, dict):
            # Handle nested dictionaries
            result[key] = recipe_dict_to_json(value)
        else:
            # Keep other types as is
            result[key] = value
    
    return result