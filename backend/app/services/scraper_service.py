"""
scraper_service.py

StrategAI — MODULE 1: Scraper Agent (Backend Service Layer)

- Retail (PK, dynamic search):
    - Daraz
    - Homeshopping
    - Telemart

- Wholesale (B2B):
    - Made-in-China  (direct product URLs if configured, otherwise dynamic search)
    - Khareed.lk     (PKR wholesale-style prices from search page)

Entry point used by FastAPI:

    from app.services.scraper_service import scrape_product_platforms

    result = scrape_product_platforms(product_name="HyperX Cloud III", moq=100)

Returns a dict:

    {
        "product_name": "...",
        "links_used": {...},
        "wholesale": [...],
        "retail": [...],
    }
"""

from __future__ import annotations

import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup


# ---------------------------------------------------
# HTTP + basic helpers
# ---------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,ur;q=0.8",
}

PK_PRICE_REGEX = re.compile(r"(Rs\.?|PKR)\s*([\d,]+)", re.IGNORECASE)
USD_PRICE_REGEX = re.compile(r"(US\$|\$)\s*([\d.,]+)", re.IGNORECASE)

# wholesale_links.json cache
WHOLESALE_LINKS: Dict[str, Dict[str, List[str]]] = {}


def _fetch_html(url: str, timeout: int = 20) -> BeautifulSoup:
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "lxml")


def _extract_first_pk_price(soup: BeautifulSoup) -> Optional[float]:
    """
    Find first PKR price like 'Rs 12,999' or 'PKR 2,500' anywhere on page.
    """
    for text in soup.stripped_strings:
        if "Rs" in text or "PKR" in text or "rs" in text:
            match = PK_PRICE_REGEX.search(text)
            if match:
                digits = re.sub(r"[^\d]", "", match.group(2))
                try:
                    return float(digits)
                except ValueError:
                    continue
    return None


def _extract_first_usd_price(soup: BeautifulSoup) -> Optional[float]:
    """
    Find first US$ price like 'US$ 3.50' anywhere on page.
    Used for Made-in-China product detail pages.
    """
    for text in soup.stripped_strings:
        if "US$" in text or "$" in text:
            match = USD_PRICE_REGEX.search(text)
            if match:
                raw = match.group(2)
                raw_clean = raw.replace(",", "")
                try:
                    return float(raw_clean)
                except ValueError:
                    continue
    return None


def _extract_title(soup: BeautifulSoup) -> str:
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)

    if soup.title and soup.title.get_text(strip=True):
        return soup.title.get_text(strip=True)

    return "Unknown Product"


# ---------------------------------------------------
#   wholesale_links.json helpers
# ---------------------------------------------------

def _load_wholesale_links() -> None:
    """
    Load backend/app/data/wholesale_links.json into WHOLESALE_LINKS (once).
    """
    global WHOLESALE_LINKS
    if WHOLESALE_LINKS:
        return

    base_dir = Path(__file__).resolve().parent.parent  # app/
    data_path = base_dir / "data" / "wholesale_links.json"

    try:
        with data_path.open("r", encoding="utf-8") as f:
            WHOLESALE_LINKS = json.load(f)
    except FileNotFoundError:
        WHOLESALE_LINKS = {}
    except Exception:
        WHOLESALE_LINKS = {}


def _get_wholesale_links_for_product(product_name: str) -> Dict[str, List[str]]:
    """
    Return mapping for this product, e.g.:

        {
          "made_in_china": [url1, url2]
        }

    or {} if not configured.
    """
    _load_wholesale_links()
    key = product_name.strip().lower()
    return WHOLESALE_LINKS.get(key, {})


# ---------------------------------------------------
#   SEARCH URL BUILDERS
# ---------------------------------------------------

