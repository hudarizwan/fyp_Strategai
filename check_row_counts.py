
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv(r'c:\Users\USER\Downloads\StrategaAi\StrategaAi\backend\.env')

db_url = os.getenv('SUPABASE_DB_URL')

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM wholesale_products")
    wholesale_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM retail_products")
    retail_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM recommendations")
    rec_count = cur.fetchone()[0]
    
    print(f"Wholesale Products: {wholesale_count}")
    print(f"Retail Products: {retail_count}")
    print(f"Recommendations: {rec_count}")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
