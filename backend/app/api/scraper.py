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
    links_used: Dict[str, str]       # <-- REQUIRED FIELD
    wholesale: List[WholesaleItem]
    retail: List[RetailItem]

# --------------------------
#   Endpoint
# --------------------------
@router.post("/start", response_model=ScrapeResponse)
def start_scrape(req: ScrapeRequest):
    """
    Module 1: Scraper Agent
    Returns REAL scraped data from PK retailers + wholesale sources.
    """
    return scrape_product_platforms(req.product_name)