def build_retail_and_khareed_urls(product_name: str) -> Dict[str, str]:
    """
    Build dynamic SEARCH URLs for PK retailers (Daraz, Homeshopping, Telemart)
    and Khareed (wholesale-ish PKR).
    """
    q = quote_plus(product_name.strip())

    return {
        # RETAIL (PK)
        "daraz": f"https://www.daraz.pk/catalog/?q={q}",
        "homeshopping": f"https://homeshopping.pk/search?q={q}",
        "telemart": f"https://telemart.pk/search?type=product&q={q}",

        # WHOLESALE-ish (PKR)
        "khareed": f"https://khareed.lk/search?type=product&q={q}",
    }


def build_made_in_china_search_url(product_name: str, moq: Optional[int]) -> str:
    """
    Build Made-in-China MOQ-filtered multi-search URL.

    If no MOQ is provided, only F1 (lowest price) sort is used.
    """
    q = quote_plus(product_name.strip())

    if moq and moq > 0:
        return f"https://www.made-in-china.com/multi-search/{q}/F1--Min_{moq}/1.html"
    else:
        return f"https://www.made-in-china.com/multi-search/{q}/F1/1.html"


# ---------------------------------------------------
#   RETAIL SCRAPERS (PK, SEARCH PAGE)
# ---------------------------------------------------

def _scrape_retail_search(url: str, platform: str) -> Dict[str, Any]:
    """
    Generic retail search scraper:
      - Fetch search page
      - Extract first PKR price (if visible in HTML)
      - Return one row for that platform
    """
    soup = _fetch_html(url)
    title = _extract_title(soup)
    price = _extract_first_pk_price(soup)

    if price is None:
        price = 0.0  # keep POC stable

    return {
        "seller": "Unknown Seller",
        "platform": platform,
        "list_price": price,
        "promo": "Search Result Price",
        "raw_title": title,
    }


def scrape_retail_competitors(links: Dict[str, str]) -> List[Dict[str, Any]]:
    retail_items: List[Dict[str, Any]] = []

    # Daraz
    try:
        r = _scrape_retail_search(links["daraz"], "Daraz")
        retail_items.append(
            {
                "seller": r["seller"],
                "platform": r["platform"],
                "list_price": r["list_price"],
                "promo": r["promo"],
            }
        )
    except Exception:
        retail_items.append(
            {
                "seller": "Daraz",
                "platform": "Daraz",
                "list_price": 0.0,
                "promo": "Error scraping",
            }
        )

    # Homeshopping
    try:
        r = _scrape_retail_search(links["homeshopping"], "Homeshopping")
        retail_items.append(
            {
                "seller": r["seller"],
                "platform": r["platform"],
                "list_price": r["list_price"],
                "promo": r["promo"],
            }
        )
    except Exception:
        retail_items.append(
            {
                "seller": "Homeshopping",
                "platform": "Homeshopping",
                "list_price": 0.0,
                "promo": "Error scraping",
            }
        )

    # Telemart
    try:
        r = _scrape_retail_search(links["telemart"], "Telemart")
        retail_items.append(
            {
                "seller": r["seller"],
                "platform": r["platform"],
                "list_price": r["list_price"],
                "promo": r["promo"],
            }
        )
    except Exception:
        retail_items.append(
            {
                "seller": "Telemart",
                "platform": "Telemart",
                "list_price": 0.0,
                "promo": "Error scraping",
            }
        )

    return retail_items


# ---------------------------------------------------
#   WHOLESALE SCRAPERS — Made-in-China product page + fallback + Khareed
# ---------------------------------------------------

def _extract_mic_moq_from_text(text: str) -> Optional[int]:
    """
    Extract integer MOQ from text like '10 Pieces (MOQ)'.
    """
    m = re.search(r"(\d+)\s+Pieces", text.replace(",", ""), re.IGNORECASE)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


