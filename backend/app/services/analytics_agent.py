"""
Hybrid analytics agent for clustered e-commerce pricing intelligence.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

try:
    from xgboost import XGBRegressor
except Exception:  # pragma: no cover
    XGBRegressor = None

from app.services.ecdb import ECDB
from app.services.commercial_intelligence import (
    build_evidence_ledger,
    build_market_intelligence_snapshot,
    build_pricing_mode_snapshot,
    classify_quality_band,
    compute_profitability_snapshot,
)


MODEL_DIR = Path(__file__).resolve().parents[1] / "models"
MODEL_PATH = MODEL_DIR / "analytics_pricing_model.joblib"
MIN_CONFIDENT_SCORE = 0.62
LOW_SAMPLE_WHOLESALE_VENDOR_THRESHOLD = int(os.getenv("ANALYTICS_LOW_SAMPLE_WHOLESALE_THRESHOLD", "3"))
LOW_SAMPLE_RETAIL_LISTING_THRESHOLD = int(os.getenv("ANALYTICS_LOW_SAMPLE_RETAIL_THRESHOLD", "5"))


@dataclass
class ClusterRecommendation:
    cluster_key: str
    cluster_db_id: Optional[str]
    analytics_result_id: Optional[str]
    status: str
    metrics: Dict[str, Any]
    pricing: Dict[str, Any]
    confidence_score: float
    confidence_reason: str
    insight_summary: str


@dataclass(frozen=True)
class PricingSanityConfig:
    retail_lower_bound_multiplier: float = 0.8
    retail_upper_bound_multiplier: float = 1.2
    sparse_retail_threshold: int = 2
    sparse_wholesale_threshold: int = 2
    buy_to_retail_cap_ratio: float = 0.92


@dataclass(frozen=True)
class CategoryMarginPolicy:
    min_margin_percent: float
    max_margin_percent: float
    sparse_data_max_margin_percent: float
    retail_anchor_multiplier_low: float = 0.8
    retail_anchor_multiplier_high: float = 1.2


DEFAULT_CATEGORY_POLICIES: Dict[str, CategoryMarginPolicy] = {
    "mobile_phones": CategoryMarginPolicy(8.0, 25.0, 18.0),
    "laptops": CategoryMarginPolicy(8.0, 20.0, 15.0),
    "headsets": CategoryMarginPolicy(10.0, 35.0, 22.0),
    "computer_accessories": CategoryMarginPolicy(12.0, 40.0, 25.0),
    "mobile_accessories": CategoryMarginPolicy(15.0, 60.0, 35.0),
    "generic_gadgets": CategoryMarginPolicy(12.0, 50.0, 30.0),
    "cameras": CategoryMarginPolicy(10.0, 35.0, 22.0),
    "home_goods": CategoryMarginPolicy(12.0, 40.0, 25.0),
    "fashion": CategoryMarginPolicy(20.0, 70.0, 40.0),
    "beauty": CategoryMarginPolicy(20.0, 70.0, 40.0),
    "general_retail": CategoryMarginPolicy(10.0, 40.0, 25.0),
    "unknown": CategoryMarginPolicy(10.0, 30.0, 20.0),
}


class HybridPricingModel:
    FEATURE_NAMES = [
        "wholesale_count",
        "retail_count",
        "wholesale_min",
        "wholesale_avg",
        "wholesale_cv",
        "retail_min",
        "retail_avg",
        "retail_max",
        "retail_cv",
        "platform_count",
        "vendor_count",
        "price_spread",
        "has_both_sources",
    ]

    def __init__(self, model_path: Path = MODEL_PATH, registry_db: Optional[ECDB] = None, model_name: str = "analytics_pricing_model"):
        self.default_model_path = model_path
        self.registry_db = registry_db
        self.model_name = model_name
        self.model_path = self._resolve_initial_model_path()
        self.scaler = StandardScaler()
        self.buy_rf = RandomForestRegressor(
            n_estimators=120,
            max_depth=8,
            random_state=42,
            n_jobs=1,
        )
        self.sell_rf = RandomForestRegressor(
            n_estimators=120,
            max_depth=8,
            random_state=43,
            n_jobs=1,
        )
        self.buy_xgb = (
            XGBRegressor(
                n_estimators=140,
                max_depth=5,
                learning_rate=0.08,
                subsample=0.9,
                colsample_bytree=0.9,
                random_state=42,
                verbosity=0,
            )
            if XGBRegressor
            else None
        )
        self.sell_xgb = (
            XGBRegressor(
                n_estimators=140,
                max_depth=5,
                learning_rate=0.08,
                subsample=0.9,
                colsample_bytree=0.9,
                random_state=43,
                verbosity=0,
            )
            if XGBRegressor
            else None
        )
        self.is_fitted = False
        self.training_metadata: Dict[str, Any] = {"source": "cold_start", "sample_count": 0}
        self.load()
        if not self.is_fitted:
            self.fit_cold_start()

    def _resolve_initial_model_path(self) -> Path:
        if self.registry_db:
            try:
                active_version = self.registry_db.get_active_analytics_model_version()
                if active_version:
                    artifact_path = active_version.get("artifact_path")
                    if artifact_path:
                        candidate = Path(str(artifact_path))
                        if candidate.is_file():
                            return candidate
                latest_version = self.registry_db.get_latest_analytics_model_version()
                if latest_version:
                    artifact_path = latest_version.get("artifact_path")
                    if artifact_path:
                        candidate = Path(str(artifact_path))
                        if candidate.is_file():
                            return candidate
            except Exception:
                pass
        return self.default_model_path

    def build_version_tag(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")

    def build_versioned_artifact_path(self, version_tag: Optional[str] = None) -> Path:
        version_tag = version_tag or self.build_version_tag()
        return self.default_model_path.with_name(f"{self.default_model_path.stem}-{version_tag}{self.default_model_path.suffix}")

    def load(self) -> None:
        candidates = [self.model_path]
        if self.default_model_path not in candidates:
            candidates.append(self.default_model_path)
        for candidate in candidates:
            if not candidate.exists():
                continue
            bundle = joblib.load(candidate)
            self.model_path = candidate
            self.scaler = bundle["scaler"]
            self.buy_rf = bundle["buy_rf"]
            self.sell_rf = bundle["sell_rf"]
            self.buy_xgb = bundle.get("buy_xgb")
            self.sell_xgb = bundle.get("sell_xgb")
            self.training_metadata = bundle.get("training_metadata", self.training_metadata)
            self.is_fitted = True
            return

    def save(self, artifact_path: Optional[Path] = None) -> Path:
        target_path = Path(artifact_path or self.default_model_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "scaler": self.scaler,
                "buy_rf": self.buy_rf,
                "sell_rf": self.sell_rf,
                "buy_xgb": self.buy_xgb,
                "sell_xgb": self.sell_xgb,
                "training_metadata": self.training_metadata,
            },
            target_path,
        )
        return target_path

    def fit_cold_start(self) -> None:
        rng = np.random.default_rng(42)
        features: List[List[float]] = []
        buy_targets: List[float] = []
        sell_targets: List[float] = []
        for _ in range(900):
            wholesale_count = int(rng.integers(1, 18))
            retail_count = int(rng.integers(0, 20))
            wholesale_min = float(rng.uniform(80, 20000))
            wholesale_avg = wholesale_min * float(rng.uniform(1.02, 1.4))
            wholesale_cv = float(rng.uniform(0.01, 0.45))
            retail_anchor = wholesale_avg * float(rng.uniform(1.12, 3.8))
            retail_min = retail_anchor * float(rng.uniform(0.82, 0.97))
            retail_avg = retail_anchor
            retail_max = retail_anchor * float(rng.uniform(1.02, 1.35))
            retail_cv = float(rng.uniform(0.02, 0.55))
            platform_count = int(rng.integers(1, 4))
            vendor_count = int(rng.integers(1, 24))
            price_spread = max(retail_avg - wholesale_avg, 0.0)
            has_both_sources = 1.0 if retail_count > 0 and wholesale_count > 0 else 0.0

            feature_row = [
                wholesale_count,
                retail_count,
                wholesale_min,
                wholesale_avg,
                wholesale_cv,
                retail_min,
                retail_avg,
                retail_max,
                retail_cv,
                platform_count,
                vendor_count,
                price_spread,
                has_both_sources,
            ]
            buy_target = wholesale_min * float(rng.uniform(0.985, 1.02))
            sell_floor = max(buy_target * 1.08, retail_min * 0.9)
            sell_ceiling = max(sell_floor, retail_avg * float(rng.uniform(0.95, 1.02)))
            sell_target = float(rng.uniform(sell_floor, sell_ceiling))
            features.append(feature_row)
            buy_targets.append(buy_target)
            sell_targets.append(sell_target)

        self.fit(features, buy_targets, sell_targets, {"source": "cold_start", "sample_count": len(features)})

    def fit(
        self,
        features: Sequence[Sequence[float]],
        buy_targets: Sequence[float],
        sell_targets: Sequence[float],
        training_metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        X = np.asarray(features, dtype=float)
        y_buy = np.asarray(buy_targets, dtype=float)
        y_sell = np.asarray(sell_targets, dtype=float)
        X_scaled = self.scaler.fit_transform(X)
        self.buy_rf.fit(X_scaled, y_buy)
        self.sell_rf.fit(X_scaled, y_sell)
        if self.buy_xgb:
            self.buy_xgb.fit(X_scaled, y_buy)
        if self.sell_xgb:
            self.sell_xgb.fit(X_scaled, y_sell)
        self.is_fitted = True
        self.training_metadata = training_metadata or {"source": "historical", "sample_count": len(features)}
        self.save(self.default_model_path)

    def predict(self, feature_row: Sequence[float]) -> Tuple[float, float]:
        if not self.is_fitted:
            self.fit_cold_start()
        X = self.scaler.transform([list(feature_row)])
        buy_preds = [float(self.buy_rf.predict(X)[0])]
        sell_preds = [float(self.sell_rf.predict(X)[0])]
        if self.buy_xgb:
            buy_preds.append(float(self.buy_xgb.predict(X)[0]))
        if self.sell_xgb:
            sell_preds.append(float(self.sell_xgb.predict(X)[0]))
        return float(np.mean(buy_preds)), float(np.mean(sell_preds))


class AnalyticsAgent:
    def __init__(self, ecdb_path: Optional[str] = None):
        self.db = ECDB(ecdb_path)
        model_path = Path(os.getenv("ANALYTICS_MODEL_PATH", str(MODEL_PATH)))
        self.model = HybridPricingModel(model_path=model_path, registry_db=self.db)
        self.pricing_config = PricingSanityConfig()
        self.category_policies = DEFAULT_CATEGORY_POLICIES

    def analyze(
        self,
        product_name: str,
        category: str,
        nlp_output: Dict[str, Any],
        pipeline_run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        clusters = self._extract_clusters(nlp_output)
        if not clusters:
            empty = self._build_empty_result(product_name, category)
            self._persist_low_confidence_recommendation(empty, pipeline_run_id)
            return empty

        cluster_results: List[ClusterRecommendation] = []
        for cluster in clusters:
            cluster_results.append(
                self._analyze_cluster(
                    cluster=cluster,
                    product_name=product_name,
                    category=category,
                    pipeline_run_id=pipeline_run_id,
                )
            )

        primary = self._select_primary_cluster(cluster_results)
        recommendation = self._build_recommendation_response(product_name, category, primary, cluster_results)
        if pipeline_run_id and primary.analytics_result_id:
            self.db.insert_recommendation(
                {
                    "pipeline_run_id": pipeline_run_id,
                    "analytics_result_id": primary.analytics_result_id,
                    "recommendation_type": "pricing",
                    "recommendation_status": recommendation["recommendation_status"],
                    "recommended_buy_price_pkr": recommendation["recommended_buy_price_pkr"],
                    "recommended_sell_price_pkr": recommendation["recommended_sell_price_pkr"],
                    "sourcing_recommendation": recommendation["sourcing_recommendation"],
                    "marketing_recommendation": recommendation["marketing_recommendation"],
                    "strategy_summary": recommendation["strategy_summary"],
                    "reasoning_trace": recommendation["analysis_details"],
                    "confidence_score": recommendation["confidence_score"],
                    "approval_status": "pending",
                }
            )
        return self._convert_types(recommendation)

    def retrain_from_history(self, limit: int = 300) -> Dict[str, Any]:
        rows = self.db._rest_get(  # type: ignore[attr-defined]
            "analytics_results",
            {"select": "*", "order": "created_at.desc", "limit": str(limit)},
        )
        features: List[List[float]] = []
        buy_targets: List[float] = []
        sell_targets: List[float] = []
        for row in rows:
            feature_row = self._feature_row_from_analytics_row(row)
            buy_target = self._as_float(row.get("estimated_optimal_buy_price"))
            sell_target = self._as_float(row.get("estimated_optimal_sell_price"))
            if not feature_row or buy_target <= 0 or sell_target <= 0:
                continue
            features.append(feature_row)
            buy_targets.append(buy_target)
            sell_targets.append(sell_target)
        if len(features) < 20:
            return {
                "status": "skipped",
                "reason": "insufficient_historical_rows",
                "sample_count": len(features),
            }
        training_metadata = {"source": "historical_analytics_results", "sample_count": len(features)}
        self.model.fit(
            features,
            buy_targets,
            sell_targets,
            training_metadata=training_metadata,
        )
        version_tag = self.model.build_version_tag()
        archive_path = self.model.build_versioned_artifact_path(version_tag)
        self.model.save(archive_path)
        version_row = self.db.insert_analytics_model_version(
            {
                "model_name": self.model.model_name,
                "version_tag": version_tag,
                "artifact_path": str(archive_path),
                "source": training_metadata["source"],
                "sample_count": len(features),
                "training_metadata": training_metadata,
                "metrics": {
                    "sample_count": len(features),
                    "feature_dimensions": len(features[0]) if features else 0,
                },
                "is_active": True,
            }
        )
        return {
            "status": "trained",
            "sample_count": len(features),
            "model_path": str(self.model.default_model_path),
            "archived_model_path": str(archive_path),
            "model_version_id": version_row.get("id"),
            "model_version_tag": version_tag,
            "is_active": version_row.get("is_active", True),
        }

    def _analyze_cluster(
        self,
        cluster: Dict[str, Any],
        product_name: str,
        category: str,
        pipeline_run_id: Optional[str],
    ) -> ClusterRecommendation:
        wholesale_records = cluster.get("wholesale_records") or [
            record for record in (cluster.get("records") or []) if record.get("source_type") == "wholesale"
        ]
        retail_records = cluster.get("retail_records") or [
            record for record in (cluster.get("records") or []) if record.get("source_type") == "retail"
        ]
        wholesale_metrics = self._compute_market_metrics(wholesale_records, role="wholesale")
        retail_metrics = self._compute_market_metrics(retail_records, role="retail")
        detected_category, category_policy, category_fallback_used, category_metadata = self._detect_pricing_category(
            cluster,
            product_name,
            category,
            wholesale_records,
            retail_records,
        )
        combined_metrics = self._compute_combined_metrics(cluster, wholesale_records, retail_records, wholesale_metrics, retail_metrics)
        combined_metrics["detected_category"] = detected_category
        confidence_score, confidence_reason = self._compute_confidence(wholesale_metrics, retail_metrics, combined_metrics)
        pricing = self._compute_pricing(wholesale_metrics, retail_metrics, combined_metrics, confidence_score, category_policy)
        final_confidence = pricing.get("confidence_after_adjustment", confidence_score)
        if final_confidence != confidence_score:
            confidence_reason = self._augment_confidence_reason(confidence_reason, pricing.get("sanity_adjustments", {}))
        low_sample_warning = self._is_low_sample(wholesale_metrics, retail_metrics)
        commercial_intelligence = self._build_commercial_intelligence(
            product_name=product_name,
            category=category,
            wholesale_metrics=wholesale_metrics,
            retail_metrics=retail_metrics,
            combined_metrics=combined_metrics,
            pricing=pricing,
            confidence_score=final_confidence,
            low_sample_warning=low_sample_warning,
        )
        status = self._cluster_status(pricing, final_confidence, wholesale_metrics, retail_metrics)
        insight_summary = self._generate_reasoning_summary(
            wholesale_metrics,
            retail_metrics,
            combined_metrics,
            pricing,
            final_confidence,
            status,
            commercial_intelligence,
        )

        analytics_result_id = None
        cluster_db_id = cluster.get("db_cluster_id")
        if pipeline_run_id and cluster_db_id:
            inserted = self.db.insert_analytics_result(
                {
                    "pipeline_run_id": pipeline_run_id,
                    "product_cluster_id": cluster_db_id,
                    "analysis_status": status,
                    "min_retail_price": retail_metrics["min_price"],
                    "max_retail_price": retail_metrics["max_price"],
                    "avg_retail_price": retail_metrics["avg_price"],
                    "avg_wholesale_price": wholesale_metrics["avg_price"],
                    "best_wholesale_price": wholesale_metrics["best_price"],
                    "price_spread": combined_metrics["price_spread"],
                    "wholesale_candidates": wholesale_records[:10],
                    "retail_candidates": retail_records[:10],
                    "vendor_count": combined_metrics["vendor_count"],
                    "platform_count": combined_metrics["platform_count"],
                    "estimated_optimal_buy_price": pricing["recommended_buy"],
                    "estimated_optimal_sell_price": pricing["recommended_sell"],
                    "expected_margin_percent": pricing["expected_margin_percent"],
                    "confidence_score": final_confidence,
                    "analysis_metadata": {
                        "product_name": product_name,
                        "category": category,
                        "cluster_key": cluster.get("cluster_id"),
                        "cluster_title": cluster.get("canonical_title"),
                        "status": status,
                        "wholesale_metrics": wholesale_metrics,
                        "retail_metrics": retail_metrics,
                        "combined_metrics": combined_metrics,
                        "detected_category": detected_category,
                        "category_policy_used": category_metadata["category_policy_used"],
                        "min_margin_percent_used": category_policy.min_margin_percent,
                        "max_margin_percent_used": category_policy.max_margin_percent,
                        "sparse_data_max_margin_percent_used": category_policy.sparse_data_max_margin_percent,
                        "category_fallback_used": category_fallback_used,
                        "category_detection_metadata": category_metadata,
                        "pricing_policy": pricing["policy"],
                        "pricing_sanity": pricing.get("sanity_adjustments"),
                        "model_predicted_buy": pricing.get("model_predicted_buy"),
                        "model_predicted_sell": pricing.get("model_predicted_sell"),
                        "margin_before_adjustment": pricing.get("margin_before_adjustment"),
                        "margin_after_adjustment": pricing.get("margin_after_adjustment"),
                        "confidence_before_adjustment": pricing.get("confidence_before_adjustment"),
                        "confidence_after_adjustment": pricing.get("confidence_after_adjustment"),
                        "commercial_intelligence": commercial_intelligence,
                        "insight_summary": insight_summary,
                        "model_training_metadata": self.model.training_metadata,
                    },
                }
            )
            analytics_result_id = inserted.get("id")

        return ClusterRecommendation(
            cluster_key=str(cluster.get("cluster_id") or cluster_db_id or "unknown_cluster"),
            cluster_db_id=cluster_db_id,
            analytics_result_id=analytics_result_id,
            status=status,
            metrics={
                "wholesale": wholesale_metrics,
                "retail": retail_metrics,
                "combined": combined_metrics,
                "commercial_intelligence": commercial_intelligence,
            },
            pricing=pricing,
            confidence_score=final_confidence,
            confidence_reason=confidence_reason,
            insight_summary=insight_summary,
        )

    def _extract_clusters(self, nlp_output: Dict[str, Any]) -> List[Dict[str, Any]]:
        clusters = nlp_output.get("clusters") or nlp_output.get("clustered_products") or []
        return [cluster for cluster in clusters if (cluster.get("records") or cluster.get("wholesale_records") or cluster.get("retail_records"))]

    def _normalize_policy_text(self, value: str) -> str:
        return "".join(char.lower() if char.isalnum() else " " for char in (value or "")).strip()

    def _policy_keyword_matches(self, normalized_text: str, keyword: str) -> bool:
        text_tokens = set(normalized_text.split())
        keyword_tokens = keyword.split()
        if not keyword_tokens:
            return False
        if len(keyword_tokens) == 1:
            return keyword_tokens[0] in text_tokens
        return keyword in normalized_text

    def _detect_pricing_category(
        self,
        cluster: Dict[str, Any],
        product_name: str,
        category: str,
        wholesale_records: List[Dict[str, Any]],
        retail_records: List[Dict[str, Any]],
    ) -> Tuple[str, CategoryMarginPolicy, bool, Dict[str, Any]]:
        texts = [
            product_name,
            category,
            cluster.get("canonical_title") or "",
            cluster.get("title") or "",
        ]
        for record in wholesale_records + retail_records:
            texts.extend(
                [
                    record.get("cleaned_title") or "",
                    record.get("raw_title") or "",
                    record.get("brand") or "",
                    record.get("model") or "",
                ]
            )
        normalized_text = " ".join(self._normalize_policy_text(text) for text in texts if text)
        keyword_sets = [
            ("mobile_accessories", {"charger", "cable", "adapter", "case", "cover", "lightning", "usb c", "power bank"}),
            ("headsets", {"hyperx", "headset", "earbuds", "headphones", "earphones", "airpods", "cloud iii"}),
            ("mobile_phones", {"iphone", "samsung galaxy", "redmi", "smartphone", "phone", "infinix", "tecno", "xiaomi"}),
            ("laptops", {"laptop", "macbook", "notebook", "thinkpad", "chromebook"}),
            ("computer_accessories", {"mouse", "keyboard", "webcam", "monitor", "ssd enclosure", "router", "speaker"}),
            ("cameras", {"camera", "webcam", "cctv", "surveillance", "camcorder", "mini camera"}),
            ("fashion", {"shirt", "dress", "shoes", "sneakers", "bag", "wallet"}),
            ("beauty", {"makeup", "serum", "cream", "lipstick", "beauty", "skincare"}),
            ("home_goods", {"kitchen", "home", "furniture", "organizer", "bed", "pillow"}),
            ("generic_gadgets", {"tracker", "smart gadget", "mini camera", "device", "smart", "portable"}),
        ]

        matched_category = None
        matched_keywords: List[str] = []
        for policy_name, keywords in keyword_sets:
            current_matches = [keyword for keyword in keywords if self._policy_keyword_matches(normalized_text, keyword)]
            if current_matches:
                matched_category = policy_name
                matched_keywords = sorted(current_matches)
                break

        fallback_used = False
        if not matched_category:
            normalized_category = self._normalize_policy_text(category)
            category_aliases = {
                "mobile": "mobile_phones",
                "phone": "mobile_phones",
                "headphone": "headsets",
                "headset": "headsets",
                "audio": "headsets",
                "camera": "cameras",
                "laptop": "laptops",
                "fashion": "fashion",
                "beauty": "beauty",
                "home": "home_goods",
                "accessories": "computer_accessories",
            }
            matched_category = category_aliases.get(normalized_category, "unknown")
            fallback_used = True

        policy = self.category_policies.get(matched_category, self.category_policies["unknown"])
        if matched_category not in self.category_policies:
            matched_category = "unknown"
            policy = self.category_policies["unknown"]
            fallback_used = True

        metadata = {
            "detected_category": matched_category,
            "category_policy_used": matched_category,
            "category_fallback_used": fallback_used,
            "matched_keywords": matched_keywords,
            "source_category": category,
        }
        return matched_category, policy, fallback_used, metadata

    def _compute_market_metrics(self, records: List[Dict[str, Any]], role: str) -> Dict[str, Any]:
        prices = [self._as_float(record.get("price_pkr")) for record in records if self._as_float(record.get("price_pkr")) > 0]
        if not prices:
            return {
                "role": role,
                "record_count": len(records),
                "usable_price_count": 0,
                "min_price": 0.0,
                "max_price": 0.0,
                "avg_price": 0.0,
                "median_price": 0.0,
                "best_price": 0.0,
                "price_variance": 0.0,
                "price_stddev": 0.0,
                "price_cv": 0.0,
                "outlier_count": 0,
                "platform_count": len({record.get("platform") for record in records if record.get("platform")}),
                "vendor_count": len({record.get("supplier_or_seller") for record in records if record.get("supplier_or_seller")}),
            }

        filtered = self._remove_price_outliers(prices)
        filtered_prices = filtered if filtered else prices
        avg_price = float(np.mean(filtered_prices))
        std_price = float(np.std(filtered_prices))
        return {
            "role": role,
            "record_count": len(records),
            "usable_price_count": len(filtered_prices),
            "min_price": float(np.min(filtered_prices)),
            "max_price": float(np.max(filtered_prices)),
            "avg_price": avg_price,
            "median_price": float(np.median(filtered_prices)),
            "best_price": float(np.min(filtered_prices)),
            "price_list": [float(price) for price in sorted(filtered_prices)],
            "price_variance": float(np.var(filtered_prices)),
            "price_stddev": std_price,
            "price_cv": float(std_price / avg_price) if avg_price > 0 else 0.0,
            "outlier_count": max(len(prices) - len(filtered_prices), 0),
            "platform_count": len({record.get("platform") for record in records if record.get("platform")}),
            "vendor_count": len({record.get("supplier_or_seller") for record in records if record.get("supplier_or_seller")}),
        }

    def _compute_combined_metrics(
        self,
        cluster: Dict[str, Any],
        wholesale_records: List[Dict[str, Any]],
        retail_records: List[Dict[str, Any]],
        wholesale_metrics: Dict[str, Any],
        retail_metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        platforms = {
            record.get("platform")
            for record in (wholesale_records + retail_records)
            if record.get("platform")
        }
        vendors = {
            record.get("supplier_or_seller")
            for record in (wholesale_records + retail_records)
            if record.get("supplier_or_seller")
        }
        retail_avg = retail_metrics.get("avg_price", 0.0)
        wholesale_avg = wholesale_metrics.get("avg_price", 0.0)
        moq_values = [self._as_float(record.get("moq")) for record in wholesale_records if self._as_float(record.get("moq")) > 0]
        return {
            "cluster_title": cluster.get("canonical_title") or cluster.get("title"),
            "cluster_record_count": len(wholesale_records) + len(retail_records),
            "has_wholesale": wholesale_metrics.get("usable_price_count", 0) > 0,
            "has_retail": retail_metrics.get("usable_price_count", 0) > 0,
            "has_both_sources": wholesale_metrics.get("usable_price_count", 0) > 0 and retail_metrics.get("usable_price_count", 0) > 0,
            "is_sparse_data": (
                wholesale_metrics.get("usable_price_count", 0) < self.pricing_config.sparse_wholesale_threshold
                or retail_metrics.get("usable_price_count", 0) < self.pricing_config.sparse_retail_threshold
            ),
            "platform_count": len(platforms),
            "vendor_count": len(vendors),
            "moq_min": min(moq_values) if moq_values else 0.0,
            "moq_max": max(moq_values) if moq_values else 0.0,
            "price_spread": max(retail_avg - wholesale_avg, 0.0) if retail_avg and wholesale_avg else 0.0,
            "spread_ratio": float((retail_avg / wholesale_avg) if wholesale_avg and retail_avg else 0.0),
            "wholesale_platform_count": wholesale_metrics.get("platform_count", 0),
            "retail_platform_count": retail_metrics.get("platform_count", 0),
        }

    def _compute_pricing(
        self,
        wholesale_metrics: Dict[str, Any],
        retail_metrics: Dict[str, Any],
        combined_metrics: Dict[str, Any],
        confidence_score: float,
        category_policy: CategoryMarginPolicy,
    ) -> Dict[str, Any]:
        if wholesale_metrics["usable_price_count"] == 0:
            return {
                "recommended_buy": 0.0,
                "recommended_sell": 0.0,
                "expected_margin_percent": 0.0,
                "policy": "insufficient_data",
                "model_predicted_buy": 0.0,
                "model_predicted_sell": 0.0,
                "margin_before_adjustment": 0.0,
                "margin_after_adjustment": 0.0,
                "confidence_before_adjustment": confidence_score,
                "confidence_after_adjustment": confidence_score,
                "sanity_adjustments": {
                    "retail_anchor_applied": False,
                    "buy_adjustment_applied": False,
                    "margin_adjustment_applied": False,
                    "low_data_adjustment_applied": False,
                    "retail_bounds_used": None,
                    "clamp_reason": "missing_wholesale_prices",
                    "original_model_sell_prediction": 0.0,
                    "clamped_sell_prediction": 0.0,
                    "category_policy_used": combined_metrics.get("detected_category", "unknown"),
                    "category_margin_cap_applied": False,
                },
            }

        feature_row = [
            wholesale_metrics["usable_price_count"],
            retail_metrics["usable_price_count"],
            wholesale_metrics["min_price"],
            wholesale_metrics["avg_price"],
            wholesale_metrics["price_cv"],
            retail_metrics["min_price"],
            retail_metrics["avg_price"],
            retail_metrics["max_price"],
            retail_metrics["price_cv"],
            combined_metrics["platform_count"],
            combined_metrics["vendor_count"],
            combined_metrics["price_spread"],
            1.0 if combined_metrics["has_both_sources"] else 0.0,
        ]
        ml_buy, ml_sell = self.model.predict(feature_row)
        heuristic_buy = wholesale_metrics["best_price"]
        heuristic_sell = self._heuristic_sell_price(wholesale_metrics, retail_metrics, combined_metrics)

        buy_lower = heuristic_buy * 0.98
        buy_upper = max(heuristic_buy * 1.05, wholesale_metrics["avg_price"] * 1.02)
        preliminary_buy = self._clamp(0.55 * heuristic_buy + 0.45 * ml_buy, buy_lower, buy_upper)
        preliminary_sell = (0.6 * heuristic_sell) + (0.4 * ml_sell)
        sanity = self._apply_pricing_sanity_layer(
            predicted_buy=preliminary_buy,
            predicted_sell=preliminary_sell,
            heuristic_buy=heuristic_buy,
            heuristic_sell=heuristic_sell,
            wholesale_metrics=wholesale_metrics,
            retail_metrics=retail_metrics,
            combined_metrics=combined_metrics,
            confidence_score=confidence_score,
            category_policy=category_policy,
        )
        recommended_buy = sanity["recommended_buy"]
        recommended_sell = sanity["recommended_sell"]
        expected_margin = sanity["margin_after_adjustment"]
        return {
            "recommended_buy": round(recommended_buy, 2),
            "recommended_sell": round(recommended_sell, 2),
            "expected_margin_percent": round(expected_margin, 2),
            "policy": sanity["policy"],
            "model_predicted_buy": round(preliminary_buy, 2),
            "model_predicted_sell": round(preliminary_sell, 2),
            "margin_before_adjustment": round(sanity["margin_before_adjustment"], 2),
            "margin_after_adjustment": round(sanity["margin_after_adjustment"], 2),
            "confidence_before_adjustment": confidence_score,
            "confidence_after_adjustment": sanity["confidence_after_adjustment"],
            "sanity_adjustments": sanity["sanity_adjustments"],
        }

    def _heuristic_sell_price(
        self,
        wholesale_metrics: Dict[str, Any],
        retail_metrics: Dict[str, Any],
        combined_metrics: Dict[str, Any],
    ) -> float:
        buy_anchor = wholesale_metrics["best_price"]
        if retail_metrics["usable_price_count"] == 0:
            return buy_anchor * 1.2
        retail_avg = retail_metrics["avg_price"]
        retail_min = retail_metrics["min_price"]
        competitive_anchor = min(retail_avg * 0.96, retail_min * 0.99 if retail_min else retail_avg)
        base_margin = 1.18 if combined_metrics["has_both_sources"] else 1.12
        cost_anchor = buy_anchor * base_margin
        return max(cost_anchor, competitive_anchor)

    def _apply_pricing_sanity_layer(
        self,
        predicted_buy: float,
        predicted_sell: float,
        heuristic_buy: float,
        heuristic_sell: float,
        wholesale_metrics: Dict[str, Any],
        retail_metrics: Dict[str, Any],
        combined_metrics: Dict[str, Any],
        confidence_score: float,
        category_policy: CategoryMarginPolicy,
    ) -> Dict[str, Any]:
        config = self.pricing_config
        clamp_reasons: List[str] = []
        retail_bounds_used = None
        adjusted_buy = max(predicted_buy, 0.0)
        adjusted_sell = max(predicted_sell, adjusted_buy * 1.01)
        buy_adjustment_applied = False
        retail_anchor_applied = False
        margin_adjustment_applied = False
        low_data_adjustment_applied = False
        confidence_after_adjustment = confidence_score

        if retail_metrics["usable_price_count"] > 0:
            retail_lower_bound = retail_metrics["min_price"] * category_policy.retail_anchor_multiplier_low
            retail_upper_bound = retail_metrics["max_price"] * category_policy.retail_anchor_multiplier_high
            retail_bounds_used = {
                "lower_bound": round(retail_lower_bound, 2),
                "upper_bound": round(retail_upper_bound, 2),
                "retail_min": retail_metrics["min_price"],
                "retail_max": retail_metrics["max_price"],
                "retail_avg": retail_metrics["avg_price"],
                "retail_median": retail_metrics["median_price"],
            }
            clamped_sell = self._clamp(adjusted_sell, retail_lower_bound, retail_upper_bound)
            if abs(clamped_sell - adjusted_sell) > 0.01:
                retail_anchor_applied = True
                clamp_reasons.append("retail_anchor_clamp")
                adjusted_sell = clamped_sell

            max_safe_buy = retail_metrics["min_price"] * config.buy_to_retail_cap_ratio
            if adjusted_buy > max_safe_buy:
                adjusted_buy = min(max_safe_buy, adjusted_sell * 0.92)
                buy_adjustment_applied = True
                clamp_reasons.append("buy_capped_against_retail_floor")
        else:
            adjusted_sell = max(adjusted_sell, heuristic_sell)

        sparse_limit = (
            wholesale_metrics["usable_price_count"] < config.sparse_wholesale_threshold
            or retail_metrics["usable_price_count"] < config.sparse_retail_threshold
        )
        if sparse_limit:
            low_data_adjustment_applied = True
            confidence_after_adjustment = round(confidence_after_adjustment * 0.8, 4)
            conservative_sell = adjusted_buy * (1.0 + (category_policy.sparse_data_max_margin_percent / 100.0))
            if retail_bounds_used:
                conservative_sell = min(conservative_sell, retail_metrics["median_price"] or retail_metrics["avg_price"] or conservative_sell)
            adjusted_sell = max(adjusted_buy * 1.05, min(adjusted_sell, conservative_sell))
            clamp_reasons.append("sparse_data_conservative_pricing")

        margin_before = ((max(predicted_sell, adjusted_buy) - max(predicted_buy, 0.01)) / max(predicted_buy, 0.01)) * 100 if predicted_buy > 0 else 0.0
        margin_after = ((adjusted_sell - adjusted_buy) / adjusted_buy) * 100 if adjusted_buy > 0 else 0.0
        max_margin = category_policy.sparse_data_max_margin_percent if sparse_limit else category_policy.max_margin_percent
        min_margin = category_policy.min_margin_percent

        if margin_after > max_margin and adjusted_buy > 0:
            adjusted_sell = adjusted_buy * (1.0 + (max_margin / 100.0))
            margin_after = max_margin
            margin_adjustment_applied = True
            clamp_reasons.append("category_margin_cap")

        if adjusted_buy > 0 and margin_after < min_margin:
            floor_sell = adjusted_buy * (1.0 + (min_margin / 100.0))
            if retail_bounds_used:
                floor_sell = min(floor_sell, retail_bounds_used["upper_bound"])
            adjusted_sell = max(adjusted_sell, floor_sell)
            margin_after = ((adjusted_sell - adjusted_buy) / adjusted_buy) * 100 if adjusted_buy > 0 else 0.0
            if margin_after >= min_margin:
                margin_adjustment_applied = True
                clamp_reasons.append("min_margin_floor")

        if confidence_after_adjustment < MIN_CONFIDENT_SCORE:
            adjusted_buy = heuristic_buy
            adjusted_sell = max(adjusted_buy * 1.05, min(adjusted_sell, heuristic_sell if heuristic_sell > 0 else adjusted_sell))
            low_data_adjustment_applied = True
            clamp_reasons.append("low_confidence_heuristic_fallback")
            policy = "hybrid_ml_sanity_low_confidence"
        else:
            policy = "hybrid_ml_sanity"

        margin_after = ((adjusted_sell - adjusted_buy) / adjusted_buy) * 100 if adjusted_buy > 0 else 0.0
        sanity_adjustments = {
            "retail_anchor_applied": retail_anchor_applied,
            "buy_adjustment_applied": buy_adjustment_applied,
            "margin_adjustment_applied": margin_adjustment_applied,
            "low_data_adjustment_applied": low_data_adjustment_applied,
            "retail_bounds_used": retail_bounds_used,
            "clamp_reason": clamp_reasons or ["none"],
            "original_model_sell_prediction": round(predicted_sell, 2),
            "clamped_sell_prediction": round(adjusted_sell, 2),
            "category_policy_used": combined_metrics.get("detected_category", "unknown"),
            "category_margin_cap_applied": "category_margin_cap" in clamp_reasons,
            "config": {
                "retail_lower_bound_multiplier": category_policy.retail_anchor_multiplier_low,
                "retail_upper_bound_multiplier": category_policy.retail_anchor_multiplier_high,
                "min_margin_percent": category_policy.min_margin_percent,
                "max_margin_percent": category_policy.max_margin_percent,
                "sparse_data_max_margin_percent": category_policy.sparse_data_max_margin_percent,
                "sparse_retail_threshold": config.sparse_retail_threshold,
                "sparse_wholesale_threshold": config.sparse_wholesale_threshold,
                "buy_to_retail_cap_ratio": config.buy_to_retail_cap_ratio,
            },
        }
        return {
            "recommended_buy": round(adjusted_buy, 2),
            "recommended_sell": round(adjusted_sell, 2),
            "margin_before_adjustment": round(margin_before, 2),
            "margin_after_adjustment": round(margin_after, 2),
            "confidence_after_adjustment": confidence_after_adjustment,
            "policy": policy,
            "sanity_adjustments": sanity_adjustments,
        }

    def _compute_confidence(
        self,
        wholesale_metrics: Dict[str, Any],
        retail_metrics: Dict[str, Any],
        combined_metrics: Dict[str, Any],
    ) -> Tuple[float, str]:
        score = 0.1
        reasons: List[str] = []
        wholesale_count = wholesale_metrics["usable_price_count"]
        retail_count = retail_metrics["usable_price_count"]
        total_count = wholesale_count + retail_count

        if wholesale_count:
            score += min(wholesale_count / 8.0, 1.0) * 0.25
        else:
            reasons.append("missing wholesale prices")
        if retail_count:
            score += min(retail_count / 8.0, 1.0) * 0.2
        else:
            reasons.append("missing retail prices")
        if combined_metrics["has_both_sources"]:
            score += 0.2
        else:
            reasons.append("single-sided market view")

        for market, label, weight in (
            (wholesale_metrics, "wholesale variance", 0.12),
            (retail_metrics, "retail variance", 0.08),
        ):
            price_cv = market.get("price_cv", 0.0)
            if market.get("usable_price_count", 0) <= 1:
                reasons.append(f"only one {market['role']} record")
                continue
            stability = max(0.0, 1.0 - min(price_cv / 0.55, 1.0))
            score += stability * weight
            if price_cv > 0.35:
                reasons.append(label)

        if total_count < 3:
            reasons.append("very small sample")
            score *= 0.7
        if wholesale_metrics["outlier_count"] or retail_metrics["outlier_count"]:
            score *= 0.95
            reasons.append("outliers removed")

        score = round(self._clamp(score, 0.0, 0.99), 4)
        if score >= 0.78:
            reason = "high confidence - both markets present with stable pricing"
        elif score >= MIN_CONFIDENT_SCORE:
            reason = "moderate confidence - usable market coverage with some variance"
        else:
            detail = ", ".join(dict.fromkeys(reasons)) if reasons else "insufficient consistent evidence"
            reason = f"low confidence - {detail}"
        return score, reason

    def _cluster_status(
        self,
        pricing: Dict[str, Any],
        confidence_score: float,
        wholesale_metrics: Dict[str, Any],
        retail_metrics: Dict[str, Any],
    ) -> str:
        if wholesale_metrics["usable_price_count"] == 0:
            return "insufficient_data"
        if confidence_score < MIN_CONFIDENT_SCORE or retail_metrics["usable_price_count"] == 0:
            return "low_confidence"
        if pricing["recommended_sell"] <= pricing["recommended_buy"]:
            return "insufficient_data"
        return "completed"

    def _augment_confidence_reason(self, confidence_reason: str, sanity_adjustments: Dict[str, Any]) -> str:
        reasons = sanity_adjustments.get("clamp_reason") or []
        meaningful = [reason for reason in reasons if reason != "none"]
        if not meaningful:
            return confidence_reason
        return f"{confidence_reason}; sanity layer: {', '.join(meaningful)}"

    def _select_primary_cluster(self, cluster_results: List[ClusterRecommendation]) -> ClusterRecommendation:
        def rank_key(result: ClusterRecommendation) -> Tuple[float, float, float]:
            metrics = result.metrics["combined"]
            total_count = float(metrics["cluster_record_count"])
            has_both = 1.0 if metrics["has_both_sources"] else 0.0
            return (has_both, result.confidence_score, total_count)

        return max(cluster_results, key=rank_key)

    def _build_recommendation_response(
        self,
        product_name: str,
        category: str,
        primary: ClusterRecommendation,
        cluster_results: List[ClusterRecommendation],
    ) -> Dict[str, Any]:
        pricing = primary.pricing
        wholesale_metrics = primary.metrics["wholesale"]
        retail_metrics = primary.metrics["retail"]
        commercial_intelligence = primary.metrics.get("commercial_intelligence") or {}
        profitability_summary = commercial_intelligence.get("profitability_summary") or {}
        market_intelligence = commercial_intelligence.get("market_intelligence") or {}
        cost_breakdown = commercial_intelligence.get("cost_breakdown") or {}
        cost_profile = commercial_intelligence.get("cost_profile") or {}
        evidence_ledger = commercial_intelligence.get("evidence_ledger") or []
        low_sample_warning = self._is_low_sample(wholesale_metrics, retail_metrics)
        reasoning_bullets = self._build_reasoning_bullets(primary, low_sample_warning)
        recommendation_status = "generated" if primary.status == "completed" else primary.status
        net_margin = float(profitability_summary.get("net_margin_percent", pricing["expected_margin_percent"]))
        gross_profit = float(profitability_summary.get("gross_profit_pkr", max(pricing["recommended_sell"] - pricing["recommended_buy"], 0.0)))
        net_profit = float(profitability_summary.get("net_profit_pkr", gross_profit))
        roi_percent = float(profitability_summary.get("roi_percent", 0.0))
        break_even_sell_price = float(profitability_summary.get("break_even_sell_price_pkr", pricing["recommended_sell"]))
        profitability_confidence = float(profitability_summary.get("profitability_confidence", primary.confidence_score))
        confidence_band = str(commercial_intelligence.get("quality_band") or classify_quality_band(
            confidence_score=primary.confidence_score,
            low_sample_warning=low_sample_warning,
            wholesale_vendor_count=wholesale_metrics["vendor_count"],
            retail_listing_count=retail_metrics["vendor_count"],
            net_margin_percent=net_margin,
        ))
        return {
            "product": product_name,
            "category": category,
            "query_product": product_name,
            "pipeline_run_id": None,
            "analytics_result_id": primary.analytics_result_id,
            "product_cluster_id": primary.cluster_db_id,
            "recommended_buy_price_pkr": pricing["recommended_buy"],
            "recommended_sell_price_pkr": pricing["recommended_sell"],
            "expected_profit_margin": net_margin,
            "confidence_score": primary.confidence_score,
            "confidence_reason": primary.confidence_reason,
            "wholesale_vendors_count": wholesale_metrics["vendor_count"],
            "retail_sellers_count": retail_metrics["vendor_count"],
            "low_sample_warning": low_sample_warning,
            "low_sample_reason": self._build_low_sample_reason(wholesale_metrics, retail_metrics) if low_sample_warning else "",
            "sample_thresholds": {
                "wholesale_vendors": LOW_SAMPLE_WHOLESALE_VENDOR_THRESHOLD,
                "retail_listings": LOW_SAMPLE_RETAIL_LISTING_THRESHOLD,
            },
            "reasoning_bullets": reasoning_bullets,
            "gross_profit_pkr": gross_profit,
            "net_profit_pkr": net_profit,
            "gross_margin_percent": float(profitability_summary.get("gross_margin_percent", pricing["expected_margin_percent"])),
            "roi_percent": roi_percent,
            "break_even_sell_price_pkr": break_even_sell_price,
            "profitability_confidence": profitability_confidence,
            "confidence_band": confidence_band,
            "cost_breakdown": cost_breakdown,
            "cost_profile": cost_profile,
            "market_intelligence": market_intelligence,
            "commercial_intelligence": commercial_intelligence,
            "profitability_summary": profitability_summary,
            "evidence_ledger": evidence_ledger,
            "price_spread_wholesale": wholesale_metrics["price_stddev"],
            "price_spread_retail": retail_metrics["price_stddev"],
            "recommendation_status": recommendation_status,
            "strategy_summary": f"{pricing['policy']} for cluster {primary.cluster_key}",
            "sourcing_recommendation": self._build_sourcing_recommendation(wholesale_metrics, primary.status),
            "marketing_recommendation": self._build_marketing_recommendation(retail_metrics, primary.status),
            "analysis_details": {
                "primary_cluster": {
                    "cluster_key": primary.cluster_key,
                    "cluster_db_id": primary.cluster_db_id,
                    "analytics_result_id": primary.analytics_result_id,
                    "status": primary.status,
                    "metrics": primary.metrics,
                    "pricing": primary.pricing,
                    "confidence_score": primary.confidence_score,
                    "confidence_reason": primary.confidence_reason,
                    "insight_summary": primary.insight_summary,
                },
                "cluster_count": len(cluster_results),
                "clusters": [
                    {
                        "cluster_key": result.cluster_key,
                        "cluster_db_id": result.cluster_db_id,
                        "analytics_result_id": result.analytics_result_id,
                        "status": result.status,
                        "confidence_score": result.confidence_score,
                        "confidence_reason": result.confidence_reason,
                        "pricing": result.pricing,
                        "metrics": result.metrics,
                        "insight_summary": result.insight_summary,
                    }
                    for result in cluster_results
                ],
                "model_training_metadata": self.model.training_metadata,
                "commercial_intelligence": commercial_intelligence,
            },
        }

    def _build_empty_result(self, product_name: str, category: str) -> Dict[str, Any]:
        empty_profitability = {
            "quality_band": "limited",
            "cost_profile": {},
            "cost_breakdown": {},
            "pricing_modes": {
                "competitive": {
                    "candidate_price_pkr": 0.0,
                    "expected_net_margin_percent": 0.0,
                    "fit_score": 0.0,
                    "market_fit_score": 0.0,
                    "margin_safety_score": 0.0,
                    "confidence_weight": 0.0,
                    "reasoning": ["insufficient market data for pricing mode selection"],
                },
                "balanced": {
                    "candidate_price_pkr": 0.0,
                    "expected_net_margin_percent": 0.0,
                    "fit_score": 0.0,
                    "market_fit_score": 0.0,
                    "margin_safety_score": 0.0,
                    "confidence_weight": 0.0,
                    "reasoning": ["insufficient market data for pricing mode selection"],
                },
                "premium": {
                    "candidate_price_pkr": 0.0,
                    "expected_net_margin_percent": 0.0,
                    "fit_score": 0.0,
                    "market_fit_score": 0.0,
                    "margin_safety_score": 0.0,
                    "confidence_weight": 0.0,
                    "reasoning": ["insufficient market data for pricing mode selection"],
                },
                "psychological": {
                    "candidate_price_pkr": 0.0,
                    "expected_net_margin_percent": 0.0,
                    "fit_score": 0.0,
                    "market_fit_score": 0.0,
                    "margin_safety_score": 0.0,
                    "confidence_weight": 0.0,
                    "reasoning": ["insufficient market data for pricing mode selection"],
                },
            },
            "primary_pricing_mode": "competitive",
            "alternate_pricing_modes": ["balanced", "psychological", "premium"],
            "profitability_summary": {
                "gross_profit_pkr": 0.0,
                "net_profit_pkr": 0.0,
                "gross_margin_percent": 0.0,
                "net_margin_percent": 0.0,
                "roi_percent": 0.0,
                "break_even_sell_price_pkr": 0.0,
                "profitability_confidence": 0.0,
                "risk_notes": ["limited data sample raises forecast uncertainty"],
                "price_band": {"min": 0.0, "max": 0.0, "avg": 0.0, "currency": "PKR"},
            },
            "market_intelligence": {
                "confidence_band": "limited",
                "confidence_score": 0.0,
                "demand_score": 0.0,
                "competition_score": 0.0,
                "supplier_quality_score": 0.0,
                "market_saturation_score": 0.0,
                "data_quality_score": 0.0,
                "risk_score": 100.0,
                "opportunity_score": 0.0,
                "reasoning": {},
            },
            "evidence_ledger": [],
        }
        return {
            "product": product_name,
            "category": category,
            "query_product": product_name,
            "recommended_buy_price_pkr": 0.0,
            "recommended_sell_price_pkr": 0.0,
            "expected_profit_margin": 0.0,
            "confidence_score": 0.0,
            "confidence_reason": "low confidence - no clustered normalized records available",
            "wholesale_vendors_count": 0,
            "retail_sellers_count": 0,
            "low_sample_warning": True,
            "low_sample_reason": "limited market data available",
            "sample_thresholds": {
                "wholesale_vendors": LOW_SAMPLE_WHOLESALE_VENDOR_THRESHOLD,
                "retail_listings": LOW_SAMPLE_RETAIL_LISTING_THRESHOLD,
            },
            "reasoning_bullets": [
                "Low confidence: no clustered normalized records available.",
                "Observed market range could not be established from the current sample.",
            ],
            "gross_profit_pkr": 0.0,
            "net_profit_pkr": 0.0,
            "gross_margin_percent": 0.0,
            "roi_percent": 0.0,
            "break_even_sell_price_pkr": 0.0,
            "profitability_confidence": 0.0,
            "confidence_band": "limited",
            "cost_breakdown": {},
            "cost_profile": {},
            "market_intelligence": empty_profitability["market_intelligence"],
            "commercial_intelligence": empty_profitability,
            "profitability_summary": empty_profitability["profitability_summary"],
            "evidence_ledger": [],
            "price_spread_wholesale": 0.0,
            "price_spread_retail": 0.0,
            "recommendation_status": "insufficient_data",
            "strategy_summary": "no analytics generated",
            "sourcing_recommendation": "collect more wholesale data",
            "marketing_recommendation": "collect more retail data",
            "analysis_details": {
                "cluster_count": 0,
                "clusters": [],
                "model_training_metadata": self.model.training_metadata,
                "commercial_intelligence": empty_profitability,
            },
        }

    def _persist_low_confidence_recommendation(self, result: Dict[str, Any], pipeline_run_id: Optional[str]) -> None:

        if not pipeline_run_id:
            return
        analytics_rows = self.db.get_run_analytics(pipeline_run_id)
        if not analytics_rows:
            return
        first_row = analytics_rows[0]
        self.db.insert_recommendation(
            {
                "pipeline_run_id": pipeline_run_id,
                "analytics_result_id": first_row["id"],
                "recommendation_type": "pricing",
                "recommendation_status": result["recommendation_status"],
                "recommended_buy_price_pkr": result["recommended_buy_price_pkr"],
                "recommended_sell_price_pkr": result["recommended_sell_price_pkr"],
                "sourcing_recommendation": result["sourcing_recommendation"],
                "marketing_recommendation": result["marketing_recommendation"],
                "strategy_summary": result["strategy_summary"],
                "reasoning_trace": result["analysis_details"],
                "confidence_score": result["confidence_score"],
                "approval_status": "pending",
            }
        )

    def _feature_row_from_analytics_row(self, row: Dict[str, Any]) -> Optional[List[float]]:
        metadata = row.get("analysis_metadata") or {}
        wholesale = metadata.get("wholesale_metrics") or {}
        retail = metadata.get("retail_metrics") or {}
        combined = metadata.get("combined_metrics") or {}
        if not wholesale and not retail:
            return None
        return [
            float(wholesale.get("usable_price_count", 0)),
            float(retail.get("usable_price_count", 0)),
            self._as_float(wholesale.get("min_price")),
            self._as_float(wholesale.get("avg_price")),
            self._as_float(wholesale.get("price_cv")),
            self._as_float(retail.get("min_price")),
            self._as_float(retail.get("avg_price")),
            self._as_float(retail.get("max_price")),
            self._as_float(retail.get("price_cv")),
            float(combined.get("platform_count", 0)),
            float(combined.get("vendor_count", 0)),
            self._as_float(combined.get("price_spread")),
            1.0 if combined.get("has_both_sources") else 0.0,
        ]

    def _is_low_sample(self, wholesale_metrics: Dict[str, Any], retail_metrics: Dict[str, Any]) -> bool:
        return (
            int(wholesale_metrics.get("vendor_count", 0) or 0) < LOW_SAMPLE_WHOLESALE_VENDOR_THRESHOLD
            or int(retail_metrics.get("vendor_count", 0) or 0) < LOW_SAMPLE_RETAIL_LISTING_THRESHOLD
        )

    def _build_low_sample_reason(self, wholesale_metrics: Dict[str, Any], retail_metrics: Dict[str, Any]) -> str:
        notes: List[str] = []
        wholesale_count = int(wholesale_metrics.get("vendor_count", 0) or 0)
        retail_count = int(retail_metrics.get("vendor_count", 0) or 0)
        if wholesale_count < LOW_SAMPLE_WHOLESALE_VENDOR_THRESHOLD:
            notes.append(f"wholesale vendors below threshold ({wholesale_count}/{LOW_SAMPLE_WHOLESALE_VENDOR_THRESHOLD})")
        if retail_count < LOW_SAMPLE_RETAIL_LISTING_THRESHOLD:
            notes.append(f"retail listings below threshold ({retail_count}/{LOW_SAMPLE_RETAIL_LISTING_THRESHOLD})")
        return "; ".join(notes) if notes else ""

    def _build_reasoning_bullets(self, primary: ClusterRecommendation, low_sample_warning: bool) -> List[str]:
        bullets: List[str] = []
        pricing = primary.pricing
        sanity = pricing.get("sanity_adjustments") or {}
        clamp_reasons = [reason for reason in (sanity.get("clamp_reason") or []) if reason and reason != "none"]
        commercial_intelligence = primary.metrics.get("commercial_intelligence") or {}
        profitability_summary = commercial_intelligence.get("profitability_summary") or {}

        if "retail_anchor_clamp" in clamp_reasons:
            bullets.append("Adjusted down: sell price was pulled back to the observed retail band.")
        if "buy_capped_against_retail_floor" in clamp_reasons:
            bullets.append("Adjusted down: buy price was capped against the retail floor.")
        if "sparse_data_conservative_pricing" in clamp_reasons:
            bullets.append("Adjusted down: sparse sample triggered conservative pricing.")
        if "category_margin_cap" in clamp_reasons:
            bullets.append("Category cap applied: margin was limited by the product policy.")
        if "min_margin_floor" in clamp_reasons:
            bullets.append("Minimum margin floor applied to keep the recommendation viable.")
        if "low_confidence_heuristic_fallback" in clamp_reasons:
            bullets.append("Low confidence fallback used: heuristic pricing replaced the model output.")

        wholesale_metrics = primary.metrics["wholesale"]
        retail_metrics = primary.metrics["retail"]
        if wholesale_metrics.get("price_cv", 0.0) > 0.35:
            bullets.append("Adjusted confidence down: high wholesale price variance.")
        if retail_metrics.get("price_cv", 0.0) > 0.35:
            bullets.append("Adjusted confidence down: high retail price variance.")
        if low_sample_warning:
            bullets.append(
                f"Low confidence - based on limited data ({int(wholesale_metrics.get('vendor_count', 0) or 0)} wholesale vendors, "
                f"{int(retail_metrics.get('vendor_count', 0) or 0)} retail listings)."
            )

        net_margin = profitability_summary.get("net_margin_percent")
        break_even = profitability_summary.get("break_even_sell_price_pkr")
        if net_margin is not None:
            bullets.append(
                f"Net margin after commissions, shipping, packaging, advertising, taxes, and overhead is {float(net_margin):.1f}%."
            )
        if break_even:
            bullets.append(f"Break-even sell price sits around PKR {float(break_even):,.0f}.")

        base_reason = primary.confidence_reason.strip()
        if base_reason:
            bullets.insert(0, base_reason[:1].upper() + base_reason[1:] if len(base_reason) > 1 else base_reason.upper())

        if not bullets:
            bullets.append("Recommendation derived from the current market sample.")

        return list(dict.fromkeys(bullets))

    def _generate_reasoning_summary(
        self,
        wholesale_metrics: Dict[str, Any],
        retail_metrics: Dict[str, Any],
        combined_metrics: Dict[str, Any],
        pricing: Dict[str, Any],
        confidence_score: float,
        status: str,
        commercial_intelligence: Optional[Dict[str, Any]] = None,
    ) -> str:
        if status == "insufficient_data":
            return "Insufficient wholesale evidence to produce a safe recommendation."
        parts = [
            f"Wholesale avg {wholesale_metrics['avg_price']:.2f} PKR from {wholesale_metrics['usable_price_count']} usable records."
        ]
        if retail_metrics["usable_price_count"]:
            parts.append(
                f"Retail avg {retail_metrics['avg_price']:.2f} PKR across {retail_metrics['usable_price_count']} records."
            )
        else:
            parts.append("Retail evidence is missing, so sell guidance is heuristic and conservative.")
        parts.append(
            f"Recommended buy {pricing['recommended_buy']:.2f} PKR and sell {pricing['recommended_sell']:.2f} PKR with confidence {confidence_score:.2f}."
        )
        if commercial_intelligence:
            profitability = commercial_intelligence.get("profitability_summary") or {}
            if profitability:
                parts.append(
                    f"Net margin after operating costs is {profitability.get('net_margin_percent', 0.0):.2f}% with break-even near PKR {profitability.get('break_even_sell_price_pkr', 0.0):.0f}."
                )
        if not combined_metrics["has_both_sources"]:
            parts.append("Cluster lacks both wholesale and retail sides.")
        return " ".join(parts)

    def _build_commercial_intelligence(
        self,
        *,
        product_name: str,
        category: str,
        wholesale_metrics: Dict[str, Any],
        retail_metrics: Dict[str, Any],
        combined_metrics: Dict[str, Any],
        pricing: Dict[str, Any],
        confidence_score: float,
        low_sample_warning: bool,
    ) -> Dict[str, Any]:
        profitability_snapshot = compute_profitability_snapshot(
            product_name=product_name,
            category=category,
            buy_price_pkr=pricing.get("recommended_buy", 0.0),
            sell_price_pkr=pricing.get("recommended_sell", 0.0),
            confidence_score=confidence_score,
            low_sample_warning=low_sample_warning,
            wholesale_metrics=wholesale_metrics,
            retail_metrics=retail_metrics,
            combined_metrics=combined_metrics,
            price_band={
                "min": retail_metrics.get("min_price", 0.0),
                "max": retail_metrics.get("max_price", 0.0),
                "avg": retail_metrics.get("avg_price", 0.0),
                "currency": "PKR",
            },
        )
        market_intelligence = build_market_intelligence_snapshot(
            wholesale_metrics=wholesale_metrics,
            retail_metrics=retail_metrics,
            combined_metrics=combined_metrics,
            profitability_snapshot=profitability_snapshot,
            confidence_score=confidence_score,
            low_sample_warning=low_sample_warning,
        )
        pricing_mode_snapshot = build_pricing_mode_snapshot(
            product_name=product_name,
            category=category,
            wholesale_metrics=wholesale_metrics,
            retail_metrics=retail_metrics,
            combined_metrics=combined_metrics,
            profitability_snapshot=profitability_snapshot,
            confidence_score=confidence_score,
            low_sample_warning=low_sample_warning,
            price_band=profitability_snapshot.get("profitability_summary", {}).get("price_band") or {},
        )
        evidence_ledger = build_evidence_ledger(
            product_name=product_name,
            category=category,
            wholesale_metrics=wholesale_metrics,
            retail_metrics=retail_metrics,
            combined_metrics=combined_metrics,
            profitability_snapshot=profitability_snapshot,
            market_intelligence=market_intelligence,
            price_band=profitability_snapshot.get("profitability_summary", {}).get("price_band") or {},
        )
        profitability = profitability_snapshot.get("profitability_summary") or {}
        return {
            "product_name": product_name,
            "category": category,
            "quality_band": profitability_snapshot.get("quality_band", "balanced"),
            "cost_profile": profitability_snapshot.get("cost_profile") or {},
            "cost_breakdown": profitability_snapshot.get("cost_breakdown") or {},
            "profitability_summary": profitability,
            "market_intelligence": market_intelligence,
            "pricing_modes": pricing_mode_snapshot["pricing_modes"],
            "primary_pricing_mode": pricing_mode_snapshot["primary_pricing_mode"],
            "alternate_pricing_modes": pricing_mode_snapshot["alternate_pricing_modes"],
            "evidence_ledger": evidence_ledger,
            "net_margin_percent": profitability.get("net_margin_percent", 0.0),
            "gross_margin_percent": profitability.get("gross_margin_percent", 0.0),
            "break_even_sell_price_pkr": profitability.get("break_even_sell_price_pkr", 0.0),
        }

    def _build_sourcing_recommendation(self, wholesale_metrics: Dict[str, Any], status: str) -> str:
        if status == "insufficient_data":
            return "Collect more wholesale offers before sourcing."
        if wholesale_metrics["price_cv"] > 0.3:
            return "Negotiate across multiple suppliers because wholesale quotes are volatile."
        return "Anchor sourcing on the lowest wholesale offer and verify MOQ and delivery terms."

    def _build_marketing_recommendation(self, retail_metrics: Dict[str, Any], status: str) -> str:
        if retail_metrics["usable_price_count"] == 0:
            return "Retail coverage is thin, so validate market demand before launch."
        if status == "low_confidence":
            return "Use conservative pricing and monitor fresh retail listings before scaling."
        return "Price slightly under the competitive retail floor while protecting margin."

    def _remove_price_outliers(self, prices: Sequence[float]) -> List[float]:
        if len(prices) < 4:
            return list(prices)
        q1 = float(np.percentile(prices, 25))
        q3 = float(np.percentile(prices, 75))
        iqr = q3 - q1
        if iqr <= 0:
            return list(prices)
        lower = q1 - (1.5 * iqr)
        upper = q3 + (1.5 * iqr)
        return [price for price in prices if lower <= price <= upper]

    def _clamp(self, value: float, lower: float, upper: float) -> float:
        if upper < lower:
            upper = lower
        return float(min(max(value, lower), upper))

    def _as_float(self, value: Any) -> float:
        try:
            if value is None or (isinstance(value, float) and math.isnan(value)):
                return 0.0
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _convert_types(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {key: self._convert_types(value) for key, value in obj.items()}
        if isinstance(obj, list):
            return [self._convert_types(item) for item in obj]
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj

    def get_stats(self) -> Dict[str, Any]:
        return self.db.get_stats()




