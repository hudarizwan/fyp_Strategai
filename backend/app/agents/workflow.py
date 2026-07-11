"""
LangGraph Workflow for Multi-Agent Orchestration
Manages agent coordination and state flow
"""

from langgraph.graph import StateGraph, END
from typing import Dict, Any
from app.agents.state import AgentState
from app.agents.enhanced_scraper_agent import EnhancedScraperAgent
from app.agents.analysis_agent import AnalysisAgent
import time


def create_workflow():
    """
    Create LangGraph workflow for multi-agent system
    
    Flow:
    1. Enhanced Scraper Agent → 3-tier scraping (Playwright/Traditional/RAG-LLM)
    2. Analysis Agent → Predicts prices
    3. Optimization Agent → Optimizes margins (Day 4)
    """
    
    # Initialize agents
    scraper = EnhancedScraperAgent("scraper_1", "EnhancedScraper")
    analyzer = AnalysisAgent("analyzer_1", "Analyzer")
    # optimizer = OptimizationAgent("optimizer_1", "Optimizer")  # Day 4
    
    # Create state graph
    workflow = StateGraph(AgentState)
    
    # Add agent nodes
    workflow.add_node("scraper", scraper)
    workflow.add_node("analyzer", analyzer)  # ✅ Day 2
    # workflow.add_node("optimizer", optimizer)  # Day 4
    
    # Define conditional routing
    def should_analyze(state: AgentState) -> str:
        """Route to analyzer if scraping succeeded"""
        if state.get("scraping_success"):
            return "analyzer"  # ✅ Day 2
        return "end"
    
    def should_optimize(state: AgentState) -> str:
        """Route to optimizer if analysis succeeded"""
        if state.get("price_prediction"):
            return "end"  # Will be "optimizer" on Day 4
        return "end"
    
    # Build workflow
    workflow.set_entry_point("scraper")
    
    workflow.add_conditional_edges(
        "scraper",
        should_analyze,
        {
            "analyzer": "analyzer",  # ✅ Day 2
            "end": END
        }
    )
    
    # ✅ Day 2: Add analyzer routing
    workflow.add_conditional_edges(
        "analyzer",
        should_optimize,
        {
            # "optimizer": "optimizer",  # Day 4
            "end": END
        }
    )
    
    # Day 4: Add optimizer routing
    # workflow.add_edge("optimizer", END)
    
    # Compile workflow
    app = workflow.compile()
    
    return app


def run_workflow(product_name: str, category: str) -> Dict[str, Any]:
    """
    Run complete multi-agent workflow
    
    Args:
        product_name: Product to analyze
        category: Product category
    
    Returns:
        Final state with all agent outputs
    """
    # Create workflow
    app = create_workflow()
    
    # Initial state
    initial_state: AgentState = {
        'product_name': product_name,
        'category': category,
        'scraped_data': None,
        'scraping_strategy': None,
        'scraping_success': False,
        'scraping_attempts': 0,
        'features': None,
        'price_prediction': None,
        'category_prediction': None,
        'confidence': 0.0,
        'optimized_prices': None,
        'optimization_strategy': None,
        'expected_margin': 0.0,
        'current_agent': '',
        'errors': [],
        'warnings': [],
        'total_time': 0.0,
        'agent_times': {}
    }
    
    # Run workflow
    start_time = time.time()
    
    try:
        result = app.invoke(initial_state)
        
        # Calculate total time
        result['total_time'] = time.time() - start_time
        
        return result
    
    except Exception as e:
        print(f"[Workflow] Error: {e}")
        initial_state['errors'].append(str(e))
        return initial_state


# Test function
if __name__ == "__main__":
    print("Testing LangGraph Workflow...")
    
    result = run_workflow("onikuma k19", "headset")
    
    print("\n=== Workflow Result ===")
    print(f"Success: {result.get('scraping_success')}")
    print(f"Strategy: {result.get('scraping_strategy')}")
    print(f"Data: {bool(result.get('scraped_data'))}")
    print(f"Time: {result.get('total_time'):.2f}s")
