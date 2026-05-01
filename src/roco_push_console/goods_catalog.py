from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Any


@lru_cache(maxsize=1)
def goods_price_info_by_name() -> dict[str, dict[str, int]]:
    payload = json.loads(
        resources.files(__package__).joinpath("random_goods_conf.json").read_text(encoding="utf-8")
    )
    rows = payload.get("RocoDataRows", {})
    if not isinstance(rows, dict):
        return {}

    result: dict[str, dict[str, int]] = {}
    for row in rows.values():
        if not isinstance(row, dict) or row.get("enable") is False:
            continue
        name = str(row.get("goods_name") or "").strip()
        price = _to_int(row.get("price"))
        buy_limit_num = _to_int(row.get("buy_limit_num"))
        if name and price is not None and buy_limit_num is not None:
            result[name] = {"price": price, "buy_limit_num": buy_limit_num}
    return result


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
