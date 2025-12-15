from __future__ import annotations

from typing import Dict, Any, List, Optional, Tuple
import re
import json
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


# ---------------------------------
#   HTTP helper + constants
# ---------------------------------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}

USD_TO_PKR = 280.0  # static for now – later replace with FX API if needed


def _fetch_html(url: str, timeout: int = 25) -> Optional[BeautifulSoup]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")
    except Exception:
        return None


def _usd_to_pkr(amount: Optional[float]) -> Optional[float]:
    if amount is None:
        return None
    try:
        return round(float(amount) * USD_TO_PKR, 2)
    except Exception:
        return None


def _clean_price_to_float(text: str) -> Optional[float]:
    """
    Generic 'Rs. 5,999/-' → 5999.0
    Works for Mega / Homeshopping / Telemart.
    """
    if not text:
        return None

    # remove non-breaking space
    text = text.replace("\xa0", " ")

    m = re.search(r"([\d.,]+)", text)
    if not m:
        return None
    num = m.group(1).replace(",", "")
    try:
        return float(num)
    except Exception:
        return None


# ---------------------------------------------------------
#   STRICT PRODUCT NAME MATCHING
# ---------------------------------------------------------
def _matches_product_name(title: str, query: str) -> bool:
    if not title:
        return False

    t = " ".join(title.lower().split())
    q = " ".join(query.lower().split())

    clean_t = re.sub(r"[^a-z0-9]+", " ", t)
    clean_q = re.sub(r"[^a-z0-9]+", " ", q)

    return clean_q in clean_t


# ---------------------------------------------------------
#   COMMON HELPERS (MOQ + LD+JSON)
# ---------------------------------------------------------
def _extract_moq_from_text(text: str) -> Optional[int]:
    m = re.search(r"(\d+)\s*Pieces?\s*\(MOQ\)", text or "", re.IGNORECASE)
    return int(m.group(1)) if m else None


def _parse_product_ld_json(soup: BeautifulSoup) -> Dict[str, Any]:
    for sc in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(sc.string or sc.text or "")
        except Exception:
            continue
        if isinstance(data, dict) and data.get("@type") == "Product":
            return data
    return {}


# =====================================================================
#                    WHOLESALE – MADE-IN-CHINA
# =====================================================================
def scrape_mic_product_page(url: str) -> Optional[Dict[str, Any]]:
    soup = _fetch_html(url)
    if not soup:
        return None

    text = soup.get_text(" ", strip=True)
    ld = _parse_product_ld_json(soup)

    title = ld.get("name")
    offers = ld.get("offers") or {}

    # price
    price = None
    currency = offers.get("priceCurrency")
    try:
        raw = offers.get("price")
        if raw:
            price = float(raw)
    except Exception:
        pass

    if price is None:
        m = re.findall(r"US\$?\s*([\d.]+)", text)
        if m:
            price = float(m[0])
            currency = "USD"

    # supplier
    brand = ld.get("brand") if isinstance(ld, dict) else None
    supplier_name = brand.get("name") if isinstance(brand, dict) else None

    loc = re.search(r"Address:\s*([^,]+China)", text)
    supplier_loc = loc.group(1) if loc else None

    # attributes
    attributes: Dict[str, str] = {}
    for div in soup.find_all("div", class_="bsc-item"):
        k = div.find("div", class_="bac-item-label")
        v = div.find("div", class_="bac-item-value")
        if k and v:
            attributes[k.get_text(strip=True)] = v.get_text(strip=True)

    return {
        "url": url,
        "title": title,
        "text": text,
        "price": {
            "min": price,
            "max": price,
            "currency": currency,
            "moq": _extract_moq_from_text(text),
        },
        "supplier": {
            "name": supplier_name,
            "location": supplier_loc,
        },
        "attributes": attributes,
    }


def _extract_listing_moq_and_attrs(card_text: str) -> Dict[str, Any]:
    listing_moq = _extract_moq_from_text(card_text)

    attrs: Dict[str, str] = {}
    for m in re.finditer(r"([A-Za-z][A-Za-z /&\-]{1,30})\s*:\s*([^:]+)", card_text):
        attrs[m.group(1).strip()] = m.group(2).strip()

    return {"moq": listing_moq, "attributes": attrs}


