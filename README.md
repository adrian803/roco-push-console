# 洛克王国世界远行商人推送控制台

[![Docker Image](https://img.shields.io/badge/docker-linxi5013%2Froco--serverchan--notifier-2496ed?logo=docker&logoColor=white)](https://hub.docker.com/r/linxi5013/roco-serverchan-notifier)
[![CI](https://github.com/adrian803/roco-serverchan-notifier/actions/workflows/ci.yml/badge.svg)](https://github.com/adrian803/roco-serverchan-notifier/actions/workflows/ci.yml)
[![Cloudflare Workers](https://img.shields.io/badge/Cloudflare%20Workers-_worker.js-F6821F?logo=cloudflare&logoColor=white)](cloudflare-worker/_worker.js)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

监控《洛克王国世界》远行商人刷新状态的推送服务。提供 **Docker 部署**（含 Web 控制台）、**GitHub Actions 定时推送**和 **Cloudflare Workers 免费托管**三种方式，将刷新结果推送到 12 种主流推送通道。

推送内容以文字和 Markdown 为主，不内置图片渲染和图片推送逻辑。

> 本项目基于 [Entropy-Increase-Team](https://github.com/Entropy-Increase-Team/) 提供的《洛克王国世界》数据源开发，只负责查询、整理和推送结果，不提供也不分发数据源 `ROCOM_API_KEY`。

## 项目简介

- 支持 12 种推送通道：Server 酱、PushPlus、Telegram、Discord、企业微信、Bark、钉钉、飞书、ntfy、Gotify 等
- 默认北京时间 `08:05,12:05,16:05,20:05` 推送，正好卡在远行商人刷新后 5 分钟
- 支持多通道同时发送、单通道发送、主备失败切换三种策略
- Docker 版自带 Web 控制台，适合页面化配置和手动测试通道
- 敏感字段保存后不回显，推送异常和 HTTP 错误会自动脱敏

## 截图

| 登录页 | 控制台 |
|:------:|:------:|
| <img src="docs/images/login.png" alt="登录页" width="380"> | <img src="docs/images/console.png" alt="控制台" width="380"> |

Server 酱推送效果：

<img src="docs/images/serverchan-push.png" alt="Server 酱推送效果" width="320">

## 部署方式选择

| | Docker | GitHub Actions | Cloudflare Workers |
|---|:---:|:---:|:---:|
| **需要服务器** | 是 | 否 | 否 |
| **Web 控制台** | 有 | 无 | 无 |
| **费用** | 服务器费用 | 免费 | 免费 |
| **定时精确度** | 精确到秒 | 延迟几分钟 | 延迟 1-2 分钟 |
| **长期稳定性** | 高 | 中（可能被暂停） | 高 |
| **配置方式** | 页面 / 环境变量 | GitHub Secrets / Variables | Worker 控制台变量 / Wrangler |
| **适合场景** | 长期运行、需要 Web 管理 | 已有 GitHub 仓库、偶尔使用 | 免费长期托管 |

**怎么选：**

- 想最快完成第一次成功推送，而且希望以后都在网页里改配置：选 **Docker Web 控制台**
- 想免费长期托管，不想维护服务器：选 **Cloudflare Workers**
- 已经在用 GitHub 仓库，并且能接受偶发延迟：选 **GitHub Actions**

## 快速开始

下面保留三条最常用的首次部署路径。想看完整部署方式、更新方法和迁移说明，请直接跳到 [文档导航](#文档导航)。

### Docker 自动托管

适合已经知道自己要用哪个推送通道，只想尽快跑起来。

```bash
docker run -d \
  --name roco-serverchan-notifier \
  --restart unless-stopped \
  -e ROCOM_API_KEY=你的接口Key \
  -e SERVERCHAN_SENDKEY=你的Server酱SendKey \
  linxi5013/roco-serverchan-notifier:latest
```

这种模式不会监听 `19892`，不需要配置 `CONSOLE_USERNAME`、`CONSOLE_PASSWORD`、`WEB_PORT`。如果你想换成 PushPlus、Telegram 等其他通道，变量名见 [环境变量参考](docs/reference/environment-variables.md)。

### Docker Web 控制台

适合想通过页面管理配置、测试通道、观察运行状态的场景。

```bash
docker run -d \
  --name roco-serverchan-notifier \
  --restart unless-stopped \
  -p 19892:19892 \
  -v ./data:/data \
  -e APP_MODE=web \
  -e CONSOLE_USERNAME=admin \
  -e CONSOLE_PASSWORD=你的控制台密码 \
  linxi5013/roco-serverchan-notifier:latest
```

启动后打开 `http://服务器IP:19892`。如果你更习惯 `docker compose`，可以从 [.env.example](.env.example) 起步，再配合 [环境变量参考](docs/reference/environment-variables.md) 使用。

### Cloudflare Workers（控制台粘贴）

适合想免费长期托管，又不想准备本地 Node.js 环境的场景。

1. 打开 Cloudflare Dashboard → Workers & Pages → Create Worker
2. 删除默认代码，把 [cloudflare-worker/_worker.js](cloudflare-worker/_worker.js) 的完整内容粘贴进去并保存部署
3. 在 Settings → Variables and Secrets 中至少添加：

| 名称 | 说明 |
|------|------|
| `ROCOM_API_KEY` | 数据源接口 Key（必需） |
| `SERVERCHAN_SENDKEY` | Server 酱 SendKey；也可以换成其他任一推送通道 |
| `TRIGGER_TOKEN` | 可选，用来保护 `/trigger` 手动触发端点 |

4. 在 Triggers → Cron Triggers 中添加 `5 0,4,8,12 * * *`
5. 访问 `https://<worker名>.workers.dev/`，确认返回健康检查结果

如果想用 Workers Builds、Wrangler 项目部署或仓库自带的一键脚本（[Windows PowerShell](scripts/deploy-cf-worker.ps1) / [Windows 双击](scripts/deploy-cf-worker.cmd) / [Linux / macOS](scripts/deploy-cf-worker.sh)），请看 [Cloudflare Workers 完整部署指南](docs/deployment/cloudflare-workers.md)。

## 首次配置

### Docker Web 控制台

进入控制台后按这个顺序配置最稳：

1. **基础配置**：填写 `ROCOM_API_KEY`
2. **数据接口**：通常保持默认即可
3. **北京时间定时**：默认 `08:05,12:05,16:05,20:05`
4. **通道配置**：添加一个推送通道并填入 token / webhook
5. 点击单通道 **测试**，确认能收到消息
6. 选择发送策略并 **保存配置**
7. 点击 **立即执行** 做一次手动检查

配置保存到 `./data/config.json`。后续如果页面和 `.env` 不一致，优先以 `config.json` 为准。

### 环境变量模式（Docker 自动托管 / Workers / GitHub Actions）

不走 Web 控制台时，首次成功推送至少需要 `ROCOM_API_KEY` 加上一个推送通道变量。完整字段说明见 [环境变量参考](docs/reference/environment-variables.md) 和 [推送通道与发送策略](docs/reference/providers-and-delivery.md)。

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

如果 `CONSOLE_PASSWORD` 为空，控制台首次启动时会随机生成强密码，并在日志中打印 `控制台默认密码: ...`。Docker Compose 用户可运行 `docker compose logs roco-serverchan-notifier` 查看。密码哈希会保存到 `./data/config.json` 的 `console_auth` 段，后续重启沿用同一密码且不会再次打印明文。

忘记密码时，可以临时设置 `CONSOLE_PASSWORD=新密码` 覆盖登录，或停止容器后删除 `./data/config.json` 里的 `console_auth` 段再重启，让程序重新生成默认密码。仅在可信本机环境调试时，可以显式设置 `CONSOLE_ALLOW_EMPTY_PASSWORD=true` 允许空密码。

</details>

<details>
<summary><b>为什么没有启动 Web 控制台？</b></summary>

默认 `APP_MODE=auto` 会在配置齐全时只启动调度器，不监听 `19892`。设置 `APP_MODE=web` 后重建容器即可强制启动。

</details>

<details>
<summary><b>为什么修改 .env 后页面没变？</b></summary>

控制台保存过配置后，会优先读取 `./data/config.json`。后续更推荐在 Web 控制台修改；如要完全使用 `.env` 默认值，需先备份并移走 `config.json`。

</details>

<details>
<summary><b>为什么收不到推送？</b></summary>

**Docker 版：** 先在“通道配置”里点击单通道“测试”。如果测试失败，检查 token / webhook 是否正确、服务商是否限流、服务器是否能访问对应推送服务。

**Cloudflare Workers 版：** 手动触发 `curl <worker-url>/trigger`，查看返回结果。若配置了 `TRIGGER_TOKEN`，使用 `curl '<worker-url>/trigger?token=你的token'`。执行日志优先在 Cloudflare Dashboard → Workers → 你的 Worker → Logs 查看；Wrangler 项目部署也可以在 `cloudflare-worker` 目录运行 `npm run tail`。

**GitHub Actions 版：** 查看 Actions 运行日志，确认 secrets 是否配置正确。完整说明见 [GitHub Actions 定时推送说明](docs/deployment/github-actions.md)。

</details>

<details>
<summary><b>GitHub Actions 定时不准怎么办？</b></summary>

GitHub Actions 的 cron 不保证精确执行，可能延迟几分钟，仓库长期不活跃还会被暂停。推荐迁移到 [Cloudflare Workers](docs/deployment/cloudflare-workers.md)，同样免费但更稳定。

</details>

<details>
<summary><b>如何更新到最新版本？</b></summary>

- **Docker：** `docker compose pull && docker compose up -d`
- **Cloudflare Workers：** 按部署方式更新，见 [Cloudflare Workers 完整部署指南](docs/deployment/cloudflare-workers.md)
- **GitHub Actions：** 同步默认分支上的 workflow 和代码即可，见 [GitHub Actions 定时推送说明](docs/deployment/github-actions.md)

</details>

## 安全提醒

### Docker 版

- 默认 `APP_MODE=auto`：配置齐时容器只启动调度器，不启动 Web 控制台；缺少配置时才启动控制台方便首次配置
- 如果使用 `APP_MODE=web`，控制台会监听 `0.0.0.0:19892`；公开部署前请设置强密码，并限制访问来源
- `CONSOLE_PASSWORD` 为空时会在首次启动生成默认强密码，明文只出现在启动日志里
- 不要提交 `./data/config.json`，其中可能包含推送 token、接口 Key 和控制台密码哈希

### Cloudflare Workers 版

- Secrets 通过 Cloudflare Worker 控制台加密存储，不会出现在仓库代码里
- `/trigger` 默认开放；如果 Worker URL 会被分享，建议配置 `TRIGGER_TOKEN`
- 使用一键脚本或 Wrangler 时，不要把 `CLOUDFLARE_API_TOKEN` 留在长期 shell 环境里

## 文档导航

### 部署

- [Cloudflare Workers 完整部署指南](docs/deployment/cloudflare-workers.md)
- [GitHub Actions 定时推送说明](docs/deployment/github-actions.md)

### 配置

- [环境变量参考](docs/reference/environment-variables.md)
- [推送通道与发送策略](docs/reference/providers-and-delivery.md)
- [.env.example](.env.example)

### 开发与维护

- [DEVELOPMENT.md](DEVELOPMENT.md)
- Python / Worker 的测试、构建与 `_worker.js` 同步检查命令统一写在 `DEVELOPMENT.md`

## 贡献 / 许可 / 鸣谢

欢迎提交 issue 和 pull request。适合贡献的方向：

- 新推送通道
- 控制台交互优化
- 部署文档和参考文档改进
- 测试用例

如果要新增推送通道、调整调度器、修改控制台认证或改 Worker 构建流程，请先阅读 [DEVELOPMENT.md](DEVELOPMENT.md)。

远行商人数据来自 [Entropy-Increase-Team](https://github.com/Entropy-Increase-Team/) 提供的接口。本仓库只负责调用接口并展示、推送结果，不内置、不分发 `ROCOM_API_KEY`，也不代为申请 Key。请按数据源项目或相关社区的规则获取 Key。

本项目不会绕过数据源服务端限制，接口调用频率以数据源后端实际限制为准。请合理设置定时任务，避免给数据源服务带来不必要的压力。

本项目是个人学习和自用工具，和游戏官方、WeGame、各推送平台均无从属关系。若需直接使用或改造 Entropy-Increase-Team 的代码，会按其 AGPL-3.0 协议要求处理。

本项目使用 [MIT License](LICENSE)。
