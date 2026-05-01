# 洛克王国世界远行商人推送控制台

[![Docker Image](https://img.shields.io/badge/docker-linxi5013%2Froco--push--console-2496ed?logo=docker&logoColor=white)](https://hub.docker.com/r/linxi5013/roco-push-console)
[![CI](https://github.com/adrian803/roco-push-console/actions/workflows/ci.yml/badge.svg)](https://github.com/adrian803/roco-push-console/actions/workflows/ci.yml)
[![Cloudflare Workers](https://img.shields.io/badge/Cloudflare%20Workers-_worker.js-F6821F?logo=cloudflare&logoColor=white)](cf-workers/_worker.js)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

监控《洛克王国世界》远行商人刷新状态的推送服务。提供 **Docker 部署**（含 Web 控制台）、**GitHub Actions 定时推送**和 **Cloudflare Workers 免费托管**三种方式，将刷新结果推送到 10 种主流推送通道。

推送内容以文字和 Markdown 为主，不内置图片渲染和图片推送逻辑。

## 目录

- [截图](#截图)
- [功能特性](#功能特性)
- [部署方式选择](#部署方式选择)
- [快速开始](#快速开始)
  - [方式一：只填 Key 自动托管](#方式一只填-key-自动托管)
  - [方式二：Docker Hub 镜像 + Web 控制台](#方式二docker-hub-镜像--web-控制台)
  - [方式三：docker compose](#方式三docker-compose)
  - [方式四：Cloudflare Workers](#方式四cloudflare-workers)
- [首次配置](#首次配置)
- [推送通道](#推送通道)
- [发送策略](#发送策略)
- [环境变量](#环境变量)
- [常用命令](#常用命令)
- [本地开发](#本地开发)
- [GitHub Actions 定时推送](#github-actions-定时推送)
- [Cloudflare Workers 详细说明](#cloudflare-workers-详细说明)
  - [架构](#架构)
  - [项目结构](#项目结构)
  - [HTTP 端点](#http-端点)
  - [Cron 调度](#cron-调度)
  - [环境变量参考](#环境变量参考)
  - [部署指南](#部署指南)
  - [本地调试与测试](#本地调试与测试)
  - [从其他方式迁移到 CF Workers](#从其他方式迁移到-cf-workers)
  - [费用](#费用)
  - [CF Workers 常见问题](#cf-workers-常见问题)
- [常见问题](#常见问题)
- [安全提醒](#安全提醒)
- [来源与鸣谢](#来源与鸣谢)
- [贡献](#贡献)
- [许可](#许可)

## 截图

| 登录页 | 控制台 |
|:------:|:------:|
| <img src="docs/images/login.png" alt="登录页" width="380"> | <img src="docs/images/console.png" alt="控制台" width="380"> |

Server 酱推送效果：

<img src="docs/images/serverchan-push.png" alt="Server 酱推送效果" width="320">

## 功能特性

**核心能力**

- 10 种推送通道：Server 酱、PushPlus、企业微信、WxPusher、Bark、钉钉、飞书、ntfy、Gotify
- 默认定时 `08:05,12:05,16:05,20:05` 推送（远行商人刷新后 5 分钟，给数据源留同步时间）
- 支持多通道同时发送、单通道发送、主备失败切换
- 三种部署方式：Docker / GitHub Actions / Cloudflare Workers

**Web 控制台**（Docker 版）

- 页面管理配置，无需反复改环境变量
- 单通道测试和按当前策略测试
- 敏感字段保存后不回显，页面显示"已配置，留空不改"
- 推送异常和 HTTP 错误脱敏，避免 token 出现在控制台和 Docker 日志

**可靠性**

- 配置持久化到 `./data/config.json`（Docker 版）
- 读取损坏配置时自动备份原文件，不会覆盖旧配置
- 容器启动时自动修正 `/data` 目录权限，适配 WSL / bind mount

## 部署方式选择

| | Docker | GitHub Actions | Cloudflare Workers |
|---|:---:|:---:|:---:|
| **需要服务器** | 是 | 否 | 否 |
| **Web 控制台** | 有 | 无 | 无 |
| **费用** | 服务器费用 | 免费 | 免费 |
| **定时精确度** | 精确到秒 | 延迟几分钟 | 延迟 1-2 分钟 |
| **长期稳定性** | 高 | 中（可能被暂停） | 高 |
| **配置方式** | 页面 / 环境变量 | GitHub Secrets | Worker 控制台变量 / Wrangler |
| **适合场景** | 长期运行、需要 Web 管理 | 偶尔使用、不想运维 | 免费长期托管 |

**推荐：**

- 需要 Web 控制台 → **Docker**
- 想要免费且稳定 → **Cloudflare Workers**
- 已有 GitHub 仓库、偶尔用用 → **GitHub Actions**

## 快速开始

### 方式一：只填 Key 自动托管

适合不想使用 Web UI、只想长期托管的场景。默认在远行商人刷新后 5 分钟推送。

Server 酱示例：

```bash
docker run -d \
  --name roco-push-console \
  --restart unless-stopped \
  -e ROCOM_API_KEY=你的接口Key \
  -e SERVERCHAN_SENDKEY=你的Server酱SendKey \
  linxi5013/roco-push-console:latest
```

PushPlus 示例：

```bash
docker run -d \
  --name roco-push-console \
  --restart unless-stopped \
  -e ROCOM_API_KEY=你的接口Key \
  -e PUSHPLUS_TOKEN=你的PushPlusToken \
  linxi5013/roco-push-console:latest
```

这种模式不会监听 `19892`，不需要配置 `CONSOLE_USERNAME`、`CONSOLE_PASSWORD`、`WEB_PORT`。

### 方式二：Docker Hub 镜像 + Web 控制台

想通过页面配置和测试通道时，显式设置 `APP_MODE=web`：

```bash
docker run -d \
  --name roco-push-console \
  --restart unless-stopped \
  -p 19892:19892 \
  -v ./data:/data \
  -e APP_MODE=web \
  -e CONSOLE_USERNAME=admin \
  -e CONSOLE_PASSWORD=你的控制台密码 \
  linxi5013/roco-push-console:latest
```

启动后打开 `http://服务器IP:19892`。

### 方式三：docker compose

```bash
git clone https://github.com/adrian803/roco-push-console.git
cd roco-push-console
cp .env.example .env
```

编辑 `.env`，填入必需 Key：

```env
ROCOM_API_KEY=你的接口Key
SERVERCHAN_SENDKEY=你的Server酱SendKey
```

启动：

```bash
docker compose up -d
```

如果想使用 Web 控制台，在 `.env` 中额外设置：

```env
APP_MODE=web
CONSOLE_USERNAME=admin
CONSOLE_PASSWORD=你的控制台密码
WEB_PORT=19892
```

**`APP_MODE` 说明：**

| 值 | 行为 |
|---|---|
| `auto`（默认） | 配置齐时只启动调度器；缺配置时启动 Web 控制台 |
| `web` | 强制启动 Web 控制台 |
| `scheduler` | 强制无控制台运行 |
| `once` | 执行一次检查后退出 |

### 方式四：Cloudflare Workers

不需要服务器，使用 Cloudflare 免费 Cron Triggers 定时执行，全球边缘节点运行。

**方式 A：控制台粘贴部署**

不需要本地环境，在 Cloudflare 网页控制台完成全部操作：

1. 打开 Cloudflare Dashboard → Workers & Pages → Create Worker
2. 进入 Worker 编辑器，删除默认代码
3. 将 [cf-workers/_worker.js](cf-workers/_worker.js) 的完整内容粘贴进去并保存部署
4. 在 Settings → Variables and Secrets 中添加以下 Secret：

| 名称 | 说明 |
|------|------|
| `ROCOM_API_KEY` | 数据源接口 Key（必需） |
| `SERVERCHAN_SENDKEY` | Server 酱 SendKey（或替换为其他通道，至少配一个） |
| `TRIGGER_TOKEN` | 可选，保护 `/trigger` 端点 |

5. 在 Triggers → Cron Triggers 中添加 `5 0,4,8,12 * * *`
6. 访问 `https://<worker名>.workers.dev/` 确认服务正常

**方式 B：Workers Builds 项目部署**

适合从 GitHub/GitLab 项目自动部署。Cloudflare Workers Builds 会在推送到生产分支后自动运行部署命令。

1. 将仓库推送到 GitHub 或 GitLab
2. 打开 Cloudflare Dashboard → Workers & Pages → Create application
3. 选择 Import a repository，授权并选择本仓库
4. Build 设置中填写：

| 设置 | 值 |
|------|----|
| Production branch | `main` |
| Root directory | `cf-workers` |
| Build command | 留空 |
| Deploy command | `npm run deploy` |

5. Worker 名称需要和 [cf-workers/wrangler.toml](cf-workers/wrangler.toml) 中的 `name` 一致，默认为 `roco-push-worker`
6. 部署后在 Worker 的 Settings → Variables and Secrets 中配置运行时 secrets
7. 访问 `https://<worker名>.workers.dev/` 确认服务正常

参考 Cloudflare 官方文档：[Workers Builds](https://developers.cloudflare.com/workers/ci-cd/builds/) 和 [Build Configuration](https://developers.cloudflare.com/workers/ci-cd/builds/configuration/)。

**方式 C：本地 Wrangler 项目部署**

适合需要从源码构建、接入 CI、或用配置文件统一管理的场景：

```bash
cd cf-workers
npm ci
npx wrangler login

# 配置 secrets
npx wrangler secret put ROCOM_API_KEY
npx wrangler secret put SERVERCHAN_SENDKEY  # 至少一个推送通道
npx wrangler secret put TRIGGER_TOKEN       # 可选

# 部署（使用 wrangler.toml 中的 cron 和非敏感变量）
npm run deploy
```

> Wrangler 部署后如果在 Dashboard 手动修改同名变量，下次 `wrangler deploy` 可能覆盖。建议选择一种方式统一管理。

**方式 D：一键脚本部署（交互式脚本 + API Token）**

这是对方式 C 的封装，也是本仓库实际验证过的 Wrangler 项目部署路径。脚本默认交互式运行，开局会先选择部署方式，再询问是否运行检查、是否配置 secrets，最后发布并访问根路径 `/` 做健康检查。

部署方式：

| 选项 | 说明 | 适合场景 |
|------|------|----------|
| `1` / `source` | **npx 编译/项目部署**：从 `src/index.ts` 构建，使用 `wrangler.toml` 发布 | 日常更新源码，推荐 |
| `2` / `worker-js` | **_worker.js 直接部署**：直接发布仓库内现有 `cf-workers/_worker.js`，不重新生成 | 只想验证或发布控制台粘贴版产物 |

准备项：

- 本机已安装 Node.js
- Windows 使用 PowerShell；Linux / macOS 使用 Bash
- 一个可用于部署 Workers 的 Cloudflare API Token
- `ROCOM_API_KEY`
- 至少一个推送通道 secret；下面示例使用 `SERVERCHAN_SENDKEY`

首次部署直接运行脚本，按提示输入敏感值：

```powershell
# Windows PowerShell，默认交互式
.\scripts\deploy-cf-worker.ps1
```

```bat
:: Windows 右键/双击入口，窗口会在结束后停住
scripts\deploy-cf-worker.cmd
```

```bash
# Linux / macOS，默认交互式
bash scripts/deploy-cf-worker.sh
```

脚本会隐藏提示输入 `CLOUDFLARE_API_TOKEN`。选择配置 secrets 后，会依次提示输入 `ROCOM_API_KEY`、`SERVERCHAN_SENDKEY` 和可选 `TRIGGER_TOKEN`，并通过 `wrangler secret put` 写入 Cloudflare，不会写入仓库文件。交互模式还允许临时修改 Worker 名称；默认仍读取 `cf-workers/wrangler.toml`。

Windows PowerShell 脚本在默认交互式模式结束时会提示“按回车键退出”，避免从资源管理器或右键运行时窗口一闪而过；已在终端里运行且不想等待时可加 `-NoPause`。如果你的 Windows `.ps1` 文件关联或执行策略会让右键运行直接关闭，优先右键/双击 [scripts/deploy-cf-worker.cmd](scripts/deploy-cf-worker.cmd)，它会用 `ExecutionPolicy Bypass` 启动 PowerShell 并在结束后停住窗口。

需要自动化时，可使用非交互模式：

```powershell
$env:CLOUDFLARE_API_TOKEN = "你的Cloudflare API Token"
.\scripts\deploy-cf-worker.ps1 -NonInteractive -DeployMode Source -ConfigureSecrets `
  -RoComApiKey "你的ROCOM_API_KEY" `
  -ServerChanSendkey "你的Server酱SendKey"
Remove-Item Env:CLOUDFLARE_API_TOKEN
```

```bash
export CLOUDFLARE_API_TOKEN="你的Cloudflare API Token"
bash scripts/deploy-cf-worker.sh --non-interactive --mode source --configure-secrets \
  --rocom-api-key "你的ROCOM_API_KEY" \
  --serverchan-sendkey "你的Server酱SendKey"
unset CLOUDFLARE_API_TOKEN
```

直接部署现有 `_worker.js`：

```powershell
.\scripts\deploy-cf-worker.ps1 -NonInteractive -DeployMode WorkerJs
```

```bash
bash scripts/deploy-cf-worker.sh --non-interactive --mode worker-js
```

后续更新代码时不需要重新配置 secrets：

```powershell
git pull
.\scripts\deploy-cf-worker.ps1
```

```bash
git pull
bash scripts/deploy-cf-worker.sh
```

只想验证本机能否构建但不发布：

```powershell
.\scripts\deploy-cf-worker.ps1 -DryRun -NonInteractive -DeployMode Source
.\scripts\deploy-cf-worker.ps1 -DryRun -NonInteractive -DeployMode WorkerJs
```

```bash
bash scripts/deploy-cf-worker.sh --dry-run --non-interactive --mode source
bash scripts/deploy-cf-worker.sh --dry-run --non-interactive --mode worker-js
```

API Token 用完建议从当前 shell 清理；如果曾经把 token 发到聊天、issue、日志或截图里，应立即在 Cloudflare 撤销并重新生成。

**部署后验证：**

```bash
# 健康检查
curl https://<worker名>.workers.dev/

# 手动触发（未配置 TRIGGER_TOKEN 时）
curl https://<worker名>.workers.dev/trigger

# 手动触发（配置 TRIGGER_TOKEN 后，任选一种）
curl "https://<worker名>.workers.dev/trigger?token=你的token"
curl -H "X-Trigger-Token: 你的token" https://<worker名>.workers.dev/trigger
curl -H "Authorization: Bearer 你的token" https://<worker名>.workers.dev/trigger
```

**配置发送策略（可选）：**

| 变量 | 说明 | 示例 |
|------|------|------|
| `DELIVERY_MODE` | 发送策略 | `all` / `single` / `failover` |
| `SELECTED_PROVIDER` | `single` 模式通道 ID | `serverchan-default` |
| `FAILOVER_ORDER` | `failover` 顺序，逗号分隔 | `pushplus-env,serverchan-default` |
| `INCLUDE_PRICE_INFO` | 推送商品价格和限购数量 | `true` / `false` |

可用通道 ID：`serverchan-default`、`pushplus-env`、`wecomchan-env`、`wecom-bot-env`、`wxpusher-env`、`bark-env`、`dingtalk-env`、`feishu-env`、`ntfy-env`、`gotify-env`。

数据接口默认使用上游 5 分钟缓存，不附带 `refresh=true`。确需绕过缓存时，可以把 `ROCOM_API_URL` 手动设置为 `https://wegame.shallow.ink/api/v1/games/rocom/merchant/info?refresh=true`，但不建议定时任务默认使用。

控制台粘贴部署在 Dashboard → Variables 中添加；Wrangler 和一键脚本部署在 `wrangler.toml` 的 `[vars]` 中设置。

详细说明见 [Cloudflare Workers 详细说明](#cloudflare-workers-详细说明)。

## 首次配置

### Docker 版（Web 控制台）

进入控制台后按此顺序操作：

1. **基础配置** — 填写 `ROCOM_API_KEY`
2. **数据接口** — 通常保持默认即可
3. **北京时间定时** — 默认 `08:05,12:05,16:05,20:05`
4. **通道配置** — 添加推送通道，填写 token / webhook
5. 点击单通道 **"测试"**，确认收到消息
6. 选择发送策略并 **保存配置**
7. 点击 **"立即执行"** 做一次手动检查

配置保存到 `./data/config.json`。

### CF Workers 版（环境变量）

控制台粘贴部署在 Cloudflare Dashboard → Worker → Settings → Variables and Secrets 中配置。Wrangler 项目部署通过 `wrangler secret put` 配置 secrets，非敏感变量放在 `cf-workers/wrangler.toml`。必需配置 `ROCOM_API_KEY` 和至少一个推送通道 secret；可选配置 `TRIGGER_TOKEN` 保护 `/trigger` 端点。详见 [环境变量参考](#secrets敏感字段)。

## 推送通道

10 种推送通道，Docker 版和 CF Workers 版完全一致：

| 通道 | 必填配置 | 说明 |
|------|---------|------|
| Server 酱 | SendKey | 推送到微信 |
| PushPlus | Token | 支持 topic、channel，默认 Markdown |
| Wecom 酱 / 企业微信应用 | CorpID、Secret、AgentID、接收人 | 自动获取并缓存 access token |
| 企业微信群机器人 | Webhook 或 Key | 发送 Markdown 消息 |
| WxPusher | AppToken | 支持 UID 列表或 Topic ID 列表 |
| Bark | Server URL、Device Key | 推送到 iOS Bark |
| 钉钉群机器人 | Webhook | 可选 secret 加签 |
| 飞书群机器人 | Webhook | 可选 secret 加签 |
| ntfy | Base URL、Topic | 可选 bearer token、priority、tags |
| Gotify | Base URL、App Token | 可配置 priority |

**Docker 版通道卡片说明：**

- **名称**：给自己看的显示名，比如"我的 Server 酱"
- **启用**：关闭后该通道不参与发送
- 服务商参数：如 Server 酱的 `SendKey`、PushPlus 的 `Token`

程序内部会为每个通道生成稳定 ID，用于配置保存和主备切换，不需要手动填写。使用"主备切换"策略时，按页面卡片顺序尝试，越靠上越先尝试，可用"上移""下移"调整优先级。

## 发送策略

通过 `DELIVERY_MODE` 控制（Docker 版在 Web 控制台选择，CF Workers 版在 Worker 控制台变量或 `wrangler.toml` 设置）：

| 策略 | 值 | 行为 |
|------|---|------|
| 所有启用通道同时发送 | `all` | 向全部启用通道发送，至少一个成功即认为送达 |
| 只发送选中通道 | `single` | 只向选中的通道发送 |
| 主备切换，成功即停 | `failover` | 按通道列表顺序尝试，第一个成功后停止 |

CF Workers 版可通过 `SELECTED_PROVIDER` 指定 `single` 的通道，通过 `FAILOVER_ORDER` 指定 `failover` 的逗号分隔顺序。可用通道 ID 见 [方式四](#方式四cloudflare-workers) 中的通道 ID 列表。

## 环境变量

`.env` 里的 `ROCOM_API_KEY`、推送通道 Key 和定时时间会作为默认配置读取。使用 Web 控制台保存过配置后，会优先读取 `./data/config.json`；自动托管或无控制台模式时，可以只维护 `.env` 或 `docker run -e` 参数。

**基础变量：**

| 变量 | 默认值 | 说明 |
|------|-------|------|
| `APP_MODE` | `auto` | 运行模式：`auto` / `web` / `scheduler` / `once` |
| `WEB_PORT` | `19892` | 宿主机访问端口 |
| `CONSOLE_USERNAME` | `admin` | 控制台用户名 |
| `CONSOLE_PASSWORD` | 空 | 控制台密码；为空时启动时随机生成强密码并打印到日志 |
| `CONSOLE_ALLOW_EMPTY_PASSWORD` | `false` | 仅可信本机环境可设为 `true`，显式允许空密码控制台 |
| `CONSOLE_SESSION_TTL` | `86400` | 登录态有效期（秒） |
| `CONSOLE_SESSION_SECRET` | 空 | Cookie 签名密钥；默认使用控制台密码 |
| `ROCOM_API_KEY` | 空 | 数据源接口 Key |
| `ROCOM_API_URL` | 空 | 自定义数据接口，空则使用内置默认值；默认使用上游缓存，不强制刷新 |
| `DELIVERY_MODE` | `all` | 发送策略：`all` / `single` / `failover` |
| `SCHEDULE_TIMES` | `08:05,12:05,16:05,20:05` | 定时推送时间 |
| `RUN_ON_START` | `false` | 容器启动后是否立即执行一次 |
| `NOTIFY_EMPTY` | `false` | 没有商品时是否也推送 |
| `INCLUDE_PRICE_INFO` | `false` | 推送商品时附带限购数量、单价和合计洛克贝 |
| `HTTP_TIMEOUT` | `30` | 请求超时秒数 |

**无控制台通道变量：**

没有 `./data/config.json` 且配置文件未写入 `providers` 时，程序会根据环境变量自动创建推送通道。只填你要用的那一组即可。

| 通道 | 最少需要 | 可选 |
|------|---------|------|
| Server 酱 | `SERVERCHAN_SENDKEY` | — |
| PushPlus | `PUSHPLUS_TOKEN` | `PUSHPLUS_TOPIC`、`PUSHPLUS_CHANNEL` |
| Wecom 酱 / 企业微信应用 | `WECOM_CORPID`、`WECOM_SECRET`、`WECOM_AGENTID` | `WECOM_TOUSER`（默认 `@all`） |
| 企业微信群机器人 | `WECOM_BOT_WEBHOOK` 或 `WECOM_BOT_KEY` | — |
| WxPusher | `WXPUSHER_APP_TOKEN` | `WXPUSHER_UIDS`、`WXPUSHER_TOPIC_IDS` |
| Bark | `BARK_DEVICE_KEY` | `BARK_SERVER_URL`、`BARK_GROUP` |
| 钉钉群机器人 | `DINGTALK_WEBHOOK` | `DINGTALK_SECRET` |
| 飞书群机器人 | `FEISHU_WEBHOOK` | `FEISHU_SECRET` |
| ntfy | `NTFY_TOPIC` | `NTFY_BASE_URL`、`NTFY_TOKEN`、`NTFY_PRIORITY`、`NTFY_TAGS` |
| Gotify | `GOTIFY_BASE_URL`、`GOTIFY_APP_TOKEN` | `GOTIFY_PRIORITY` |

> CF Workers 版的环境变量略有不同，详见 [环境变量参考](#secrets敏感字段)。

## 常用命令

```bash
# 查看日志
docker compose logs -f

# 重启
docker compose restart

# 升级到最新镜像
docker compose pull && docker compose up -d

# 停止并移除容器
docker compose down

# 备份配置
cp ./data/config.json ./config.backup.json
```

## 本地开发

### Docker 版（Python）

```bash
# 环境准备
uv sync --frozen

# 启动 Web 控制台
uv run python -m roco_push_console.web

# 启动自动模式
uv run python -m roco_push_console.launcher

# 一次性执行检查
uv run python main.py

# 运行测试
uv run python -m unittest discover -s tests
uv run python -m compileall -q src main.py tests
docker compose config --quiet

# 构建镜像
docker build -t roco-push-console:latest .
```

### CF Workers 版（本地调试）

控制台粘贴部署不需要本地环境；以下命令用于调试、测试、Wrangler 项目部署，以及从 TypeScript 源码重新生成可粘贴的 `_worker.js`。

```bash
cd cf-workers
npm install

# 复制 secrets 模板
cp .dev.vars.example .dev.vars
# 编辑 .dev.vars 填入你的 secrets

# 本地调试
npm run dev
# 访问 http://localhost:8787/
# 手动触发 http://localhost:8787/trigger

# 测试、类型检查和生成粘贴文件
npm test
npx tsc --noEmit
npm run build:worker

# 可选：Wrangler 项目部署
npm run deploy
```

## GitHub Actions 定时推送

不需要部署服务器，直接用 GitHub Actions 免费定时运行推送检查。默认 cron 对应北京时间：

| 本地时间 | UTC cron |
|:--------:|:--------:|
| 08:05 | `5 0 * * *` |
| 12:05 | `5 4 * * *` |
| 16:05 | `5 8 * * *` |
| 20:05 | `5 12 * * *` |

**配置步骤：**

1. 仓库 → **Settings** → **Secrets and variables** → **Actions**
2. 添加以下 Secret（至少选一个推送通道）：

| 名称 | 说明 |
|------|------|
| `ROCOM_API_KEY` | 数据源接口 Key（必需） |
| `SERVERCHAN_SENDKEY` | Server 酱 SendKey（或替换为其他通道） |

可选添加 Repository Variable：`PUSHPLUS_TOKEN`、`DELIVERY_MODE`、`NOTIFY_EMPTY`、`INCLUDE_PRICE_INFO`、`HTTP_TIMEOUT` 等。

> **注意：** GitHub Actions 定时任务不是严格实时，可能延迟几分钟；只在默认分支生效，仓库长期无活动可能被暂停。如果需要更稳定的免费方案，推荐使用 [Cloudflare Workers](#方式四cloudflare-workers)。

**其他 Actions 工作流：**

- `ci.yml` — PR 和 push 时运行测试 + 编译检查
- `docker-publish.yml` — 自动构建并发布多架构镜像（`amd64` / `arm64`）到 Docker Hub
- `worker-release.yml` — 发布 GitHub Release 时上传 `cf-workers/_worker.js` 附件

## Cloudflare Workers 详细说明

CF Workers 版将核心推送逻辑打包为单文件 [cf-workers/_worker.js](cf-workers/_worker.js)，使用 Cloudflare Cron Triggers 定时执行。支持四种入口：控制台粘贴 `_worker.js`、Workers Builds 从 GitHub/GitLab 项目部署、一键脚本部署，或本地 Wrangler 部署。四种方式使用同一份源码，`_worker.js` 是从 `src/` 构建出的产物。

### 架构

```
┌─────────────────────────────────────────────────┐
│              Cloudflare Workers                  │
│                                                  │
│  Cron Trigger ──┐     HTTP Request ──┐          │
│  (每天4次定时)    │     (/trigger)     │          │
│                  ▼                    ▼          │
│            ┌──────────┐                         │
│            │ runPipeline│                        │
│            └─────┬─────┘                         │
│                  │                               │
│      ┌───────────┼───────────┐                   │
│      ▼           ▼           ▼                   │
│  fetchMerchant  process    sendDelivery          │
│  (获取数据)     (过滤活跃)   (推送到通道)           │
│      │           │           │                   │
│      ▼           ▼           ▼                   │
│  ROCOM API    按时间戳      10 种推送通道          │
│  (数据源)     过滤+轮次      同时/单选/主备         │
└─────────────────────────────────────────────────┘
```

### 项目结构

```
cf-workers/
├── _worker.js                 # 控制台粘贴部署文件
├── wrangler.toml              # Wrangler 项目部署和本地调试配置
├── package.json               # 脚本和依赖
├── tsconfig.json              # TypeScript 配置（strict, ES2022）
├── .gitignore                 # 忽略 node_modules、.wrangler、.dev.vars、dist
├── .dev.vars.example          # 本地调试 secrets 模板
├── scripts/
│   └── write-worker-bundle.mjs # 从 Wrangler bundle 生成 _worker.js
├── test/
│   └── worker.test.ts         # Worker 单元测试
└── src/
    ├── index.ts               # 入口：scheduled（cron）+ fetch（HTTP）handler
    ├── types.ts               # 所有 TypeScript 接口定义
    ├── config.ts              # 环境变量 → Config 对象构建
    ├── rocom.ts               # API 客户端 + 时间工具 + Markdown 构建
    ├── push.ts                # 10 个推送通道实现 + 投递引擎
    └── provider-specs.ts      # 通道字段规格定义（required/secret/default）
```

**源码映射（Python → TypeScript）：**

| Python 文件 | TypeScript 文件 | 内容 |
|---|---|---|
| `app.py` | `index.ts` | 流程编排 |
| `config.py` | `config.ts` | 环境变量映射 |
| `rocom.py` | `rocom.ts` | API 客户端 |
| `time_utils.py` | `rocom.ts` | 时间工具（合并） |
| `push.py` | `push.ts` | 10 个通道 + 投递引擎 |
| `provider_specs.py` | `provider-specs.ts` | 通道规格 |

### HTTP 端点

| 路径 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 健康检查，返回 `{ ok: true, timestamp: "..." }` |
| `/health` | GET | 兼容旧监控的健康检查别名 |
| `/trigger` | GET/POST | 手动触发一次完整推送流程，返回执行结果 |

`/trigger` 默认保持开放，便于迁移和外部手动触发。配置 `TRIGGER_TOKEN` secret 后，触发请求必须提供匹配 token；Cron Trigger、`/` 和兼容别名 `/health` 不受影响。

```bash
# 健康检查
curl https://roco-push-worker.<子域>.workers.dev/

# 开放模式
curl https://roco-push-worker.<子域>.workers.dev/trigger

# 配置 TRIGGER_TOKEN 后任选一种
curl "https://roco-push-worker.<子域>.workers.dev/trigger?token=你的token"
curl -H "X-Trigger-Token: 你的token" https://roco-push-worker.<子域>.workers.dev/trigger
curl -H "Authorization: Bearer 你的token" https://roco-push-worker.<子域>.workers.dev/trigger
```

**返回示例：**

```json
{ "exitCode": 0, "summary": "2/3 个通道成功" }
```

```json
{ "exitCode": 2, "summary": "缺少必要环境变量: ROCOM_API_KEY" }
```

### Cron 调度

默认每天北京时间 08:05、12:05、16:05、20:05 触发，即远行商人刷新后 5 分钟。

| 北京时间 | UTC 时间 | Cron 表达式 |
|:--------:|:--------:|:-----------:|
| 08:05 | 00:05 | `5 0 * * *` |
| 12:05 | 04:05 | `5 4 * * *` |
| 16:05 | 08:05 | `5 8 * * *` |
| 20:05 | 12:05 | `5 12 * * *` |

控制台粘贴部署：在 Dashboard → Worker → Triggers → Cron Triggers 中添加 `5 0,4,8,12 * * *`。

Wrangler 项目部署：在 `wrangler.toml` 中维护：

```toml
[triggers]
crons = ["5 0,4,8,12 * * *"]
```

Cloudflare Cron Triggers 不保证精确到秒，实际执行可能有延迟。免费计划的额度通常足够本项目默认每天 4 次调度，具体限制以 Cloudflare 官方文档为准。

### 环境变量参考

#### Secrets（敏感字段）

通过控制台 Variables and Secrets 添加，或用 `wrangler secret put <NAME>` 命令行配置。

| 变量 | 通道 | 说明 |
|------|------|------|
| `ROCOM_API_KEY` | 数据源 | 数据源接口 Key（必需） |
| `SERVERCHAN_SENDKEY` | Server 酱 | SendKey |
| `PUSHPLUS_TOKEN` | PushPlus | Token |
| `WECOM_CORPID` | 企业微信 | CorpID |
| `WECOM_SECRET` | 企业微信 | Secret |
| `WECOM_AGENTID` | 企业微信 | AgentID |
| `WECOM_BOT_WEBHOOK` | 企微群机器人 | Webhook URL |
| `WECOM_BOT_KEY` | 企微群机器人 | Key |
| `WXPUSHER_APP_TOKEN` | WxPusher | AppToken |
| `BARK_DEVICE_KEY` | Bark | Device Key |
| `DINGTALK_WEBHOOK` | 钉钉 | Webhook URL |
| `DINGTALK_SECRET` | 钉钉 | 加签密钥（可选） |
| `FEISHU_WEBHOOK` | 飞书 | Webhook URL |
| `FEISHU_SECRET` | 飞书 | 加签密钥（可选） |
| `NTFY_TOPIC` | ntfy | Topic |
| `NTFY_TOKEN` | ntfy | Bearer Token（可选） |
| `GOTIFY_APP_TOKEN` | Gotify | App Token |
| `TRIGGER_TOKEN` | 手动触发 | `/trigger` 手动触发 token（可选） |

#### Variables（非敏感字段）

控制台粘贴部署在 Dashboard Variables 中添加；Wrangler 项目部署在 `wrangler.toml` 的 `[vars]` 中设置。

| 变量 | 默认值 | 说明 |
|------|-------|------|
| `ROCOM_API_URL` | 内置默认 | 数据接口地址；默认使用上游缓存，不强制刷新 |
| `NOTIFY_EMPTY` | `false` | 无商品时是否推送 |
| `INCLUDE_PRICE_INFO` | `false` | 推送商品时附带限购数量、单价和合计洛克贝 |
| `DELIVERY_MODE` | `all` | 发送策略：`all` / `single` / `failover` |
| `SELECTED_PROVIDER` | 第一个启用通道 | `single` 模式使用的 provider id |
| `FAILOVER_ORDER` | 启用通道默认顺序 | `failover` 模式顺序，逗号分隔 provider id |
| `HTTP_TIMEOUT` | `30` | 请求超时秒数 |
| `PUSHPLUS_TOPIC` | 空 | PushPlus 群组编码 |
| `PUSHPLUS_CHANNEL` | 空 | PushPlus 渠道 |
| `WECOM_TOUSER` | `@all` | 企业微信接收人 |
| `WXPUSHER_UIDS` | 空 | WxPusher UID 列表（逗号分隔） |
| `WXPUSHER_TOPIC_IDS` | 空 | WxPusher Topic ID 列表 |
| `BARK_SERVER_URL` | `https://api.day.app` | Bark 服务器地址 |
| `BARK_GROUP` | `洛克王国` | Bark 消息分组 |
| `NTFY_BASE_URL` | `https://ntfy.sh` | ntfy 服务器地址 |
| `NTFY_PRIORITY` | `default` | ntfy 优先级 |
| `NTFY_TAGS` | 空 | ntfy 标签 |
| `GOTIFY_BASE_URL` | 空 | Gotify 服务器地址 |
| `GOTIFY_PRIORITY` | `5` | Gotify 优先级 |

### 部署指南

- 普通使用者：控制台粘贴 `_worker.js`，不需要安装 Node.js。
- 自动化项目部署：用 Workers Builds 连接 GitHub/GitLab，Root directory 设为 `cf-workers`，Deploy command 设为 `npm run deploy`。
- Windows / PowerShell 用户：终端里运行 [scripts/deploy-cf-worker.ps1](scripts/deploy-cf-worker.ps1)；从资源管理器右键/双击时运行 [scripts/deploy-cf-worker.cmd](scripts/deploy-cf-worker.cmd)，窗口会在结束后停住。
- Linux / macOS 用户：运行 [scripts/deploy-cf-worker.sh](scripts/deploy-cf-worker.sh)，流程与 PowerShell 脚本一致。
- 本地项目部署：用 Wrangler 登录后运行 `npm run deploy`。
- 源码改动后：运行 `npm run build:worker` 重新生成 `_worker.js` 并提交；CI 会用 `npm run check:worker` 检查是否同步。
- 发布 Release 时：`worker-release.yml` 会重新跑 Worker 测试和 bundle 检查，并把 `cf-workers/_worker.js` 上传到 GitHub Release 附件。

**Wrangler 常用命令：**

```bash
cd cf-workers
npm test
npx tsc --noEmit
npm run dry-run
npm run deploy
npm run tail
```

**一键脚本常用命令：**

```powershell
# Windows 首次部署：默认交互式，先选择 npx 编译/项目部署或 _worker.js 直接部署
.\scripts\deploy-cf-worker.ps1

# Windows 右键/双击运行：使用 cmd 启动器，避免黑窗口一闪而过
scripts\deploy-cf-worker.cmd

# 后续更新：保留 Cloudflare 上已有 secrets，只重新测试并发布代码
git pull
.\scripts\deploy-cf-worker.ps1

# 仅构建验证，不发布
.\scripts\deploy-cf-worker.ps1 -DryRun -NonInteractive -DeployMode Source
.\scripts\deploy-cf-worker.ps1 -DryRun -NonInteractive -DeployMode WorkerJs
```

```bash
# Linux / macOS 首次部署：默认交互式，先选择 npx 编译/项目部署或 _worker.js 直接部署
bash scripts/deploy-cf-worker.sh

# 后续更新
git pull
bash scripts/deploy-cf-worker.sh

# 仅构建验证，不发布
bash scripts/deploy-cf-worker.sh --dry-run --non-interactive --mode source
bash scripts/deploy-cf-worker.sh --dry-run --non-interactive --mode worker-js
```

**自定义域名（可选）：**

控制台粘贴部署和 Workers Builds 都可以在 Cloudflare Dashboard → Worker → Settings → Domains & Routes 中添加自定义域名或路由。本地 Wrangler 项目部署也可以在 `wrangler.toml` 中配置 routes 后重新部署：

```toml
routes = [
  { pattern = "push.example.com/*", zone_name = "example.com" }
]
```

### 本地调试与测试

控制台粘贴部署不需要本地环境；以下命令用于调试、测试、Wrangler 项目部署，以及从 TypeScript 源码重新生成 `_worker.js`。

```bash
cd cf-workers
npm ci

# 本地调试
cp .dev.vars.example .dev.vars   # 编辑填入 secrets
npm run dev                       # http://localhost:8787

# 测试与检查
npm test
npx tsc --noEmit
npm run dry-run

# 重新生成控制台粘贴文件，并检查 _worker.js 是否已提交
npm run check:worker
```

提交 PR 前建议运行：

```bash
npm ci
npm test
npx tsc --noEmit
npm run check:worker
```

### 从其他方式迁移到 CF Workers

**从 GitHub Actions 迁移：**

1. 在 Cloudflare 控制台创建 Worker，并粘贴 [cf-workers/_worker.js](cf-workers/_worker.js)
2. 将 GitHub Actions Secrets 中的值迁移到 Worker 的 Variables and Secrets
3. 在 Triggers → Cron Triggers 中添加 `5 0,4,8,12 * * *`
4. 访问根路径 `/` 验证服务状态，再手动访问 `/trigger` 验证推送
5. 确认正常后，删除或停用 `.github/workflows/scheduled-push.yml`

**从 Docker 版迁移：**

| Docker 环境变量 | CF Workers 配置 |
|---|---|
| `ROCOM_API_KEY` | Secret |
| `SERVERCHAN_SENDKEY` | Secret |
| `DELIVERY_MODE` | Variable |
| `NOTIFY_EMPTY` | Variable |
| `INCLUDE_PRICE_INFO` | Variable |
| `HTTP_TIMEOUT` | Variable |
| 其他通道 Key | Secret |
| 其他通道可选参数 | Variable |

不需要迁移 `APP_MODE`、`WEB_PORT`、`CONSOLE_*`、`SCHEDULE_TIMES`、`RUN_ON_START`，这些只属于 Docker 版。

### 外部监控

任何支持 HTTP 健康检查的服务都可以监控根路径 `/`：[UptimeRobot](https://uptimerobot.com/)、[Better Uptime](https://betteruptime.com/)、[Freshping](https://www.freshworks.com/website-monitoring/)、[Hetrix Tools](https://hetrixtools.com/)。旧的 `/health` 仍保留为兼容别名。

### 费用

默认每天 4 次触发 = 每月约 120 次，请求量很低，通常适合 Cloudflare Workers 免费计划。具体额度以 [Cloudflare Workers Limits](https://developers.cloudflare.com/workers/platform/limits/) 为准。

### CF Workers 常见问题

**`_worker.js` 是手写的吗？** 不是。源码在 `src/*.ts`，`_worker.js` 由 `npm run build:worker` 生成。改源码后需要重新生成并提交 `_worker.js`。

**如何更新到最新版本？** 控制台粘贴部署：复制仓库或 GitHub Release 附件中的新版 [_worker.js](cf-workers/_worker.js) 全量内容，替换 Worker 编辑器中的代码并保存部署。Workers Builds：推送到生产分支后自动部署。一键脚本部署：`git pull` 后运行 `.\scripts\deploy-cf-worker.ps1` 或 `bash scripts/deploy-cf-worker.sh`。手动 Wrangler 项目部署：`git pull && cd cf-workers && npm ci && npm run deploy`。

**如何查看执行日志？** Cloudflare Dashboard → Workers → 你的 Worker → Logs。Wrangler 项目部署也可以用 `npm run tail`。

## 常见问题

<details>
<summary><b>如何获取 ROCOM_API_KEY？</b></summary>

请按 [Entropy-Increase-Team](https://github.com/Entropy-Increase-Team/) 项目或相关社区的规则获取。本项目不提供、不分发 API Key。

</details>

<details>
<summary><b>三种部署方式怎么选？</b></summary>

- 需要 Web 控制台管理配置 → **Docker**
- 想免费且稳定运行 → **Cloudflare Workers**
- 已有 GitHub 仓库、偶尔用 → **GitHub Actions**

三种方式的推送逻辑完全一致，区别在于配置方式和运维成本。

</details>

<details>
<summary><b>默认控制台密码在哪里？</b></summary>

如果 `CONSOLE_PASSWORD` 为空，控制台启动时会随机生成一个本次启动有效的强密码，并在日志中打印 `控制台默认密码: ...`。Docker Compose 用户可运行 `docker compose logs roco-push-console` 查看。重启后会重新生成；长期运行建议在 `.env` 设置固定强密码，或使用 `APP_MODE=auto` 填齐 Key 让服务进入无控制台托管模式。仅在可信本机环境调试时，可以显式设置 `CONSOLE_ALLOW_EMPTY_PASSWORD=true` 允许空密码。

</details>

<details>
<summary><b>为什么没有启动 Web 控制台？</b></summary>

默认 `APP_MODE=auto` 会在配置齐全时只启动调度器，不监听 `19892`。设置 `APP_MODE=web` 后重建容器即可强制启动。

</details>

<details>
<summary><b>为什么提示缺少 ROCOM_API_KEY？</b></summary>

本项目不提供 API Key。请按 [Entropy-Increase-Team](https://github.com/Entropy-Increase-Team/) 项目或相关社区的规则获取 `ROCOM_API_KEY`，再填入控制台或 `.env`。

</details>

<details>
<summary><b>为什么修改 .env 后页面没变？</b></summary>

控制台保存过配置后，会优先读取 `./data/config.json`。后续更推荐在 Web 控制台修改；如要完全使用 `.env` 默认值，需先备份并移走 `config.json`。

</details>

<details>
<summary><b>为什么收不到推送？</b></summary>

**Docker 版：** 先在"通道配置"里点击单通道"测试"。如果测试失败，检查 token / webhook 是否正确、服务商是否限流、服务器是否能访问对应推送服务。

**CF Workers 版：** 手动触发 `curl <worker-url>/trigger`，查看返回结果。若配置了 `TRIGGER_TOKEN`，使用 `curl '<worker-url>/trigger?token=你的token'`。执行日志优先在 Cloudflare Dashboard → Workers → 你的 Worker → Logs 查看；Wrangler 项目部署也可以在 `cf-workers` 目录运行 `npm run tail`。

**GitHub Actions 版：** 查看 Actions 运行日志，确认 secrets 是否配置正确。

</details>

<details>
<summary><b>配置文件损坏怎么办？</b></summary>

程序读取失败时会把损坏文件备份为 `config.json.invalid-时间戳.bak`，并在控制台状态区显示提示。

</details>

<details>
<summary><b>保存配置提示 Permission denied？</b></summary>

旧容器在 WSL + bind mount 场景下可能出现权限问题。执行：

```bash
docker exec -u root roco-push-console chown -R app:app /data
```

然后刷新再保存。长期建议更新镜像并重建容器：

```bash
docker compose pull && docker compose up -d --force-recreate
```

</details>

<details>
<summary><b>GitHub Actions 定时不准怎么办？</b></summary>

GitHub Actions 的 cron 不保证精确执行，可能延迟几分钟，仓库长期不活跃还会被暂停。推荐迁移到 [Cloudflare Workers](#方式四cloudflare-workers)，同样免费但更稳定。

</details>

<details>
<summary><b>如何从 GitHub Actions 迁移到 CF Workers？</b></summary>

1. 在 Cloudflare 控制台创建 Worker，并粘贴 [cf-workers/_worker.js](cf-workers/_worker.js)
2. 将 GitHub Secrets 中的值迁移到 Worker 的 Variables and Secrets
3. 删除仓库中的 `.github/workflows/scheduled-push.yml`
4. CI 和 Docker Publish workflows 保留不变

</details>

## 安全提醒

### Docker 版

默认 `APP_MODE=auto`：配置齐时容器只启动调度器，不启动 Web 控制台；缺少配置时才启动控制台方便首次配置。

如果使用 `APP_MODE=web`，或因缺少 Key 进入控制台模式，控制台监听 `0.0.0.0` 并发布到宿主机 `19892` 端口。`CONSOLE_PASSWORD` 为空时会生成本次启动默认密码，并在日志中打印 `控制台默认密码: ...`。

**公开部署前请务必：**

- 在 `.env` 设置强密码：`CONSOLE_PASSWORD=你的密码`
- 只在可信网络开放 `19892`，或用防火墙 / 反向代理限制访问
- 本机访问改为 `127.0.0.1:${WEB_PORT:-19892}:19892`
- 仅本机临时调试时才使用 `CONSOLE_ALLOW_EMPTY_PASSWORD=true`
- 不要提交 `./data/config.json`（含明文 token 和 Key）

### CF Workers 版

Secrets 通过 Cloudflare Worker 控制台加密存储，不会出现在代码或日志中。`/trigger` 端点默认开放；公开分享 Worker URL 前建议配置 `TRIGGER_TOKEN`，让手动触发必须带 token。

## 来源与鸣谢

远行商人数据来自 [Entropy-Increase-Team](https://github.com/Entropy-Increase-Team/) 提供的接口。本仓库只负责调用接口并展示、推送结果，不内置、不分发 `ROCOM_API_KEY`，也不代为申请 Key。请按数据源项目或相关社区的规则获取 Key。

本项目不会绕过数据源服务端限制，接口调用频率以数据源后端实际限制为准。请合理设置定时任务，避免给数据源服务带来不必要的压力。

已询问过数据源项目提供方，本项目只是调用 Entropy-Increase-Team 的接口，标注数据来源即可。若需直接使用或改造其代码，会按其 AGPL-3.0 协议要求处理。

## 贡献

欢迎提交 issue 和 pull request。适合贡献的方向：

- 新推送通道
- 控制台交互优化
- 部署文档
- 测试用例

提交 PR 前请运行：

```bash
# Docker 版
uv run python -m unittest discover -s tests
uv run python -m compileall -q src main.py tests
docker compose config --quiet

# CF Workers 版
cd cf-workers
npm ci
npm test
npx tsc --noEmit
npm run check:worker
```

## 路线图

- 支持更多推送平台
- 增加更完整的端到端测试
- ~~Cloudflare Workers Cron 适配器~~ ✅ 已完成

## 免责声明

本项目是个人学习和自用工具，和游戏官方、WeGame、各推送平台均无从属关系。项目只保存使用者自行填写的接口 Key 和推送 token，不提供、不出售、不共享任何第三方 API Key。请遵守相关服务条款，不要滥用接口或推送能力。

## 许可

本项目使用 [MIT License](LICENSE)。
