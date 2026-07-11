"""
Agent State Definition for LangGraph
Defines the shared state structure for all agents
"""

from typing import TypedDict, List, Dict, Any, Optional


class AgentState(TypedDict, total=False):
    """
    Shared state for multi-agent system
    
    Flow:
    1. Scraper Agent: Collects data
    2. Analysis Agent: Predicts prices
    3. Optimization Agent: Optimizes margins
    """
    
    # === INPUT ===
    product_name: str
    category: str
    
    # === SCRAPER OUTPUT ===
    scraped_data: Optional[Dict[str, Any]]
    scraping_strategy: Optional[str]
    scraping_success: bool
    scraping_attempts: int
    
    # === ANALYSIS OUTPUT ===
    features: Optional[List[float]]
    price_prediction: Optional[Dict[str, float]]
    category_prediction: Optional[str]
    confidence: float
    
    # === OPTIMIZATION OUTPUT ===
    optimized_prices: Optional[Dict[str, float]]
    optimization_strategy: Optional[str]
    expected_margin: float
    
    # === META ===
    current_agent: str
    errors: List[str]
    warnings: List[str]
    
    # === PERFORMANCE ===
    total_time: float
    agent_times: Dict[str, float]
