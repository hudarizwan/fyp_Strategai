"""
NLP Agent for StrategAI.

Transforms noisy scraper output into normalized, clustered, analytics-ready
records and optionally persists both records and cluster summaries into ECDB.
"""

from __future__ import annotations

import math
import logging
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.services.ecdb import ECDB

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:  # pragma: no cover - local compiled sklearn may be unavailable
    TfidfVectorizer = None
    cosine_similarity = None


logger = logging.getLogger(__name__)


def _cosine(v1: List[float], v2: List[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


class SimpleTfidfVectorizer:
    """Small fallback TF-IDF implementation used when sklearn is unavailable."""

    def __init__(self):
        self.vocabulary_: List[str] = []
        self.idf_: Dict[str, float] = {}

    def fit_transform(self, texts: List[str]) -> List[List[float]]:
        docs = [text.split() for text in texts]
        document_count = len(docs) or 1
        df = Counter()

        for doc in docs:
            for token in set(doc):
                df[token] += 1

        self.vocabulary_ = sorted(df.keys())
        self.idf_ = {
            token: math.log((1 + document_count) / (1 + freq)) + 1.0
            for token, freq in df.items()
        }

        matrix: List[List[float]] = []
        for doc in docs:
            counts = Counter(doc)
            total = sum(counts.values()) or 1
            row = []
            for token in self.vocabulary_:
                tf = counts[token] / total
                row.append(tf * self.idf_[token])
            matrix.append(row)

        return matrix


class NLPAgent:
    """Cleaning, normalization, matching, clustering, and persistence pipeline."""

    USD_TO_PKR = 280.0
    CNY_TO_PKR = 39.0
    AED_TO_PKR = 76.0
    TFIDF_SIMILARITY_THRESHOLD = 0.68
    MARKETING_NOISE = {
        "new",
        "sale",
        "hot",
        "deal",
        "offer",
        "best",
        "top",
        "original",
        "authentic",
        "genuine",
        "official",
        "wholesale",
        "retail",
        "cheap",
        "discount",
        "free",
        "shipping",
        "delivery",
        "shop",
        "store",
        "seller",
        "pakistan",
    }
    ACCESSORY_KEYWORDS = {
        "case",
        "cover",
        "protector",
        "glass",
        "pouch",
        "bag",
        "holder",
        "stand",
        "cable",
        "charger",
        "adapter",
        "mount",
        "strap",
        "skin",
        "sticker",
        "replacement",
        "spare",
        "part",
        "keycap",
        "wrist",
        "rest",
    }
    STORAGE_PATTERN = re.compile(r"\b(64|128|256|512|1024)\s*gb\b", re.IGNORECASE)
    ROMAN_NUMERAL_TOKENS = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"}
    MODEL_STOPWORDS = {
        "wireless",
        "wired",
        "gaming",
        "headset",
        "headphone",
        "headphones",
        "earbuds",
        "earphones",
        "bluetooth",
        "stereo",
        "noise",
        "cancelling",
        "cancellation",
        "original",
        "factory",
        "spatial",
        "audio",
    }

    def __init__(
        self,
        ecdb_path: Optional[str] = None,
        similarity_threshold: float = TFIDF_SIMILARITY_THRESHOLD,
    ):
        self.db = ECDB(ecdb_path)
        self.similarity_threshold = similarity_threshold
        self.vectorizer = (
            TfidfVectorizer(max_features=250, stop_words="english", ngram_range=(1, 2))
            if TfidfVectorizer
            else SimpleTfidfVectorizer()
        )

    def process(
        self,
        raw_data: Dict[str, Any],
        product_name: str,
        category: str,
        persist: bool = True,
        pipeline_run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run the full NLP pipeline and optionally persist results."""
        extracted_records = self.extract_raw_records(raw_data, product_name, category)
        normalized_records = self.normalize_records(extracted_records, product_name, category)
        valid_records = [record for record in normalized_records if self.validate_record(record)]

        similarity_matrix = self.compute_similarity_matrix(valid_records)
        clusters = self.cluster_similar_products(valid_records, similarity_matrix, product_name, category)
        analytics_ready = self.build_cluster_entities(clusters, product_name, category)

        persisted = {"records": 0, "clusters": 0}
        if persist:
            persisted = self.persist_cleaned_results(
                normalized_records,
                valid_records,
                analytics_ready,
                similarity_matrix,
                pipeline_run_id=pipeline_run_id,
            )

        return {
            "query": product_name,
            "category": category,
            "records": valid_records,
            "products": valid_records,
            "clusters": analytics_ready,
            "clustered_products": analytics_ready,
            "product_groups": [cluster["record_indexes"] for cluster in analytics_ready],
            "similarity_threshold": self.similarity_threshold,
            "stats": {
                "total_extracted": len(extracted_records),
                "after_validation": len(valid_records),
                "cluster_count": len(analytics_ready),
                "persisted_normalized": persisted.get("normalized", 0),
                "persisted_records": persisted["records"],
                "persisted_clusters": persisted["clusters"],
                "persisted_similarity_edges": persisted.get("similarity_edges", 0),
            },
            "clean_data": {
                "wholesale": [record for record in valid_records if record["source_type"] == "wholesale"],
                "retail": [record for record in valid_records if record["source_type"] == "retail"],
            },
            "persisted": persist,
        }

    def clean_text(self, text: str) -> str:
        """Lowercase, remove punctuation/platform junk, and normalize whitespace."""
        if not text:
            return ""

        text = text.lower()
        text = re.sub(r"https?://\S+", " ", text)
        text = re.sub(r"[\[\](){}|_/\\\-,:;]+", " ", text)
        text = re.sub(r"[^a-z0-9\s+]", " ", text)
        tokens = [token for token in text.split() if token not in self.MARKETING_NOISE]
        return " ".join(tokens).strip()

    def extract_raw_records(self, raw_data: Dict[str, Any], product_name: str, category: str) -> List[Dict[str, Any]]:
        """Flatten scraper output into platform-independent raw records."""
        records: List[Dict[str, Any]] = []
        scraped_at = datetime.now(timezone.utc).isoformat()

        for platform, items in (raw_data.get("wholesale") or {}).items():
            for item in items:
                records.append(
                    {
                        "query": product_name,
                        "category": category,
                        "platform": platform,
                        "source_type": "wholesale",
                        "title": item.get("title") or item.get("supplier") or "",
                        "description": " ".join(str(v) for v in (item.get("attributes_listing") or {}).values()),
                        "price_original": item.get("unit_price"),
                        "currency_original": item.get("currency") or "USD",
                        "supplier_or_seller": item.get("supplier") or item.get("vendor_name"),
                        "moq": item.get("moq"),
                        "delivery_info": item.get("delivery_info") or item.get("shipping_terms"),
                        "stock_status": item.get("stock_status") or item.get("stock"),
                        "url": item.get("source_url") or item.get("url"),
                        "vendor_location": item.get("origin") or item.get("vendor_location"),
                        "raw_payload": item,
                        "raw_scrape_record_id": item.get("_raw_scrape_record_id"),
                        "raw_source_type": item.get("_raw_source_type") or "wholesale",
                        "scrape_timestamp": scraped_at,
                    }
                )

        for item in raw_data.get("retail", []):
            detail = item.get("detail") or {}
            delivery_info = detail.get("delivery_options") or detail.get("delivery")
            stock_status = detail.get("stock_status") or detail.get("availability")
            records.append(
                {
                    "query": product_name,
                    "category": category,
                    "platform": item.get("platform", "unknown"),
                    "source_type": "retail",
                    "title": item.get("title") or "",
                    "description": detail.get("full_description") or detail.get("highlights") or "",
                    "price_original": item.get("list_price") or item.get("price_pkr"),
                    "currency_original": item.get("currency") or "PKR",
                    "supplier_or_seller": item.get("seller") or detail.get("seller_name"),
                    "moq": item.get("moq"),
                    "delivery_info": delivery_info,
                    "stock_status": stock_status,
                    "url": item.get("url"),
                    "vendor_location": detail.get("delivery_location"),
                    "seller_rating": self._extract_rating(detail),
                    "raw_payload": item,
                    "raw_scrape_record_id": item.get("_raw_scrape_record_id"),
                    "raw_source_type": item.get("_raw_source_type") or "retail",
                    "scrape_timestamp": scraped_at,
                }
            )

        return records

    def normalize_record(self, record: Dict[str, Any], product_name: str, category: str) -> Dict[str, Any]:
        raw_title = (record.get("title") or "").strip()
        cleaned_title = self.clean_text(raw_title)
        brand, model = self.extract_brand_model(cleaned_title, product_name)
        storage_variant = self.extract_storage_variant(cleaned_title)
        currency_original = (record.get("currency_original") or "PKR").upper()
        price_original = record.get("price_original")
        price_pkr = self.normalize_price(price_original, currency_original)
        raw_payload = record.get("raw_payload") or {}

        return {
            "query": product_name,
            "category": category,
            "platform": record.get("platform", "unknown"),
            "source_type": record.get("source_type", "retail"),
            "raw_title": raw_title,
            "cleaned_title": cleaned_title,
            "normalized_text": self.build_normalized_text(cleaned_title, brand, model, category),
            "cluster_id": None,
            "price_original": price_original,
            "currency_original": currency_original,
            "price_pkr": price_pkr,
            "supplier_or_seller": record.get("supplier_or_seller"),
            "vendor_name": record.get("supplier_or_seller"),
            "seller_name": record.get("supplier_or_seller"),
            "seller_rating": record.get("seller_rating"),
            "moq": record.get("moq") or 1,
            "delivery_info": record.get("delivery_info"),
            "stock_status": record.get("stock_status"),
            "url": record.get("url") or "",
            "brand": brand,
            "model": model,
            "storage_variant": storage_variant,
            "query_product": product_name,
            "scrape_timestamp": record.get("scrape_timestamp") or datetime.utcnow().isoformat(),
            "raw_payload": raw_payload,
            "raw_record": record,
            "raw_scrape_record_id": record.get("raw_scrape_record_id"),
            "raw_source_type": record.get("raw_source_type") or record.get("source_type", "retail"),
            "is_accessory": self.is_accessory(cleaned_title),
            "feature_vector": None,
        }

    def normalize_records(self, records: List[Dict[str, Any]], product_name: str, category: str) -> List[Dict[str, Any]]:
        return [self.normalize_record(record, product_name, category) for record in records]

    def validate_record(self, record: Dict[str, Any]) -> bool:
        if not record.get("raw_title") or not record.get("cleaned_title"):
            return False
        if record.get("price_pkr") in (None, 0, 0.0):
            return False
        if record.get("is_accessory"):
            return False
        return True

    def build_tfidf_vectors(self, records: List[Dict[str, Any]]) -> List[Any]:
        texts = [record["normalized_text"] for record in records]
        if not texts:
            return []
        return self.vectorizer.fit_transform(texts)

    def compute_similarity_matrix(self, records: List[Dict[str, Any]]) -> List[List[float]]:
        if not records:
            return []
        if len(records) == 1:
            return [[1.0]]

        vectors = self.build_tfidf_vectors(records)
        if cosine_similarity is not None and TfidfVectorizer is not None:
            matrix = cosine_similarity(vectors)
            return [[float(value) for value in row] for row in matrix]

        return [[_cosine(v1, v2) for v2 in vectors] for v1 in vectors]

    def cluster_similar_products(
        self,
        records: List[Dict[str, Any]],
        similarity_matrix: List[List[float]],
        product_name: str,
        category: str,
    ) -> List[Dict[str, Any]]:
        if not records:
            return []

        visited = set()
        clusters: List[Dict[str, Any]] = []

        for index, record in enumerate(records):
            if index in visited:
                continue

            queue = [index]
            component = []
            while queue:
                current = queue.pop()
                if current in visited:
                    continue
                visited.add(current)
                component.append(current)

                for neighbor in range(len(records)):
                    if neighbor == current or neighbor in visited:
                        continue
                    if self._records_should_cluster(records[current], records[neighbor], similarity_matrix[current][neighbor]):
                        queue.append(neighbor)

            component.sort()
            cluster_id = self._build_cluster_id(product_name, category, records, component)
            for record_index in component:
                records[record_index]["cluster_id"] = cluster_id

            clusters.append(
                {
                    "cluster_id": cluster_id,
                    "record_indexes": component,
                    "records": [records[i] for i in component],
                }
            )

        return clusters

    def build_cluster_entities(
        self,
        clusters: List[Dict[str, Any]],
        product_name: str,
        category: str,
    ) -> List[Dict[str, Any]]:
        entities: List[Dict[str, Any]] = []
        for cluster in clusters:
            records = cluster["records"]
            wholesale = [record for record in records if record["source_type"] == "wholesale"]
            retail = [record for record in records if record["source_type"] == "retail"]
            prices = [record["price_pkr"] for record in records if record.get("price_pkr")]
            title_counts = Counter(record["cleaned_title"] for record in records if record.get("cleaned_title"))
            canonical_title = title_counts.most_common(1)[0][0] if title_counts else product_name
            platforms = sorted({record["platform"] for record in records})
            vendors = sorted({record["supplier_or_seller"] for record in records if record.get("supplier_or_seller")})

            entity = {
                "cluster_id": cluster["cluster_id"],
                "query": product_name,
                "category": category,
                "canonical_title": canonical_title,
                "brand": self._pick_first(records, "brand"),
                "model": self._pick_first(records, "model"),
                "storage_variant": self._pick_first(records, "storage_variant"),
                "platforms": platforms,
                "platform_count": len(platforms),
                "vendor_count": len(vendors),
                "vendors": vendors,
                "record_indexes": cluster["record_indexes"],
                "records": records,
                "wholesale_records": wholesale,
                "retail_records": retail,
                "wholesale_price_candidates": sorted(
                    [record["price_pkr"] for record in wholesale if record.get("price_pkr")]
                ),
                "retail_price_candidates": sorted(
                    [record["price_pkr"] for record in retail if record.get("price_pkr")]
                ),
                "min_retail_price": min((record["price_pkr"] for record in retail), default=0.0),
                "max_retail_price": max((record["price_pkr"] for record in retail), default=0.0),
                "avg_price": sum(prices) / len(prices) if prices else 0.0,
                "price_spread": (max(prices) - min(prices)) if len(prices) >= 2 else 0.0,
                "traceability": [
                    {
                        "platform": record["platform"],
                        "source_type": record["source_type"],
                        "raw_title": record["raw_title"],
                        "url": record["url"],
                    }
                    for record in records
                ],
            }
            entities.append(entity)

        return entities

    def persist_cleaned_results(
        self,
        normalized_records: List[Dict[str, Any]],
        records: Optional[List[Dict[str, Any]]] = None,
        clusters: Optional[List[Dict[str, Any]]] = None,
        similarity_matrix: Optional[List[List[float]]] = None,
        pipeline_run_id: Optional[str] = None,
    ) -> Dict[str, int]:
        if clusters is None and isinstance(records, list):
            clusters = records
            records = normalized_records
            similarity_matrix = similarity_matrix or [[1.0 for _ in normalized_records] for _ in normalized_records]
        records = records or normalized_records
        clusters = clusters or []
        similarity_matrix = similarity_matrix or [[1.0 for _ in records] for _ in records]
        record_count = 0
        cluster_count = 0
        normalized_count = 0
        similarity_count = 0
        normalized_row_ids: Dict[int, str] = {}

        for index, record in enumerate(normalized_records):
            if pipeline_run_id and record.get("raw_scrape_record_id"):
                normalized_payload = {
                    "pipeline_run_id": pipeline_run_id,
                    "validation_status": "valid" if record in records else "rejected",
                    "rejection_reason": None if record in records else ("accessory" if record.get("is_accessory") else "invalid_or_missing_fields"),
                    "is_accessory": bool(record.get("is_accessory")),
                    "raw_title": record["raw_title"],
                    "cleaned_title": record["cleaned_title"],
                    "normalized_text": record["normalized_text"],
                    "canonical_brand": record.get("brand"),
                    "canonical_model": record.get("model"),
                    "storage_variant": record.get("storage_variant"),
                    "source_type": record["source_type"],
                    "platform_name": record["platform"],
                    "normalized_price_pkr": record.get("price_pkr"),
                    "price_original": record.get("price_original"),
                    "currency_original": record.get("currency_original"),
                    "normalized_supplier_seller": record.get("supplier_or_seller"),
                    "normalized_moq": record.get("moq"),
                    "normalized_stock_status": record.get("stock_status"),
                    "normalized_delivery_info": record.get("delivery_info"),
                    "url": record.get("url"),
                    "feature_vector": record.get("feature_vector"),
                    "normalization_metadata": {
                        "query": record.get("query"),
                        "category": record.get("category"),
                    },
                    "source_type": record["source_type"],
                }
                if record["source_type"] == "wholesale":
                    normalized_payload["raw_wholesale_record_id"] = record["raw_scrape_record_id"]
                else:
                    normalized_payload["raw_retail_record_id"] = record["raw_scrape_record_id"]
                inserted = self.db.insert_normalized_record(normalized_payload)
                normalized_row_ids[index] = inserted.get("id")
                record["_normalized_record_id"] = inserted.get("id")
                normalized_count += 1

        for record in records:
            payload = {
                "product_name": record["query"],
                "category": record["category"],
                "platform": record["platform"],
                "source_type": record["source_type"],
                "clean_title": record["cleaned_title"],
                "brand": record["brand"],
                "model": record["model"],
                "price_pkr": record["price_pkr"],
                "currency": "PKR",
                "moq": record["moq"],
                "vendor_name": record["supplier_or_seller"] if record["source_type"] == "wholesale" else None,
                "seller_name": record["supplier_or_seller"] if record["source_type"] == "retail" else None,
                "seller_rating": record.get("seller_rating"),
                "vendor_location": record.get("vendor_location"),
                "url": record["url"],
                "is_accessory": False,
                "cluster_id": record["cluster_id"],
                "raw_title": record["raw_title"],
                "delivery_info": record.get("delivery_info"),
                "stock_status": record.get("stock_status"),
                "raw_payload": record["raw_payload"],
                "feature_vector": {
                    "normalized_text": record["normalized_text"],
                    "currency_original": record["currency_original"],
                    "price_original": record["price_original"],
                },
            }
            self.db.insert_product(payload)
            record_count += 1

        for cluster in clusters:
            if pipeline_run_id:
                cluster_row = self.db.insert_product_cluster({
                    "pipeline_run_id": pipeline_run_id,
                    "cluster_key": cluster["cluster_id"],
                    "query_text": cluster.get("query"),
                    "category": cluster.get("category"),
                    "canonical_title": cluster.get("canonical_title"),
                    "canonical_brand": cluster.get("brand"),
                    "canonical_model": cluster.get("model"),
                    "storage_variant": cluster.get("storage_variant"),
                    "cluster_status": "active",
                    "similarity_threshold": self.similarity_threshold,
                    "cluster_confidence": 1.0,
                    "platform_count": cluster.get("platform_count"),
                    "vendor_count": cluster.get("vendor_count"),
                    "cluster_metadata": {
                        "wholesale_price_candidates": cluster.get("wholesale_price_candidates"),
                        "retail_price_candidates": cluster.get("retail_price_candidates"),
                        "traceability": cluster.get("traceability"),
                    },
                })
                cluster["db_cluster_id"] = cluster_row.get("id")
                for record_index in cluster.get("record_indexes", []):
                    normalized_record_id = normalized_row_ids.get(record_index)
                    if normalized_record_id:
                        try:
                            self.db.insert_cluster_membership({
                                "pipeline_run_id": pipeline_run_id,
                                "product_cluster_id": cluster_row.get("id"),
                                "normalized_record_id": normalized_record_id,
                                "source_type": records[record_index]["source_type"],
                                "membership_score": 1.0,
                                "is_primary": record_index == cluster["record_indexes"][0],
                            })
                        except Exception as exc:
                            logger.warning(
                                "Cluster membership persistence failed for run %s cluster %s record %s: %s",
                                pipeline_run_id,
                                cluster_row.get("id"),
                                normalized_record_id,
                                exc,
                            )
            self.db.upsert_cluster_summary(cluster)
            cluster_count += 1

        if pipeline_run_id:
            for left in range(len(records)):
                left_id = records[left].get("_normalized_record_id")
                if not left_id:
                    continue
                for right in range(left + 1, len(records)):
                    score = similarity_matrix[left][right]
                    if score < self.similarity_threshold:
                        continue
                    right_id = records[right].get("_normalized_record_id")
                    if not right_id:
                        continue
                    try:
                        self.db.insert_similarity_edge({
                            "pipeline_run_id": pipeline_run_id,
                            "left_normalized_record_id": left_id,
                            "left_source_type": records[left]["source_type"],
                            "right_normalized_record_id": right_id,
                            "right_source_type": records[right]["source_type"],
                            "similarity_score": score,
                            "match_reason": "tfidf_threshold",
                        })
                        similarity_count += 1
                    except Exception as exc:
                        logger.warning(
                            "Similarity edge persistence failed for run %s between %s and %s: %s",
                            pipeline_run_id,
                            left_id,
                            right_id,
                            exc,
                        )

        return {
            "records": record_count,
            "clusters": cluster_count,
            "normalized": normalized_count,
            "similarity_edges": similarity_count,
        }

    def build_normalized_text(
        self,
        cleaned_title: str,
        brand: Optional[str],
        model: Optional[str],
        category: str,
    ) -> str:
        tokens = [cleaned_title]
        if brand:
            tokens.append(brand)
        if model:
            tokens.append(model)
        if category:
            tokens.append(category.lower())
        return " ".join(token for token in tokens if token).strip()

    def normalize_price(self, price: Optional[float], currency: str) -> float:
        if price in (None, "", 0):
            return 0.0
        currency = (currency or "PKR").upper()
        numeric = float(price)
        if currency in {"PKR", "RS", "RUP", "RUPEES"}:
            return numeric
        if currency in {"USD", "$"}:
            return numeric * self.USD_TO_PKR
        if currency in {"CNY", "RMB", "¥"}:
            return numeric * self.CNY_TO_PKR
        if currency in {"AED"}:
            return numeric * self.AED_TO_PKR
        return numeric

    def extract_storage_variant(self, cleaned_title: str) -> Optional[str]:
        match = self.STORAGE_PATTERN.search(cleaned_title or "")
        if not match:
            return None
        return f"{match.group(1)}gb"

    def is_accessory(self, cleaned_title: str) -> bool:
        tokens = set(cleaned_title.split())
        return bool(tokens & self.ACCESSORY_KEYWORDS)

    def extract_brand_model(self, cleaned_title: str, query_product: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        tokens = cleaned_title.split()
        if not tokens:
            return None, None
        query_tokens = self.clean_text(query_product or "").split()
        brand = query_tokens[0] if query_tokens and query_tokens[0] in tokens else tokens[0]

        if len(query_tokens) >= 3 and query_tokens[1] in tokens and query_tokens[2] in tokens and query_tokens[2] in self.ROMAN_NUMERAL_TOKENS:
            return brand, f"{query_tokens[1]} {query_tokens[2]}"
        if len(query_tokens) >= 2 and query_tokens[1] in tokens:
            return brand, query_tokens[1]

        for token in tokens[1:]:
            if re.match(r"^[a-z0-9]{2,12}$", token) and any(char.isdigit() for char in token):
                return brand, token

        for index in range(2, len(tokens)):
            token = tokens[index]
            previous = tokens[index - 1]
            if token in self.ROMAN_NUMERAL_TOKENS and previous not in self.MODEL_STOPWORDS:
                return brand, f"{previous} {token}"

        for token in tokens[1:4]:
            if token not in self.MODEL_STOPWORDS and len(token) >= 2:
                return brand, token

        return brand, None

    def _extract_rating(self, detail: Dict[str, Any]) -> Optional[float]:
        rating_value = detail.get("seller_positive_rating") or detail.get("product_rating")
        if not rating_value:
            return None
        match = re.search(r"(\d+(\.\d+)?)", str(rating_value))
        return float(match.group(1)) if match else None

    def _records_should_cluster(self, left: Dict[str, Any], right: Dict[str, Any], similarity: float) -> bool:
        left_storage = left.get("storage_variant")
        right_storage = right.get("storage_variant")
        if left_storage and right_storage and left_storage != right_storage:
            return False
        if similarity >= self.similarity_threshold:
            return True
        if left.get("brand") and left.get("brand") == right.get("brand") and left.get("model") and left.get("model") == right.get("model"):
            return True
        return False

    def _build_cluster_id(
        self,
        product_name: str,
        category: str,
        records: List[Dict[str, Any]],
        component: List[int],
    ) -> str:
        seed_title = records[component[0]].get("cleaned_title", "product").replace(" ", "-")
        storage = records[component[0]].get("storage_variant")
        if storage:
            return f"{category.lower()}::{product_name.lower().replace(' ', '-')}::{storage}::{seed_title}"
        return f"{category.lower()}::{product_name.lower().replace(' ', '-')}::{seed_title}"

    def _pick_first(self, records: Iterable[Dict[str, Any]], field: str) -> Optional[Any]:
        for record in records:
            value = record.get(field)
            if value:
                return value
        return None

    def get_stats(self) -> Dict[str, Any]:
        return self.db.get_stats()
