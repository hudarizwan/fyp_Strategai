# app/services/scraper.py

from typing import Dict, Any, Optional, List
from urllib.parse import quote_plus
from playwright.sync_api import sync_playwright


# ---------------------------
# Helper: Convert Daraz price text → float
# ---------------------------
def parse_price(text: str) -> float:
    if not text:
        return 0.0
    cleaned = (
        text.replace("Rs.", "")
            .replace("Rs", "")
            .replace("₨", "")
            .replace(",", "")
            .strip()
    )
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


# ---------------------------
# DARAZ SCRAPER (multi-listing)
# ---------------------------
def scrape_daraz(product_name: str, max_items: int = 5):
    search_query = quote_plus(product_name)
    search_url = f"https://www.daraz.pk/catalog/?q={search_query}"

    retail_items: List[Dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(search_url, wait_until="networkidle")

        # Wait for lazy loading
        page.wait_for_timeout(4000)

        # Product card selector (Daraz changes frequently — adjust if needed)
        cards = page.query_selector_all("div[data-qa-locator='product-item']")

        if not cards:
            cards = page.query_selector_all(".gridItem--Yd0sa")  # fallback

        for card in cards[:max_items]:

            # Title + URL
            a_tag = card.query_selector("a")
            title = a_tag.get_attribute("title") if a_tag else ""
            url = a_tag.get_attribute("href") if a_tag else ""

            if url and url.startswith("/"):
                url = "https://www.daraz.pk" + url

            # Price
            price_el = card.query_selector(".price--NVB62") or card.query_selector(".price")
            price_text = price_el.inner_text() if price_el else ""
            list_price = parse_price(price_text)

            # Promo
            promo_el = card.query_selector(".discount") or card.query_selector(".discount--HADrg")
            promo = promo_el.inner_text().strip() if promo_el else ""

            # Seller (Daraz list page rarely includes seller — blank allowed)
            seller = ""

            retail_items.append({
                "seller": seller,
                "platform": "daraz",
                "list_price": list_price,
                "promo": promo,
                "url": url,
                "title": title
            })

        browser.close()

    return retail_items, search_url


# ---------------------------
# MAIN SCRAPER ENTRYPOINT
# Called by FastAPI router
# ---------------------------
def scrape_product_platforms(
    product_name: str,
    moq: Optional[int] = None
) -> Dict[str, Any]:

    # 1) Retail data from Daraz
    daraz_items, daraz_link = scrape_daraz(product_name, max_items=5)

    # 2) Placeholder wholesale data (for future Alibaba / Made-in-China)
    wholesale_items: List[Dict[str, Any]] = []

    # 3) Links used
    links_used = {
        "daraz": daraz_link,
    }

    # 4) Final unified response (FastAPI validates this)
    return {
        "product_name": product_name,
        "links_used": links_used,
        "wholesale": wholesale_items,
        "retail": daraz_items,
    }
