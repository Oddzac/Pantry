import sqlite3
import os
import sys
import requests
import zipfile
import io
import csv
import json
import time
import tempfile
import shutil

class FoodDataManager:
    """
    Manages food data with on-demand downloading and processing capabilities.
    Uses proper database connection handling to prevent locking issues.
    """
    
    # URLs for the data sources
    CSV_URL = "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_branded_food_csv_2025-04-24.zip"
    JSON_URL = "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_branded_food_json_2025-04-24.zip"
    
    # Essential fields to extract
    ESSENTIAL_FIELDS = [
        "brandOwner", 
        "description", 
        "gtinUpc", 
        "brandedFoodCategory", 
        "servingSize", 
        "servingSizeUnit", 
        "householdServingFullText"
    ]
    
    def __init__(self, db_path):
        """
        Initialize the food data manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.ensure_database_exists()
        
        # Cache for CSV data
        self.csv_temp_dir = None
        self.branded_food_path = None
    
    def ensure_database_exists(self):
        """
        Make sure the database exists and has the correct schema.
        If it doesn't exist, create a minimal version.
        """
        db_exists = os.path.exists(self.db_path)
        
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if not db_exists:
                print(f"Creating new database at {self.db_path}")
                
                # Create the food_items table
                cursor.execute('''
                CREATE TABLE food_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    upc TEXT NOT NULL,
                    brand_owner TEXT,
                    description TEXT,
                    food_category TEXT,
                    serving_size REAL,
                    serving_size_unit TEXT,
                    household_serving TEXT
                )
                ''')
                
                # Create an index on the UPC field for fast lookups
                cursor.execute('CREATE INDEX idx_upc ON food_items(upc)')
                
                # Create a table to track which UPCs we've already checked online
                cursor.execute('''
                CREATE TABLE checked_upcs (
                    upc TEXT PRIMARY KEY,
                    checked_timestamp INTEGER,
                    found INTEGER
                )
                ''')
                
                conn.commit()
        except sqlite3.Error as e:
            print(f"Database error during initialization: {e}")
        finally:
            if conn:
                conn.close()
    
    def lookup_food_by_upc(self, upc):
        """
        Look up food items by UPC code, first in local database,
        then online if not found locally.
        
        Args:
            upc: The UPC code to look up
        
        Returns:
            List of food items matching the UPC
        """
        # First, check if we have this UPC locally
        local_results = self._lookup_local(upc)
        
        if local_results:
            print(f"Found {len(local_results)} items with UPC {upc} in local database:")
            self._print_results(local_results)
            return local_results
        
        # Check if we've already looked for this UPC online
        if self._already_checked_online(upc):
            print(f"No items found with UPC {upc} (previously checked online)")
            # Prompt user to manually enter product details
            manual_entry = self._prompt_for_manual_entry(upc)
            if manual_entry:
                self._save_to_local_db([manual_entry])
                return [manual_entry]
            return []
        
        # Not found locally, try to find it online
        print(f"UPC {upc} not found in local database. Checking online...")
        online_results = self._lookup_online(upc)
        
        if online_results:
            print(f"Found {len(online_results)} items with UPC {upc} online:")
            self._print_results(online_results)
            
            # Save these results to the local database
            self._save_to_local_db(online_results)
            return online_results
        else:
            print(f"No items found with UPC {upc} online")
            
            # Prompt user to manually enter product details
            manual_entry = self._prompt_for_manual_entry(upc)
            if manual_entry:
                self._save_to_local_db([manual_entry])
                self._mark_as_checked(upc, found=True)
                return [manual_entry]
            else:
                # Mark this UPC as checked but not found
                self._mark_as_checked(upc, found=False)
                return []
    
    def _prompt_for_manual_entry(self, upc):
        """
        Prompt the user to manually enter product details.
        
        Args:
            upc: The UPC code for the product
            
        Returns:
            Dictionary with product details or None if user cancels
        """
        print("\n" + "="*50)
        print(f"Product with UPC {upc} not found. Would you like to enter details manually?")
        choice = input("Enter 'y' to continue or any other key to skip: ").strip().lower()
        
        if choice != 'y':
            return None
        
        print("\nPlease enter the following product details:")
        brand_owner = input("Brand name: ").strip()
        description = input("Product description: ").strip()
        category = input("Product category (e.g., Cereal, Snacks, Beverages): ").strip()
        
        serving_size = None
        while serving_size is None:
            try:
                serving_size_input = input("Serving size (numeric value only): ").strip()
                if serving_size_input:
                    serving_size = float(serving_size_input)
                else:
                    serving_size = 0
            except ValueError:
                print("Please enter a valid number.")
        
        serving_size_unit = input("Serving size unit (e.g., g, ml, oz): ").strip()
        household_serving = input("Household serving (e.g., 1 cup, 2 tbsp): ").strip()
        
        return {
            "gtinUpc": upc,
            "brandOwner": brand_owner,
            "description": description,
            "brandedFoodCategory": category,
            "servingSize": serving_size,
            "servingSizeUnit": serving_size_unit,
            "householdServingFullText": household_serving
        }
    
    def _lookup_local(self, upc):
        """
        Look up a UPC in the local database.
        
        Args:
            upc: The UPC code to look up
        
        Returns:
            List of dictionaries with food item data
        """
        conn = None
        items = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # This enables column access by name
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM food_items WHERE upc = ?", (upc,))
            results = cursor.fetchall()
            
            # Convert to list of dictionaries
            for row in results:
                items.append({
                    "id": row["id"],
                    "upc": row["upc"],
                    "brandOwner": row["brand_owner"],
                    "description": row["description"],
                    "brandedFoodCategory": row["food_category"],
                    "servingSize": row["serving_size"],
                    "servingSizeUnit": row["serving_size_unit"],
                    "householdServingFullText": row["household_serving"]
                })
        
        except sqlite3.Error as e:
            print(f"Database error during local lookup: {e}")
        finally:
            if conn:
                conn.close()
        
        return items
    
    def _already_checked_online(self, upc):
        """
        Check if we've already looked for this UPC online.
        
        Args:
            upc: The UPC code to check
        
        Returns:
            Boolean indicating if we've already checked this UPC
        """
        conn = None
        result = False
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT found FROM checked_upcs WHERE upc = ?", (upc,))
            row = cursor.fetchone()
            
            result = row is not None and row[0] == 0
        
        except sqlite3.Error as e:
            print(f"Database error during checked_upcs lookup: {e}")
        finally:
            if conn:
                conn.close()
        
        return result
    
    def _mark_as_checked(self, upc, found=True):
        """
        Mark a UPC as having been checked online.
        
        Args:
            upc: The UPC code to mark
            found: Whether the UPC was found online
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT OR REPLACE INTO checked_upcs (upc, checked_timestamp, found) VALUES (?, ?, ?)",
                (upc, int(time.time()), 1 if found else 0)
            )
            
            conn.commit()
        
        except sqlite3.Error as e:
            print(f"Database error during marking UPC as checked: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
    
    def _lookup_online(self, upc):
        """
        Look up a UPC in the online data sources using the most efficient method.
        
        Args:
            upc: The UPC code to look up
        
        Returns:
            List of dictionaries with food item data
        """
        # Try the API approach first (much more efficient)
        print(f"Looking up UPC {upc} using USDA API...")
        api_results = self._lookup_online_api(upc)
        if api_results:
            return api_results
        
        # If API fails, try the direct CSV approach
        print(f"API lookup failed. Trying direct CSV download...")
        return self._lookup_online_csv_direct(upc)
    
    def _lookup_online_api(self, upc):
        """
        Look up a UPC using the USDA FoodData Central API.
        This is much more efficient than downloading the entire dataset.
        
        Args:
            upc: The UPC code to look up
        
        Returns:
            List of dictionaries with food item data
        """
        try:
            # USDA FoodData Central API endpoint
            # Note: You should register for your own API key at https://fdc.nal.usda.gov/api-key-signup.html
            # This is a demo key with limited usage
            api_key = "DEMO_KEY"
            api_url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key={api_key}&query={upc}&dataType=Branded"
            
            print(f"Querying USDA API for UPC {upc}...")
            start_time = time.time()
            
            response = requests.get(api_url)
            if response.status_code != 200:
                print(f"API request failed with status code {response.status_code}")
                return []
            
            data = response.json()
            
            if 'foods' not in data or len(data['foods']) == 0:
                print(f"No foods found in API response for UPC {upc}")
                return []
            
            results = []
            for food in data['foods']:
                # Check if this is the exact UPC we're looking for
                if 'gtinUpc' in food and food['gtinUpc'] == upc:
                    # Extract essential fields
                    item = {}
                    for field in self.ESSENTIAL_FIELDS:
                        if field in food:
                            item[field] = food[field]
                    
                    if item:
                        results.append(item)
            
            elapsed_time = time.time() - start_time
            print(f"API lookup completed in {elapsed_time:.2f} seconds")
            
            return results
            
        except Exception as e:
            print(f"Error during API lookup: {e}")
            return []
    
    def _lookup_online_csv_direct(self, upc):
        """
        Look up a UPC by directly downloading and searching the CSV file.
        This is more efficient than downloading the entire JSON file.
        
        Args:
            upc: The UPC code to look up
        
        Returns:
            List of dictionaries with food item data
        """
        try:
            # Check if we already have the CSV data cached
            if not self.branded_food_path or not os.path.exists(self.branded_food_path):
                # We need to download and extract the CSV
                self._download_and_extract_csv()
                
                if not self.branded_food_path:
                    print("Failed to download and extract CSV data")
                    return []
            
            print(f"Searching for UPC {upc} in CSV file...")
            start_time = time.time()
            results = []
            
            # Process the CSV file
            with open(self.branded_food_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('gtinUpc') == upc:
                        # Extract essential fields
                        item = {}
                        for field in self.ESSENTIAL_FIELDS:
                            if field in row:
                                item[field] = row[field]
                        
                        if item:
                            results.append(item)
                            print(f"Found matching UPC {upc} in CSV file")
            
            elapsed_time = time.time() - start_time
            print(f"CSV lookup completed in {elapsed_time:.2f} seconds")
            
            return results
                
        except Exception as e:
            print(f"Error during CSV lookup: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _download_and_extract_csv(self):
        """
        Download and extract the CSV data, caching it for future use.
        """
        # URL for the branded foods CSV file (smaller than the JSON)
        csv_url = self.CSV_URL
        
        print("Downloading CSV data...")
        start_time = time.time()
        
        # Create a temporary directory to extract files if we don't have one already
        if not self.csv_temp_dir:
            self.csv_temp_dir = tempfile.mkdtemp()
        
        try:
            # Download the ZIP file
            zip_path = os.path.join(self.csv_temp_dir, "food_data.zip")
            
            print("Downloading ZIP file...")
            with requests.get(csv_url, stream=True) as response:
                response.raise_for_status()
                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            
            print("Extracting ZIP file...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.csv_temp_dir)
            
            # Look for the branded_food.csv file
            self.branded_food_path = None
            for root, dirs, files in os.walk(self.csv_temp_dir):
                for file in files:
                    if file.endswith('.csv') and 'branded_food' in file:
                        self.branded_food_path = os.path.join(root, file)
                        break
                if self.branded_food_path:
                    break
            
            if not self.branded_food_path:
                print("Could not find branded_food.csv in the ZIP file")
                return
            
            elapsed_time = time.time() - start_time
            print(f"CSV download and extraction completed in {elapsed_time:.2f} seconds")
            
        except Exception as e:
            print(f"Error during CSV download and extraction: {e}")
            import traceback
            traceback.print_exc()
    
    def cleanup(self):
        """
        Clean up temporary files and directories.
        """
        if self.csv_temp_dir and os.path.exists(self.csv_temp_dir):
            try:
                shutil.rmtree(self.csv_temp_dir)
                self.csv_temp_dir = None
                self.branded_food_path = None
                print("Cleaned up temporary CSV data")
            except Exception as e:
                print(f"Error cleaning up temporary directory: {e}")
    
    def _save_to_local_db(self, items):
        """
        Save food items to the local database.
        
        Args:
            items: List of food item dictionaries
        """
        if not items:
            return
        
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Begin transaction
            conn.execute("BEGIN TRANSACTION")
            
            for item in items:
                cursor.execute('''
                INSERT INTO food_items (
                    upc, 
                    brand_owner, 
                    description, 
                    food_category, 
                    serving_size, 
                    serving_size_unit, 
                    household_serving
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    item.get('gtinUpc', ''),
                    item.get('brandOwner', ''),
                    item.get('description', ''),
                    item.get('brandedFoodCategory', ''),
                    item.get('servingSize', None),
                    item.get('servingSizeUnit', ''),
                    item.get('householdServingFullText', '')
                ))
            
            # Mark this UPC as checked and found in the same transaction
            cursor.execute(
                "INSERT OR REPLACE INTO checked_upcs (upc, checked_timestamp, found) VALUES (?, ?, ?)",
                (items[0].get('gtinUpc', ''), int(time.time()), 1)
            )
            
            # Commit the transaction
            conn.commit()
            
            print(f"Saved {len(items)} items to local database")
        
        except sqlite3.Error as e:
            print(f"Database error during save: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
    
    def _print_results(self, items):
        """
        Print food item results in a readable format.
        
        Args:
            items: List of food item dictionaries
        """
        for item in items:
            print(f"UPC: {item.get('upc', '')}")
            print(f"Brand: {item.get('brandOwner', '')}")
            print(f"Description: {item.get('description', '')}")
            print(f"Category: {item.get('brandedFoodCategory', '')}")
            print(f"Serving Size: {item.get('servingSize', '')} {item.get('servingSizeUnit', '')}")
            print(f"Household Serving: {item.get('householdServingFullText', '')}")
            print()

def interactive_lookup(db_path):
    """
    Interactive mode that prompts the user for UPC codes and looks them up.
    
    Args:
        db_path: Path to the SQLite database file
    """
    data_manager = FoodDataManager(db_path)
    
    try:
        print(f"Food Database Lookup Tool (On-Demand Version)")
        print(f"Database: {db_path}")
        print("Enter a UPC/barcode to look up food information")
        print("Items not found locally will be searched online")
        print("Type 'exit', 'quit', or 'q' to exit the program")
        print("-" * 50)
        
        while True:
            upc = input("\nEnter UPC/barcode: ").strip()
            
            # Check for exit commands
            if upc.lower() in ['exit', 'quit', 'q']:
                print("Exiting program. Goodbye!")
                break
            
            # Skip empty input
            if not upc:
                continue
            
            # Look up the UPC
            data_manager.lookup_food_by_upc(upc)
    finally:
        # Clean up temporary files when exiting
        data_manager.cleanup()

def import_from_existing_db(source_db_path, target_db_path):
    """
    Import data from an existing database.
    
    Args:
        source_db_path: Path to the source SQLite database
        target_db_path: Path to the target SQLite database
    """
    if not os.path.exists(source_db_path):
        print(f"Source database {source_db_path} does not exist")
        return
    
    print(f"Importing data from {source_db_path} to {target_db_path}...")
    
    # Create the target database if it doesn't exist
    data_manager = FoodDataManager(target_db_path)
    
    source_conn = None
    target_conn = None
    
    try:
        # Connect to both databases
        source_conn = sqlite3.connect(source_db_path)
        source_conn.row_factory = sqlite3.Row
        source_cursor = source_conn.cursor()
        
        target_conn = sqlite3.connect(target_db_path)
        target_cursor = target_conn.cursor()
        
        # Begin transaction
        target_conn.execute("BEGIN TRANSACTION")
        
        # Get all food items from the source database
        source_cursor.execute("SELECT * FROM food_items")
        rows = source_cursor.fetchall()
        
        print(f"Found {len(rows)} items in source database")
        
        # Insert each item into the target database
        for row in rows:
            target_cursor.execute('''
            INSERT OR IGNORE INTO food_items (
                upc, 
                brand_owner, 
                description, 
                food_category, 
                serving_size, 
                serving_size_unit, 
                household_serving
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['upc'],
                row['brand_owner'],
                row['description'],
                row['food_category'],
                row['serving_size'],
                row['serving_size_unit'],
                row['household_serving']
            ))
        
        # Get all checked UPCs from the source database
        source_cursor.execute("SELECT * FROM checked_upcs")
        rows = source_cursor.fetchall()
        
        print(f"Found {len(rows)} checked UPCs in source database")
        
        # Insert each checked UPC into the target database
        for row in rows:
            target_cursor.execute('''
            INSERT OR IGNORE INTO checked_upcs (
                upc,
                checked_timestamp,
                found
            ) VALUES (?, ?, ?)
            ''', (
                row['upc'],
                row['checked_timestamp'],
                row['found']
            ))
        
        # Commit the transaction
        target_conn.commit()
        
        print("Import completed successfully")
    
    except sqlite3.Error as e:
        print(f"Database error during import: {e}")
        if target_conn:
            target_conn.rollback()
    finally:
        # Close the connections
        if source_conn:
            source_conn.close()
        if target_conn:
            target_conn.close()

if __name__ == "__main__":
    # Check for import command
    if len(sys.argv) > 1 and sys.argv[1] == "import" and len(sys.argv) == 4:
        source_db_path = sys.argv[2]
        target_db_path = sys.argv[3]
        import_from_existing_db(source_db_path, target_db_path)
    else:
        # Use the provided database path or default to a local file
        if len(sys.argv) > 1:
            db_path = sys.argv[1]
        else:
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "upc_database.db")
        
        interactive_lookup(db_path)