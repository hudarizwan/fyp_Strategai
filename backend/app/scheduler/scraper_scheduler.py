"""
Scheduled Scraper for POC Products
Runs daily to collect training data
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import sys
sys.path.append('.')

from app.services.scraper_service import scrape_product_platforms
from app.services.ecdb import ECDB
from app.services.nlp_agent import NLPAgent


# 5 POC Products for Electronics
POC_PRODUCTS = [
    {"name": "onikuma k19", "category": "headset"},
    {"name": "logitech k380", "category": "keyboard"},
    {"name": "hyperx cloud", "category": "headset"},
    {"name": "razer deathadder", "category": "mouse"},
    {"name": "corsair k70", "category": "keyboard"}
]


class ScheduledScraper:
    """
    Scheduled scraper for automatic data collection
    
    Features:
    - Daily scraping at 2 AM
    - 5 POC products
    - Automatic database storage
    - Pattern learning for model training
    """
    
    def __init__(self):
        self.db = ECDB()
        self.nlp_agent = NLPAgent()
        self.scheduler = BackgroundScheduler()
        
        print("[Scheduler] Initialized")
    
    def scrape_all_poc_products(self):
        """Scrape all POC products"""
        print(f"\n{'='*50}")
        print(f"[Scheduler] Starting scheduled scrape: {datetime.now()}")
        print(f"{'='*50}\n")
        
        results = {
            'success': [],
            'failed': [],
            'total_products': 0
        }
        
        for product in POC_PRODUCTS:
            try:
                print(f"\n[Scheduler] Scraping: {product['name']} ({product['category']})")
                
                # Scrape (already has filters)
                data = scrape_product_platforms(
                    product['name'],
                    product['category']
                )
                
                if data:
                    # Process with NLP agent
                    processed = self.nlp_agent.process(
                        data,
                        product['name'],
                        product['category']
                    )
                    
                    wholesale_count = len(data.get('wholesale', []))
                    retail_count = len(data.get('retail', []))
                    
                    results['success'].append(product['name'])
                    results['total_products'] += wholesale_count + retail_count
                    
                    print(f"  ✅ Success: {wholesale_count} wholesale, {retail_count} retail")
                else:
                    results['failed'].append(product['name'])
                    print(f"  ❌ Failed: No data")
            
            except Exception as e:
                results['failed'].append(product['name'])
                print(f"  ❌ Error: {e}")
        
        # Summary
        print(f"\n{'='*50}")
        print(f"[Scheduler] Scrape Complete!")
        print(f"  Success: {len(results['success'])}/{len(POC_PRODUCTS)}")
        print(f"  Total Products: {results['total_products']}")
        print(f"  Failed: {results['failed']}")
        print(f"{'='*50}\n")
        
        return results
    
    def start(self):
        """Start the scheduler"""
        # Add daily job at 2 AM
        self.scheduler.add_job(
            self.scrape_all_poc_products,
            CronTrigger(hour=2, minute=0),
            id='daily_scrape',
            name='Daily POC Product Scrape',
            replace_existing=True
        )
        
        self.scheduler.start()
        print("[Scheduler] Started - Daily scrape at 2:00 AM")
    
    def run_now(self):
        """Run scraping immediately (for testing)"""
        print("[Scheduler] Running immediate scrape...")
        return self.scrape_all_poc_products()
    
    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        print("[Scheduler] Stopped")


# Singleton instance
_scheduler_instance = None

def get_scheduler() -> ScheduledScraper:
    """Get scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = ScheduledScraper()
    return _scheduler_instance


# For testing
if __name__ == "__main__":
    scheduler = ScheduledScraper()
    
    print("Running immediate test scrape...")
    results = scheduler.run_now()
    
    print("\n✅ Test complete!")
    print(f"Success: {results['success']}")
    print(f"Failed: {results['failed']}")
