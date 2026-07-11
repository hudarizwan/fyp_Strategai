
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv(r'c:\Users\USER\Downloads\StrategaAi\StrategaAi\backend\.env')
db_url = os.getenv('SUPABASE_DB_URL')

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    print("--- LAST 5 WHOLESALE PRODUCTS ---")
    cur.execute("SELECT product_name, category, clean_title, price_pkr FROM wholesale_products ORDER BY id DESC LIMIT 5")
    for row in cur.fetchall():
        print(row)
        
    print("\n--- LAST 5 RETAIL PRODUCTS ---")
    cur.execute("SELECT product_name, category, clean_title, price_pkr FROM retail_products ORDER BY id DESC LIMIT 5")
    for row in cur.fetchall():
        print(row)
        
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