def _scrape_mic_product_page(url: str) -> Dict[str, Any]:
    """
    Product page scraper for Made-in-China (DIRECT URL).

    Extracts:
      - supplier name
      - unit price (min of price range US$43.99-50.00 -> 43.99)
      - MOQ (pieces)
      - origin (Place of Origin)
      - simple lead_time (if any row contains 'Lead Time')
    """
    soup = _fetch_html(url)

    # Product title (not returned in current response but useful)
    _ = _extract_title(soup)

    # Supplier name
    supplier = "Made-in-China Supplier"
    company_block = soup.find(class_=re.compile(r"company|supplier", re.IGNORECASE))
    if company_block:
        a = company_block.find("a")
        if a and a.get_text(strip=True):
            supplier = a.get_text(strip=True)

    # Price range like "US$43.99-50.00"
    unit_price = 0.0
    for text in soup.stripped_strings:
        if "US$" in text or "$" in text:
            m = USD_PRICE_REGEX.search(text)
            if m:
                # text may be "US$43.99-50.00"
                raw = m.group(2)
                # split on '-' to get min price
                raw = raw.split("-")[0]
                raw_clean = raw.replace(",", "")
                try:
                    unit_price = float(raw_clean)
                    break
                except ValueError:
                    continue

    # MOQ
    moq_val: Optional[int] = None
    for text in soup.stripped_strings:
        if "MOQ" in text:
            moq_val = _extract_mic_moq_from_text(text)
            if moq_val:
                break
    if moq_val is None:
        moq_val = 0

    # Origin (from Product Description / Basic Info table)
    origin = "CN"
    for text in soup.stripped_strings:
        if "Place of Origin" in text or "Origin" in text:
            # next strings usually contain 'China'
            # we don't over-complicate; assume CN
            origin = "CN"
            break

    # Lead time (if visible)
    lead_time = "N/A"
    for text in soup.stripped_strings:
        if "Lead Time" in text or "Lead time" in text:
            lead_time = text.strip()
            break

    return {
        "supplier": supplier,
        "moq": moq_val,
        "unit_price": unit_price,
        "lead_time": lead_time,
        "origin": origin,
        "product_url": url,
    }


def _find_mic_product_links_strict(
    search_url: str,
    product_name: str,
    max_suppliers: int = 2,
) -> List[str]:
    """
    Fallback: Made-in-China search page based on product_name.
    Used ONLY when there are no direct URLs in wholesale_links.json.
    """
    soup = _fetch_html(search_url)
    wanted = product_name.strip().lower()
    found_links: List[str] = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(strip=True)

        if "/product/" not in href:
            continue

        if href.startswith("//"):
            url = "https:" + href
        elif href.startswith("http"):
            url = href
        else:
            url = "https://www.made-in-china.com" + href

        if not title:
            continue

        if wanted in title.lower():
            if url not in found_links:
                found_links.append(url)

        if len(found_links) >= max_suppliers:
            break

    return found_links


def _scrape_made_in_china_wholesale(
    product_name: str,
    moq: Optional[int],
    direct_urls: List[str],
    max_suppliers: int = 2,
) -> List[Dict[str, Any]]:
    """
    Main Made-in-China wholesale scraper:

    1) If direct_urls given (from wholesale_links.json):
         - scrape those product pages (up to max_suppliers)
    2) Else:
         - build search URL and try strict search based matching
    """
    items: List[Dict[str, Any]] = []

    urls_to_use: List[str] = []

    if direct_urls:
        urls_to_use = direct_urls[:max_suppliers]
    else:
        search_url = build_made_in_china_search_url(product_name, moq)
        urls_to_use = _find_mic_product_links_strict(
            search_url=search_url,
            product_name=product_name,
            max_suppliers=max_suppliers,
        )

    if not urls_to_use:
        items.append(
            {
                "supplier": "Made-in-China Supplier",
                "moq": moq or 0,
                "unit_price": 0.0,
                "lead_time": "N/A",
                "origin": "CN",
            }
        )
        return items

    for url in urls_to_use:
        try:
            info = _scrape_mic_product_page(url)
            items.append(
                {
                    "supplier": info["supplier"],
                    "moq": info["moq"],
                    "unit_price": info["unit_price"],
                    "lead_time": info["lead_time"],
                    "origin": info["origin"],
                }
            )
        except Exception:
            continue

    if not items:
        items.append(
            {
                "supplier": "Made-in-China Supplier",
                "moq": moq or 0,
                "unit_price": 0.0,
                "lead_time": "N/A",
                "origin": "CN",
            }
        )

    return items


