from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.services.scraper_service import scrape_product_platforms

router = APIRouter()


# --------------------------
#   Request Model
# --------------------------
class ScrapeRequest(BaseModel):
    product_name: str
    category: str             
    

# --------------------------
#   Wholesale Item
# --------------------------
class WholesaleItem(BaseModel):
    platform: str                # made-in-china

    supplier: str
    moq: int
    unit_price: float            # USD
    unit_price_pkr: float | None = None
    currency: str | None = None

    origin: str

    moq_listing: int | None = None
    attributes_listing: Dict[str, str] = {}


# --------------------------
#   Retail Item
# --------------------------
class RetailItem(BaseModel):
    seller: str
    platform: str               # "mega.pk" / "homeshopping" / "telemart" / "daraz"
    list_price: float
    promo: str
    url: str | None = None
    title: str | None = None
    detail: Dict[str, Any] | None = None  # daraz/homeshopping/mega detail etc.


# --------------------------
#   Response Model
# --------------------------
class ScrapeResponse(BaseModel):
    product_name: str
    links_used: Dict[str, Any]

    # wholesale: dict of platform -> list[WholesaleItem]
    wholesale: Dict[str, List[WholesaleItem]]
    retail: List[RetailItem]


# --------------------------
#   Endpoint
# --------------------------
@router.post("/start", response_model=ScrapeResponse)
def start_scrape(req: ScrapeRequest):
    """
    Module 1: Scraper Agent
    Made-in-China wholesale + PK Retail (Mega, Homeshopping, Telemart, Daraz)
    """
    result = scrape_product_platforms(
        product_name=req.product_name,
        category=req.category
        
    )
    return result
