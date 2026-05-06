# 推送通道与发送策略

这份文档汇总所有支持的推送通道、发送策略，以及 Cloudflare Workers / 环境变量模式下会用到的 provider id。

## 推送通道

Docker 版和 Cloudflare Workers 版支持完全一致的 12 种推送通道：

| 通道 | 必填配置 | 说明 |
|------|---------|------|
| Server 酱 | SendKey | 推送到微信 |
| PushPlus | Token | 支持 topic、channel，默认 Markdown |
| Telegram | Bot Token、Chat ID | 通过 Bot API 发送纯文本消息 |
| Discord | Webhook | 通过 Incoming Webhook 发送纯文本消息 |
| Wecom 酱 / 企业微信应用 | CorpID、Secret、AgentID、接收人 | 自动获取并缓存 access token |
| 企业微信群机器人 | Webhook 或 Key | 发送 Markdown 消息 |
| WxPusher | AppToken | 支持 UID 列表或 Topic ID 列表 |
| Bark | Server URL、Device Key | 推送到 iOS Bark |
| 钉钉群机器人 | Webhook | 可选 secret 加签 |
| 飞书群机器人 | Webhook | 可选 secret 加签 |
| ntfy | Base URL、Topic | 可选 bearer token、priority、tags |
| Gotify | Base URL、App Token | 可配置 priority |

如果你在查具体变量名，请搭配 [环境变量参考](environment-variables.md) 一起看。

## Docker Web 控制台的通道卡片说明

- **名称**：给自己看的显示名，比如“我的 Server 酱”
- **启用**：关闭后该通道不参与发送
- **服务商参数**：如 Server 酱的 `SendKey`、PushPlus 的 `Token`

程序内部会为每个通道生成稳定 ID，用于配置保存和主备切换，不需要手动填写。使用“主备切换”策略时，按页面卡片顺序尝试，越靠上越先尝试，可用“上移”“下移”调整优先级。

## 发送策略

通过 `DELIVERY_MODE` 控制：

| 策略 | 值 | 行为 |
|------|---|------|
| 所有启用通道同时发送 | `all` | 向全部启用通道发送，至少一个成功即认为送达 |
| 只发送选中通道 | `single` | 只向选中的通道发送 |
| 主备切换，成功即停 | `failover` | 按通道列表顺序尝试，第一个成功后停止 |

- Docker 版：在 Web 控制台里直接选择发送策略
- Cloudflare Workers / GitHub Actions / 环境变量模式：通过 `DELIVERY_MODE`、`SELECTED_PROVIDER`、`FAILOVER_ORDER` 控制

## Cloudflare Workers / 环境变量模式中的 provider id

如果你使用 `single` 或 `failover`，下面这些固定 ID 会出现在 `SELECTED_PROVIDER` 和 `FAILOVER_ORDER` 中：

| 通道 | provider id |
|------|-------------|
| Server 酱 | `serverchan-default` |
| PushPlus | `pushplus-env` |
| Telegram | `telegram-env` |
| Discord | `discord-env` |
| Wecom 酱 / 企业微信应用 | `wecomchan-env` |
| 企业微信群机器人 | `wecom-bot-env` |
| WxPusher | `wxpusher-env` |
| Bark | `bark-env` |
| 钉钉群机器人 | `dingtalk-env` |
| 飞书群机器人 | `feishu-env` |
| ntfy | `ntfy-env` |
| Gotify | `gotify-env` |

示例：

```env
DELIVERY_MODE=single
SELECTED_PROVIDER=serverchan-default
```

```env
DELIVERY_MODE=failover
FAILOVER_ORDER=pushplus-env,serverchan-default
```

## Cloudflare Workers 中常见的发送相关变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `DELIVERY_MODE` | 发送策略 | `all` / `single` / `failover` |
| `SELECTED_PROVIDER` | `single` 模式的通道 ID | `serverchan-default` |
| `FAILOVER_ORDER` | `failover` 顺序，逗号分隔 | `pushplus-env,serverchan-default` |
| `INCLUDE_PRICE_INFO` | 推送商品价格和限购数量 | `true` / `false` |

数据接口默认使用上游 5 分钟缓存，不附带 `refresh=true`。确需绕过缓存时，可以把 `ROCOM_API_URL` 设置为 `https://wegame.shallow.ink/api/v1/games/rocom/merchant/info?refresh=true`，但不建议定时任务默认使用。
