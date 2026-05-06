from __future__ import annotations

from .token import (
    send_bark,
    send_gotify,
    send_ntfy,
    send_pushplus,
    send_serverchan,
    send_wxpusher,
)
from .webhook import send_dingtalk_bot, send_feishu_bot
from .wecom import send_wecom_bot, send_wecomchan


PROVIDER_SENDERS = {
    "serverchan": send_serverchan,
    "pushplus": send_pushplus,
    "wecomchan": send_wecomchan,
    "wecom_bot": send_wecom_bot,
    "wxpusher": send_wxpusher,
    "bark": send_bark,
    "dingtalk_bot": send_dingtalk_bot,
    "feishu_bot": send_feishu_bot,
    "ntfy": send_ntfy,
    "gotify": send_gotify,
}