def _find_mic_product_urls_from_search(product_name: str) -> Dict[str, Any]:
    q = quote_plus(product_name)
    search_url = f"https://www.made-in-china.com/productdirectory.do?word={q}&subaction=hunt"

    soup = _fetch_html(search_url)
    if not soup:
        return {"search_url": search_url, "product_urls": [], "listing_meta": {}}

    urls: List[str] = []
    listing_meta: Dict[str, Dict[str, Any]] = {}

    for a in soup.find_all("a", href=True):
        href = a["href"]

        if "product-detail" in href or "/product/" in href:
            full = (
                "https:" + href[2:]
                if href.startswith("//")
                else urljoin("https://www.made-in-china.com", href)
                if href.startswith("/")
                else href
            )
            full = full.split("#")[0]

            if full not in urls:
                urls.append(full)

                # listing card text
                card = a
                for _ in range(4):
                    if card.parent:
                        card = card.parent
                txt = card.get_text(" ", strip=True)
                listing_meta[full] = _extract_listing_moq_and_attrs(txt)

        if len(urls) >= 10:
            break

    return {
        "search_url": search_url,
        "product_urls": urls,
        "listing_meta": listing_meta,
    }


def _should_accept_candidate(new: Dict[str, Any], existing: List[Dict[str, Any]]) -> bool:
    """
    MIC candidate de-dup logic.
    """
    for old in existing:
        # same URL
        if new["source_url"] == old["source_url"]:
            return False

        # same supplier + same unit price
        if new["supplier"] == old["supplier"] and new["unit_price"] == old["unit_price"]:
            return False

        # same price + same MOQ (both known)
        if (
            new["unit_price"] == old["unit_price"]
            and new["moq"] == old["moq"]
            and new["moq"] is not None
        ):
            return False

    return True


def scrape_mic_wholesale_for_product(
    product_name: str,
    moq: Optional[int] = None,
) -> Dict[str, Any]:
    """
    1) Search Made-in-China
    2) Get product pages
    3) Strict title matching
    4) De-dup
    5) Cheapest top-2
    """
    info = _find_mic_product_urls_from_search(product_name)
    urls = info["product_urls"]
    listing_meta = info["listing_meta"]
    search_url = info["search_url"]

    candidates: List[Dict[str, Any]] = []

    for url in urls:
        detail = scrape_mic_product_page(url)
        if not detail:
            continue

        title = detail.get("title") or ""
        if not _matches_product_name(title, product_name):
            continue

        price = detail["price"]["min"]
        if not price:
            continue

        detail_moq = detail["price"]["moq"] or 0

        meta = listing_meta.get(url, {})
        listing_moq = meta.get("moq")
        listing_attrs = meta.get("attributes") or {}

        best_moq = detail_moq or listing_moq or 0

        # optional MOQ filter (abhi user se moq nahi aa raha, default None)
        if moq is not None and best_moq > moq:
            continue

        supplier = detail.get("supplier") or {}

        new = {
            "supplier": supplier.get("name") or "Unknown Supplier",
            "moq": best_moq,
            "moq_listing": listing_moq,
            "unit_price": float(price),
            "unit_price_pkr": _usd_to_pkr(price),
            "currency": detail["price"]["currency"] or "USD",
            "lead_time": "7–14d",
            "origin": supplier.get("location") or "CN",
            "source_url": url,
            "attributes_listing": listing_attrs,
        }

        if _should_accept_candidate(new, candidates):
            candidates.append(new)

    # cheapest 2
    candidates = sorted(candidates, key=lambda x: x["unit_price"])[:2]

    return {
        "links_used": {
            "made_in_china_search": search_url,
            "made_in_china_products": [c["source_url"] for c in candidates],
        },
        "wholesale": candidates,
    }


# =====================================================================
#                     RETAIL – MEGA / HOMESHOPPING / TELEMART
# =====================================================================
def scrape_telemart(product_name: str) -> List[Dict[str, Any]]:
    q = quote_plus(product_name)
    url = f"https://telemart.pk/search?query={q}"

    soup = _fetch_html(url)
    if not soup:
        return []

    results = []

    cards = soup.select("div.product-wrapper")

    for card in cards:
        title_el = card.select_one("h3.product-title a")
        price_el = card.select_one("span.price-new") or card.select_one("span.price-old")

        if not title_el or not price_el:
            continue

        title = title_el.get_text(strip=True)
        if not _matches_product_name(title, product_name):
            continue

        price = _clean_price_to_float(price_el.get_text(strip=True))
        if price is None:
            continue

        href = title_el.get("href")
        if href.startswith("/"):
            href = "https://telemart.pk" + href

        results.append(
            {
                "seller": "Telemart",
                "platform": "telemart",
                "title": title,
                "list_price": price,
                "promo": "",
                "url": href,
            }
        )

    return results


def scrape_homeshopping(product_name: str) -> List[Dict[str, Any]]:
    q = quote_plus(product_name)
    url = f"https://www.homeshopping.pk/{q}?map=ft"

    soup = _fetch_html(url)
    if not soup:
        return []

    results = []

    cards = soup.select("div.hs-product-card")

    for card in cards:
        title_el = card.select_one("h2.product-name a")
        price_el = card.select_one("span.price-new") or card.select_one("span.price-old")

        if not title_el or not price_el:
            continue

        title = title_el.get_text(strip=True)
        if not _matches_product_name(title, product_name):
            continue

        price = _clean_price_to_float(price_el.get_text(strip=True))
        if price is None:
            continue

        href = title_el.get("href")
        if href.startswith("/"):
            href = "https://www.homeshopping.pk" + href

        results.append(
            {
                "seller": "Homeshopping",
                "platform": "homeshopping",
                "title": title,
                "list_price": price,
                "promo": "",
                "url": href,
            }
        )

    return results


