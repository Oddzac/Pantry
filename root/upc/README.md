# UPC Database Converter

This tool converts a UPC map JSON file to a SQLite database for easier querying and integration with other applications.

## Files

- `upc_map.json` - Source JSON file containing UPC product data
- `upc_to_sqlite.py` - Python script to convert JSON to SQLite
- `upc_database.db` - Output SQLite database (created by the script)
- `check_db.py` - Utility script to check database contents

## Usage

### Converting JSON to SQLite

```bash
python upc_to_sqlite.py [json_file_path] [sqlite_file_path]
```

If no arguments are provided, the script will use default paths:
- JSON file: `./upc_map.json`
- SQLite file: `./upc_database.db`

### Checking Database Contents

```bash
python check_db.py
```

## Database Schema

The SQLite database contains a single table `upc_products` with the following columns:

| Column | Type | Description |
|--------|------|-------------|
| upc | TEXT | UPC code (primary key) |
| brand_owner | TEXT | Brand or manufacturer name |
| description | TEXT | Product description |
| category | TEXT | Product category |
| serving_size | REAL | Serving size value |
| serving_size_unit | TEXT | Unit of measurement for serving size |
| household_serving | TEXT | Human-readable serving size description |

## Statistics

- Total products: 452,998
- Unique brands: 22,942
- Unique categories: 352

### Top Categories

1. Candy: 22,897 products
2. Popcorn, Peanuts, Seeds & Related Snacks: 22,074 products
3. Cheese: 18,128 products
4. Ice Cream & Frozen Yogurt: 13,381 products
5. Cookies & Biscuits: 13,333 products
6. Chips, Pretzels & Snacks: 12,536 products
7. Chocolate: 10,844 products
8. Breads & Buns: 10,421 products
9. Pickles, Olives, Peppers & Relishes: 10,419 products
10. Cakes, Cupcakes, Snack Cakes: 9,434 products