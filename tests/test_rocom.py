from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

try:
    from .helpers import RocoTestCase, load_cross_runtime_fixture
except ImportError:
    from helpers import RocoTestCase, load_cross_runtime_fixture

from roco_serverchan_notifier.merchant_message import build_merchant_markdown
from roco_serverchan_notifier.provider_specs import (
    PROVIDER_TYPES,
    provider_env_binding_names,
    provider_env_fields,
    provider_env_id,
    provider_required_fields,
    provider_secret_fields,
    validate_provider_manifest,
)
from roco_serverchan_notifier.rocom import process_merchant_data
from roco_serverchan_notifier.time_utils import get_round_info



class RocomTests(RocoTestCase):
    def test_round_info_before_open(self):
        now = datetime(2026, 4, 26, 7, 30, tzinfo=timezone(timedelta(hours=8)))
        self.assertEqual(get_round_info(now)["current"], "未开放")

    def test_process_merchant_data_filters_current_round(self):
        tz = timezone(timedelta(hours=8))
        now = datetime(2026, 4, 26, 9, 0, tzinfo=tz)
        active_start = int(datetime(2026, 4, 26, 8, 0, tzinfo=tz).timestamp() * 1000)
        active_end = int(datetime(2026, 4, 26, 12, 0, tzinfo=tz).timestamp() * 1000)
        expired_start = int(datetime(2026, 4, 26, 0, 0, tzinfo=tz).timestamp() * 1000)
        expired_end = int(datetime(2026, 4, 26, 4, 0, tzinfo=tz).timestamp() * 1000)
        data = {
            "merchantActivities": [
                {
                    "name": "远行商人",
                    "get_props": [
                        {"name": "当前商品", "start_time": active_start, "end_time": active_end},
                        {"name": "过期商品", "start_time": expired_start, "end_time": expired_end},
                    ],
                    "get_pets": [],
                }
            ]
        }

        processed = process_merchant_data(data, now=now)

        self.assertEqual(processed["product_count"], 1)
        self.assertEqual(processed["products"][0]["name"], "当前商品")

    def test_process_merchant_data_enriches_known_goods_price_and_limit(self):
        tz = timezone(timedelta(hours=8))
        now = datetime(2026, 4, 26, 17, 0, tzinfo=tz)
        active_start = int(datetime(2026, 4, 26, 16, 0, tzinfo=tz).timestamp() * 1000)
        active_end = int(datetime(2026, 4, 26, 20, 0, tzinfo=tz).timestamp() * 1000)

        processed = process_merchant_data(
            {
                "merchantActivities": [
                    {
                        "name": "远行商人",
                        "get_props": [
                            {
                                "name": "黑晶琉璃",
                                "start_time": active_start,
                                "end_time": active_end,
                            }
                        ],
                        "get_pets": [],
                    }
                ]
            },
            now=now,
        )

        product = processed["products"][0]
        self.assertEqual(product["price"], 1000)
        self.assertEqual(product["buy_limit_num"], 100)

    def test_process_merchant_data_enriches_alias_and_preserves_missing_price(self):
        tz = timezone(timedelta(hours=8))
        now = datetime(2026, 4, 26, 17, 0, tzinfo=tz)
        active_start = int(datetime(2026, 4, 26, 16, 0, tzinfo=tz).timestamp() * 1000)
        active_end = int(datetime(2026, 4, 26, 20, 0, tzinfo=tz).timestamp() * 1000)

        processed = process_merchant_data(
            {
                "merchantActivities": [
                    {
                        "name": "远行商人",
                        "get_props": [
                            {"name": "绝缘球", "start_time": active_start, "end_time": active_end},
                            {"name": "炫彩精灵蛋", "start_time": active_start, "end_time": active_end},
                            {"name": "魔力果", "start_time": active_start, "end_time": active_end},
                        ],
                        "get_pets": [],
                    }
                ]
            },
            now=now,
        )

        products = {product["name"]: product for product in processed["products"]}
        self.assertNotIn("price", products["绝缘球"])
        self.assertEqual(products["炫彩精灵蛋"]["price"], 1600000)
        self.assertEqual(products["炫彩精灵蛋"]["buy_limit_num"], 1)
        self.assertEqual(products["魔力果"]["price"], 6000)
        self.assertEqual(products["魔力果"]["buy_limit_num"], 20)

    def test_merchant_markdown_contains_products(self):
        processed = {
            "round_info": {"current": 1, "total": 4, "countdown": "3小时"},
            "products": [{"name": "咕噜球", "time_label": "08:00 - 12:00"}],
        }

        markdown = build_merchant_markdown(processed)

        self.assertIn("咕噜球", markdown)
        self.assertIn("轮次：1/4 · 剩余：3小时", markdown)

    def test_merchant_markdown_can_include_price_and_quantity(self):
        processed = {
            "round_info": {"current": 3, "total": 4, "countdown": "3小时"},
            "products": [
                {
                    "name": "黑晶琉璃",
                    "time_label": "16:00 - 20:00",
                    "price": 1000,
                    "buy_limit_num": 100,
                }
            ],
        }

        markdown = build_merchant_markdown(processed, include_price_info=True)

        self.assertIn("1. 黑晶琉璃", markdown)
        self.assertIn("数量：100", markdown)
        self.assertIn("单价：1,000", markdown)
        self.assertIn("合计：100,000（10万洛克贝）", markdown)

    def test_merchant_markdown_marks_missing_prices_and_includes_quantity_one(self):
        processed = {
            "round_info": {"current": 3, "total": 4, "countdown": "3小时"},
            "products": [
                {"name": "绝缘球", "time_label": "08:00 - 23:59"},
                {
                    "name": "炫彩精灵蛋",
                    "time_label": "16:00 - 20:00",
                    "price": 1600000,
                    "buy_limit_num": 1,
                },
                {
                    "name": "魔力果",
                    "time_label": "16:00 - 20:00",
                    "price": 6000,
                    "buy_limit_num": 20,
                },
            ],
        }

        markdown = build_merchant_markdown(processed, include_price_info=True)

        self.assertIn("1. 绝缘球", markdown)
        self.assertIn("价格：未收录", markdown)
        self.assertIn("2. 炫彩精灵蛋", markdown)
        self.assertIn("单价：1,600,000", markdown)
        self.assertIn("3. 魔力果", markdown)
        self.assertIn("单价：6,000", markdown)
        self.assertIn("合计：120,000（12万洛克贝）", markdown)

    def test_merchant_markdown_omits_price_and_quantity_by_default(self):
        processed = {
            "round_info": {"current": 3, "total": 4, "countdown": "3小时"},
            "products": [
                {
                    "name": "黑晶琉璃",
                    "time_label": "16:00 - 20:00",
                    "price": 1000,
                    "buy_limit_num": 100,
                }
            ],
        }

        markdown = build_merchant_markdown(processed)

        self.assertIn("1. 黑晶琉璃", markdown)
        self.assertIn("时段：16:00 - 20:00", markdown)
        self.assertNotIn("单价：", markdown)


    def test_shared_price_markdown_fixture_matches_python(self):
        fixture = load_cross_runtime_fixture()
        case = fixture["price_markdown"]

        markdown = build_merchant_markdown(case["python_processed"], include_price_info=True)

        for expected_line in case["expected_lines"]:
            self.assertIn(expected_line, markdown)

    def test_shared_provider_specs_fixture_matches_python(self):
        fixture = load_cross_runtime_fixture()

        for case in fixture["provider_specs"]:
            self.assertEqual(sorted(provider_secret_fields(case["type"])), sorted(case["secret_fields"]))
            self.assertEqual(sorted(provider_required_fields(case["type"])), sorted(case["required_fields"]))

    def test_shared_provider_manifest_exposes_env_mapping(self):
        for provider_type, spec in PROVIDER_TYPES.items():
            self.assertEqual(provider_env_id(provider_type), spec["envId"])
            self.assertEqual(provider_env_fields(provider_type), spec["envVars"])

    def test_provider_env_binding_names_are_derived_from_manifest(self):
        expected: list[str] = []
        for spec in PROVIDER_TYPES.values():
            for env_name in spec["envVars"].values():
                if env_name not in expected:
                    expected.append(env_name)

        self.assertEqual(provider_env_binding_names(), expected)

    def test_provider_manifest_validation_rejects_unmapped_env_vars(self):
        with self.assertRaises(ValueError):
            validate_provider_manifest(
                {
                    "providers": [
                        {
                            "type": "broken",
                            "label": "Broken",
                            "description": "Broken provider",
                            "envId": "broken-env",
                            "envVars": {"token": "BROKEN_TOKEN"},
                            "fields": [{"name": "other", "label": "Other"}],
                        }
                    ]
                }
            )


if __name__ == "__main__":
    unittest.main()
