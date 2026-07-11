from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
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
    normalize: bool = False
    persist: bool = False
    use_parallel: bool = True
    

# --------------------------
#   Wholesale Item
# --------------------------
class WholesaleItem(BaseModel):
    platform: str
    supplier: str
    moq: int
    unit_price: float
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
    platform: str
    list_price: float
    promo: str
    url: str | None = None
    title: str | None = None
    detail: Dict[str, Any] | None = None


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
#   Main Endpoint (Fast)
# --------------------------
@router.post("/start")
def start_scrape(req: ScrapeRequest):
    """
    Verified scraper endpoint.
    Returns the current wholesale + retail scrape payload used by the frontend.
    """
    result = scrape_product_platforms(
        product_name=req.product_name,
        category=req.category,
        normalize=req.normalize,
        persist=req.persist,
        use_parallel=req.use_parallel,
    )
    return jsonable_encoder(result)
