import unittest
import types
from unittest.mock import patch

from app.services import scraper_service
from app.services.ecdb import ECDB


class ScraperSubsystemTests(unittest.TestCase):
    def test_modular_sieve_filters_missing_accessories_and_duplicates(self):
        raw = {
            "product_name": "logitech k380",
            "links_used": {},
            "wholesale": {
                "made_in_china": [
                    {
                        "platform": "made_in_china",
                        "title": "Logitech K380 Wireless Keyboard",
                        "supplier": "MIC Supplier",
                        "unit_price": 10.0,
                        "currency": "USD",
                        "moq": 10,
                        "source_url": "https://mic/item1",
                    },
                    {
                        "platform": "made_in_china",
                        "title": "Replacement case for Logitech K380",
                        "supplier": "MIC Supplier",
                        "unit_price": 1.0,
                        "currency": "USD",
                        "moq": 50,
                        "source_url": "https://mic/item2",
                    },
                ],
            },
            "retail": [
                {
                    "seller": "Daraz Seller",
                    "platform": "daraz",
                    "title": "Logitech K380 Wireless Keyboard",
                    "list_price": 4999,
                    "promo": "",
                    "url": "https://daraz/item1",
                    "detail": None,
                },
                {
                    "seller": "Daraz Seller",
                    "platform": "daraz",
                    "title": "Logitech K380 Wireless Keyboard",
                    "list_price": 4999,
                    "promo": "",
                    "url": "https://daraz/item1",
                    "detail": None,
                },
                {
                    "seller": "Daraz Seller",
                    "platform": "daraz",
                    "title": "Replacement case for Logitech K380",
                    "list_price": 999,
                    "promo": "",
                    "url": "https://daraz/item2",
                    "detail": None,
                },
            ],
        }

        filtered = scraper_service.modular_sieve_filter(raw, "logitech k380", "keyboard")

        self.assertEqual(len(filtered["wholesale"]["made_in_china"]), 1)
        self.assertEqual(len(filtered["retail"]), 1)
        self.assertGreaterEqual(filtered["sieve_stats"]["constraint_rejected"], 1)
        self.assertGreaterEqual(filtered["sieve_stats"]["duplicate_rejected"], 1)

    def test_modular_sieve_rejects_titles_that_only_shuffle_query_tokens(self):
        raw = {
            "product_name": "HyperX Cloud III",
            "links_used": {},
            "wholesale": {},
            "retail": [
                {
                    "seller": "Daraz Seller",
                    "platform": "daraz",
                    "title": "Wireless Gaming Headset Cloud III by HyperX",
                    "list_price": 34999,
                    "promo": "",
                    "url": "https://daraz/item1",
                    "detail": None,
                }
            ],
        }

        filtered = scraper_service.modular_sieve_filter(raw, "HyperX Cloud III", "headset")

        self.assertEqual(len(filtered["retail"]), 0)

    def test_generic_search_extractor_parses_price_and_links(self):
        html = """
        <html><body>
            <div class="card">
                <a href="/product/1">Logitech K380 Wireless Keyboard</a>
                <span>Rs. 4,999</span>
            </div>
        </body></html>
        """

        with patch("app.services.scraper_service._fetch_html", return_value=scraper_service.BeautifulSoup(html, "html.parser")):
            results = scraper_service._generic_extract_search_results(
                "https://example.com/search",
                "mega.pk",
                "retail",
                max_items=5,
            )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Logitech K380 Wireless Keyboard")
        self.assertEqual(results[0]["list_price"], 4999.0)

    def test_execute_job_group_is_fault_tolerant(self):
        jobs = {
            "ok": (lambda: [{"title": "item"}], "https://ok"),
            "bad": (lambda: (_ for _ in ()).throw(RuntimeError("boom")), "https://bad"),
        }

        results = scraper_service._execute_job_group(jobs, use_parallel=True)

        self.assertEqual(len(results["ok"][0]), 1)
        self.assertEqual(results["bad"][0], [])

    def test_scrape_product_platforms_orchestrates_verified_sources(self):
        with (
            patch(
                "app.services.scraper_service._scrape_made_in_china_listing_with_diagnostics",
                return_value=(
                    [{"platform": "made_in_china", "title": "logitech k380 keyboard", "supplier": "MIC", "unit_price": 10.0, "currency": "USD", "moq": 10, "source_url": "mic"}],
                    "mic-search",
                    {"accepted_items": 1},
                ),
            ),
            patch("app.services.scraper_service.scrape_daraz_listing", return_value=([{"seller": "Daraz", "platform": "daraz", "title": "logitech k380 keyboard", "list_price": 5300.0, "promo": "", "url": "daraz", "detail": None}], "daraz-search")),
        ):
            result = scraper_service.scrape_product_platforms("logitech k380", "keyboard", use_parallel=False)

        self.assertEqual(len(result["wholesale"]["made_in_china"]), 1)
        self.assertEqual(len(result["retail"]), 1)
        self.assertEqual(result["retail"][0]["platform"], "daraz")
        self.assertIn("daraz_search", result["links_used"])
        self.assertIn("made_in_china_search", result["links_used"])

    def test_scrape_mic_listing_parses_search_cards(self):
        html = """
        <html><body>
            <div class="card">
                <h2><a href="https://supplier.en.made-in-china.com/product/abc/Test.html">HyperX Cloud III Wireless Gaming Headset</a></h2>
                <div>US$50.00-60.00</div>
                <div>10 Pieces (MOQ)</div>
                <a href="https://supplier.en.made-in-china.com">Shenzhen Audio Technology Co., Ltd.</a>
                <div>Guangdong, China</div>
            </div>
        </body></html>
        """

        with patch("app.services.scraper_service._fetch_html", return_value=scraper_service.BeautifulSoup(html, "html.parser")):
            results, search_url = scraper_service.scrape_made_in_china_listing("HyperX Cloud III", max_items=5)

        self.assertEqual(search_url, scraper_service._mic_listing_search_urls("HyperX Cloud III")[0])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["supplier"], "Shenzhen Audio Technology Co., Ltd.")
        self.assertEqual(results[0]["moq"], 10)
        self.assertEqual(results[0]["unit_price"], 50.0)
        self.assertEqual(results[0]["currency"], "USD")

    def test_mic_supplier_cleanup_removes_card_noise(self):
        raw_supplier = (
            "Shenzhen Borange Technology Co., Ltd. Shenzhen Borange Technology Co., Ltd. "
            "Gold Member Audited Supplier Guangdong, China"
        )
        cleaned = scraper_service._clean_supplier_name(raw_supplier)
        self.assertEqual(cleaned, "Shenzhen Borange Technology Co., Ltd.")

    def test_wholesale_semantic_match_rejects_out_of_order_noise(self):
        self.assertTrue(scraper_service._wholesale_semantic_match("HyperX Cloud III Wireless Gaming Headset", "HyperX Cloud III"))
        self.assertFalse(scraper_service._wholesale_semantic_match("Cloud HyperX Wired Headset III", "HyperX Cloud III"))

    def test_wholesale_semantic_match_is_case_insensitive(self):
        self.assertTrue(
            scraper_service._wholesale_semantic_match(
                "Hyperx Cloud III Wireless Gaming Headset",
                "HyperX cloud III",
            )
        )
        self.assertTrue(
            scraper_service.strict_name_match(
                "hyperx cloud iii wireless gaming headset",
                "HyperX Cloud III",
            )
        )

    def test_tire_family_titles_allow_size_details_and_tyres_spelling(self):
        raw = {
            "product_name": "Bridgestone Tire",
            "links_used": {},
            "wholesale": {
                "made_in_china": [
                    {
                        "platform": "made_in_china",
                        "title": "Bridgestone EP150 Ecopia 205/60/16 Tyre",
                        "supplier": "Supplier 1",
                        "unit_price": 100.0,
                        "currency": "USD",
                        "moq": 10,
                        "source_url": "https://mic/item1",
                    }
                ]
            },
            "retail": [
                {
                    "seller": "Daraz Seller",
                    "platform": "daraz",
                    "title": "Bridgestone EP150 Ecopia 205/60/16 Tyre",
                    "list_price": 35000,
                    "promo": "",
                    "url": "https://daraz/item1",
                    "detail": None,
                }
            ],
        }

        filtered = scraper_service.modular_sieve_filter(raw, "Bridgestone Tire", "tyres")

        self.assertEqual(len(filtered["wholesale"]["made_in_china"]), 1)
        self.assertEqual(len(filtered["retail"]), 1)
        self.assertTrue(scraper_service.strict_name_match("Bridgestone EP150 Ecopia 205/60/16 Tyre", "Bridgestone Tire"))
        self.assertIsNone(
            scraper_service.constraint_failure_reason(
                {"platform": "made_in_china", "title": "Bridgestone EP150 Ecopia 205/60/16 Tyre"},
                "Bridgestone Tire",
                "tyres",
            )
        )

    def test_tire_family_titles_without_tire_word_still_match_size_and_model_signals(self):
        raw = {
            "product_name": "Bridgestone Tire",
            "links_used": {},
            "wholesale": {
                "made_in_china": [
                    {
                        "platform": "made_in_china",
                        "title": "Bridgestone EP150 Ecopia 205/60/16",
                        "supplier": "Supplier 1",
                        "unit_price": 100.0,
                        "currency": "USD",
                        "moq": 10,
                        "source_url": "https://mic/item1",
                    }
                ]
            },
            "retail": [
                {
                    "seller": "Daraz Seller",
                    "platform": "daraz",
                    "title": "Bridgestone Tire| 205/60/16 EP150 Ecopia | Tyres for car 16 inch | Premium Quality Car Tyres (Single piece price )",
                    "list_price": 35000,
                    "promo": "",
                    "url": "https://daraz/item1",
                    "detail": None,
                }
            ],
        }

        filtered = scraper_service.modular_sieve_filter(raw, "Bridgestone Tire", "tyres")

        self.assertEqual(len(filtered["wholesale"]["made_in_china"]), 1)
        self.assertEqual(len(filtered["retail"]), 1)
        self.assertTrue(scraper_service._tire_family_title_match("Bridgestone Tire| 205/60/16 EP150 Ecopia | Tyres for car 16 inch | Premium Quality Car Tyres (Single piece price )", "Bridgestone Tire"))
        self.assertIsNone(
            scraper_service.constraint_failure_reason(
                {"platform": "daraz", "title": "Bridgestone Tire| 205/60/16 EP150 Ecopia | Tyres for car 16 inch | Premium Quality Car Tyres (Single piece price )"},
                "Bridgestone Tire",
                "tyres",
            )
        )
    def test_dependency_pattern_ignores_for_inside_regular_words(self):
        title = "U39 Wireless Gaming Earbuds_Bluetooth Headphones Headset_ENC Noise Cancelling Bluetooth Earphones_Latest 5.3 Bluethoot Chip Powerful Performance Fast Transmission_Long Battery True Stereo Earbuds"
        self.assertFalse(scraper_service._contains_dependency_pattern(title))
        self.assertIsNone(
            scraper_service.constraint_failure_reason(
                {"platform": "daraz", "title": title},
                "U39 Wireless Gaming Earbuds",
                "earbuds",
            )
        )

    def test_audio_family_titles_allow_long_marketplace_descriptions(self):
        title = "U39 Wireless Gaming Earbuds_Bluetooth Headphones Headset_ENC Noise Cancelling Bluetooth Earphones_Latest 5.3 Bluethoot Chip Powerful Performance Fast Transmission_Long Battery True Stereo Earbuds"
        self.assertFalse(scraper_service._too_broad_title(title, "U39 Wireless Gaming Earbuds", "earbuds"))
        self.assertIsNone(
            scraper_service.constraint_failure_reason(
                {"platform": "daraz", "title": title},
                "U39 Wireless Gaming Earbuds",
                "earbuds",
            )
        )


    def test_accessory_filters_reject_broad_dependency_titles(self):
        self.assertTrue(
            scraper_service.is_accessory(
                "HyperX Cloud III replacement ear pads for gaming headset",
                "HyperX Cloud III",
                "headset",
            )
        )
        self.assertTrue(
            scraper_service.is_accessory(
                "Gaming accessory bundle for HyperX Cloud III headset stand case combo",
                "HyperX Cloud III",
                "headset",
            )
        )

    def test_modular_sieve_reports_constraint_reasons(self):
        raw = {
            "product_name": "HyperX Cloud III",
            "links_used": {},
            "wholesale": {
                "made_in_china": [
                    {
                        "platform": "made_in_china",
                        "title": "Replacement ear pads for HyperX Cloud III headset",
                        "supplier": "Supplier 1",
                        "unit_price": 5.0,
                        "currency": "USD",
                        "moq": 10,
                        "source_url": "https://mic/item1",
                    }
                ]
            },
            "retail": [],
        }

        filtered = scraper_service.modular_sieve_filter(raw, "HyperX Cloud III", "headset")

        self.assertEqual(filtered["sieve_stats"]["constraint_reasons"]["dependency_pattern"], 1)
        self.assertEqual(
            filtered["sieve_stats"]["platform_breakdown"]["wholesale"]["made_in_china"]["constraint_reasons"]["dependency_pattern"],
            1,
        )

    def test_short_model_query_allows_category_specific_longer_title(self):
        self.assertFalse(
            scraper_service.is_accessory(
                "E88 PRO Drone 4K HD Dual Camera Drone Aerial Photography Long Endurance Fixed Height Remote Control Aircraft Foldable Mini Drone",
                "e88 pro",
                "drone",
            )
        )

    def test_bundle_query_does_not_reject_valid_set_title_as_too_broad(self):
        reason = scraper_service.constraint_failure_reason(
            {
                "platform": "made_in_china",
                "title": "Natural Green Aventurine Jade Stone Facial Skincare Massage Jade Roller and Gua Sha Set",
            },
            "jade roller and gua sha",
            "beauty",
        )
        self.assertNotEqual(reason, "too_broad")

    def test_modular_sieve_caps_each_platform_to_top_five_matches(self):
        wholesale_items = []
        for index in range(7):
            wholesale_items.append(
                {
                    "platform": "made_in_china",
                    "title": f"HyperX Cloud III Headset Gen{index}",
                    "supplier": f"Supplier {index}",
                    "unit_price": 20.0 + index,
                    "currency": "USD",
                    "moq": 10,
                    "source_url": f"https://mic/item{index}",
                }
            )

        raw = {
            "product_name": "HyperX Cloud III",
            "links_used": {},
            "wholesale": {"made_in_china": wholesale_items},
            "retail": [],
        }

        filtered = scraper_service.modular_sieve_filter(raw, "HyperX Cloud III", "headset")

        self.assertEqual(len(filtered["wholesale"]["made_in_china"]), 5)

    def test_mic_query_variants_help_generic_model_queries(self):
        variants = scraper_service._mic_query_variants("p47 wireless headphones", "headset")
        self.assertIn("p47 headset", [variant.lower() for variant in variants])
        self.assertIn("p47 headphones", [variant.lower() for variant in variants])

    def test_mic_query_variants_use_drone_variants_for_drone_category(self):
        variants = scraper_service._mic_query_variants("e88 pro", "drone")
        lowered = [variant.lower() for variant in variants]
        self.assertIn("e88 drone", lowered)
        self.assertIn("e88 quadcopter", lowered)
        self.assertNotIn("e88 headset", lowered)

    def test_mic_diagnostics_show_semantic_acceptance_for_p47_style_title(self):
        html = """
        <html><body>
            <div class="card">
                <h2><a href="https://supplier.en.made-in-china.com/product/abc/Test.html">P47 Wireless Headphones Bluetooth Stereo Foldable Headset</a></h2>
                <div>US$0.55-0.75</div>
                <div>100 Pieces (MOQ)</div>
                <a href="https://supplier.en.made-in-china.com">Anhui Xianwei E-Commerce Co., Ltd.</a>
                <div>Anhui, China</div>
            </div>
        </body></html>
        """
        with patch("app.services.scraper_service._fetch_html", return_value=scraper_service.BeautifulSoup(html, "html.parser")):
            results, _search_url, diagnostics = scraper_service._scrape_made_in_china_listing_with_diagnostics("p47 wireless headphones", category="headset", max_items=5)

        self.assertEqual(len(results), 1)
        self.assertEqual(diagnostics["accepted_items"], 1)

    def test_mic_allows_missing_origin_when_title_and_price_are_valid(self):
        html = """
        <html><body>
            <div class="card">
                <h2><a href="https://supplier.en.made-in-china.com/product/abc/Test.html">HyperX Cloud III Wireless Gaming Headset</a></h2>
                <div>US$50.00-60.00</div>
                <div>10 Pieces (MOQ)</div>
                <a href="https://supplier.en.made-in-china.com">Shenzhen Audio Technology Co., Ltd.</a>
            </div>
        </body></html>
        """
        with patch("app.services.scraper_service._fetch_html", return_value=scraper_service.BeautifulSoup(html, "html.parser")):
            results, _search_url, diagnostics = scraper_service._scrape_made_in_china_listing_with_diagnostics("HyperX Cloud III", max_items=5)

        self.assertEqual(len(results), 1)
        self.assertGreaterEqual(diagnostics["cards_missing_supplier_or_origin"], 1)
        self.assertEqual(diagnostics["accepted_items"], 1)

    def test_post_process_preserves_wholesale_diagnostics(self):
        raw = {
            "product_name": "hyperx cloud iii",
            "links_used": {},
            "wholesale": {
                "made_in_china": [
                    {
                        "platform": "made_in_china",
                        "title": "HyperX Cloud III Wireless Gaming Headset",
                        "supplier": "MIC Supplier",
                        "unit_price": 50.0,
                        "currency": "USD",
                        "moq": 10,
                        "source_url": "https://mic/item1",
                    }
                ]
            },
            "retail": [],
            "wholesale_diagnostics": {"made_in_china": {"accepted_items": 1}},
        }

        filtered = scraper_service._post_process_scrape_result(raw, "hyperx cloud iii", "headset")

        self.assertIn("wholesale_diagnostics", filtered)
        self.assertEqual(filtered["wholesale_diagnostics"]["made_in_china"]["accepted_items"], 1)

    def test_extract_daraz_api_items_parses_signed_search_payload(self):
        payload = {
            "data": {
                "mods": {
                    "listItems": [
                        {
                            "name": "HyperX Cloud III Wireless - Gaming Headset",
                            "priceShow": "Rs. 25,000",
                            "discount": "5% Off",
                            "sellerName": "Shinwari Mart .1",
                            "productUrl": "//www.daraz.pk/products/x-iii-i809525243-s3712347605.html",
                            "inStock": True,
                            "brandName": "HyperX",
                            "location": "Khyber Pakhtunkhwa",
                            "description": ["Ultra-Clear Microphone", "120-hour battery"],
                        }
                    ]
                }
            }
        }

        items = scraper_service._extract_daraz_api_items(payload, max_items=5)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["seller"], "Shinwari Mart .1")
        self.assertEqual(items[0]["list_price"], 25000.0)
        self.assertTrue(items[0]["url"].startswith("https://www.daraz.pk/products/"))
        self.assertEqual(items[0]["detail"]["brand_name"], "HyperX")

    def test_scrape_product_platforms_can_request_normalized_output_without_persist(self):
        with (
            patch("app.services.scraper_service.scrape_daraz_listing", return_value=([], "daraz-search")),
        ):
            fake_module = types.ModuleType("app.services.nlp_agent")
            mocked_process = unittest.mock.Mock(return_value={"products": [], "stats": {"persisted_count": 0}})

            class FakeNLPAgent:
                def process(self, *args, **kwargs):
                    return mocked_process(*args, **kwargs)

            fake_module.NLPAgent = FakeNLPAgent

            with patch.dict("sys.modules", {"app.services.nlp_agent": fake_module}):
                result = scraper_service.scrape_product_platforms(
                    "logitech k380",
                    "keyboard",
                    normalize=True,
                    persist=False,
                    use_parallel=False,
                )

        self.assertIn("normalized_output", result)
        mocked_process.assert_called_once()
        self.assertFalse(result["persisted"])

    def test_ecdb_compatibility_wrappers_delegate_to_existing_methods(self):
        db = ECDB.__new__(ECDB)
        db.get_wholesale_products_by_query = lambda product_name, category: [{"product_name": product_name, "category": category}]
        db.get_retail_products_by_query = lambda product_name, category: [{"product_name": product_name, "category": category}]
        db.get_wholesale_products_by_category = lambda category, limit=500: [{"category": category, "limit": limit}]
        db.get_retail_products_by_category = lambda category, limit=500: [{"category": category, "limit": limit}]

        self.assertEqual(len(db.get_wholesale_by_query("p", "c")), 1)
        self.assertEqual(len(db.get_retail_by_query("p", "c")), 1)
        self.assertEqual(db.get_wholesale_by_category("c", 10)[0]["limit"], 10)
        self.assertEqual(db.get_retail_by_category("c", 20)[0]["limit"], 20)


if __name__ == "__main__":
    unittest.main()