def scrape_mega_pk(product_name: str) -> List[Dict[str, Any]]:
    q = product_name.replace(" ", "+")
    url = f"https://www.mega.pk/search/{q}/"

    soup = _fetch_html(url)
    if not soup:
        return []

    results = []

    cards = soup.select("div.product_wrap")

    for card in cards:
        title_el = card.select_one("div.product_details h3 a")
        price_el = card.select_one("span.price")

        if not title_el or not price_el:
            continue

        title = title_el.get_text(strip=True)
        if not _matches_product_name(title, product_name):
            continue

        price = _clean_price_to_float(price_el.get_text(strip=True))
        if price is None:
            continue

        href = title_el.get("href")
        if href.startswith("/"):
            href = "https://www.mega.pk" + href

        results.append(
            {
                "seller": "Mega.pk",
                "platform": "mega.pk",
                "title": title,
                "list_price": price,
                "promo": "",
                "url": href,
            }
        )

    return results


# =====================================================================
#                          D A R A Z
# =====================================================================
def _parse_daraz_price(text: str) -> float:
    if not text:
        return 0.0
    cleaned = (
        text.replace("Rs.", "")
        .replace("Rs", "")
        .replace(",", "")
        .strip()
    )
    try:
        return float(cleaned)
    except Exception:
        return 0.0


