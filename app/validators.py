from fastapi import HTTPException

#Accepted values per filter
VALID_REGIONS = {
    "Dhaka", "Chittagong", "Sylhet", "Rajshahi",
    "Khulna", "Rangpur", "Barisal", "Mymensingh",
}

VALID_FARM_TYPES = {"Small", "Medium", "Large", "Commercial"}

VALID_CROP_CATEGORIES = {
    "Cereal", "Vegetable", "Fruit", "Pulse",
    "Oilseed", "Cash Crop", "Spice",
}

VALID_SEASONS = {"Spring", "Summer", "Autumn", "Winter"}

VALID_GROWING_SEASONS = {"Rabi", "Kharif", "Zaid", "Year-Round"}

VALID_MARKET_TYPES = {
    "Local", "Wholesale", "Export", "Retail", "Government Procurement",
}

VALID_PRICE_TIERS = {"Low", "Medium", "High", "Premium"}

VALID_QUALITY_GRADES = {"A", "B", "C", "D"}

VALID_PESTICIDE_RESIDUES = {"None", "Trace", "Low", "High"}

VALID_WATER_REQUIREMENTS = {"Low", "Medium", "High"}

VALID_YEARS = {2022, 2023, 2024}

VALID_QUARTERS = {1, 2, 3, 4}

VALID_METRICS = {"profit", "revenue", "yield"}


#Helper: raise 422 if value not in allowed set
def validate(value, allowed: set, field_name: str):
    """Raise HTTP 422 if value is not in the allowed set."""
    if value is not None and value not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid value '{value}' for '{field_name}'. "
                   f"Accepted values: {sorted(allowed)}",
        )
