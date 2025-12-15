# app/services/scraper_service.py
from typing import Dict, Any, Optional, List
from ....backend.app.services.daraz_scraper import scrape_daraz

def scrape_product_platforms(
    product_name: str,
    moq: Optional[int] = None,
) -> Dict[str, Any]:
    # 1) Daraz se retail data lao
    daraz_items, daraz_search_url = scrape_daraz(product_name, max_items=5)

    # 2) Agar baad me Made-in-China / Alibaba wholesale add karna ho, yahan add karna:
    wholesale_items: List[Dict[str, Any]] = []

    # 3) links_used map
    links_used = {
        "daraz": daraz_search_url,
        # "alibaba": "...", etc (future)
    }

    # 4) Final dict FastAPI response model ke format me
    return {
        "product_name": product_name,
        "links_used": links_used,
        "wholesale": wholesale_items,
        "retail": daraz_items,
    }
