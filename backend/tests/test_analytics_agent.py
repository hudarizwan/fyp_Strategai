import sys
import types
import unittest
from unittest.mock import patch

ecdb_stub = types.ModuleType("app.services.ecdb")


class _ImportStubECDB:
    pass


ecdb_stub.ECDB = _ImportStubECDB
sys.modules.setdefault("app.services.ecdb", ecdb_stub)

from app.services.analytics_agent import AnalyticsAgent


class FakeDB:
    def __init__(self):
        self.analytics_rows = []
        self.recommendations = []

    def insert_analytics_result(self, payload):
        row = {"id": f"analytics-{len(self.analytics_rows) + 1}", **payload}
        self.analytics_rows.append(row)
        return row

    def insert_recommendation(self, payload):
        self.recommendations.append(payload)
        return payload

    def get_run_analytics(self, pipeline_run_id):
        return self.analytics_rows

    def get_stats(self):
        return {"ok": True}

    def _rest_get(self, *_args, **_kwargs):
        return []


class AnalyticsAgentTests(unittest.TestCase):
    def build_agent(self):
        with patch("app.services.analytics_agent.ECDB", return_value=FakeDB()):
            return AnalyticsAgent()

    def build_cluster(self, wholesale_prices=None, retail_prices=None):
        wholesale_prices = wholesale_prices or []
        retail_prices = retail_prices or []
        records = []
        for index, price in enumerate(wholesale_prices):
            records.append(
                {
                    "source_type": "wholesale",
                    "price_pkr": price,
                    "platform": "made_in_china",
                    "supplier_or_seller": f"factory-{index}",
                }
            )
        for index, price in enumerate(retail_prices):
            records.append(
                {
                    "source_type": "retail",
                    "price_pkr": price,
                    "platform": "daraz",
                    "supplier_or_seller": f"seller-{index}",
                }
            )
        return {
            "cluster_id": "cluster-1",
            "db_cluster_id": "db-cluster-1",
            "canonical_title": "Sample Product",
            "records": records,
        }

    def test_detect_pricing_category_for_phone_cluster(self):
        agent = self.build_agent()
        cluster = {"canonical_title": "Apple iPhone 13 128GB Smartphone", "records": []}
        detected, policy, fallback_used, metadata = agent._detect_pricing_category(cluster, "iPhone 13", "mobile", [], [])
        self.assertEqual(detected, "mobile_phones")
        self.assertEqual(policy.max_margin_percent, 25.0)
        self.assertFalse(fallback_used)
        self.assertIn("iphone", metadata["matched_keywords"])

    def test_detect_pricing_category_for_headset_cluster(self):
        agent = self.build_agent()
        cluster = {"canonical_title": "HyperX Cloud III Wireless Gaming Headset", "records": []}
        detected, policy, _fallback_used, _metadata = agent._detect_pricing_category(cluster, "HyperX Cloud III", "headset", [], [])
        self.assertEqual(detected, "headsets")
        self.assertEqual(policy.max_margin_percent, 35.0)

    def test_phone_keyword_does_not_match_inside_headphone(self):
        agent = self.build_agent()
        cluster = {"canonical_title": "Wireless Headphones with Noise Cancellation", "records": []}
        detected, policy, _fallback_used, _metadata = agent._detect_pricing_category(cluster, "wireless headphones", "audio", [], [])
        self.assertEqual(detected, "headsets")
        self.assertEqual(policy.max_margin_percent, 35.0)

    def test_detect_pricing_category_for_mobile_accessory_cluster(self):
        agent = self.build_agent()
        cluster = {"canonical_title": "iPhone 13 Fast Charger USB C Cable", "records": []}
        detected, policy, _fallback_used, _metadata = agent._detect_pricing_category(cluster, "iphone charger", "accessories", [], [])
        self.assertEqual(detected, "mobile_accessories")
        self.assertEqual(policy.max_margin_percent, 60.0)

    def test_unknown_cluster_uses_conservative_fallback_policy(self):
        agent = self.build_agent()
        cluster = {"canonical_title": "Mystery Product ZXQ", "records": []}
        detected, policy, fallback_used, _metadata = agent._detect_pricing_category(cluster, "zxq mystery", "misc", [], [])
        self.assertEqual(detected, "unknown")
        self.assertTrue(fallback_used)
        self.assertEqual(policy.max_margin_percent, 30.0)

    def test_compute_market_metrics_removes_outlier(self):
        agent = self.build_agent()
        metrics = agent._compute_market_metrics(
            [
                {"price_pkr": 100, "platform": "made_in_china", "supplier_or_seller": "a"},
                {"price_pkr": 105, "platform": "made_in_china", "supplier_or_seller": "b"},
                {"price_pkr": 110, "platform": "made_in_china", "supplier_or_seller": "c"},
                {"price_pkr": 5000, "platform": "made_in_china", "supplier_or_seller": "d"},
            ],
            role="wholesale",
        )
        self.assertEqual(metrics["usable_price_count"], 3)
        self.assertEqual(metrics["outlier_count"], 1)
        self.assertAlmostEqual(metrics["best_price"], 100.0)

    def test_confidence_is_low_without_retail(self):
        agent = self.build_agent()
        wholesale = {"role": "wholesale", "usable_price_count": 3, "price_cv": 0.08, "outlier_count": 0}
        retail = {"role": "retail", "usable_price_count": 0, "price_cv": 0.0, "outlier_count": 0}
        combined = {"has_both_sources": False}
        score, reason = agent._compute_confidence(wholesale, retail, combined)
        self.assertLess(score, 0.62)
        self.assertIn("low confidence", reason)

    def test_normal_data_keeps_realistic_sell_without_unnecessary_clamp(self):
        agent = self.build_agent()
        wholesale = agent._compute_market_metrics(
            [{"price_pkr": p, "platform": "made_in_china", "supplier_or_seller": str(p)} for p in [500, 540, 560]],
            role="wholesale",
        )
        retail = agent._compute_market_metrics(
            [{"price_pkr": p, "platform": "daraz", "supplier_or_seller": str(p)} for p in [1100, 1150, 1200]],
            role="retail",
        )
        combined = agent._compute_combined_metrics(self.build_cluster([500, 540, 560], [1100, 1150, 1200]), [], [], wholesale, retail)
        pricing = agent._compute_pricing(wholesale, retail, combined, confidence_score=0.85, category_policy=agent.category_policies["computer_accessories"])
        self.assertGreater(pricing["recommended_sell"], pricing["recommended_buy"])
        self.assertLessEqual(pricing["recommended_sell"], 1440.0)
        self.assertLessEqual(pricing["expected_margin_percent"], 40.0)
        self.assertGreaterEqual(pricing["recommended_sell"], pricing["recommended_buy"] * 1.1)
        self.assertIn(pricing["policy"], {"hybrid_ml_sanity", "hybrid_ml_sanity_low_confidence"})

    def test_sparse_data_clamps_extreme_prediction_and_reduces_confidence(self):
        agent = self.build_agent()
        wholesale = agent._compute_market_metrics(
            [{"price_pkr": 2800, "platform": "made_in_china", "supplier_or_seller": "w1"}],
            role="wholesale",
        )
        retail = agent._compute_market_metrics(
            [{"price_pkr": 25000, "platform": "daraz", "supplier_or_seller": "r1"}],
            role="retail",
        )
        combined = agent._compute_combined_metrics(self.build_cluster([2800], [25000]), [], [], wholesale, retail)
        policy = agent.category_policies["headsets"]
        with patch.object(agent.model, "predict", return_value=(2800.0, 100000.0)):
            pricing = agent._compute_pricing(wholesale, retail, combined, confidence_score=0.6, category_policy=policy)
        self.assertLessEqual(pricing["recommended_sell"], 25000.0)
        self.assertLess(pricing["confidence_after_adjustment"], 0.6)
        self.assertTrue(pricing["sanity_adjustments"]["low_data_adjustment_applied"])
        self.assertIn("low_confidence_heuristic_fallback", pricing["sanity_adjustments"]["clamp_reason"])
        self.assertLessEqual(pricing["expected_margin_percent"], policy.sparse_data_max_margin_percent)

    def test_extreme_ml_prediction_is_clamped_into_retail_band(self):
        agent = self.build_agent()
        wholesale = agent._compute_market_metrics(
            [{"price_pkr": p, "platform": "made_in_china", "supplier_or_seller": str(p)} for p in [500, 520, 540]],
            role="wholesale",
        )
        retail = agent._compute_market_metrics(
            [{"price_pkr": p, "platform": "daraz", "supplier_or_seller": str(p)} for p in [1000, 1100, 1200]],
            role="retail",
        )
        combined = agent._compute_combined_metrics(self.build_cluster([500, 520, 540], [1000, 1100, 1200]), [], [], wholesale, retail)
        policy = agent.category_policies["computer_accessories"]
        with patch.object(agent.model, "predict", return_value=(520.0, 10000.0)):
            pricing = agent._compute_pricing(wholesale, retail, combined, confidence_score=0.9, category_policy=policy)
        self.assertLessEqual(pricing["recommended_sell"], 1440.0)
        self.assertIn("retail_anchor_clamp", pricing["sanity_adjustments"]["clamp_reason"])
        self.assertLessEqual(pricing["expected_margin_percent"], policy.max_margin_percent)

    def test_phone_policy_caps_margin_lower_than_accessory_policy(self):
        agent = self.build_agent()
        wholesale = agent._compute_market_metrics(
            [{"price_pkr": p, "platform": "made_in_china", "supplier_or_seller": str(p)} for p in [80000, 82000, 84000]],
            role="wholesale",
        )
        retail = agent._compute_market_metrics(
            [{"price_pkr": p, "platform": "daraz", "supplier_or_seller": str(p)} for p in [110000, 112000, 115000]],
            role="retail",
        )
        combined = agent._compute_combined_metrics(self.build_cluster([80000, 82000, 84000], [110000, 112000, 115000]), [], [], wholesale, retail)
        with patch.object(agent.model, "predict", return_value=(82000.0, 180000.0)):
            phone_pricing = agent._compute_pricing(wholesale, retail, combined, confidence_score=0.9, category_policy=agent.category_policies["mobile_phones"])
            accessory_pricing = agent._compute_pricing(wholesale, retail, combined, confidence_score=0.9, category_policy=agent.category_policies["mobile_accessories"])
        self.assertLessEqual(phone_pricing["expected_margin_percent"], 25.0)
        self.assertLessEqual(accessory_pricing["expected_margin_percent"], 60.0)
        self.assertLess(phone_pricing["recommended_sell"], accessory_pricing["recommended_sell"])

    def test_no_wholesale_returns_insufficient_data(self):
        agent = self.build_agent()
        wholesale = agent._compute_market_metrics([], role="wholesale")
        retail = agent._compute_market_metrics(
            [{"price_pkr": 1000, "platform": "daraz", "supplier_or_seller": "seller"}],
            role="retail",
        )
        combined = {"has_both_sources": False, "platform_count": 1, "vendor_count": 1, "price_spread": 0.0}
        pricing = agent._compute_pricing(wholesale, retail, combined, confidence_score=0.3, category_policy=agent.category_policies["unknown"])
        self.assertEqual(pricing["policy"], "insufficient_data")
        self.assertEqual(pricing["recommended_buy"], 0.0)

    def test_no_retail_uses_safe_low_confidence_path(self):
        agent = self.build_agent()
        wholesale = agent._compute_market_metrics(
            [{"price_pkr": p, "platform": "made_in_china", "supplier_or_seller": str(p)} for p in [700, 720, 750]],
            role="wholesale",
        )
        retail = agent._compute_market_metrics([], role="retail")
        combined = {
            "has_both_sources": False,
            "platform_count": 1,
            "vendor_count": 3,
            "price_spread": 0.0,
            "is_sparse_data": True,
        }
        pricing = agent._compute_pricing(wholesale, retail, combined, confidence_score=0.4, category_policy=agent.category_policies["unknown"])
        self.assertEqual(pricing["policy"], "hybrid_ml_sanity_low_confidence")
        self.assertTrue(pricing["sanity_adjustments"]["low_data_adjustment_applied"])

    def test_analyze_persists_one_analytics_row_per_cluster_and_recommendation(self):
        agent = self.build_agent()
        nlp_output = {
            "clusters": [
                {
                    "cluster_id": "cluster-1",
                    "db_cluster_id": "db-cluster-1",
                    "canonical_title": "A9 Mini Camera",
                    "records": [
                        {
                            "source_type": "wholesale",
                            "price_pkr": 500,
                            "platform": "made_in_china",
                            "supplier_or_seller": "factory-a",
                        },
                        {
                            "source_type": "wholesale",
                            "price_pkr": 550,
                            "platform": "made_in_china",
                            "supplier_or_seller": "factory-b",
                        },
                        {
                            "source_type": "retail",
                            "price_pkr": 1200,
                            "platform": "daraz",
                            "supplier_or_seller": "seller-a",
                        },
                        {
                            "source_type": "retail",
                            "price_pkr": 1250,
                            "platform": "daraz",
                            "supplier_or_seller": "seller-b",
                        },
                    ],
                }
            ]
        }
        result = agent.analyze("A9 Mini camera", "camera", nlp_output, pipeline_run_id="run-1")
        self.assertGreater(result["recommended_sell_price_pkr"], result["recommended_buy_price_pkr"])
        self.assertEqual(len(agent.db.analytics_rows), 1)
        self.assertEqual(len(agent.db.recommendations), 1)
        self.assertIn(agent.db.analytics_rows[0]["analysis_status"], {"completed", "low_confidence"})
        metadata = agent.db.analytics_rows[0]["analysis_metadata"]
        self.assertIn("pricing_sanity", metadata)
        self.assertIn("model_predicted_sell", metadata)
        self.assertIn("detected_category", metadata)
        self.assertIn("category_policy_used", metadata)
        self.assertIn("max_margin_percent_used", metadata)


    def test_commercial_intelligence_returns_four_pricing_modes(self):
        agent = self.build_agent()
        wholesale = agent._compute_market_metrics(
            [{"price_pkr": p, "platform": "made_in_china", "supplier_or_seller": str(p)} for p in [2800, 2900, 3000, 3100]],
            role="wholesale",
        )
        retail = agent._compute_market_metrics(
            [{"price_pkr": p, "platform": "daraz", "supplier_or_seller": str(p)} for p in [3950, 4050, 4150, 4250, 4350, 4450]],
            role="retail",
        )
        combined = agent._compute_combined_metrics(
            self.build_cluster([2800, 2900, 3000, 3100], [3950, 4050, 4150, 4250, 4350, 4450]),
            [],
            [],
            wholesale,
            retail,
        )
        pricing = agent._compute_pricing(
            wholesale,
            retail,
            combined,
            confidence_score=0.83,
            category_policy=agent.category_policies["headsets"],
        )

        snapshot = agent._build_commercial_intelligence(
            product_name="HyperX Cloud III",
            category="headset",
            wholesale_metrics=wholesale,
            retail_metrics=retail,
            combined_metrics=combined,
            pricing=pricing,
            confidence_score=0.83,
            low_sample_warning=False,
        )

        self.assertEqual(
            set(snapshot["pricing_modes"]),
            {"competitive", "balanced", "premium", "psychological"},
        )
        self.assertIn(snapshot["primary_pricing_mode"], snapshot["pricing_modes"])
        self.assertEqual(len(snapshot["alternate_pricing_modes"]), 3)

    def test_primary_mode_changes_with_market_shape(self):
        agent = self.build_agent()

        weak_wholesale = agent._compute_market_metrics(
            [{"price_pkr": p, "platform": "made_in_china", "supplier_or_seller": str(i)} for i, p in enumerate([2800, 3200])],
            role="wholesale",
        )
        weak_retail = agent._compute_market_metrics(
            [{"price_pkr": p, "platform": "daraz", "supplier_or_seller": str(i)} for i, p in enumerate([3600, 4700, 5200])],
            role="retail",
        )
        weak_combined = agent._compute_combined_metrics(
            self.build_cluster([2800, 3200], [3600, 4700, 5200]),
            [],
            [],
            weak_wholesale,
            weak_retail,
        )
        weak_pricing = agent._compute_pricing(
            weak_wholesale,
            weak_retail,
            weak_combined,
            confidence_score=0.46,
            category_policy=agent.category_policies["headsets"],
        )
        weak_market = agent._build_commercial_intelligence(
            product_name="Wireless headset",
            category="headset",
            wholesale_metrics=weak_wholesale,
            retail_metrics=weak_retail,
            combined_metrics=weak_combined,
            pricing=weak_pricing,
            confidence_score=0.46,
            low_sample_warning=True,
        )

        strong_wholesale = agent._compute_market_metrics(
            [{"price_pkr": p, "platform": "made_in_china", "supplier_or_seller": str(i)} for i, p in enumerate([2600, 2650, 2700, 2750, 2800])],
            role="wholesale",
        )
        strong_retail = agent._compute_market_metrics(
            [{"price_pkr": p, "platform": "daraz", "supplier_or_seller": str(i)} for i, p in enumerate([4300, 4320, 4350, 4380, 4400, 4420, 4450])],
            role="retail",
        )
        strong_combined = agent._compute_combined_metrics(
            self.build_cluster([2600, 2650, 2700, 2750, 2800], [4300, 4320, 4350, 4380, 4400, 4420, 4450]),
            [],
            [],
            strong_wholesale,
            strong_retail,
        )
        strong_pricing = agent._compute_pricing(
            strong_wholesale,
            strong_retail,
            strong_combined,
            confidence_score=0.88,
            category_policy=agent.category_policies["headsets"],
        )
        strong_market = agent._build_commercial_intelligence(
            product_name="Wireless headset",
            category="headset",
            wholesale_metrics=strong_wholesale,
            retail_metrics=strong_retail,
            combined_metrics=strong_combined,
            pricing=strong_pricing,
            confidence_score=0.88,
            low_sample_warning=False,
        )

        self.assertNotEqual(
            weak_market["primary_pricing_mode"],
            strong_market["primary_pricing_mode"],
        )


if __name__ == "__main__":
    unittest.main()
