# 环境变量参考

这份文档汇总 Docker / 本地运行 和 Cloudflare Workers 版的全部环境变量。根目录 [README](../../README.md) 只保留首次部署真正需要的少量字段，这里负责查全量表。

## 使用优先级

- `.env`、`docker run -e`、GitHub Actions Secrets / Variables、Cloudflare Worker Variables / Secrets 都是配置来源
- Docker Web 控制台保存过配置后，会优先读取 `./data/config.json`
- 没有 `./data/config.json`，或配置文件里还没有 `providers` 时，程序会根据环境变量自动创建推送通道

## Docker / 本地运行

### 基础变量

| 变量 | 默认值 | 说明 |
|------|-------|------|
| `APP_MODE` | `auto` | 运行模式。`auto` 表示“缺配置时开控制台，配置齐后只跑调度器”；`web` 强制开控制台；`scheduler` 只跑定时任务；`once` 执行一次后退出。 |
| `WEB_PORT` | `19892` | 宿主机暴露端口，浏览器访问地址默认是 `http://<主机>:19892`。 |
| `CONSOLE_USERNAME` | `admin` | 控制台登录用户名。 |
| `CONSOLE_PASSWORD` | 空 | 控制台登录密码；留空时首次启动会生成强密码并打印到日志，哈希保存到 `./data/config.json`。 |
| `CONSOLE_ALLOW_EMPTY_PASSWORD` | `false` | 仅限可信本机调试环境。设为 `true` 后允许控制台空密码登录，不建议公开部署。 |
| `CONSOLE_SESSION_TTL` | `86400` | 控制台登录态有效期，单位秒。 |
| `CONSOLE_SESSION_SECRET` | 空 | 控制台 Cookie 签名密钥；留空时默认复用控制台密码。 |
| `ROCOM_API_KEY` | 空 | 数据源接口 Key。需要你自行从熵增项目组相关渠道获取。 |
| `ROCOM_API_URL` | 空 | 自定义数据源地址。留空时使用内置默认地址；通常不需要改。 |
| `DELIVERY_MODE` | `all` | 推送策略。`all` 全部已启用通道都发；`single` 只发一个通道；`failover` 按顺序重试直到成功。 |
| `SCHEDULE_TIMES` | `08:05,12:05,16:05,20:05` | 北京时间定时执行点，多个时间用英文逗号分隔。 |
| `RUN_ON_START` | `false` | 容器启动完成后是否立即执行一次检查。 |
| `NOTIFY_EMPTY` | `false` | 当前没有商品时是否仍然发一条“空结果”通知。 |
| `INCLUDE_PRICE_INFO` | `false` | 推送中是否附带限购数量、单价和总价信息。 |
| `HTTP_TIMEOUT` | `30` | 请求超时时间，单位秒；同时影响数据源请求和推送请求。 |

### 无控制台通道变量

没有 `./data/config.json` 且配置文件未写入 `providers` 时，程序会根据环境变量自动创建推送通道。只填你要用的那一组即可。

| 通道 | 最少需要 | 字段解释 | 可选 |
|------|---------|---------|------|
| Server 酱 | `SERVERCHAN_SENDKEY` | `SERVERCHAN_SENDKEY`：Server 酱后台生成的 SendKey。 | — |
| PushPlus | `PUSHPLUS_TOKEN` | `PUSHPLUS_TOKEN`：PushPlus 的用户 token。 | `PUSHPLUS_TOPIC`：群组编码；`PUSHPLUS_CHANNEL`：PushPlus 指定渠道。 |
| Telegram | `TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID` | `TELEGRAM_BOT_TOKEN`：从 BotFather 获取的 bot token；`TELEGRAM_CHAT_ID`：接收消息的用户、群组或频道 chat id。 | — |
| Discord | `DISCORD_WEBHOOK` | `DISCORD_WEBHOOK`：Discord Incoming Webhook 的完整 URL。 | — |
| Wecom 酱 / 企业微信应用 | `WECOM_CORPID`、`WECOM_SECRET`、`WECOM_AGENTID` | `WECOM_CORPID`：企业 ID；`WECOM_SECRET`：应用 secret；`WECOM_AGENTID`：应用 AgentID。 | `WECOM_TOUSER`：接收成员，默认 `@all`。 |
| 企业微信群机器人 | `WECOM_BOT_WEBHOOK` 或 `WECOM_BOT_KEY` | `WECOM_BOT_WEBHOOK`：机器人的完整 webhook；`WECOM_BOT_KEY`：仅填写 webhook 中的 key 片段也可。二选一即可。 | — |
| WxPusher | `WXPUSHER_APP_TOKEN` | `WXPUSHER_APP_TOKEN`：应用 AppToken。 | `WXPUSHER_UIDS`：接收 UID 列表；`WXPUSHER_TOPIC_IDS`：Topic ID 列表。 |
| Bark | `BARK_DEVICE_KEY` | `BARK_DEVICE_KEY`：设备 key。 | `BARK_SERVER_URL`：Bark 服务地址；`BARK_GROUP`：通知分组名。 |
| 钉钉群机器人 | `DINGTALK_WEBHOOK` | `DINGTALK_WEBHOOK`：完整 webhook 地址。 | `DINGTALK_SECRET`：开启加签时填写 secret。 |
| 飞书群机器人 | `FEISHU_WEBHOOK` | `FEISHU_WEBHOOK`：完整 webhook 地址。 | `FEISHU_SECRET`：开启签名校验时填写 secret。 |
| ntfy | `NTFY_TOPIC` | `NTFY_TOPIC`：发布目标 topic。 | `NTFY_BASE_URL`：ntfy 服务地址；`NTFY_TOKEN`：Bearer token；`NTFY_PRIORITY`：优先级；`NTFY_TAGS`：标签列表。 |
| Gotify | `GOTIFY_BASE_URL`、`GOTIFY_APP_TOKEN` | `GOTIFY_BASE_URL`：Gotify 服务根地址；`GOTIFY_APP_TOKEN`：应用 token。 | `GOTIFY_PRIORITY`：消息优先级。 |

