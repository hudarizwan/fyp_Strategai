import types
import unittest
from unittest.mock import Mock

from app.services.nlp_agent import NLPAgent
from app.agents.nlp_cleaning_agent import NLPCleaningAgent


class FakeDB:
    def __init__(self):
        self.inserted_products = []
        self.inserted_clusters = []

    def insert_product(self, payload):
        self.inserted_products.append(payload)
        return len(self.inserted_products)

    def upsert_cluster_summary(self, cluster):
        self.inserted_clusters.append(cluster)
        return cluster["cluster_id"]

    def get_stats(self):
        return {"ok": True}


class NLPAgentTests(unittest.TestCase):
    def build_agent(self):
        agent = NLPAgent.__new__(NLPAgent)
        agent.db = FakeDB()
        agent.similarity_threshold = 0.68
        agent.vectorizer = types.SimpleNamespace(fit_transform=lambda texts: [[1.0 if i == j else 0.5 for j, _ in enumerate(texts)] for i, _ in enumerate(texts)])
        return agent

    def test_clean_text_removes_noise(self):
        agent = self.build_agent()
        cleaned = NLPAgent.clean_text(agent, "NEW Logitech K380!!! Free Shipping in Pakistan")
        self.assertEqual(cleaned, "logitech k380 in")

    def test_normalize_record_standardizes_schema(self):
        agent = self.build_agent()
        record = agent.normalize_record(
            {
                "title": "Logitech K380 Wireless Keyboard",
                "platform": "daraz",
                "source_type": "retail",
                "price_original": 4999,
                "currency_original": "PKR",
                "supplier_or_seller": "Daraz Mall",
                "url": "https://example.com",
                "raw_payload": {"x": 1},
                "scrape_timestamp": "2025-01-01T00:00:00",
            },
            "logitech k380",
            "keyboard",
        )
        self.assertEqual(record["query"], "logitech k380")
        self.assertEqual(record["cleaned_title"], "logitech k380 wireless keyboard")
        self.assertEqual(record["price_pkr"], 4999.0)
        self.assertEqual(record["platform"], "daraz")

    def test_currency_normalization_supports_usd(self):
        agent = self.build_agent()
        self.assertEqual(agent.normalize_price(10, "USD"), 2800.0)

    def test_extract_brand_model_handles_roman_numeral_models(self):
        agent = self.build_agent()
        brand, model = agent.extract_brand_model("hyperx cloud iii wired gaming headset")
        self.assertEqual(brand, "hyperx")
        self.assertEqual(model, "cloud iii")

    def test_cluster_similar_products_groups_cross_platform_titles(self):
        agent = self.build_agent()
        records = [
            {
                "cleaned_title": "logitech k380 wireless keyboard",
                "normalized_text": "logitech k380 wireless keyboard keyboard",
                "brand": "logitech",
                "model": "k380",
            },
            {
                "cleaned_title": "logitech k380 bluetooth keyboard",
                "normalized_text": "logitech k380 bluetooth keyboard keyboard",
                "brand": "logitech",
                "model": "k380",
            },
        ]
        similarity = [[1.0, 0.8], [0.8, 1.0]]
        clusters = agent.cluster_similar_products(records, similarity, "logitech k380", "keyboard")
        self.assertEqual(len(clusters), 1)
        self.assertEqual(records[0]["cluster_id"], records[1]["cluster_id"])

    def test_build_cluster_entities_computes_aggregates(self):
        agent = self.build_agent()
        records = [
            {
                "cluster_id": "c1",
                "query": "logitech k380",
                "category": "keyboard",
                "cleaned_title": "logitech k380 wireless keyboard",
                "brand": "logitech",
                "model": "k380",
                "platform": "daraz",
                "source_type": "retail",
                "price_pkr": 5000.0,
                "supplier_or_seller": "Daraz",
                "raw_title": "Logitech K380 Wireless Keyboard",
                "url": "daraz",
            },
            {
                "cluster_id": "c1",
                "query": "logitech k380",
                "category": "keyboard",
                "cleaned_title": "logitech k380 wireless keyboard",
                "brand": "logitech",
                "model": "k380",
                "platform": "made_in_china",
                "source_type": "wholesale",
                "price_pkr": 2800.0,
                "supplier_or_seller": "MIC",
                "raw_title": "Logitech K380 Wireless Keyboard",
                "url": "mic",
            },
        ]
        clusters = [{"cluster_id": "c1", "record_indexes": [0, 1], "records": records}]
        entities = agent.build_cluster_entities(clusters, "logitech k380", "keyboard")
        self.assertEqual(entities[0]["min_retail_price"], 5000.0)
        self.assertEqual(entities[0]["vendor_count"], 2)
        self.assertEqual(entities[0]["platform_count"], 2)

    def test_persist_cleaned_results_saves_records_and_clusters(self):
        agent = self.build_agent()
        records = [
            {
                "query": "logitech k380",
                "category": "keyboard",
                "platform": "daraz",
                "source_type": "retail",
                "cleaned_title": "logitech k380 wireless keyboard",
                "brand": "logitech",
                "model": "k380",
                "price_pkr": 5000.0,
                "moq": 1,
                "supplier_or_seller": "Daraz",
                "seller_rating": 4.5,
                "vendor_location": None,
                "url": "daraz",
                "cluster_id": "c1",
                "raw_title": "Logitech K380 Wireless Keyboard",
                "delivery_info": None,
                "stock_status": "In stock",
                "raw_payload": {"id": 1},
                "normalized_text": "logitech k380 wireless keyboard keyboard",
                "currency_original": "PKR",
                "price_original": 5000.0,
            }
        ]
        clusters = [{"cluster_id": "c1", "query": "logitech k380", "category": "keyboard"}]
        persisted = agent.persist_cleaned_results(records, clusters)
        self.assertEqual(persisted["records"], 1)
        self.assertEqual(persisted["clusters"], 1)

    def test_process_returns_clean_data_and_clusters(self):
        agent = self.build_agent()
        agent.compute_similarity_matrix = Mock(return_value=[[1.0, 0.8], [0.8, 1.0]])
        raw_data = {
            "wholesale": {"made_in_china": [{"title": "Logitech K380 Wireless Keyboard", "unit_price": 10.0, "currency": "USD", "supplier": "MIC", "source_url": "mic"}]},
            "retail": [{"title": "Logitech K380 Wireless Keyboard", "list_price": 5000.0, "platform": "daraz", "seller": "Daraz", "url": "daraz", "detail": {}}],
        }
        result = agent.process(raw_data, "logitech k380", "keyboard", persist=True)
        self.assertIn("clusters", result)
        self.assertIn("clean_data", result)
        self.assertEqual(result["stats"]["cluster_count"], 1)


class NLPCleaningAgentTests(unittest.TestCase):
    def test_wrapper_agent_exports_nlp_output(self):
        wrapper = NLPCleaningAgent("nlp_1")
        wrapper.service = types.SimpleNamespace(
            process=lambda raw, product, category, persist=True: {
                "clean_data": {"wholesale": [], "retail": []},
                "clusters": [{"cluster_id": "c1"}],
                "records": [{"cluster_id": "c1"}],
                "persisted": True,
            }
        )
        wrapper.update_belief("scraped_data", {"wholesale": {}, "retail": []})
        wrapper.update_belief("product_name", "logitech k380")
        wrapper.update_belief("category", "keyboard")

        self.assertTrue(wrapper.execute_action("run_nlp_pipeline", {}))
        exported = wrapper.export_state()
        self.assertEqual(len(exported["clustered_products"]), 1)
        self.assertTrue(exported["db_saved"])


if __name__ == "__main__":
    unittest.main()