def scrape_daraz_listing(product_name: str, max_items: int = 5) -> Tuple[List[Dict[str, Any]], str]:
    q = quote_plus(product_name)
    search_url = f"https://www.daraz.pk/catalog/?q={q}"

    results: List[Dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(search_url, wait_until="networkidle")
        page.wait_for_timeout(4000)

        cards = page.query_selector_all("div.Ms6aG")

        for card in cards[:max_items]:
            title_el = card.query_selector("div.RfADt a")
            price_el = card.query_selector("span.ooOxS")
            promo_el = card.query_selector("div.WNoq3 span")

            if not title_el or not price_el:
                continue

            title = title_el.inner_text().strip()
            # apply same strict constraint if you want
            # if not _matches_product_name(title, product_name):
            #     continue

            url = title_el.get_attribute("href") or ""
            if url.startswith("//"):
                url = "https:" + url

            results.append(
                {
                    "seller": "",
                    "platform": "daraz",
                    "title": title,
                    "url": url,
                    "list_price": _parse_daraz_price(price_el.inner_text()),
                    "promo": promo_el.inner_text().strip() if promo_el else "",
                }
            )

        browser.close()

    return results, search_url


def scrape_daraz_product(url: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(3000)

        def safe(selector: str) -> str:
            try:
                el = page.query_selector(selector)
                return el.inner_text().strip() if el else ""
            except:
                return ""

        # -------------------------
        # BASIC FIELDS
        # -------------------------
        data["title"] = safe("h1.pdp-mod-product-badge-title")
        data["price_sale"] = safe("span.pdp-price_type_normal")
        data["price_original"] = safe("span.pdp-price_type_deleted")
        data["rating"] = safe("div.pdp-mod-rating span")
        data["rating_count"] = safe("a.pdp-review-summary__link") or safe("div.pdp-review-summary a")

        data["brand"] = safe("a.pdp-product-brand__brand-link")

        # -------------------------------------------------
        # SELLER NAME (this is the new selector)
        # -------------------------------------------------
        data["seller_name"] = (
            safe("div.seller-name__detail-name a")
            or safe("a.seller-name__detail-name__wrapper")
            or safe("div.pdp-seller-info__seller-name")
        )

        # Seller rating %
        data["seller_rating"] = safe("div.seller-info-value")

        # -------------------------------------------------
        # DELIVERY INFO
        # -------------------------------------------------
        data["delivery_city"] = safe("span.delivery-location__address") or safe("div.delivery-option-item__location")
        data["delivery_cost"] = safe("div.delivery-option-item__shipping-fee")

        # -------------------------------------------------
        # WARRANTY
        # -------------------------------------------------
        data["warranty"] = (
            safe("div.pdp-product-warranty span")
            or safe("div.warranty__content")
            or safe("div.pdp-mod-warranty span")
        )

        # -------------------------------------------------
        # RETURN POLICY
        # -------------------------------------------------
        data["return_policy"] = (
            safe("div.return-text")
            or safe("div.pdp-return-policy")
            or safe("div.return-policy-text")
        )

        # -------------------------------------------------
        # IMAGES
        # -------------------------------------------------
        try:
            imgs = []
            nodes = page.query_selector_all("img.pdp-mod-common-image")
            for img in nodes:
                src = img.get_attribute("src")
                if src:
                    imgs.append(src)
            data["images"] = imgs
        except:
            data["images"] = []

        # -------------------------------------------------
        # SPECIFICATIONS (KEY : VALUE LIST)
        # -------------------------------------------------
        specs = []
        try:
            rows = page.query_selector_all("div.pdp-general-features table tr")
            for row in rows:
                cols = row.query_selector_all("td")
                if len(cols) == 2:
                    key = cols[0].inner_text().strip()
                    val = cols[1].inner_text().strip()
                    specs.append({key: val})
        except:
            pass

        data["specifications"] = specs

        browser.close()

    return data

def strict_name_match(title: str, product_name: str) -> bool:
    """
    Full strict phrase check.
    """
    t = " ".join(title.lower().split())
    p = " ".join(product_name.lower().split())
    return p in t


def category_match(title: str, category: str) -> bool:
    """
    Category must appear in title.
    """
    return category.lower() in title.lower()


def is_accessory(title: str, category: str) -> bool:
    """
    If product contains model but not category, or contains accessory hints → reject.
    """
    t = title.lower()
    c = category.lower()

    # If category missing, likely accessory
    if c not in t:
        return True

    accessory_words = [
        "pad", "pads", "cushion", "foam", "earpad", "replace", "replacement",retail.append(item)
        "cable", "wire", "cover", "shell", "sticker", "skin", "adapter"
    ]

    return any(w in t for w in accessory_words)
def passes_all_constraints(item, product_name, category):
    title = item["title"].lower()

    # 1) Strict name match
    if not strict_name_match(title, product_name):
        return False

    # 2) Category must match
    if not category_match(title, category):
        return False

    # 3) Accessory blocker
    if is_accessory(title, category):
        return False

    return True


# =====================================================================
#                  MAIN ENTRYPOINT – used by /scraper/start
# =====================================================================
def scrape_product_platforms(
    product_name: str,
    moq: Optional[int] = None,
) -> Dict[str, Any]:
    """
    - Wholesale: Made-in-China (top 2)
    - Retail: Mega.pk + Homeshopping.pk + Telemart.pk + Daraz.pk
    - Daraz ke har listing ka product page detail bhi laata hai
    """

    # -------- WHOLESALE (MIC) --------
    mic = scrape_mic_wholesale_for_product(product_name, moq)

    wholesale_items = [
        {**item, "platform": "made-in-china"} for item in mic["wholesale"]
    ]

    # -------- RETAIL LISTINGS (3 local stores) --------
    mega = scrape_mega_pk(product_name)
    hs = scrape_homeshopping(product_name)
    tm = scrape_telemart(product_name)

    retail: List[Dict[str, Any]] = []

    # add detail=None
    mega = [m for m in scrape_mega_pk(product_name) if passes_all_constraints(m, product_name, category)]
    for item in mega:
        item["detail"] = None
        retail.append(item)

    hs = [m for m in scrape_homeshopping(product_name) if passes_all_constraints(m, product_name, category)]
    for item in hs:
        item["detail"] = None
        retail.append(item)
    tm = [m for m in scrape_telemart(product_name) if passes_all_constraints(m, product_name, category)]

    for item in tm:
        item["detail"] = None
        retail.append(item)

    # -------- DARAZ: listing + product page detail --------
    # -------- DARAZ: listing + product page detail --------
daraz_items, daraz_search_url = scrape_daraz_listing(product_name, max_items=20)

filtered_daraz = []
for item in daraz_items:
    if passes_all_constraints(item, product_name, category):
        
        # Add product page detail
        try:
            detail = scrape_daraz_product(item["url"])
        except:
            detail = None

        item["detail"] = detail
        filtered_daraz.append(item)

# sort by price
filtered_daraz.sort(key=lambda x: x["list_price"])

# pick top 5 only
filtered_daraz = filtered_daraz[:5]

for f in filtered_daraz:
    retail.append(f)


    # -------- LINKS_USED MERGING --------
    links_used: Dict[str, Any] = dict(mic["links_used"])

    mega_search_url = f"https://www.mega.pk/search/{product_name.replace(' ', '+')}/"
    hs_search_url = f"https://www.homeshopping.pk/{quote_plus(product_name)}?map=ft"
    tm_search_url = f"https://telemart.pk/search?query={quote_plus(product_name)}"

    links_used.update(
        {
            "mega_pk_search": mega_search_url,
            "homeshopping_search": hs_search_url,
            "telemart_search": tm_search_url,
            "daraz_search": daraz_search_url,
        }
    )

    return {
        "product_name": product_name,
        "links_used": links_used,
        "wholesale": wholesale_items,
        "retail": retail,
    }
