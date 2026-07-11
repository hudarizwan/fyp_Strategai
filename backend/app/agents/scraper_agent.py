"""
Scraper Agent with Database Check and Smart Scraping
Uses epsilon-greedy for strategy learning + database optimization
"""

from app.agents.base_agent import BDIAgent, Goal, Plan
from typing import Dict, Any, List
import numpy as np
from collections import defaultdict
from datetime import datetime, timedelta
import time


class ScraperAgent(BDIAgent):
    """
    Enhanced Adaptive Scraping Agent
    
    Features:
    - Database check (use recent data if available)
    - Live scraping (when needed)
    - Multiple scraping strategies
    - Learns which strategy works best
    - Epsilon-greedy exploration
    - Automatic retry with different strategies
    """
    
    def __init__(self, agent_id: str, name: str = "Scraper"):
        super().__init__(agent_id, name)
        
        # Available strategies
        self.strategies = ['primary', 'fallback', 'aggressive']
        
        # Strategy performance tracking
        self.strategy_rewards = defaultdict(list)
        
        # Exploration rate
        self.epsilon = 0.2
        
        # Max attempts
        self.max_attempts = 3
        
        # Database freshness threshold (24 hours)
        self.freshness_hours = 24
        self.min_products = 5
    
    def generate_goals(self) -> List[Goal]:
        """Generate scraping goals based on beliefs"""
        goals = []
        
        # Check if scraping is needed
        if self.has_belief('product_name') and self.has_belief('category'):
            # Priority 1: Check database first
            goals.append(Goal(
                name="check_database",
                priority=10,
                params={
                    'product': self.get_belief('product_name'),
                    'category': self.get_belief('category')
                }
            ))
        
        # Check if should explore new strategies
        if self.should_explore():
            goals.append(Goal(
                name="explore_strategy",
                priority=5
            ))
        
        return goals
    
    def create_plan(self, goal: Goal) -> Plan:
        """Create scraping plan"""
        if goal.name == "check_database":
            return Plan(steps=[
                "check_database_freshness",
                "decide_scraping_method",
                "execute_scraping",
                "validate_data",
                "record_performance"
            ], context={
                'product': goal.params.get('product'),
                'category': goal.params.get('category'),
                'attempt': 0
            })
        
        return Plan(steps=[])
    
    def execute_action(self, action: str, context: Dict[str, Any]) -> bool:
        """Execute scraping action"""
        try:
            if action == "check_database_freshness":
                product = context['product']
                category = context['category']
                
                # Check database for recent data
                fresh_data = self.get_fresh_database_data(product, category)
                
                if fresh_data:
                    self.log(f"✅ Using database (fresh data available)")
                    self.update_belief('scraped_data', fresh_data)
                    self.update_belief('scraping_success', True)
                    self.update_belief('data_source', 'database')
                    context['use_database'] = True
                else:
                    self.log(f"⚠️ Database data old/missing - will scrape live")
                    context['use_database'] = False
                
                return True
            
            elif action == "decide_scraping_method":
                if context.get('use_database'):
                    # Skip scraping
                    context['skip_scraping'] = True
                else:
                    # Select strategy for live scraping
                    strategy = self.select_strategy()
                    context['strategy'] = strategy
                    context['skip_scraping'] = False
                    self.log(f"Selected strategy: {strategy}")
                
                return True
            
            elif action == "execute_scraping":
                # Skip if using database
                if context.get('skip_scraping'):
                    return True
                
                product = context['product']
                category = context['category']
                strategy = context['strategy']
                
                self.log(f"Scraping live: {product} ({category})")
                
                # Actual scraping
                data = self.scrape_with_strategy(product, category, strategy)
                
                if data:
                    self.update_belief('scraped_data', data)
                    self.update_belief('scraping_success', True)
                    self.update_belief('data_source', 'live')
                    
                    # Record success
                    self.record_strategy_performance(strategy, 1.0)
                    return True
                else:
                    # Try different strategy
                    context['attempt'] += 1
                    if context['attempt'] < self.max_attempts:
                        # Select new strategy
                        context['strategy'] = self.select_strategy()
                        self.log(f"Retry with strategy: {context['strategy']}")
                        return False  # Will retry
                    else:
                        self.update_belief('scraping_success', False)
                        self.record_strategy_performance(strategy, 0.0)
                        return False
            
            elif action == "validate_data":
                data = self.get_belief('scraped_data')
                
                if not data:
                    return False
                
                # Validate data quality
                valid = self.validate_scraped_data(data)
                
                if not valid:
                    self.log("Data validation failed")
                    return False
                
                self.log("Data validated successfully")
                return True
            
            elif action == "record_performance":
                source = self.get_belief('data_source', 'unknown')
                success = self.get_belief('scraping_success', False)
                
                self.log(f"Source: {source}, Success: {success}")
                return True
            
            return False
        
        except Exception as e:
            self.log(f"Error in {action}: {e}")
            return False
    
    def get_fresh_database_data(self, product_name: str, category: str) -> Dict[str, Any]:
        """
        Check database for fresh data
        Returns data if:
        - Data exists
        - Data is recent (< 24 hours)
        - Sufficient quantity (>= 5 products)
        """
        try:
            from app.services.ecdb import ECDB
            db = ECDB()
            
            # Get products from database
            wholesale = db.get_wholesale_by_query(product_name, category)
            retail = db.get_retail_by_query(product_name, category)
            
            if not wholesale and not retail:
                return None
            
            # Check quantity
            total_count = len(wholesale) + len(retail)
            if total_count < self.min_products:
                self.log(f"Database: Only {total_count} products (need {self.min_products})")
                return None
            
            # Check freshness
            all_products = wholesale + retail
            timestamps = [p.get('scraped_at') for p in all_products if p.get('scraped_at')]
            
            if not timestamps:
                return None
            
            latest = max(timestamps)
            if isinstance(latest, str):
                latest = datetime.fromisoformat(latest.replace('Z', '+00:00'))
            
            age = datetime.now() - latest.replace(tzinfo=None)
            
            if age > timedelta(hours=self.freshness_hours):
                self.log(f"Database: Data is {age.total_seconds()/3600:.1f} hours old")
                return None
            
            # Data is fresh!
            self.log(f"Database: Fresh data ({total_count} products, {age.total_seconds()/3600:.1f}h old)")
            
            return {
                'wholesale': wholesale,
                'retail': retail,
                'source': 'database',
                'age_hours': age.total_seconds() / 3600
            }
        
        except Exception as e:
            self.log(f"Database check error: {e}")
            return None
    
    def scrape_with_strategy(self, product: str, category: str, strategy: str) -> Dict[str, Any]:
        """
        Execute scraping with selected strategy
        Integrates with existing scraper service
        """
        try:
            # Import existing scraper
            from app.services.scraper_service import scrape_product_platforms
            
            self.log(f"Executing live scraping...")
            
            # Call existing scraper (already has filters)
            data = scrape_product_platforms(product, category)
            
            return data
        
        except Exception as e:
            self.log(f"Scraping failed: {e}")
            return {}
    
    def validate_scraped_data(self, data: Dict[str, Any]) -> bool:
        """Validate scraped data quality"""
        if not data:
            return False
        
        # Check required fields
        required_fields = ['wholesale', 'retail']
        if not all(field in data for field in required_fields):
            return False
        
        # Check data quantity
        wholesale = data.get('wholesale', {})
        if isinstance(wholesale, dict):
            wholesale_count = sum(len(items) for items in wholesale.values())
        else:
            wholesale_count = len(wholesale)
        retail_count = len(data.get('retail', []))
        
        if wholesale_count == 0 and retail_count == 0:
            return False
        
        return True
    
    def select_strategy(self) -> str:
        """Select scraping strategy using epsilon-greedy"""
        if np.random.random() < self.epsilon:
            # Explore: random strategy
            strategy = np.random.choice(self.strategies)
            return strategy
        else:
            # Exploit: best strategy
            avg_rewards = {
                s: np.mean(self.strategy_rewards[s]) if self.strategy_rewards[s] else 0.5
                for s in self.strategies
            }
            best_strategy = max(avg_rewards, key=avg_rewards.get)
            return best_strategy
    
    def record_strategy_performance(self, strategy: str, reward: float):
        """Record strategy success/failure"""
        self.strategy_rewards[strategy].append(reward)
        
        # Keep last 100 attempts
        if len(self.strategy_rewards[strategy]) > 100:
            self.strategy_rewards[strategy].pop(0)
        
        # Decay epsilon over time
        self.epsilon = max(0.05, self.epsilon * 0.995)
    
    def should_explore(self) -> bool:
        """Decide if should try new strategies"""
        total_attempts = sum(len(rewards) for rewards in self.strategy_rewards.values())
        
        # Explore more in early stages
        if total_attempts < 50:
            return True
        
        # Random exploration
        return np.random.random() < 0.1
    
    def export_state(self) -> Dict[str, Any]:
        """Export state for LangGraph"""
        return {
            'scraped_data': self.get_belief('scraped_data'),
            'scraping_strategy': self.get_belief('data_source'),
            'scraping_success': self.get_belief('scraping_success', False),
            'current_agent': self.name
        }

    """
    Adaptive web scraping agent
    
    Features:
    - Multiple scraping strategies
    - Learns which strategy works best
    - Epsilon-greedy exploration
    - Automatic retry with different strategies
    """
    
    def __init__(self, agent_id: str, name: str = "Scraper"):
        super().__init__(agent_id, name)
        
        # Available strategies
        self.strategies = ['primary', 'fallback', 'aggressive']
        
        # Strategy performance tracking
        self.strategy_rewards = defaultdict(list)
        
        # Exploration rate
        self.epsilon = 0.2
        
        # Max attempts
        self.max_attempts = 3
    
    def generate_goals(self) -> List[Goal]:
        """Generate scraping goals based on beliefs"""
        goals = []
        
        # Check if scraping is needed
        if self.has_belief('product_name') and self.has_belief('category'):
            # Check if not already scraped
            if not self.has_belief('scraped_data'):
                goals.append(Goal(
                    name="scrape_product",
                    priority=10,
                    params={
                        'product': self.get_belief('product_name'),
                        'category': self.get_belief('category')
                    }
                ))
        
        # Check if should explore new strategies
        if self.should_explore():
            goals.append(Goal(
                name="explore_strategy",
                priority=5
            ))
        
        return goals
    
    def create_plan(self, goal: Goal) -> Plan:
        """Create scraping plan"""
        if goal.name == "scrape_product":
            # Select best strategy
            strategy = self.select_strategy()
            
            return Plan(
                steps=[
                    "initialize_scraper",
                    "execute_scraping",
                    "validate_data",
                    "record_performance"
                ],
                context={
                    'strategy': strategy,
                    'product': goal.params.get('product'),
                    'category': goal.params.get('category'),
                    'attempt': 0
                }
            )
        
        return Plan(steps=[])
    
    def execute_action(self, action: str, context: Dict[str, Any]) -> bool:
        """Execute scraping action"""
        try:
            if action == "initialize_scraper":
                strategy = context['strategy']
                self.log(f"Initializing with strategy: {strategy}")
                self.update_belief('scraping_strategy', strategy)
                return True
            
            elif action == "execute_scraping":
                product = context['product']
                category = context['category']
                strategy = context['strategy']
                
                self.log(f"Scraping: {product} ({category})")
                
                # Actual scraping
                data = self.scrape_with_strategy(product, category, strategy)
                
                if data:
                    self.update_belief('scraped_data', data)
                    self.update_belief('scraping_success', True)
                    
                    # Record success
                    self.record_strategy_performance(strategy, 1.0)
                    return True
                else:
                    # Try different strategy
                    context['attempt'] += 1
                    if context['attempt'] < self.max_attempts:
                        # Select new strategy
                        context['strategy'] = self.select_strategy()
                        self.log(f"Retry with strategy: {context['strategy']}")
                        return False  # Will retry
                    else:
                        self.update_belief('scraping_success', False)
                        self.record_strategy_performance(strategy, 0.0)
                        return False
            
            elif action == "validate_data":
                data = self.get_belief('scraped_data')
                
                if not data:
                    return False
                
                # Validate data quality
                valid = self.validate_scraped_data(data)
                
                if not valid:
                    self.log("Data validation failed")
                    return False
                
                self.log("Data validated successfully")
                return True
            
            elif action == "record_performance":
                strategy = context['strategy']
                success = self.get_belief('scraping_success', False)
                
                self.log(f"Strategy {strategy}: {'Success' if success else 'Failed'}")
                return True
            
            return False
        
        except Exception as e:
            self.log(f"Error in {action}: {e}")
            return False
    
    def scrape_with_strategy(self, product: str, category: str, strategy: str) -> Dict[str, Any]:
        """
        Execute scraping with selected strategy
        Integrates with existing scraper service
        """
        try:
            # Import existing scraper
            from app.services.scraper_service import scrape_product_platforms
            
            self.log(f"Executing scraping...")
            
            # Call existing scraper
            data = scrape_product_platforms(product, category)
            
            return data
        
        except Exception as e:
            self.log(f"Scraping failed: {e}")
            return {}
    
    def validate_scraped_data(self, data: Dict[str, Any]) -> bool:
        """Validate scraped data quality"""
        if not data:
            return False
        
        # Check required fields
        required_fields = ['wholesale', 'retail']
        if not all(field in data for field in required_fields):
            return False
        
        # Check data quantity
        wholesale_count = len(data.get('wholesale', []))
        retail_count = len(data.get('retail', []))
        
        if wholesale_count == 0 and retail_count == 0:
            return False
        
        return True
    
    def select_strategy(self) -> str:
        """Select scraping strategy using epsilon-greedy"""
        if np.random.random() < self.epsilon:
            # Explore: random strategy
            strategy = np.random.choice(self.strategies)
            self.log(f"Exploring strategy: {strategy}")
            return strategy
        else:
            # Exploit: best strategy
            avg_rewards = {
                s: np.mean(self.strategy_rewards[s]) if self.strategy_rewards[s] else 0.5
                for s in self.strategies
            }
            best_strategy = max(avg_rewards, key=avg_rewards.get)
            self.log(f"Exploiting best strategy: {best_strategy}")
            return best_strategy
    
    def record_strategy_performance(self, strategy: str, reward: float):
        """Record strategy success/failure"""
        self.strategy_rewards[strategy].append(reward)
        
        # Keep last 100 attempts
        if len(self.strategy_rewards[strategy]) > 100:
            self.strategy_rewards[strategy].pop(0)
        
        # Decay epsilon over time
        self.epsilon = max(0.05, self.epsilon * 0.995)
    
    def should_explore(self) -> bool:
        """Decide if should try new strategies"""
        total_attempts = sum(len(rewards) for rewards in self.strategy_rewards.values())
        
        # Explore more in early stages
        if total_attempts < 50:
            return True
        
        # Random exploration
        return np.random.random() < 0.1
    
    def export_state(self) -> Dict[str, Any]:
        """Export state for LangGraph"""
        return {
            'scraped_data': self.get_belief('scraped_data'),
            'scraping_strategy': self.get_belief('scraping_strategy'),
            'scraping_success': self.get_belief('scraping_success', False),
            'current_agent': self.name
        }
