from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import json
import logging
import re
import time
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from app.config.scraperapi_config import SCRAPERAPI_ENDPOINT, SCRAPERAPI_KEY

try:
    from playwright.sync_api import sync_playwright  # type: ignore
except Exception:  # pragma: no cover - depends on local Playwright runtime
    sync_playwright = None


logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

FX_RATES_TO_PKR = {
    "USD": 280.0,
    "CNY": 39.0,
    "RMB": 39.0,
    "AED": 76.0,
    "PKR": 1.0,
}

MAX_FINAL_ITEMS_PER_PLATFORM = 5
DEPENDENCY_PATTERNS = (
    "for",
    "compatible with",
    "replacement",
    "spare",
)
ACCESSORY_KEYWORDS = {
    "case",
    "cover",
    "protector",
    "skin",
    "sleeve",
    "bag",
    "pouch",
    "holder",
    "stand",
    "mount",
    "cable",
    "charger",
    "adapter",
    "dongle",
    "keycap",
    "replacement",
    "spare",
    "sticker",
    "shell",
    "housing",
    "frame",
    "tripod",
    "strap",
}
TIRE_SYNONYMS = {"tire", "tires", "tyre", "tyres"}
TIRE_MODEL_MARKERS = {
    "ecopia",
    "potenza",
    "turanza",
    "dueler",
    "regno",
    "weatherpeak",
    "driveguard",
    "potenza",
    "s001",
    "ep150",
    "ep200",
}


def _playwright_is_available() -> bool:
    return sync_playwright is not None


