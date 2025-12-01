from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
from app.services.scraper_service import scrape_product_platforms




router = APIRouter()

# --------------------------
#   Request Model
# --------------------------
class ScrapeRequest(BaseModel):
    product_name: str
    moq: int | None = None      # ✅ User can send MOQ (optional)

# --------------------------
#   Response Models
# --------------------------
class WholesaleItem(BaseModel):
    supplier: str
    moq: int
    unit_price: float
    lead_time: str
    origin: str


class RetailItem(BaseModel):
    seller: str
    platform: str
    list_price: float
    promo: str


class ScrapeResponse(BaseModel):
    product_name: str
    links_used: Dict[str, str]
    wholesale: List[WholesaleItem]
    retail: List[RetailItem]

# --------------------------
#   Endpoint
# --------------------------
@router.post("/start", response_model=ScrapeResponse)
def start_scrape(req: ScrapeRequest):
    """
    Module 1: Scraper Agent
    PK Retailers + Wholesale (MOQ-aware Made-in-China)
    """
    result = scrape_product_platforms(
        product_name=req.product_name,
        moq=req.moq                    # ✅ PASS MOQ to service layer
    )
    return result
