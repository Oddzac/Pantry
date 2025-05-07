from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class Ingredient(BaseModel):
    """Model for recipe ingredients with standardized measurements."""
    name: str
    measurement: Optional[str] = None
    unit_type: Optional[str] = None


class Recipe(BaseModel):
    """Model for storing recipe information in a standardized format."""
    url: HttpUrl
    title: str
    total_time: Optional[int] = None  # in minutes
    yields: Optional[str] = None
    ingredients: List[Ingredient]
    instructions: str
    image: Optional[HttpUrl] = None
    host: str
    nutrients: Dict[str, Any] = Field(default_factory=dict)
    notes: Dict[str, Any] = Field(default_factory=dict)  # For additional information like language

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://rachlmansfield.com/chocolate-thumbprint-cookies-gluten-free/",
                "title": "Chocolate Thumbprint Cookies (gluten-free)",
                "total_time": 20,
                "yields": "9 servings",
                "ingredients": [
                    {
                        "name": "coconut oil, melted and cooled",
                        "measurement": "1",
                        "unit_type": "tablespoon"
                    },
                    {
                        "name": "maple syrup",
                        "measurement": "1/3",
                        "unit_type": "cup"
                    }
                ],
                "instructions": "Preheat the Oven\nPreheat your oven to 350 degrees F...",
                "image": "https://rachlmansfield.com/wp-content/uploads/2024/08/IMG_5496-2-1-scaled.jpg",
                "host": "rachlmansfield.com",
                "nutrients": {},
                "notes": {}
            }
        }
    
    def dict(self, *args, **kwargs):
        """
        Override the dict method to convert HttpUrl objects to strings.
        """
        result = super().dict(*args, **kwargs)
        
        # Convert HttpUrl objects to strings
        if 'url' in result and result['url'] is not None:
            result['url'] = str(result['url'])
        
        if 'image' in result and result['image'] is not None:
            result['image'] = str(result['image'])
        
        return result