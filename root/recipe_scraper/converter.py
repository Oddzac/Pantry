from typing import Dict, Tuple, Optional

class MeasurementConverter:
    """
    Utility class for converting between different measurement units.
    Focuses on converting metric measurements to US standard measurements.
    """
    
    # Conversion factors for volume
    VOLUME_CONVERSIONS = {
        # From milliliters to various US units
        'ml_to_tsp': 0.202884,
        'ml_to_tbsp': 0.067628,
        'ml_to_floz': 0.033814,
        'ml_to_cup': 0.00422675,
        
        # From liters to various US units
        'l_to_tsp': 202.884,
        'l_to_tbsp': 67.628,
        'l_to_floz': 33.814,
        'l_to_cup': 4.22675,
        'l_to_pint': 2.11338,
        'l_to_quart': 1.05669,
        'l_to_gallon': 0.264172,
    }
    
    # Conversion factors for weight
    WEIGHT_CONVERSIONS = {
        # From grams to various US units
        'g_to_oz': 0.035274,
        'g_to_lb': 0.00220462,
        
        # From kilograms to various US units
        'kg_to_oz': 35.274,
        'kg_to_lb': 2.20462,
    }
    
    def __init__(self):
        pass
    
    def convert_to_us_units(self, value: float, unit: str) -> Tuple[float, str]:
        """
        Convert a metric measurement to the most appropriate US unit.
        
        Args:
            value: The numeric value of the measurement
            unit: The unit of measurement (e.g., 'g', 'ml', 'l', 'kg')
            
        Returns:
            Tuple[float, str]: The converted value and its US unit
        """
        unit = unit.lower()
        
        # Handle volume conversions
        if unit in ['ml', 'milliliter', 'millilitre']:
            return self._convert_milliliters(value)
        elif unit in ['l', 'liter', 'litre']:
            return self._convert_liters(value)
        
        # Handle weight conversions
        elif unit in ['g', 'gram']:
            return self._convert_grams(value)
        elif unit in ['kg', 'kilogram']:
            return self._convert_kilograms(value)
        
        # If the unit is already in US units or unknown, return as is
        return value, unit
    
    def _convert_milliliters(self, ml: float) -> Tuple[float, str]:
        """Convert milliliters to the most appropriate US volume unit."""
        if ml < 5:
            # Less than 5ml, use teaspoons
            return ml * self.VOLUME_CONVERSIONS['ml_to_tsp'], 'teaspoon'
        elif ml < 15:
            # Less than 15ml, use tablespoons
            return ml * self.VOLUME_CONVERSIONS['ml_to_tbsp'], 'tablespoon'
        elif ml < 240:
            # Less than 240ml, use fluid ounces
            return ml * self.VOLUME_CONVERSIONS['ml_to_floz'], 'fluid ounce'
        else:
            # 240ml or more, use cups
            return ml * self.VOLUME_CONVERSIONS['ml_to_cup'], 'cup'
    
    def _convert_liters(self, l: float) -> Tuple[float, str]:
        """Convert liters to the most appropriate US volume unit."""
        if l < 0.25:
            # Less than 0.25L, use cups
            return l * self.VOLUME_CONVERSIONS['l_to_cup'], 'cup'
        elif l < 0.5:
            # Less than 0.5L, use pints
            return l * self.VOLUME_CONVERSIONS['l_to_pint'], 'pint'
        elif l < 1:
            # Less than 1L, use quarts
            return l * self.VOLUME_CONVERSIONS['l_to_quart'], 'quart'
        else:
            # 1L or more, use gallons
            return l * self.VOLUME_CONVERSIONS['l_to_gallon'], 'gallon'
    
    def _convert_grams(self, g: float) -> Tuple[float, str]:
        """Convert grams to the most appropriate US weight unit."""
        if g < 100:
            # Less than 100g, use ounces
            return g * self.WEIGHT_CONVERSIONS['g_to_oz'], 'ounce'
        else:
            # 100g or more, use pounds
            return g * self.WEIGHT_CONVERSIONS['g_to_lb'], 'pound'
    
    def _convert_kilograms(self, kg: float) -> Tuple[float, str]:
        """Convert kilograms to the most appropriate US weight unit."""
        if kg < 0.5:
            # Less than 0.5kg, use ounces
            return kg * self.WEIGHT_CONVERSIONS['kg_to_oz'], 'ounce'
        else:
            # 0.5kg or more, use pounds
            return kg * self.WEIGHT_CONVERSIONS['kg_to_lb'], 'pound'
    
    def format_measurement(self, value: float, unit: str) -> str:
        """
        Format a measurement value and unit into a human-readable string.
        
        Args:
            value: The numeric value of the measurement
            unit: The unit of measurement
            
        Returns:
            str: Formatted measurement string
        """
        # Round to 2 decimal places and remove trailing zeros
        formatted_value = f"{value:.2f}".rstrip('0').rstrip('.')
        
        # Handle pluralization of units
        if value != 1:
            if unit.endswith('ch'):  # For 'inch'
                unit += 'es'
            elif unit not in ['tsp', 'tbsp']:  # Don't pluralize abbreviations
                unit += 's'
        
        return f"{formatted_value} {unit}"