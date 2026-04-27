from __future__ import annotations

from datetime import datetime
from typing import Any

import requests

from .time_utils import ensure_beijing_time, format_timestamp, get_round_info


def fetch_merchant_data(
    api_url: str,
    api_key: str,
    *,
    session: requests.Session | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    if not api_key:
        raise RuntimeError("缺少 ROCOM_API_KEY")

    client = session or requests.Session()
    response = client.get(api_url, headers={"X-API-Key": api_key}, timeout=timeout)
    response.raise_for_status()

    payload = response.json()
    if payload.get("code") != 0:
        raise RuntimeError(str(payload.get("message") or "接口返回失败"))

    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("接口返回 data 不是对象")
    return data


def _is_active_item(item: dict[str, Any], now_ms: int) -> bool:
    start_time = item.get("start_time")
    end_time = item.get("end_time")
    if not start_time or not end_time:
        return True

    try:
        return int(start_time) <= now_ms < int(end_time)
    except (TypeError, ValueError):
        return False


def process_merchant_data(
    data: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = ensure_beijing_time(now)
    now_ms = int(now.timestamp() * 1000)
    round_info = get_round_info(now)

    activities = data.get("merchantActivities") or []
    activity = activities[0] if activities else {}
    if not isinstance(activity, dict):
        activity = {}

    props = activity.get("get_props") or []
    pets = activity.get("get_pets") or []
    all_items = [item for item in [*props, *pets] if isinstance(item, dict)]

    active_products: list[dict[str, str]] = []
    for item in all_items:
        if not _is_active_item(item, now_ms):
            continue

        start_time = item.get("start_time")
        end_time = item.get("end_time")
        if start_time and end_time:
            time_label = f"{format_timestamp(start_time)} - {format_timestamp(end_time)}"
        else:
            time_label = "全天供应"

        active_products.append(
            {
                "name": str(item.get("name") or "未知"),
                "image": str(item.get("icon_url") or ""),
                "time_label": time_label,
            }
        )

    return {
        "title": activity.get("name", "远行商人"),
        "subtitle": activity.get("start_date", "每日 08:00 / 12:00 / 16:00 / 20:00 刷新"),
        "product_count": len(active_products),
        "round_info": round_info,
        "products": active_products,
        "_res_path": "",
        "background": "img/bg.C8CUoi7I.jpg",
        "titleIcon": True,
    }