def _http_session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    retry = Retry(
        total=1,
        connect=1,
        read=1,
        backoff_factor=0.4,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(HEADERS)
    return session


def _fetch_html(url: str, timeout: int = 12) -> Optional[BeautifulSoup]:
    try:
        response = _http_session().get(url, timeout=timeout)
        response.raise_for_status()
        try:
            return BeautifulSoup(response.text, "lxml")
        except Exception:
            logger.info("lxml parser unavailable for %s; falling back to html.parser", url)
            return BeautifulSoup(response.text, "html.parser")
    except Exception as exc:
        logger.warning("HTML fetch failed for %s: %s", url, exc)
        return None


def _fetch_html_via_scraperapi(url: str, timeout: int = 20) -> Optional[BeautifulSoup]:
    if not SCRAPERAPI_KEY:
        return None
    try:
        response = _http_session().get(
            SCRAPERAPI_ENDPOINT,
            params={"api_key": SCRAPERAPI_KEY, "url": url, "keep_headers": "true"},
            timeout=timeout,
        )
        response.raise_for_status()
        try:
            return BeautifulSoup(response.text, "lxml")
        except Exception:
            return BeautifulSoup(response.text, "html.parser")
    except Exception as exc:
        logger.warning("ScraperAPI fetch failed for %s: %s", url, exc)
        return None


DARAZ_GOTO_TIMEOUT_MS = 20000
DARAZ_SETTLE_TIMEOUT_MS = 2500
DARAZ_MTOP_APP_KEY = "24937400"
DARAZ_MTOP_API = "mtop.lazada.gsearch.appsearch"
DARAZ_MTOP_ENDPOINT = "https://acs-m.daraz.pk/h5/mtop.lazada.gsearch.appsearch/1.0/"


def _clean_price_to_float(text: str) -> Optional[float]:
    if not text:
        return None
    match = re.search(r"([\d,]+(?:\.\d+)?)", text.replace("\xa0", " "))
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", ""))
    except Exception:
        return None


def _daraz_api_params(data: str, timestamp_ms: str, sign: Optional[str] = None) -> Dict[str, str]:
    params = {
        "jsv": "2.6.1",
        "appKey": DARAZ_MTOP_APP_KEY,
        "t": timestamp_ms,
        "api": DARAZ_MTOP_API,
        "v": "1.0",
        "type": "originaljson",
        "dataType": "json",
        "timeout": "20000",
        "AntiCreep": "true",
        "preventFallback": "false",
        "ecode": "0",
        "data": data,
    }
    if sign:
        params["sign"] = sign
    return params


def _daraz_mtop_search_payload(product_name: str, page: int = 1) -> Optional[Dict[str, Any]]:
    session = _http_session()
    query = (product_name or "").strip()
    if not query:
        return None

    data = json.dumps({"q": query, "page": page}, separators=(",", ":"))
    try:
        session.get(f"https://www.daraz.pk/catalog/?q={quote_plus(query)}", timeout=15)
        seed_t = str(int(time.time() * 1000))
        session.get(DARAZ_MTOP_ENDPOINT, params=_daraz_api_params(data, seed_t), timeout=15)
        token = session.cookies.get("_m_h5_tk", "").split("_")[0]
        if not token:
            logger.warning("Daraz mtop token was not issued for %s", product_name)
            return None
        signed_t = str(int(time.time() * 1000))
        sign = hashlib.md5(f"{token}&{signed_t}&{DARAZ_MTOP_APP_KEY}&{data}".encode("utf-8")).hexdigest()
        response = session.get(
            DARAZ_MTOP_ENDPOINT,
            params=_daraz_api_params(data, signed_t, sign=sign),
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        if any(str(ret).startswith("FAIL_") for ret in payload.get("ret") or []):
            logger.warning("Daraz mtop search failed for %s: %s", product_name, payload.get("ret"))
            return None
        return payload
    except Exception as exc:
        logger.warning("Daraz mtop search failed for %s: %s", product_name, exc)
        return None


def _extract_daraz_api_items(payload: Dict[str, Any], max_items: int = 10) -> List[Dict[str, Any]]:
    items = (((payload.get("data") or {}).get("mods") or {}).get("listItems") or [])[:max_items]
    results: List[Dict[str, Any]] = []
    for item in items:
        title = (item.get("name") or "").strip()
        price = _clean_price_to_float(str(item.get("priceShow") or item.get("price") or ""))
        url = item.get("productUrl") or item.get("itemUrl") or ""
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/"):
            url = urljoin("https://www.daraz.pk", url)
        if not title or not price or not url:
            continue
        results.append(
            {
                "seller": (item.get("sellerName") or "daraz").strip() or "daraz",
                "platform": "daraz",
                "title": title,
                "url": url,
                "list_price": price,
                "promo": (item.get("discount") or "").strip(),
                "detail": {
                    "stock_status": "in_stock" if item.get("inStock") else "out_of_stock",
                    "seller_name": item.get("sellerName"),
                    "brand_name": item.get("brandName"),
                    "delivery_location": item.get("location"),
                    "highlights": " ".join(item.get("description") or []),
                },
            }
        )
    return results


def _price_range_from_text(text: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    if not text:
        return None, None, None

    normalized = text.replace("\xa0", " ")
    currency = None
    if "US$" in normalized or "USD" in normalized.upper():
        currency = "USD"
    elif "RMB" in normalized.upper() or "CNY" in normalized.upper():
        currency = "CNY"

    numbers = [
        float(match.replace(",", ""))
        for match in re.findall(r"(\d[\d,]*(?:\.\d+)?)", normalized)
    ]
    if not numbers:
        return None, None, currency
    if len(numbers) == 1:
        return numbers[0], numbers[0], currency
    return min(numbers), max(numbers), currency


def _mic_price_summary(text: str) -> Dict[str, Any]:
    min_price, max_price, currency = _price_range_from_text(text)
    return {
        "unit_price": min_price,
        "price_max": max_price,
        "currency": currency or "USD",
        "price_text": (text or "").strip(),
    }


def _parse_daraz_price(text: str) -> float:
    return _clean_price_to_float(text) or 0.0


def _convert_to_pkr(amount: Optional[float], currency: Optional[str]) -> Optional[float]:
    if amount in (None, "", 0, 0.0):
        return None
    rate = FX_RATES_TO_PKR.get((currency or "PKR").upper(), 1.0)
    return round(float(amount) * rate, 2)


def _clean_tokens(text: str) -> List[str]:
    cleaned = re.sub(r"[^a-z0-9]+", " ", (text or "").lower())
    tokens: List[str] = []
    for token in cleaned.split():
        if not token:
            continue
        if token in TIRE_SYNONYMS:
            tokens.append("tyre")
        else:
            tokens.append(token)
    return tokens


def _slugify_query_for_mic(product_name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", (product_name or "").strip())
    return re.sub(r"_+", "_", cleaned).strip("_") or "products"


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _normalized_phrase(text: str) -> str:
    return " ".join(_clean_tokens(text))


def _find_subsequence_start(haystack: List[str], needle: List[str]) -> int:
    if not haystack or not needle or len(needle) > len(haystack):
        return -1
    last = len(haystack) - len(needle) + 1
    for index in range(last):
        if haystack[index:index + len(needle)] == needle:
            return index
    return -1


def _contains_tokens_in_order(haystack: List[str], needle: List[str]) -> bool:
    if not haystack or not needle:
        return False

    haystack_index = 0
    for token in needle:
        found = False
        while haystack_index < len(haystack):
            if haystack[haystack_index] == token:
                found = True
                haystack_index += 1
                break
            haystack_index += 1
        if not found:
            return False
    return True


def _category_tokens(category: str) -> List[str]:
    tokens = _clean_tokens(category)
    expanded: List[str] = []
    for token in tokens:
        expanded.append(token)
        if token.endswith("s") and len(token) > 3:
            expanded.append(token[:-1])
    seen = set()
    ordered: List[str] = []
    for token in expanded:
        if token not in seen:
            seen.add(token)
            ordered.append(token)
    return ordered


def _contains_dependency_pattern(text: str) -> bool:
    tokens = _clean_tokens(text)
    if "for" in tokens or "replacement" in tokens or "spare" in tokens:
        return True
    normalized = _normalized_phrase(text)
    return "compatible with" in normalized


def _extra_word_count(title: str, product_name: str) -> int:
    return max(0, len(_clean_tokens(title)) - len(_clean_tokens(product_name)))


def _is_short_model_query(product_name: str) -> bool:
    tokens = _clean_tokens(product_name)
    return len(tokens) <= 3 and any(any(char.isdigit() for char in token) for token in tokens)


def _is_bundle_style_query(product_name: str) -> bool:
    tokens = set(_clean_tokens(product_name))
    return bool(tokens.intersection({"and", "set", "kit", "combo", "bundle"}))


def _is_audio_family_query(product_name: str, category: str) -> bool:
    query_tokens = set(_clean_tokens(product_name))
    category_tokens = set(_category_tokens(category))
    audio_markers = {"earbud", "earbuds", "earphone", "earphones", "headset", "headphone", "headphones", "audio", "speaker"}
    return bool(query_tokens.intersection(audio_markers) or category_tokens.intersection(audio_markers))


def _is_tire_family_query(product_name: str, category: str) -> bool:
    query_tokens = set(_clean_tokens(product_name))
    category_tokens = set(_category_tokens(category))
    return "tyre" in query_tokens or "tyre" in category_tokens


def _tire_family_title_match(title: str, product_name: str) -> bool:
    title_tokens = _clean_tokens(title)
    query_tokens = [token for token in _clean_tokens(product_name) if token != "tyre"]
    if not title_tokens or not query_tokens:
        return False
    if not _contains_tokens_in_order(title_tokens, query_tokens):
        return False

    has_numeric_signal = any(any(char.isdigit() for char in token) for token in title_tokens)
    has_model_signal = any(token in TIRE_MODEL_MARKERS for token in title_tokens)
    return has_numeric_signal or has_model_signal


def _too_broad_title(title: str, product_name: str, category: str) -> bool:
    extra_words = _extra_word_count(title, product_name)
    if extra_words < 5:
        return False

    title_tokens = _clean_tokens(title)
    query_tokens = _clean_tokens(product_name)
    query_start = _find_subsequence_start(title_tokens, query_tokens)
    category_tokens = _category_tokens(category)

    if _is_tire_family_query(product_name, category):
        if any(any(char.isdigit() for char in token) for token in title_tokens):
            return False
        return extra_words >= 10

    if _is_audio_family_query(product_name, category):
        if query_start != -1:
            return False
        return extra_words >= 12

    if _is_short_model_query(product_name):
        if query_start != -1 and category_tokens:
            nearby_window = title_tokens[query_start + len(query_tokens):query_start + len(query_tokens) + 3]
            if any(token in category_tokens for token in nearby_window):
                return False
        return extra_words >= 12

    if _is_bundle_style_query(product_name):
        if any(term in title_tokens for term in {"set", "kit", "combo", "bundle"}):
            return extra_words >= 10
        return extra_words >= 8

    return True


def _category_noun_too_late(title: str, product_name: str, category: str) -> bool:
    title_tokens = _clean_tokens(title)
    query_tokens = _clean_tokens(product_name)
    category_tokens = _category_tokens(category)
    if not title_tokens or not query_tokens or not category_tokens:
        return False

    category_positions = [
        index for index, token in enumerate(title_tokens) if token in category_tokens
    ]
    if not category_positions:
        return False

    query_start = _find_subsequence_start(title_tokens, query_tokens)
    category_index = category_positions[0]
    broad_title = _too_broad_title(title, product_name, category)
    if query_start == -1:
        return broad_title and category_index > 4

    return broad_title and category_index > (query_start + len(query_tokens) + 3)


def _positional_accessory_match(title: str, product_name: str) -> bool:
    title_tokens = _clean_tokens(title)
    query_tokens = _clean_tokens(product_name)
    if not title_tokens or not query_tokens:
        return False

    query_start = _find_subsequence_start(title_tokens, query_tokens)
    if query_start == -1:
        return False

    before = title_tokens[:query_start]
    after = title_tokens[query_start + len(query_tokens):query_start + len(query_tokens) + 3]

    if any(token in ACCESSORY_KEYWORDS for token in before):
        return True
    if any(token in ACCESSORY_KEYWORDS for token in after):
        return True
    return False


def strict_name_match(title: str, product_name: str) -> bool:
    title_tokens = _clean_tokens(title)
    query_tokens = _clean_tokens(product_name)
    if not title_tokens or not query_tokens:
        return False
    return _contains_tokens_in_order(title_tokens, query_tokens)


def retail_name_match(title: str, product_name: str) -> bool:
    return strict_name_match(title, product_name)


def is_accessory(title: str, product_name: str, category: str) -> bool:
    normalized_title = _normalized_phrase(title)
    if not normalized_title:
        return False

    if _contains_dependency_pattern(normalized_title):
        return True
    if _too_broad_title(title, product_name, category):
        return True
    if _category_noun_too_late(title, product_name, category):
        return True
    if _positional_accessory_match(title, product_name):
        return True
    return any(keyword in normalized_title.split() for keyword in ACCESSORY_KEYWORDS)


def constraint_failure_reason(item: Dict[str, Any], product_name: str, category: str) -> Optional[str]:
    title = (item.get("title") or "").strip()
    if not title:
        return "missing_title"

    platform = (item.get("platform") or "").strip().lower()
    if strict_name_match(title, product_name):
        pass
    elif _is_tire_family_query(product_name, category) and _tire_family_title_match(title, product_name):
        pass
    elif platform == "daraz" and retail_name_match(title, product_name):
        pass
    else:
        return "name_mismatch"

    normalized_title = _normalized_phrase(title)
    if not _is_tire_family_query(product_name, category) and _contains_dependency_pattern(normalized_title):
        return "dependency_pattern"
    if _too_broad_title(title, product_name, category):
        return "too_broad"
    if _category_noun_too_late(title, product_name, category):
        return "category_noun_late"
    if _positional_accessory_match(title, product_name):
        return "positional_accessory"
    if any(keyword in normalized_title.split() for keyword in ACCESSORY_KEYWORDS):
        return "accessory_keyword"

    return None


def passes_all_constraints(item: Dict[str, Any], product_name: str, category: str) -> bool:
    return constraint_failure_reason(item, product_name, category) is None


def _count_wholesale_items(wholesale: Dict[str, List[Dict[str, Any]]]) -> int:
    return sum(len(items) for items in wholesale.values())


def _summarize_platform_counts(payload: Dict[str, Any]) -> Dict[str, Any]:
    wholesale = payload.get("wholesale") or {}
    retail = payload.get("retail") or []
    return {
        "wholesale_by_platform": {
            platform: len(items or [])
            for platform, items in wholesale.items()
        },
        "wholesale_total": _count_wholesale_items(wholesale),
        "retail_total": len(retail),
    }


def _dedupe_dict_items(items: List[Dict[str, Any]], keys: List[str]) -> List[Dict[str, Any]]:
    deduped: List[Dict[str, Any]] = []
    seen_urls = set()
    seen_secondary = set()
    for item in items:
        url = str(item.get("source_url") or item.get("url") or "").strip().lower()
        if url:
            if url in seen_urls:
                continue
            seen_urls.add(url)

        signature = tuple(str(item.get(key, "")).strip().lower() for key in keys)
        if signature in seen_secondary:
            continue
        seen_secondary.add(signature)
        deduped.append(item)
    return deduped


def _normalize_retail_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    normalized = deepcopy(item)
    title = (normalized.get("title") or "").strip()
    list_price = normalized.get("list_price") or normalized.get("price_pkr")
    if not title or list_price in (None, 0, 0.0):
        return None

    normalized["title"] = title
    normalized["seller"] = normalized.get("seller") or normalized.get("platform", "Unknown Seller")
    normalized["platform"] = normalized.get("platform") or "daraz"
    normalized["url"] = normalized.get("url") or ""
    normalized["promo"] = normalized.get("promo") or ""
    normalized["list_price"] = float(list_price)
    normalized["price_pkr"] = float(list_price)
    normalized["detail"] = normalized.get("detail")
    return normalized


def _normalize_wholesale_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    normalized = deepcopy(item)
    title = (normalized.get("title") or "").strip()
    unit_price = normalized.get("unit_price")
    if unit_price in (None, "", 0, 0.0):
        min_price, _, _ = _price_range_from_text(normalized.get("price_text") or "")
        unit_price = min_price
    if not title or unit_price in (None, "", 0, 0.0):
        return None

    normalized["title"] = title
    normalized["supplier"] = normalized.get("supplier") or "Unknown Supplier"
    normalized["unit_price"] = float(unit_price)
    normalized["currency"] = (normalized.get("currency") or "USD").upper()
    normalized["unit_price_pkr"] = normalized.get("unit_price_pkr") or _convert_to_pkr(normalized["unit_price"], normalized["currency"])
    normalized["source_url"] = normalized.get("source_url") or normalized.get("url") or ""
    normalized["platform"] = normalized.get("platform") or "made_in_china"
    normalized["moq"] = int(normalized.get("moq") or 1)
    normalized["attributes_listing"] = normalized.get("attributes_listing") or {}
    normalized["origin"] = normalized.get("origin") or normalized.get("vendor_location") or ""
    return normalized


def modular_sieve_filter(raw_result: Dict[str, Any], product_name: str, category: str) -> Dict[str, Any]:
    filtered_wholesale: Dict[str, List[Dict[str, Any]]] = {}
    rejection_stats = {
        "missing_required": 0,
        "constraint_rejected": 0,
        "duplicate_rejected": 0,
        "constraint_reasons": {},
    }
    platform_stats: Dict[str, Dict[str, int]] = {}

    for platform, items in (raw_result.get("wholesale") or {}).items():
        normalized_items: List[Dict[str, Any]] = []
        raw_count = len(items or [])
        platform_reason_counts: Dict[str, int] = {}
        for item in items:
            normalized = _normalize_wholesale_item(item)
            if not normalized:
                rejection_stats["missing_required"] += 1
                continue
            failure_reason = constraint_failure_reason(normalized, product_name, category)
            if failure_reason:
                rejection_stats["constraint_rejected"] += 1
                rejection_stats["constraint_reasons"][failure_reason] = rejection_stats["constraint_reasons"].get(failure_reason, 0) + 1
                platform_reason_counts[failure_reason] = platform_reason_counts.get(failure_reason, 0) + 1
                continue
            normalized_items.append(normalized)

        deduped_wholesale = _dedupe_dict_items(
            normalized_items,
            ["supplier", "unit_price"],
        )[:MAX_FINAL_ITEMS_PER_PLATFORM]
        rejection_stats["duplicate_rejected"] += max(0, len(normalized_items) - len(deduped_wholesale))
        platform_stats[platform] = {
            "raw": raw_count,
            "normalized": len(normalized_items),
            "final": len(deduped_wholesale),
            "constraint_reasons": platform_reason_counts,
        }
        if deduped_wholesale:
            filtered_wholesale[platform] = deduped_wholesale

    filtered_retail: List[Dict[str, Any]] = []
    retail_raw_count = len(raw_result.get("retail", []))
    retail_reason_counts: Dict[str, int] = {}
    for item in raw_result.get("retail", []):
        normalized = _normalize_retail_item(item)
        if not normalized:
            rejection_stats["missing_required"] += 1
            continue
        failure_reason = constraint_failure_reason(normalized, product_name, category)
        if failure_reason:
            rejection_stats["constraint_rejected"] += 1
            rejection_stats["constraint_reasons"][failure_reason] = rejection_stats["constraint_reasons"].get(failure_reason, 0) + 1
            retail_reason_counts[failure_reason] = retail_reason_counts.get(failure_reason, 0) + 1
            continue
        filtered_retail.append(normalized)

    deduped_retail = _dedupe_dict_items(filtered_retail, ["seller", "list_price"])[:MAX_FINAL_ITEMS_PER_PLATFORM]
    rejection_stats["duplicate_rejected"] += max(0, len(filtered_retail) - len(deduped_retail))
    retail_stats = {
        "raw": retail_raw_count,
        "normalized": len(filtered_retail),
        "final": len(deduped_retail),
        "constraint_reasons": retail_reason_counts,
    }

    return {
        "product_name": raw_result.get("product_name", product_name),
        "links_used": raw_result.get("links_used", {}),
        "wholesale": filtered_wholesale,
        "retail": deduped_retail,
        "sieve_stats": {
            **rejection_stats,
            "wholesale_count": _count_wholesale_items(filtered_wholesale),
            "retail_count": len(deduped_retail),
            "platform_breakdown": {
                "wholesale": platform_stats,
                "retail": retail_stats,
            },
        },
    }


def _mic_listing_search_urls(product_name: str) -> List[str]:
    q = quote_plus(product_name)
    slug = _slugify_query_for_mic(product_name)
    return [
        f"https://www.made-in-china.com/productdirectory.do?word={q}&subaction=hunt",
        f"https://www.made-in-china.com/products-search/hot-china-products/{slug}.html",
    ]


def _mic_query_variants(product_name: str, category: str = "") -> List[str]:
    cleaned = _normalize_whitespace(product_name)
    variants = [cleaned]
    tokens = cleaned.split()
    lowered_category = _normalize_whitespace(category).lower()
    if tokens:
        model_like = next((token for token in tokens if any(char.isdigit() for char in token)), None)
        if model_like:
            if any(term in lowered_category for term in ("headset", "headphone", "earbud", "audio", "speaker")):
                variants.extend(
                    [
                        f"{model_like} headset",
                        f"{model_like} headphones",
                        f"{model_like} bluetooth headset",
                    ]
                )
            elif any(term in lowered_category for term in ("drone", "quadcopter", "uav")):
                variants.extend(
                    [
                        f"{model_like} drone",
                        f"{model_like} quadcopter",
                    ]
                )
    lowered = cleaned.lower()
    is_audio_category = any(term in lowered_category for term in ("headset", "headphone", "earbud", "audio", "speaker"))
    if "wireless headphones" in lowered and (is_audio_category or not lowered_category):
        variants.append(cleaned.lower().replace("wireless headphones", "bluetooth headset"))
        variants.append(cleaned.lower().replace("wireless headphones", "headset"))
    if "headphones" in lowered and (is_audio_category or not lowered_category):
        variants.append(cleaned.lower().replace("headphones", "headset"))
    deduped: List[str] = []
    seen = set()
    for variant in variants:
        normalized = _normalize_whitespace(variant)
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped


def _is_probable_supplier_name(text: str) -> bool:
    lowered = _normalize_whitespace(text).lower()
    if not lowered:
        return False
    if "us$" in lowered or "moq" in lowered or "pieces" in lowered:
        return False
    if ":" in lowered:
        return False
    if len(lowered) > 160:
        return False
    supplier_markers = ("co., ltd", "company", "factory", "technology", "trading", "industry", "industrial")
    return any(marker in lowered for marker in supplier_markers)


def _clean_supplier_name(text: str) -> str:
    cleaned = _normalize_whitespace(text)
    if not cleaned:
        return ""

    cleaned = re.split(
        r"(Suppliers with verified business licenses|Secured Trading Service|Rating:|Audited Supplier|Gold Member|Diamond Member|Manufacturer/Factory|Trading Company|Buy Now|Send Inquiry|Chat Now|Add to inquiry basket)",
        cleaned,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    cleaned = re.sub(r"\b(guangdong|henan|jiangsu|jiangxi|foshan|shenzhen),\s*china\b.*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -,.")

    company_phrases = re.findall(r"[A-Z][A-Za-z0-9 .,&()'/-]*?Co\., Ltd\.?", cleaned)
    if company_phrases:
        first_company = company_phrases[0].strip(" -,.")
        duplicate_companies = [
            phrase.strip(" -,.").lower()
            for phrase in company_phrases
            if phrase.strip(" -,.")
        ]
        if duplicate_companies.count(first_company.lower()) >= 2:
            cleaned = first_company

    company_phrase = re.match(r"^(.+?Co\., Ltd\.)", cleaned, flags=re.IGNORECASE)
    if company_phrase:
        maybe_company = company_phrase.group(1).strip()
        if maybe_company.lower() in cleaned[len(maybe_company):].lower():
            cleaned = maybe_company

    repeated_company = re.match(r"^(.+?Co\., Ltd\.?)\s+\1$", cleaned, flags=re.IGNORECASE)
    if repeated_company:
        cleaned = repeated_company.group(1)

    repeated_generic = re.match(r"^(.+?)\s+\1$", cleaned, flags=re.IGNORECASE)
    if repeated_generic:
        cleaned = repeated_generic.group(1)

    tokens = cleaned.split()
    if len(tokens) % 2 == 0:
        midpoint = len(tokens) // 2
        left = " ".join(tokens[:midpoint]).strip()
        right = " ".join(tokens[midpoint:]).strip()
        if left and left.lower() == right.lower():
            cleaned = left

    if cleaned.endswith("Ltd") and "Co.," in cleaned:
        cleaned += "."
    return cleaned.strip()


def _clean_origin(text: str) -> str:
    cleaned = _normalize_whitespace(text)
    cleaned = re.sub(
        r"\b(?:Audited Supplier|Gold Member|Diamond Member|Secured Trading Service|verified business licenses|Supplier|Service|licenses?)\b",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    matches = re.findall(r"([A-Za-z][A-Za-z .&'-]{1,40},\s*China)\b", cleaned)
    return matches[-1] if matches else ""


def _wholesale_semantic_match(title: str, product_name: str) -> bool:
    return strict_name_match(title, product_name)


def _find_first_text(nodes: List[Any], pattern: str) -> Optional[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    for node in nodes:
        text = node.get_text(" ", strip=True)
        if text and regex.search(text):
            return text
    return None


def _build_mic_listing_item(anchor: Any) -> Optional[Dict[str, Any]]:
    title = _normalize_whitespace(anchor.get_text(" ", strip=True))
    href = (anchor.get("href") or "").strip()
    if not title or len(title) < 5 or not href:
        return None
    if title.lower().startswith("us$") or "fob price" in title.lower():
        return None

    absolute_url = href
    if href.startswith("//"):
        absolute_url = "https:" + href
    elif href.startswith("/"):
        absolute_url = urljoin("https://www.made-in-china.com", href)

    if "made-in-china.com" not in absolute_url and ".en.made-in-china.com" not in absolute_url:
        return None

    card = anchor
    for _ in range(6):
        parent = getattr(card, "parent", None)
        if not parent:
            break
        card = parent
        card_text = card.get_text(" ", strip=True)
        if "MOQ" in card_text and ("US$" in card_text or "USD" in card_text.upper()):
            break

    text_nodes = card.find_all(["a", "div", "span", "p", "li", "strong"])
    card_text = card.get_text(" ", strip=True)
    price_text = _find_first_text(text_nodes, r"(US\$|USD|RMB|CNY)\s*\d")
    moq_text = _find_first_text(text_nodes, r"\b\d[\d,]*\s*(pieces?|sets?)\s*\(MOQ\)")
    if not moq_text:
        moq_text = _find_first_text(text_nodes, r"\bMOQ\b")
    supplier_name = None
    for node in text_nodes:
        text = _normalize_whitespace(node.get_text(" ", strip=True))
        if text == title:
            continue
        cleaned_supplier = _clean_supplier_name(text)
        if _is_probable_supplier_name(cleaned_supplier):
            supplier_name = cleaned_supplier
            break

    cleaned_origin = _clean_origin(card_text)
    price_info = _mic_price_summary(price_text or card_text)
    if not price_info["unit_price"]:
        return None

    moq_match = re.search(r"(\d[\d,]*)\s*(?:pieces?|sets?)\s*\(MOQ\)", moq_text or card_text, re.IGNORECASE)
    moq = int(moq_match.group(1).replace(",", "")) if moq_match else None

    return {
        "platform": "made_in_china",
        "title": title,
        "supplier": supplier_name or "Unknown Supplier",
        "moq": moq or 1,
        "unit_price": price_info["unit_price"],
        "price_max": price_info["price_max"],
        "unit_price_pkr": _convert_to_pkr(price_info["unit_price"], price_info["currency"]),
        "currency": price_info["currency"],
        "origin": cleaned_origin,
        "source_url": absolute_url.split("#")[0],
        "attributes_listing": {},
        "price_text": price_info["price_text"],
        "raw_card_text": _normalize_whitespace(card_text),
    }


def _scrape_made_in_china_listing_with_diagnostics(
    product_name: str,
    category: str = "",
    max_items: int = 10,
    moq: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], str, Dict[str, Any]]:
    query_variants = _mic_query_variants(product_name, category)
    last_search_url = _mic_listing_search_urls(product_name)[0]
    all_results: List[Dict[str, Any]] = []
    seen = set()
    diagnostics = {
        "query_variants_tried": query_variants,
        "search_urls_tried": [],
        "fetch_failures": 0,
        "pages_with_no_anchors": 0,
        "cards_parsed": 0,
        "cards_missing_supplier_or_origin": 0,
        "cards_rejected_semantic": 0,
        "cards_rejected_moq": 0,
        "accepted_items": 0,
    }

    for query_variant in query_variants:
        for search_url in _mic_listing_search_urls(query_variant):
            last_search_url = search_url
            diagnostics["search_urls_tried"].append(search_url)
            soup = _fetch_html(search_url)
            if not soup:
                diagnostics["fetch_failures"] += 1
                continue

            title_selectors = [
                "h2 a[href]",
                "h3 a[href]",
                'a[href*="made-in-china.com/product"]',
                'a[href*=".en.made-in-china.com/product"]',
            ]

            anchors: List[Any] = []
            for selector in title_selectors:
                anchors.extend(soup.select(selector))
            if not anchors:
                anchors = soup.find_all("a", href=True)
            if not anchors:
                diagnostics["pages_with_no_anchors"] += 1
                continue

            for anchor in anchors:
                item = _build_mic_listing_item(anchor)
                if not item:
                    continue
                diagnostics["cards_parsed"] += 1
                if item.get("supplier") == "Unknown Supplier" or not item.get("origin"):
                    diagnostics["cards_missing_supplier_or_origin"] += 1
                if not _wholesale_semantic_match(item["title"], product_name):
                    diagnostics["cards_rejected_semantic"] += 1
                    continue
                if moq is not None and item.get("moq") and item["moq"] > moq:
                    diagnostics["cards_rejected_moq"] += 1
                    continue

                signature = (
                    item["title"].strip().lower(),
                    item["supplier"].strip().lower(),
                    item["source_url"].strip().lower(),
                )
                if signature in seen:
                    continue
                seen.add(signature)
                all_results.append(item)
                diagnostics["accepted_items"] += 1
                if len(all_results) >= max_items:
                    return all_results[:max_items], last_search_url, diagnostics

            if all_results:
                return all_results[:max_items], last_search_url, diagnostics

    return all_results[:max_items], last_search_url, diagnostics


def scrape_made_in_china_listing(product_name: str, category: str = "", max_items: int = 10, moq: Optional[int] = None) -> Tuple[List[Dict[str, Any]], str]:
    results, search_url, diagnostics = _scrape_made_in_china_listing_with_diagnostics(product_name, category=category, max_items=max_items, moq=moq)
    logger.info("MIC diagnostics for %s: %s", product_name, diagnostics)
    return results, search_url


def _generic_extract_search_results(
    url: str,
    platform: str,
    source_type: str,
    max_items: int = 10,
    soup: Optional[BeautifulSoup] = None,
) -> List[Dict[str, Any]]:
    soup = soup or _fetch_html(url)
    if not soup:
        return []

    results: List[Dict[str, Any]] = []
    seen = set()

    for anchor in soup.find_all("a", href=True):
        title = anchor.get_text(" ", strip=True)
        href = anchor["href"]
        if not title or len(title) < 3:
            continue

        card = anchor.parent or anchor
        price = None
        for node in card.find_all(["span", "div", "p", "strong"]):
            text = node.get_text(" ", strip=True)
            if "rs" in text.lower() or "$" in text:
                price = _clean_price_to_float(text)
                if price:
                    break
        if price is None:
            price = _clean_price_to_float(card.get_text(" ", strip=True))
        if not price:
            continue

        key = (title.lower(), href)
        if key in seen:
            continue
        seen.add(key)

        if source_type == "retail":
            results.append(
                {
                    "seller": platform,
                    "platform": platform,
                    "title": title,
                    "list_price": price,
                    "promo": "",
                    "url": href,
                    "detail": None,
                }
            )
        elif source_type == "wholesale":
            results.append(
                {
                    "platform": platform,
                    "title": title,
                    "supplier": platform,
                    "moq": 1,
                    "unit_price": price,
                    "currency": "USD" if "$" in card.get_text(" ", strip=True) else "PKR",
                    "origin": "",
                    "source_url": href,
                    "attributes_listing": {},
                    "price_text": card.get_text(" ", strip=True),
                }
            )
        if len(results) >= max_items:
            break

    return results


def scrape_daraz_listing(product_name: str, max_items: int = 10) -> Tuple[List[Dict[str, Any]], str]:
    q = quote_plus(product_name)
    search_url = f"https://www.daraz.pk/catalog/?q={q}"
    results: List[Dict[str, Any]] = []

    def _daraz_fallback(rendered_html: Optional[str] = None) -> List[Dict[str, Any]]:
        if rendered_html:
            try:
                rendered_soup = BeautifulSoup(rendered_html, "html.parser")
                items = _generic_extract_search_results(
                    search_url,
                    "daraz",
                    "retail",
                    max_items=max_items,
                    soup=rendered_soup,
                )
                if items:
                    logger.info("Daraz fallback via rendered HTML returned %s items for %s", len(items), product_name)
                    return items
            except Exception as exc:
                logger.warning("Daraz rendered HTML fallback failed for %s: %s", product_name, exc)
        api_payload = _daraz_mtop_search_payload(product_name, page=1)
        if api_payload:
            items = _extract_daraz_api_items(api_payload, max_items=max_items)
            if items:
                logger.info("Daraz fallback via mtop API returned %s items for %s", len(items), product_name)
                return items
        scraperapi_soup = _fetch_html_via_scraperapi(search_url)
        if scraperapi_soup:
            items = _generic_extract_search_results(
                search_url,
                "daraz",
                "retail",
                max_items=max_items,
                soup=scraperapi_soup,
            )
            if items:
                logger.info("Daraz fallback via ScraperAPI returned %s items for %s", len(items), product_name)
                return items
        return _generic_extract_search_results(search_url, "daraz", "retail", max_items=max_items)

    if not _playwright_is_available():
        logger.warning("Playwright unavailable for Daraz; using fallback HTML extraction")
        return _daraz_fallback(), search_url

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
            )
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=HEADERS["User-Agent"],
            )
            page = context.new_page()
            page.goto(search_url, wait_until="domcontentloaded", timeout=DARAZ_GOTO_TIMEOUT_MS)
            page.wait_for_timeout(DARAZ_SETTLE_TIMEOUT_MS)

            cards = page.query_selector_all('div[class*="Bm3ON"]')
            for card in cards[:max_items]:
                title_el = card.query_selector('a[href*="/products/"]')
                price_el = card.query_selector("span.ooOxS")
                promo_el = card.query_selector("div.WNoq3 span")
                if not title_el or not price_el:
                    continue

                title_div = card.query_selector('div[class*="fADt"]')
                title = title_div.inner_text().strip() if title_div else ""
                if not title:
                    title = title_el.get_attribute("title") or title_el.inner_text().strip()

                url = title_el.get_attribute("href") or ""
                if url.startswith("//"):
                    url = "https:" + url

                # Keep the verified Daraz source simple and reliable.
                # Listing data is the only part consistently working in live runs.
                detail = None
                seller_name = "daraz"

                results.append(
                    {
                        "seller": seller_name,
                        "platform": "daraz",
                        "title": title,
                        "url": url,
                        "list_price": _parse_daraz_price(price_el.inner_text()),
                        "promo": promo_el.inner_text().strip() if promo_el else "",
                        "detail": detail,
                    }
                )

            if not results:
                rendered_html = page.content()
                logger.info("Daraz Playwright selectors returned no cards for %s; trying fallback extraction", product_name)
                browser.close()
                return _daraz_fallback(rendered_html), search_url

            browser.close()
    except Exception as exc:
        logger.warning("Daraz listing scrape failed for %s: %s", product_name, exc)
        return _daraz_fallback(), search_url

    return results, search_url


def _run_job(job_name: str, runner, search_url: str) -> Tuple[str, List[Dict[str, Any]], str]:
    try:
        items = runner()
        return job_name, items or [], search_url
    except Exception as exc:
        logger.warning("Scraper job failed for %s: %s", job_name, exc)
        return job_name, [], search_url


def _execute_job_group(
    jobs: Dict[str, Tuple[Any, str]],
    use_parallel: bool = True,
) -> Dict[str, Tuple[List[Dict[str, Any]], str]]:
    results: Dict[str, Tuple[List[Dict[str, Any]], str]] = {}
    if not use_parallel:
        for job_name, (runner, search_url) in jobs.items():
            _, items, link = _run_job(job_name, runner, search_url)
            results[job_name] = (items, link)
        return results

    with ThreadPoolExecutor(max_workers=max(1, len(jobs))) as executor:
        futures = {
            executor.submit(_run_job, job_name, runner, search_url): job_name
            for job_name, (runner, search_url) in jobs.items()
        }
        for future in as_completed(futures):
            job_name = futures[future]
            _, items, link = future.result()
            results[job_name] = (items, link)
    return results


def _build_raw_scrape_result(
    product_name: str,
    wholesale_results: Dict[str, Tuple[List[Dict[str, Any]], str]],
    retail_results: Dict[str, Tuple[List[Dict[str, Any]], str]],
) -> Dict[str, Any]:
    links_used: Dict[str, Any] = {}
    wholesale: Dict[str, List[Dict[str, Any]]] = {}
    retail: List[Dict[str, Any]] = []
    for platform, (items, search_url) in wholesale_results.items():
        wholesale[platform] = items
        links_used[f"{platform}_search"] = search_url
    for platform, (items, search_url) in retail_results.items():
        retail.extend(items)
        links_used[f"{platform}_search"] = search_url
    return {
        "product_name": product_name,
        "links_used": links_used,
        "wholesale": wholesale,
        "retail": retail,
    }


def _post_process_scrape_result(
    raw_result: Dict[str, Any],
    product_name: str,
    category: str,
    normalize: bool = False,
    persist: bool = False,
) -> Dict[str, Any]:
    filtered = modular_sieve_filter(raw_result, product_name, category)
    filtered["raw_capture"] = raw_result
    if raw_result.get("wholesale_diagnostics"):
        filtered["wholesale_diagnostics"] = raw_result["wholesale_diagnostics"]

    raw_counts = _summarize_platform_counts(raw_result)
    final_counts = _summarize_platform_counts(filtered)
    logger.info(
        "Scrape counts for %s | wholesale raw=%s retail raw=%s | wholesale final=%s retail final=%s",
        product_name,
        raw_counts["wholesale_by_platform"],
        raw_counts["retail_total"],
        final_counts["wholesale_by_platform"],
        final_counts["retail_total"],
    )
    for platform, stats in (filtered.get("sieve_stats", {}).get("platform_breakdown", {}).get("wholesale", {}) or {}).items():
        logger.info(
            "%s counts for %s | raw=%s normalized=%s final=%s",
            platform,
            product_name,
            stats["raw"],
            stats["normalized"],
            stats["final"],
        )
    retail_stats = (filtered.get("sieve_stats", {}).get("platform_breakdown", {}).get("retail") or {})
    logger.info(
        "Retail counts for %s | raw=%s normalized=%s final=%s",
        product_name,
        retail_stats.get("raw", 0),
        retail_stats.get("normalized", 0),
        retail_stats.get("final", 0),
    )
    if normalize or persist:
        from app.services.nlp_agent import NLPAgent

        nlp_agent = NLPAgent()
        normalized_output = nlp_agent.process(filtered, product_name, category, persist=persist)
        filtered["normalized_output"] = normalized_output
        filtered["persisted"] = persist
    return filtered


def scrape_product_platforms_traditional(
    product_name: str,
    category: str,
    moq: Optional[int] = None,
) -> Dict[str, Any]:
    wholesale_jobs: Dict[str, Tuple[Any, str]] = {
        "made_in_china": (
            lambda: scrape_made_in_china_listing(product_name, max_items=10, moq=moq)[0],
            _mic_listing_search_urls(product_name)[0],
        )
    }
    retail_jobs: Dict[str, Tuple[Any, str]] = {
        "daraz": (
            lambda: scrape_daraz_listing(product_name, max_items=10)[0]
            or _generic_extract_search_results(
                f"https://www.daraz.pk/catalog/?q={quote_plus(product_name)}",
                "daraz",
                "retail",
                max_items=10,
            ),
            f"https://www.daraz.pk/catalog/?q={quote_plus(product_name)}",
        )
    }
    raw = _build_raw_scrape_result(
        product_name,
        _execute_job_group(wholesale_jobs, use_parallel=False),
        _execute_job_group(retail_jobs, use_parallel=False),
    )
    return modular_sieve_filter(raw, product_name, category)


def scrape_product_platforms_generic(
    product_name: str,
    category: str,
) -> Dict[str, Any]:
    search_url = f"https://www.daraz.pk/catalog/?q={quote_plus(product_name)}"
    raw = {
        "product_name": product_name,
        "links_used": {"daraz_search": search_url, "made_in_china_search": _mic_listing_search_urls(product_name)[0]},
        "wholesale": {
            "made_in_china": _generic_extract_search_results(
                _mic_listing_search_urls(product_name)[0],
                "made_in_china",
                "wholesale",
                max_items=10,
            ),
        },
        "retail": _generic_extract_search_results(search_url, "daraz", "retail", max_items=10),
    }
    return modular_sieve_filter(raw, product_name, category)


def persist_scrape_results(
    scraped_result: Dict[str, Any],
    product_name: str,
    category: str,
) -> Dict[str, Any]:
    from app.services.nlp_agent import NLPAgent

    nlp_agent = NLPAgent()
    return nlp_agent.process(scraped_result, product_name, category, persist=True)


def scrape_product_platforms(
    product_name: str,
    category: str,
    moq: Optional[int] = None,
    normalize: bool = False,
    persist: bool = False,
    use_parallel: bool = True,
) -> Dict[str, Any]:
    mic_diagnostics: Dict[str, Any] = {}

    def _mic_runner() -> List[Dict[str, Any]]:
        nonlocal mic_diagnostics
        items, _search_url, diagnostics = _scrape_made_in_china_listing_with_diagnostics(product_name, category=category, max_items=20, moq=moq)
        mic_diagnostics = diagnostics
        return items

    wholesale_jobs: Dict[str, Tuple[Any, str]] = {
        "made_in_china": (
            _mic_runner,
            _mic_listing_search_urls(product_name)[0],
        )
    }
    retail_jobs: Dict[str, Tuple[Any, str]] = {
        "daraz": (
            lambda: scrape_daraz_listing(product_name, max_items=20)[0]
            or _generic_extract_search_results(
                f"https://www.daraz.pk/catalog/?q={quote_plus(product_name)}",
                "daraz",
                "retail",
                max_items=10,
            ),
            f"https://www.daraz.pk/catalog/?q={quote_plus(product_name)}",
        )
    }

    wholesale_results = _execute_job_group(wholesale_jobs, use_parallel=use_parallel)
    retail_results = _execute_job_group(retail_jobs, use_parallel=use_parallel)
    raw = _build_raw_scrape_result(product_name, wholesale_results, retail_results)
    raw["wholesale_diagnostics"] = {"made_in_china": mic_diagnostics}
    return _post_process_scrape_result(raw, product_name, category, normalize=normalize, persist=persist)
