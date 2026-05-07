# Cloudflare Workers 完整部署指南

Cloudflare Workers 版适合想免费长期托管、又不想维护服务器的场景。它把核心推送逻辑打包为单文件 [releases/cloudflare-worker/_worker.js](../../releases/cloudflare-worker/_worker.js)，使用 Cloudflare Cron Triggers 定时执行。

如果你只想最快跑起来，请先看根目录的 [README](../../README.md)。这份文档面向需要完整部署方式、更新方法、本地调试和迁移说明的使用者。

## 目录

- [部署方式总览](#部署方式总览)
- [最少需要准备什么](#最少需要准备什么)
- [默认调度](#默认调度)
- [方式一：控制台粘贴](#方式一控制台粘贴-_workerjs)
- [方式二：Workers Builds](#方式二workers-builds)
- [方式三：Wrangler 项目部署](#方式三wrangler-项目部署)
- [方式四：一键脚本部署](#方式四一键脚本部署)
- [部署后验证与日常运维](#部署后验证与日常运维)
- [本地调试与测试](#本地调试与测试)
- [关键文件](#关键文件)
- [从其他方式迁移到 CF Workers](#从其他方式迁移到-cf-workers)
- [常见问题](#常见问题)

## 部署方式总览

| 方式 | 适合场景 | 是否需要本地 Node.js |
|------|----------|:--------------------:|
| 控制台粘贴 `_worker.js` | 最快上线，不想准备本地环境 | 否 |
| Workers Builds | 仓库托管在 GitHub / GitLab，希望自动部署 | 否 |
| Wrangler 项目部署 | 想从 TypeScript 源码构建并接入 CI | 是 |
| 一键脚本部署 | 想用仓库自带脚本完成交互式或非交互式部署 | 是 |

## 最少需要准备什么

无论你选哪种部署方式，至少需要下面这些值：

| 名称 | 说明 |
|------|------|
| `ROCOM_API_KEY` | 数据源接口 Key（必需） |
| 至少一个推送通道 Secret | 例如 `SERVERCHAN_SENDKEY`、`PUSHPLUS_TOKEN`、`TELEGRAM_BOT_TOKEN` |
| `TRIGGER_TOKEN` | 可选，用来保护 `/trigger` 手动触发端点 |

如果你还没确定先接哪一条推送通道，建议优先用 [Server 酱](https://sct.ftqq.com/r/1636)。当前仓库维护者主要实测的也是 Server 酱；该链接包含推荐参数，如后续发生付费订阅，可能为项目维护者带来佣金。

完整字段清单见：

- [环境变量参考](../reference/environment-variables.md)
- [推送通道与发送策略](../reference/providers-and-delivery.md)

## 默认调度

默认每天北京时间 08:05、12:05、16:05、20:05 触发，即远行商人刷新后 5 分钟。

| 北京时间 | UTC 时间 | Cron 表达式 |
|:--------:|:--------:|:-----------:|
| 08:05 | 00:05 | `5 0 * * *` |
| 12:05 | 04:05 | `5 4 * * *` |
| 16:05 | 08:05 | `5 8 * * *` |
| 20:05 | 12:05 | `5 12 * * *` |

控制台粘贴部署请在 Dashboard → Worker → Triggers → Cron Triggers 中添加 `5 0,4,8,12 * * *`。Wrangler 项目部署则在 `wrangler.toml` 中维护：

```toml
[triggers]
crons = ["5 0,4,8,12 * * *"]
```

Cloudflare Cron Triggers 不保证精确到秒，实际执行可能有延迟。免费计划通常足够本项目默认每天 4 次调度。

## 方式一：控制台粘贴 `_worker.js`

1. 打开 Cloudflare Dashboard → Workers & Pages → Create Worker
2. 进入 Worker 编辑器，删除默认代码
3. 将 [releases/cloudflare-worker/_worker.js](../../releases/cloudflare-worker/_worker.js) 的完整内容粘贴进去并保存部署
4. 在 Settings → Variables and Secrets 中添加：

| 名称 | 说明 |
|------|------|
| `ROCOM_API_KEY` | 数据源接口 Key（必需） |
| `SERVERCHAN_SENDKEY` | Server 酱 SendKey；也可以替换成其他任一推送通道 |
| `TRIGGER_TOKEN` | 可选，保护 `/trigger` |

5. 在 Triggers → Cron Triggers 中添加 `5 0,4,8,12 * * *`
6. 访问 `https://<worker名>.workers.dev/` 确认服务正常

这是最适合第一次尝试的方式，不需要本地安装 Node.js。

## 方式二：Workers Builds

适合从 GitHub / GitLab 仓库自动部署。Cloudflare Workers Builds 会在推送到生产分支后自动运行部署命令。

1. 将仓库推送到 GitHub 或 GitLab
2. 打开 Cloudflare Dashboard → Workers & Pages → Create application
3. 选择 Import a repository，授权并选择本仓库
4. Build 设置使用下面这组值：

| 设置 | 值 |
|------|----|
| Production branch | `main` |
| Root directory | `cloudflare-worker` |
| Build command | 留空 |
| Deploy command | `npm run deploy` |

5. Worker 名称需要和 [cloudflare-worker/wrangler.toml](../../cloudflare-worker/wrangler.toml) 中的 `name` 一致，默认是 `roco-serverchan-notifier-worker`
6. 部署后在 Worker 的 Settings → Variables and Secrets 中配置运行时 secrets
7. 访问 `https://<worker名>.workers.dev/` 确认服务正常

Cloudflare 官方文档可参考 [Workers Builds](https://developers.cloudflare.com/workers/ci-cd/builds/) 和 [Build Configuration](https://developers.cloudflare.com/workers/ci-cd/builds/configuration/)。

## 方式三：Wrangler 项目部署

适合需要从 TypeScript 源码构建、接入 CI、或用配置文件统一管理的场景。

```bash
cd cloudflare-worker
npm ci
npx wrangler login

# 配置 secrets
npx wrangler secret put ROCOM_API_KEY
npx wrangler secret put SERVERCHAN_SENDKEY  # 至少一个推送通道
npx wrangler secret put TRIGGER_TOKEN       # 可选

# 部署
npm run deploy
```

> 如果你在 Dashboard 手动修改同名变量，下次 `wrangler deploy` 可能覆盖。建议选择一种方式统一管理。

## 方式四：一键脚本部署

仓库自带三套脚本：

- Windows PowerShell：[scripts/deploy-cf-worker.ps1](../../scripts/deploy-cf-worker.ps1)
- Windows 右键 / 双击：[scripts/deploy-cf-worker.cmd](../../scripts/deploy-cf-worker.cmd)（用 `ExecutionPolicy Bypass` 启动 PowerShell，结束后停住窗口）
- Linux / macOS：[scripts/deploy-cf-worker.sh](../../scripts/deploy-cf-worker.sh)

它们是对 Wrangler 项目部署的封装，默认交互式运行，开局会先选择部署方式，再询问是否运行检查、是否配置 secrets，最后发布并访问根路径 `/` 做健康检查。

### 部署模式

| 选项 | 说明 | 适合场景 |
|------|------|----------|
| `source` | 从 `src/index.ts` 构建，使用 `wrangler.toml` 发布 | 日常更新源码，推荐 |
| `worker-js` | 直接发布仓库内现有 `cloudflare-worker/_worker.js` | 只想验证或发布控制台粘贴版产物 |

### 先决条件

- 本机已安装 Node.js
- Windows 使用 PowerShell；Linux / macOS 使用 Bash
- 一个可用于部署 Workers 的 Cloudflare API Token
- `ROCOM_API_KEY`
- 至少一个推送通道 secret；下面示例使用 `SERVERCHAN_SENDKEY`

### 首次交互式部署

```powershell
# Windows PowerShell
.\scripts\deploy-cf-worker.ps1
```

```bat
:: Windows 右键/双击入口，窗口会在结束后停住
scripts\deploy-cf-worker.cmd
```

```bash
# Linux / macOS
bash scripts/deploy-cf-worker.sh
```

交互模式会隐藏提示输入 `CLOUDFLARE_API_TOKEN`，并在你选择配置 secrets 后依次提示输入 `ROCOM_API_KEY`、`SERVERCHAN_SENDKEY` 和可选的 `TRIGGER_TOKEN`。这些值会通过 `wrangler secret put` 写入 Cloudflare，不会写回仓库文件。

如果你的 Windows `.ps1` 右键运行会直接关闭，优先双击或右键运行 [scripts/deploy-cf-worker.cmd](../../scripts/deploy-cf-worker.cmd)，它会用 `ExecutionPolicy Bypass` 启动 PowerShell 并在结束后停住窗口。

### 非交互式部署

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

### 仅验证构建，不发布

```powershell
.\scripts\deploy-cf-worker.ps1 -DryRun -NonInteractive -DeployMode Source
.\scripts\deploy-cf-worker.ps1 -DryRun -NonInteractive -DeployMode WorkerJs
```

```bash
bash scripts/deploy-cf-worker.sh --dry-run --non-interactive --mode source
bash scripts/deploy-cf-worker.sh --dry-run --non-interactive --mode worker-js
```

### 后续更新

```powershell
git pull
.\scripts\deploy-cf-worker.ps1
```

```bash
git pull
bash scripts/deploy-cf-worker.sh
```

API Token 用完建议从当前 shell 清理；如果曾经把 token 发到聊天、issue、日志或截图里，应立即在 Cloudflare 撤销并重新生成。

## 部署后验证与日常运维

### 健康检查和手动触发

```bash
# 健康检查
curl https://<worker名>.workers.dev/

# 手动触发（未配置 TRIGGER_TOKEN 时）
curl https://<worker名>.workers.dev/trigger

# 配置 TRIGGER_TOKEN 后任选一种
curl "https://<worker名>.workers.dev/trigger?token=你的token"
curl -H "X-Trigger-Token: 你的token" https://<worker名>.workers.dev/trigger
curl -H "Authorization: Bearer 你的token" https://<worker名>.workers.dev/trigger
```

### 查看日志

- Cloudflare Dashboard → Workers → 你的 Worker → Logs
- Wrangler 项目部署：`cd cloudflare-worker && npm run tail`

### 更新到最新版本

- **控制台粘贴部署：** 复制仓库或 GitHub Release 附件中的新版 [_worker.js](../../releases/cloudflare-worker/_worker.js) 全量内容，替换 Worker 编辑器中的代码并保存部署
- **Workers Builds：** 推送到生产分支后自动部署
- **一键脚本部署：** `git pull` 后重新运行对应脚本
- **Wrangler 项目部署：** `git pull && cd cloudflare-worker && npm ci && npm run deploy`

### 自定义域名（可选）

控制台粘贴部署和 Workers Builds 都可以在 Cloudflare Dashboard → Worker → Settings → Domains & Routes 中添加自定义域名或路由。本地 Wrangler 项目部署也可以在 `wrangler.toml` 中配置 `routes` 后重新部署：

```toml
routes = [
  { pattern = "push.example.com/*", zone_name = "example.com" }
]
```

### 外部监控

任何支持 HTTP 健康检查的服务都可以监控根路径 `/`，例如 [UptimeRobot](https://uptimerobot.com/)、[Better Uptime](https://betteruptime.com/)、[Freshping](https://www.freshworks.com/website-monitoring/)、[Hetrix Tools](https://hetrixtools.com/)。旧的 `/health` 仍保留为兼容别名。

## 本地调试与测试

控制台粘贴部署不需要本地环境；以下命令用于调试、测试、Wrangler 项目部署，以及从 TypeScript 源码重新生成 `_worker.js`。生成后会同时同步 `cloudflare-worker/_worker.js` 和 `releases/cloudflare-worker/_worker.js`。

```bash
cd cloudflare-worker
npm ci

# 本地调试
cp .dev.vars.example .dev.vars   # 编辑填入 secrets
npm run dev                       # http://localhost:8787

# 测试与检查
npm test
npx tsc --noEmit
npm run dry-run

# 重新生成控制台粘贴文件，并检查 _worker.js 是否同步
npm run check:worker
```

提交 PR 前建议运行：

```bash
cd cloudflare-worker
npm ci
npm test
npx tsc --noEmit
npm run check:worker
```

## 关键文件

```text
cloudflare-worker/
├── _worker.js                   控制台粘贴部署文件（生成产物，不要手写）
├── wrangler.toml                Wrangler 项目部署和本地调试配置
├── package.json                 脚本和依赖
├── scripts/
│   └── write-worker-bundle.mjs  从 Wrangler bundle 生成 _worker.js
├── src/
│   ├── index.ts                 Worker HTTP / Cron 入口
│   ├── config.ts                Worker 环境变量装配
│   ├── types.ts                 Env 类型定义
│   ├── provider-specs.ts        共享 provider manifest 读取和校验
│   ├── push.ts                  推送兼容导出入口
│   ├── push-delivery.ts         all/single/failover 投递策略
│   ├── push-providers.ts        provider 校验、分发和脱敏门面
│   ├── push-provider-senders/   各推送通道实现（一 provider 一模块）
│   ├── push-provider-auth.ts    企业微信 token、钉钉/飞书签名
│   ├── push-http.ts             通用 HTTP 结果解析
│   ├── push-redaction.ts        推送错误脱敏
│   ├── rocom.ts                 数据入口
│   ├── rocom-client.ts          数据源 API 调用
│   ├── rocom-processing.ts      商品过滤与处理
│   ├── rocom-message.ts         Markdown 消息构建
│   └── rocom-time.ts            北京时间与轮次计算
└── tests/
    ├── worker.test.ts           入口、配置、触发鉴权和端到端流程
    ├── push-modules.test.ts     推送模块边界、sender、HTTP 和脱敏
    ├── rocom-modules.test.ts    时间、数据处理、消息构建模块边界
    └── cross-runtime.test.ts    Python/Worker 共享行为 fixture
```

源码改动后，不要手写修改 `_worker.js`。统一运行 `npm run check:worker`，它会重新构建并检查 `_worker.js` 是否同步。

仓库根目录的 `releases/cloudflare-worker/_worker.js` 会和 `cloudflare-worker/_worker.js` 一起同步生成，前者更适合直接作为 Release 附件或给控制台粘贴部署使用。

## 从其他方式迁移到 CF Workers

### 从 GitHub Actions 迁移

1. 在 Cloudflare 控制台创建 Worker，并粘贴 [releases/cloudflare-worker/_worker.js](../../releases/cloudflare-worker/_worker.js)
2. 将 GitHub Actions Secrets 中的值迁移到 Worker 的 Variables and Secrets
3. 在 Triggers → Cron Triggers 中添加 `5 0,4,8,12 * * *`
4. 访问根路径 `/` 验证服务状态，再手动访问 `/trigger` 验证推送
5. 确认正常后，删除或停用 `.github/workflows/scheduled-push.yml`

### 从 Docker 版迁移

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

## 常见问题

**`_worker.js` 是手写的吗？** 不是。源码在 `src/*.ts`，`npm run build:worker` 会同时生成 `cloudflare-worker/_worker.js` 和 `releases/cloudflare-worker/_worker.js`。提交前建议直接跑 `npm run check:worker`。

**如何查看执行日志？** Cloudflare Dashboard → Workers → 你的 Worker → Logs。Wrangler 项目部署也可以用 `npm run tail`。

**Cloudflare Workers 免费计划够用吗？** 默认每天 4 次触发，每月约 120 次，请求量很低，通常适合免费计划。