## Cloudflare Workers

控制台粘贴部署在 Dashboard → Variables and Secrets 中配置。Wrangler 项目部署通过 `wrangler secret put` 配置 secrets，非敏感变量放在 `wrangler.toml` 的 `[vars]` 中。

### Secrets（敏感字段）

| 变量 | 通道 | 说明 |
|------|------|------|
| `ROCOM_API_KEY` | 数据源 | 数据源接口 Key（必需）。 |
| `SERVERCHAN_SENDKEY` | Server 酱 | Server 酱 SendKey。 |
| `PUSHPLUS_TOKEN` | PushPlus | PushPlus 用户 token。 |
| `TELEGRAM_BOT_TOKEN` | Telegram | 由 BotFather 生成的机器人 token。 |
| `DISCORD_WEBHOOK` | Discord | Discord Incoming Webhook 完整 URL。 |
| `WECOM_CORPID` | 企业微信 | 企业 ID。 |
| `WECOM_SECRET` | 企业微信 | 企业微信应用 secret。 |
| `WECOM_AGENTID` | 企业微信 | 企业微信应用 AgentID。 |
| `WECOM_BOT_WEBHOOK` | 企微群机器人 | 企微群机器人完整 webhook 地址。 |
| `WECOM_BOT_KEY` | 企微群机器人 | 企微群机器人 webhook 中的 key。 |
| `WXPUSHER_APP_TOKEN` | WxPusher | WxPusher 应用 AppToken。 |
| `BARK_DEVICE_KEY` | Bark | Bark 设备 key。 |
| `DINGTALK_WEBHOOK` | 钉钉 | 钉钉机器人完整 webhook 地址。 |
| `DINGTALK_SECRET` | 钉钉 | 钉钉机器人加签 secret。 |
| `FEISHU_WEBHOOK` | 飞书 | 飞书机器人完整 webhook 地址。 |
| `FEISHU_SECRET` | 飞书 | 飞书机器人签名 secret。 |
| `NTFY_TOPIC` | ntfy | ntfy 推送目标 topic。 |
| `NTFY_TOKEN` | ntfy | ntfy Bearer token。 |
| `GOTIFY_APP_TOKEN` | Gotify | Gotify 应用 token。 |
| `TRIGGER_TOKEN` | 手动触发 | 保护 `/trigger` 端点的访问 token。 |

### Variables（非敏感字段）

| 变量 | 默认值 | 说明 |
|------|-------|------|
| `ROCOM_API_URL` | 内置默认 | 数据接口地址；默认走上游缓存，不强制刷新。 |
| `NOTIFY_EMPTY` | `false` | 没有商品时是否仍然发送通知。 |
| `INCLUDE_PRICE_INFO` | `false` | 推送正文中是否附带数量、单价和总价。 |
| `DELIVERY_MODE` | `all` | 发送策略：`all` / `single` / `failover`。 |
| `SELECTED_PROVIDER` | 第一个启用通道 | `single` 模式使用的 provider id。 |
| `FAILOVER_ORDER` | 启用通道默认顺序 | `failover` 模式使用的 provider id 顺序，多个值用英文逗号分隔。 |
| `HTTP_TIMEOUT` | `30` | 请求超时秒数。 |
| `PUSHPLUS_TOPIC` | 空 | PushPlus 群组编码。 |
| `PUSHPLUS_CHANNEL` | 空 | PushPlus 指定渠道。 |
| `TELEGRAM_CHAT_ID` | 空 | Telegram 接收目标的 chat id；可以是私聊、群组或频道 id。 |
| `WECOM_TOUSER` | `@all` | 企业微信应用消息接收人。 |
| `WXPUSHER_UIDS` | 空 | WxPusher 接收 UID 列表，多个值用英文逗号分隔。 |
| `WXPUSHER_TOPIC_IDS` | 空 | WxPusher Topic ID 列表。 |
| `BARK_SERVER_URL` | `https://api.day.app` | Bark 服务地址，自建服务时改成自己的域名。 |
| `BARK_GROUP` | `洛克王国` | Bark 通知分组名称。 |
| `NTFY_BASE_URL` | `https://ntfy.sh` | ntfy 服务地址；自建实例时改成自己的地址。 |
| `NTFY_PRIORITY` | `default` | ntfy 消息优先级。 |
| `NTFY_TAGS` | 空 | ntfy 标签，多个标签按 ntfy 规则填写。 |
| `GOTIFY_BASE_URL` | 空 | Gotify 服务根地址。 |
| `GOTIFY_PRIORITY` | `5` | Gotify 消息优先级。 |

推送通道说明、发送策略和 Worker 使用的 provider id 列表见 [推送通道与发送策略](providers-and-delivery.md)。
