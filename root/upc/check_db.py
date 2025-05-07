#!/usr/bin/env python3
"""
Check SQLite database contents

This script examines the UPC database structure and provides statistics
about the data. It works with both the structure created by upc_to_sqlite.py
and the structure created by scanner.py.
"""

import sqlite3
import os
import sys
from pathlib import Path

def check_database(db_path):
    """Check the contents of the SQLite database"""
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return False
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # First, determine the database structure by checking which tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [table[0] for table in cursor.fetchall()]
    print(f"Database tables: {', '.join(tables)}")
    
    if 'upc_products' in tables:
        # This is the structure created by upc_to_sqlite.py
        check_upc_products_structure(conn)
    elif 'food_items' in tables:
        # This is the structure created by scanner.py
        check_food_items_structure(conn)
    else:
        print("Unknown database structure. No recognized tables found.")
    
    conn.close()
    return True

def check_upc_products_structure(conn):
    """Check the database with upc_products table structure"""
    cursor = conn.cursor()
    
    # Get total count
    cursor.execute('SELECT COUNT(*) FROM upc_products')
    count = cursor.fetchone()[0]
    print(f'Total products in database: {count}')
    
    # Get sample data
    cursor.execute('SELECT * FROM upc_products LIMIT 5')
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    
    print('\nSample data (first 5 rows):')
    for row in rows:
        print('\n--- Product ---')
        for i in range(len(columns)):
            print(f'{columns[i]}: {row[i]}')
    
    # Get some statistics
    cursor.execute('SELECT COUNT(DISTINCT brand_owner) FROM upc_products')
    brand_count = cursor.fetchone()[0]
    print(f'\nNumber of unique brands: {brand_count}')
    
    cursor.execute('SELECT COUNT(DISTINCT category) FROM upc_products')
    category_count = cursor.fetchone()[0]
    print(f'Number of unique categories: {category_count}')
    
    cursor.execute('SELECT category, COUNT(*) as count FROM upc_products GROUP BY category ORDER BY count DESC LIMIT 10')
    top_categories = cursor.fetchall()
    print('\nTop 10 categories:')
    for category, count in top_categories:
        print(f'  {category}: {count} products')

def check_food_items_structure(conn):
    """Check the database with food_items table structure"""
    cursor = conn.cursor()
    
    # Get total count
    cursor.execute('SELECT COUNT(*) FROM food_items')
    count = cursor.fetchone()[0]
    print(f'Total products in database: {count}')
    
    # Get sample data
    cursor.execute('SELECT * FROM food_items LIMIT 5')
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    
    print('\nSample data (first 5 rows):')
    for row in rows:
        print('\n--- Product ---')
        for i in range(len(columns)):
            print(f'{columns[i]}: {row[i]}')
    
    # Get some statistics
    cursor.execute('SELECT COUNT(DISTINCT brand_owner) FROM food_items')
    brand_count = cursor.fetchone()[0]
    print(f'\nNumber of unique brands: {brand_count}')
    
    cursor.execute('SELECT COUNT(DISTINCT food_category) FROM food_items')
    category_count = cursor.fetchone()[0]
    print(f'Number of unique categories: {category_count}')
    
    cursor.execute('SELECT food_category, COUNT(*) as count FROM food_items GROUP BY food_category ORDER BY count DESC LIMIT 10')
    top_categories = cursor.fetchall()
    print('\nTop 10 categories:')
    for category, count in top_categories:
        print(f'  {category}: {count} products')
    
    # Check the checked_upcs table if it exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='checked_upcs'")
    if cursor.fetchone():
        cursor.execute('SELECT COUNT(*) FROM checked_upcs')
        checked_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM checked_upcs WHERE found = 1')
        found_count = cursor.fetchone()[0]
        
        print(f'\nChecked UPCs: {checked_count} (Found: {found_count}, Not Found: {checked_count - found_count})')

def main():
    """Main function to run the script"""
    # Get the directory of this script
    script_dir = Path(__file__).parent.absolute()
    
    # Set default path
    db_path = script_dir / "upc_database.db"
    
    # Check if command line argument is provided
    if len(sys.argv) > 1:
        db_path = Path(sys.argv[1])
    
    check_database(db_path)

if __name__ == "__main__":
    main()