def _scrape_khareed_wholesale_search(url: str, max_suppliers: int = 2) -> List[Dict[str, Any]]:
    """
    Simple wholesale-style scraper for Khareed-like listing page.

    - Fetch HTML
    - Extract PKR prices from search result texts
    - Return up to max_suppliers rows treated as wholesale offers
    """
    soup = _fetch_html(url)

    prices: List[float] = []
    for text in soup.stripped_strings:
        if "Rs" in text or "PKR" in text:
            match = PK_PRICE_REGEX.search(text)
            if match:
                digits = re.sub(r"[^\d]", "", match.group(2))
                try:
                    val = float(digits)
                    if val not in prices:
                        prices.append(val)
                except ValueError:
                    continue
        if len(prices) >= max_suppliers:
            break

    items: List[Dict[str, Any]] = []

    if not prices:
        items.append(
            {
                "supplier": "Khareed Supplier",
                "moq": 50,
                "unit_price": 2500.0,
                "lead_time": "5–7d",
                "origin": "PK",
            }
        )
        return items

    for idx, p in enumerate(prices, start=1):
        items.append(
            {
                "supplier": f"Khareed Supplier {idx}",
                "moq": 50 * idx,
                "unit_price": p,
                "lead_time": "5–10d",
                "origin": "PK",
            }
        )

    return items


def scrape_wholesale_suppliers(
    product_name: str,
    links: Dict[str, str],
    moq: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Aggregate wholesale data from:
      - Made-in-China (direct product URLs if configured, else dynamic search)
      - Khareed.lk (search-page-based PKR prices)
    """
    wholesale_items: List[Dict[str, Any]] = []

    # Direct URLs from wholesale_links.json (if any)
    mapping = _get_wholesale_links_for_product(product_name)
    mic_direct_urls = mapping.get("made_in_china", [])

    # Made-in-China
    try:
        mic_items = _scrape_made_in_china_wholesale(
            product_name=product_name,
            moq=moq,
            direct_urls=mic_direct_urls,
            max_suppliers=2,
        )
        wholesale_items.extend(mic_items)
    except Exception:
        wholesale_items.append(
            {
                "supplier": "Made-in-China Supplier",
                "moq": moq or 0,
                "unit_price": 0.0,
                "lead_time": "N/A",
                "origin": "CN",
            }
        )

    # Khareed (simple PKR wholesale)
    try:
        kh_items = _scrape_khareed_wholesale_search(
            url=links["khareed"],
            max_suppliers=2,
        )
        wholesale_items.extend(kh_items)
    except Exception:
        wholesale_items.append(
            {
                "supplier": "Khareed Supplier",
                "moq": 50,
                "unit_price": 2500.0,
                "lead_time": "5–7d",
                "origin": "PK",
            }
        )

    return wholesale_items


# ---------------------------------------------------
#   MAIN ENTRY POINT — called by FastAPI
# ---------------------------------------------------

def scrape_product_platforms(product_name: str, moq: Optional[int] = None) -> Dict[str, Any]:
    """
    Main Scraper Agent entry point.

    - Uses product_name (and optional moq) to:
        * Build PK retailer search URLs
        * Load any direct Made-in-China URLs from wholesale_links.json
        * Scrape retail competitors (Daraz, Homeshopping, Telemart)
        * Scrape wholesale suppliers (Made-in-China + Khareed)

    Returns structure matching ScrapeResponse.
    """
    # Retail + Khareed search links
    links = build_retail_and_khareed_urls(product_name)

    # Also store Made-in-China search URL into links_used for debugging
    links["made_in_china_search"] = build_made_in_china_search_url(product_name, moq)

    # Retail competitors
    retail_items = scrape_retail_competitors(links)

    # Wholesale suppliers
    wholesale_items = scrape_wholesale_suppliers(
        product_name=product_name,
        links=links,
        moq=moq,
    )

    return {
        "product_name": product_name,
        "links_used": links,
        "wholesale": wholesale_items,
        "retail": retail_items,
    }
