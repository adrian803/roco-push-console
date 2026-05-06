from __future__ import annotations

import unittest

from roco_serverchan_notifier import app as app_module
from roco_serverchan_notifier.merchant_message import (
    build_merchant_markdown,
    build_notification_message,
    product_summary,
)


class MerchantMessageTests(unittest.TestCase):
    def test_build_merchant_markdown_keeps_price_display_behavior(self):
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
            ],
        }

        markdown = build_merchant_markdown(processed, include_price_info=True)

        self.assertIn("轮次：3/4 · 剩余：3小时", markdown)
        self.assertIn("1. 绝缘球", markdown)
        self.assertIn("价格：未收录", markdown)
        self.assertIn("2. 炫彩精灵蛋", markdown)
        self.assertIn("数量：1", markdown)
        self.assertIn("单价：1,600,000", markdown)
        self.assertIn("合计：1,600,000（160万洛克贝）", markdown)

    def test_build_merchant_markdown_omits_price_by_default(self):
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

    def test_build_notification_message_uses_summary_and_markdown(self):
        processed = {
            "round_info": {"current": 3, "total": 4, "countdown": "3小时"},
            "products": [{"name": "魔力果", "time_label": "16:00 - 20:00"}],
        }

        message = build_notification_message(processed, include_price_info=False)

        self.assertEqual(message.title, "远行商人已刷新")
        self.assertEqual(message.body, "1件商品：魔力果")
        self.assertTrue(message.markdown.startswith("轮次：3/4 · 剩余：3小时\n\n1. 魔力果"))

    def test_app_reexports_build_merchant_markdown_for_compatibility(self):
        self.assertIs(app_module.build_merchant_markdown, build_merchant_markdown)
        self.assertEqual(product_summary([]), "当前暂无活跃商品")


if __name__ == "__main__":
    unittest.main()
