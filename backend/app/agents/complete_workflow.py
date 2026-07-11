"""
Complete Multi-Agent Workflow
Integrates: Scraper → NLP → Analytics
"""

from langgraph.graph import StateGraph, END
from typing import Dict, Any
from app.agents.state import AgentState
from app.agents.enhanced_scraper_agent import EnhancedScraperAgent
from app.agents.nlp_cleaning_agent import NLPCleaningAgent
from app.agents.analytics_agent_ensemble import AnalyticsAgent
import time


def create_complete_workflow():
    """
    Create complete LangGraph workflow
    
    Flow:
    1. Scraper Agent → 3-tier scraping
    2. NLP Agent → Data cleaning & standardization
    3. Analytics Agent → Price prediction (XGBoost + RF)
    """
    
    # Initialize agents
    scraper = EnhancedScraperAgent("scraper_1", "EnhancedScraper")
    nlp = NLPCleaningAgent("nlp_1", "NLP_Cleaner")
    analytics = AnalyticsAgent("analytics_1", "Analytics")
    
    # Create state graph
    workflow = StateGraph(AgentState)
    
    # Add agent nodes
    workflow.add_node("scraper", scraper)
    workflow.add_node("nlp", nlp)
    workflow.add_node("analytics", analytics)
    
    # Define routing
    def should_clean(state: AgentState) -> str:
        """Route to NLP if scraping succeeded"""
        if state.get("scraping_success"):
            return "nlp"
        return "end"
    
    def should_analyze(state: AgentState) -> str:
        """Route to analytics if cleaning succeeded"""
        if state.get("clean_data"):
            return "analytics"
        return "end"
    
    # Build workflow
    workflow.set_entry_point("scraper")
    
    workflow.add_conditional_edges(
        "scraper",
        should_clean,
        {
            "nlp": "nlp",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "nlp",
        should_analyze,
        {
            "analytics": "analytics",
            "end": END
        }
    )
    
    workflow.add_edge("analytics", END)
    
    # Compile workflow
    app = workflow.compile()
    
    return app


def run_complete_workflow(product_name: str, category: str) -> Dict[str, Any]:
    """
    Run complete multi-agent workflow
    
    Args:
        product_name: Product to analyze
        category: Product category
    
    Returns:
        Final state with all agent outputs
    """
    # Create workflow
    app = create_complete_workflow()
    
    # Initial state
    initial_state: AgentState = {
        'product_name': product_name,
        'category': category,
        'scraped_data': None,
        'scraping_strategy': None,
        'scraping_success': False,
        'scraping_attempts': 0,
        'clean_data': None,
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
        print(f"\n🚀 Starting workflow: {product_name} ({category})")
        print("="*70)
        
        result = app.invoke(initial_state)
        
        # Calculate total time
        result['total_time'] = time.time() - start_time
        
        print("\n" + "="*70)
        print("✅ Workflow Complete!")
        print("="*70)
        
        return result
    
    except Exception as e:
        print(f"\n❌ Workflow Error: {e}")
        initial_state['errors'].append(str(e))
        return initial_state


# Test function
if __name__ == "__main__":
    print("\n" + "="*70)
    print("COMPLETE MULTI-AGENT WORKFLOW TEST")
    print("="*70)
    
    # Run workflow
    result = run_complete_workflow("onikuma k19", "headset")
    
    # Display results
    print("\n📊 RESULTS:")
    print("-"*70)
    
    # Scraper results
    print(f"\n1️⃣ SCRAPER:")
    print(f"   Success: {result.get('scraping_success')}")
    print(f"   Source: {result.get('scraping_strategy')}")
    if result.get('scraped_data'):
        data = result['scraped_data']
        w_count = len(data.get('wholesale', []))
        r_count = len(data.get('retail', []))
        print(f"   Products: {w_count} wholesale, {r_count} retail")
    
    # NLP results
    print(f"\n2️⃣ NLP:")
    if result.get('clean_data'):
        clean = result['clean_data']
        w_count = len(clean.get('wholesale', []))
        r_count = len(clean.get('retail', []))
        print(f"   Cleaned: {w_count} wholesale, {r_count} retail")
        print(f"   Status: ✅ Data standardized")
    else:
        print(f"   Status: ❌ No clean data")
    
    # Analytics results
    print(f"\n3️⃣ ANALYTICS:")
    if result.get('price_prediction'):
        print(f"   Prediction: {result['price_prediction']:.2f} PKR")
        print(f"   Confidence: {result.get('confidence', 0):.2f}")
        if result.get('xgb_prediction'):
            print(f"   XGBoost: {result['xgb_prediction']:.2f} PKR")
        if result.get('rf_prediction'):
            print(f"   Random Forest: {result['rf_prediction']:.2f} PKR")
    else:
        print(f"   Status: ⚠️ Models not trained")
    
    # Performance
    print(f"\n⏱️ PERFORMANCE:")
    print(f"   Total Time: {result.get('total_time', 0):.2f}s")
    
    # Errors
    if result.get('errors'):
        print(f"\n⚠️ ERRORS:")
        for error in result['errors']:
            print(f"   - {error}")
    
    print("\n" + "="*70)
    print("🎯 Workflow Test Complete!")
    print("="*70)
