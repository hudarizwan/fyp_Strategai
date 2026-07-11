"""
Simple Database Check - Direct SQL Query
"""

import os
from dotenv import load_dotenv
import psycopg2

# Load environment
load_dotenv()

DB_URL = os.getenv('SUPABASE_DB_URL')

def check_database(product_name: str, category: str):
    """Check if product exists in database"""
    
    print(f"\n{'='*70}")
    print(f"DATABASE CHECK: {product_name} ({category})")
    print(f"{'='*70}\n")
    
    try:
        # Connect to database
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        # Check wholesale
        print("Checking Wholesale Products...")
        cursor.execute("""
            SELECT clean_title, price_pkr, platform, scraped_at 
            FROM wholesale_products 
            WHERE LOWER(product_name) LIKE %s 
            AND LOWER(category) = %s
            LIMIT 5
        """, (f'%{product_name.lower()}%', category.lower()))
        
        wholesale = cursor.fetchall()
        
        if wholesale:
            print(f"Found {len(wholesale)} wholesale products\n")
            for i, row in enumerate(wholesale, 1):
                print(f"  {i}. {row[0]}")
                print(f"     Price: {row[1]} PKR")
                print(f"     Platform: {row[2]}")
                print(f"     Scraped: {row[3]}\n")
        else:
            print("No wholesale products found\n")
        
        # Check retail
        print("Checking Retail Products...")
        cursor.execute("""
            SELECT clean_title, price_pkr, platform, scraped_at 
            FROM retail_products 
            WHERE LOWER(product_name) LIKE %s 
            AND LOWER(category) = %s
            LIMIT 5
        """, (f'%{product_name.lower()}%', category.lower()))
        
        retail = cursor.fetchall()
        
        if retail:
            print(f"Found {len(retail)} retail products\n")
            for i, row in enumerate(retail, 1):
                print(f"  {i}. {row[0]}")
                print(f"     Price: {row[1]} PKR")
                print(f"     Platform: {row[2]}")
                print(f"     Scraped: {row[3]}\n")
        else:
            print("No retail products found\n")
        
        # Summary
        total = len(wholesale) + len(retail)
        print(f"{'='*70}")
        print(f"TOTAL: {total} products in database")
        print(f"  Wholesale: {len(wholesale)}")
        print(f"  Retail: {len(retail)}")
        print(f"{'='*70}\n")
        
        cursor.close()
        conn.close()
        
        return total > 0
    
    except Exception as e:
        print(f"Error: {e}\n")
        return False


if __name__ == "__main__":
    # Test configuration
    PRODUCT_NAME = "hyperx cloud iii"
    CATEGORY = "headset"
    exists = check_database(PRODUCT_NAME, CATEGORY)
    
    if not exists:
        print("⚠️ Product not found in database")
        print("\nTo add data:")
        print("1. Use frontend: http://localhost:5173")
        print("3. Data will be saved to database")
