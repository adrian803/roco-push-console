# 洛克王国世界远行商人推送控制台

[![Docker Image](https://img.shields.io/badge/docker-linxi5013%2Froco--push--console-2496ed?logo=docker&logoColor=white)](https://hub.docker.com/r/linxi5013/roco-push-console)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

一个用于监控《洛克王国世界》远行商人刷新状态的 Docker 常驻服务。项目提供 Web 控制台，也支持只配置必要 Key 后自动进入无控制台托管模式，并把刷新结果推送到微信、企业微信、飞书、钉钉、Bark、ntfy、Gotify 等服务。

目前推送内容以文字和 Markdown 为主，方便在不同推送平台之间保持一致；项目不内置图片渲染和图片推送逻辑。

## 截图

登录页：

<img src="docs/images/login.png" alt="登录页" width="760">

控制台：

<img src="docs/images/console.png" alt="控制台" width="760">

Server 酱推送效果：

<img src="docs/images/serverchan-push.png" alt="Server 酱推送效果" width="420">

## 功能

- Docker 常驻运行，控制台默认端口 `19892`
- Web 控制台管理配置，无需反复改环境变量
- 支持自动托管模式，配置齐 `ROCOM_API_KEY` 和任一推送通道 Key 后不启动 Web UI
- 默认定时在远行商人刷新后 5 分钟推送，减少数据源同步延迟带来的空推送
- 配置持久化到 `./data/config.json`
- 支持多通道同时发送、单通道发送、主备失败切换
- 支持单通道测试和按当前策略测试
- 敏感字段保存后不回显，页面显示“已配置，留空不改”
- 推送异常、HTTP 错误和服务商返回详情会脱敏，避免 token / readkey 出现在控制台状态区和 Docker 日志里
- 读取损坏配置时自动备份原文件，避免直接覆盖旧配置
- 容器启动时自动修正 `/data` 目录权限，适配 WSL / bind mount 场景

## 来源与鸣谢

远行商人数据来自 [Entropy-Increase-Team](https://github.com/Entropy-Increase-Team/) 提供的接口。本仓库只负责调用接口并展示、推送结果，不内置、不分发 `ROCOM_API_KEY`，也不代为申请 Key。请按数据源项目或相关社区的规则获取 Key；如果后续数据源项目提供官方前端，也可以按其官方流程自行注册获取。

本项目不会绕过数据源服务端限制，接口调用频率以数据源后端实际限制为准。请合理设置定时任务，避免给数据源服务带来不必要的压力。

### 许可说明

本仓库自有代码使用 MIT License。第三方项目、数据接口和推送平台仍遵循各自的许可证与服务条款。

已询问过数据源项目提供方，本项目只是调用 Entropy-Increase-Team 的接口，像现在这样标注数据来源即可。若需直接使用、复制或改造其项目代码，则会按其 AGPL-3.0 协议要求处理：保留相应版权和协议标注，并公开相关修改源码。

## 安全提醒

默认 `APP_MODE=auto`：当 `ROCOM_API_KEY` 和任一推送通道 Key 已配置时，容器只启动调度器，不启动 Web 控制台；缺少必要配置时才会启动 Web 控制台方便首次配置。

如果显式使用 `APP_MODE=web`，或因为缺少 Key 进入控制台模式，`docker-compose.yml` 会让容器内控制台监听 `0.0.0.0`，并发布到宿主机 `19892` 端口；同时 `CONSOLE_PASSWORD` 为空时会关闭 Web 控制台认证。这对本地首次部署比较方便，但如果机器能被局域网或公网访问，就等同于把管理端暴露出去。

公开部署或共享服务器上至少要做这几件事：

- 在 `.env` 里设置强密码：`CONSOLE_PASSWORD=换成你的控制台密码`
- 只在可信网络内开放 `19892`，或用防火墙 / 反向代理限制访问来源
- 如果只想本机访问，把 compose 端口改成 `127.0.0.1:${WEB_PORT:-19892}:19892`
- 不要提交或公开 `./data/config.json`，里面会明文保存推送 token 和接口 Key

## 快速开始

### 方式一：只配置 Key 自动托管

适合不想使用 Web UI、只想运行起来后长期托管的场景。只填数据源 Key 和一种推送通道 Key 即可，默认会在 `08:05,12:05,16:05,20:05` 推送，也就是远行商人刷新后 5 分钟。

Server 酱最小示例：

```bash
docker run -d \
  --name roco-push-console \
  --restart unless-stopped \
  -e ROCOM_API_KEY=换成你的接口Key \
  -e SERVERCHAN_SENDKEY=换成你的Server酱SendKey \
  linxi5013/roco-push-console:latest
```

也可以换成其他推送通道，只填对应通道需要的环境变量。例如 PushPlus：

```bash
docker run -d \
  --name roco-push-console \
  --restart unless-stopped \
  -e ROCOM_API_KEY=换成你的接口Key \
  -e PUSHPLUS_TOKEN=换成你的PushPlusToken \
  linxi5013/roco-push-console:latest
```

这种模式不会监听 `19892`，也不需要配置 `CONSOLE_USERNAME`、`CONSOLE_PASSWORD`、`WEB_PORT`。

### 方式二：Docker Hub 镜像 + Web 控制台

如果想通过页面配置和测试通道，显式设置 `APP_MODE=web`：

```bash
docker run -d \
  --name roco-push-console \
  --restart unless-stopped \
  -p 19892:19892 \
  -v ./data:/data \
  -e APP_MODE=web \
  -e CONSOLE_USERNAME=admin \
  -e CONSOLE_PASSWORD=换成你的控制台密码 \
  linxi5013/roco-push-console:latest
```

启动后打开：

```text
http://服务器IP:19892
```

### 方式三：docker compose

```bash
git clone https://github.com/adrian803/roco-push-console.git
cd roco-push-console
cp .env.example .env
```

如果想自动托管，只在 `.env` 里设置必需 Key：

```env
ROCOM_API_KEY=换成你的接口Key
SERVERCHAN_SENDKEY=换成你的Server酱SendKey
```

启动：

```bash
docker compose up -d
```

本地重新构建：

```bash
docker compose up -d --build
```

如果想使用 Web 控制台，在 `.env` 里显式设置：

```env
APP_MODE=web
CONSOLE_USERNAME=admin
CONSOLE_PASSWORD=换成你的控制台密码
WEB_PORT=19892
```

可用镜像标签：

```bash
docker pull linxi5013/roco-push-console:latest
```

### 无控制台模式说明

`APP_MODE=auto` 会自动判断：配置齐 `ROCOM_API_KEY` 和任一推送通道 Key 时进入无控制台调度；缺配置时进入 Web 控制台。也可以显式设置 `APP_MODE=scheduler` 强制无控制台运行。

如果同时填写多个推送通道变量，程序会把它们都启用。默认发送策略是 `all`，也就是同时发送；需要主备切换时可以设置 `DELIVERY_MODE=failover`。

## 首次配置

进入控制台后按这个顺序配置：

1. 在“基础配置”填写 `ROCOM_API_KEY`。
2. 确认“数据接口”，通常保持默认即可。
3. 设置“北京时间定时”，默认是 `08:05,12:05,16:05,20:05`，也就是远行商人刷新后 5 分钟再推送，给数据源留一点同步时间。
4. 在“通道配置”添加推送通道，填写对应 token / webhook。
5. 点击单个通道的“测试”，确认能收到测试消息。
6. 选择发送策略并保存配置。
7. 点击“立即执行”做一次手动检查。

配置保存后会写入：

```text
./data/config.json
```

## 推送通道

| 通道                    | 必填配置                        | 说明                                |
| ----------------------- | ------------------------------- | ----------------------------------- |
| Server 酱               | SendKey                         | 通过 Server 酱推送到微信            |
| PushPlus                | Token                           | 支持 topic、channel，默认 Markdown  |
| Wecom 酱 / 企业微信应用 | CorpID、Secret、AgentID、接收人 | 自动获取并缓存企业微信 access token |
| 企业微信群机器人        | Webhook 或 Key                  | 发送 Markdown 消息                  |
| WxPusher                | AppToken                        | 支持 UID 列表或 Topic ID 列表       |
| Bark                    | Server URL、Device Key          | 推送到 iOS Bark                     |
| 钉钉群机器人            | Webhook                         | 可选 secret 加签                    |
| 飞书群机器人            | Webhook                         | 可选 secret 加签                    |
| ntfy                    | Base URL、Topic                 | 可选 bearer token、priority、tags   |
| Gotify                  | Base URL、App Token             | 可配置 priority                     |

### 通道卡片说明

每个通道卡片只展示日常会用到的配置：

- `名称`：给自己看的显示名，比如“我的 Server 酱”“备用 PushPlus”。
- `启用`：关闭后该通道不会参与发送。
- 服务商参数：例如 Server 酱的 `SendKey`、PushPlus 的 `Token`、企业微信机器人的 `Webhook`。

程序内部会自动为每个通道生成稳定 ID，用来保存配置、测试单个通道和执行主备切换。这个 ID 对普通使用没有实际操作意义，所以控制台不展示，也不需要手动填写。

如果使用“主备切换，成功即停”，发送顺序就是页面里的通道卡片顺序。可以用卡片右上角的“上移”“下移”调整优先级，越靠上越先尝试。

## 发送策略

| 策略                 | 行为                                             |
| -------------------- | ------------------------------------------------ |
| 所有启用通道同时发送 | 向全部启用通道发送，至少一个成功即认为本轮有送达 |
| 只发送选中通道       | 只向下拉框选中的通道发送                         |
| 主备切换，成功即停   | 按页面通道列表顺序尝试启用通道，第一个成功后停止 |

## 环境变量

`.env` 里的 `ROCOM_API_KEY`、推送通道 Key 和定时时间会作为默认配置读取。使用 Web 控制台保存过配置后，会优先读取 `./data/config.json`；使用自动托管或无控制台模式时，可以只维护 `.env` 或 `docker run -e` 参数。

| 变量                     | 默认值                               | 说明                                                     |
| ------------------------ | ------------------------------------ | -------------------------------------------------------- |
| `DOCKER_IMAGE`           | `linxi5013/roco-push-console:latest` | compose 使用的镜像                                       |
| `APP_MODE`               | `auto`                               | 运行模式：`auto` 自动判断 / `web` 控制台 / `scheduler` 无控制台定时 / `once` 执行一次 |
| `WEB_PORT`               | `19892`                              | 宿主机访问端口                                           |
| `CONSOLE_USERNAME`       | `admin`                              | 控制台用户名                                             |
| `CONSOLE_PASSWORD`       | 空                                   | 控制台密码；为空时不启用认证，部署到可访问网络前必须设置 |
| `CONSOLE_SESSION_TTL`    | `86400`                              | 控制台登录态有效期，单位秒                               |
| `CONSOLE_SESSION_SECRET` | 空                                   | Cookie 签名密钥；默认使用控制台密码                      |
| `ROCOM_API_KEY`          | 空                                   | 首次启动默认 WeGame 接口 Key                             |
| `ROCOM_API_URL`          | 空                                   | 自定义 WeGame 数据接口，保持空使用内置默认值             |
| `SERVERCHAN_SENDKEY`     | 空                                   | 兼容旧配置，首次启动时创建 Server 酱通道                 |
| `DELIVERY_MODE`          | `all`                                | 首次启动默认发送策略：`all` / `single` / `failover`      |
| `SCHEDULE_TIMES`         | `08:05,12:05,16:05,20:05`            | 首次启动默认定时，默认在刷新后 5 分钟推送                 |
| `RUN_ON_START`           | `false`                              | 容器启动后是否立即执行一次                               |
| `NOTIFY_EMPTY`           | `false`                              | 没有商品时是否也推送                                     |
| `HTTP_TIMEOUT`           | `30`                                 | 请求超时秒数                                             |

### 无控制台通道变量

没有 `./data/config.json`，或配置文件还没有写入 `providers` 字段时，程序会根据下面这些环境变量自动创建推送通道。只填你要用的那一组即可。

| 通道                    | 最少需要填写                         | 可选变量                                                |
| ----------------------- | ------------------------------------ | ------------------------------------------------------- |
| Server 酱               | `SERVERCHAN_SENDKEY`                 | -                                                       |
| PushPlus                | `PUSHPLUS_TOKEN`                     | `PUSHPLUS_TOPIC`、`PUSHPLUS_CHANNEL`                    |
| Wecom 酱 / 企业微信应用 | `WECOM_CORPID`、`WECOM_SECRET`、`WECOM_AGENTID` | `WECOM_TOUSER`，默认 `@all`                 |
| 企业微信群机器人        | `WECOM_BOT_WEBHOOK` 或 `WECOM_BOT_KEY` | -                                                     |
| WxPusher                | `WXPUSHER_APP_TOKEN`                 | `WXPUSHER_UIDS`、`WXPUSHER_TOPIC_IDS`                   |
| Bark                    | `BARK_DEVICE_KEY`                    | `BARK_SERVER_URL`，默认 `https://api.day.app`；`BARK_GROUP` |
| 钉钉群机器人            | `DINGTALK_WEBHOOK`                   | `DINGTALK_SECRET`                                      |
| 飞书群机器人            | `FEISHU_WEBHOOK`                     | `FEISHU_SECRET`                                        |
| ntfy                    | `NTFY_TOPIC`                         | `NTFY_BASE_URL`，默认 `https://ntfy.sh`；`NTFY_TOKEN`、`NTFY_PRIORITY`、`NTFY_TAGS` |
| Gotify                  | `GOTIFY_BASE_URL`、`GOTIFY_APP_TOKEN` | `GOTIFY_PRIORITY`                                     |

## 常用命令

查看日志：

```bash
docker compose logs -f
```

重启：

```bash
docker compose restart
```

升级到最新镜像：

```bash
docker compose pull
docker compose up -d
```

停止并移除容器：

```bash
docker compose down
```

备份配置：

```bash
cp ./data/config.json ./config.backup.json
```

## 本地开发

环境准备：

```bash
uv sync --frozen
```

启动 Web 控制台：

```bash
uv run python -m roco_push_console.web
```

启动自动模式：

```bash
uv run python -m roco_push_console.launcher
```

一次性执行检查：

```bash
uv run python main.py
```

本地测试：

```bash
uv run python -m unittest discover -s tests
uv run python -m compileall -q src main.py tests
docker compose config --quiet
```

构建镜像：

```bash
docker build -t roco-push-console:latest .
```

## GitHub Actions

### CI 和测试目录

是的，如果希望 GitHub Actions 或 PR 检查运行：

```bash
uv run python -m unittest discover -s tests
uv run python -m compileall -q src main.py tests
docker compose config --quiet
```

就需要把 `tests/` 一起提交到 GitHub。仓库已提供 `.github/workflows/ci.yml`，会在 PR、`main` / `master` 分支 push、手动触发时运行这些检查。

### 自动构建和发布镜像

`.github/workflows/docker-publish.yml` 会在 `main` / `master` 分支 push、`v*.*.*` 标签、手动触发时构建并发布多架构镜像：

- `linux/amd64`
- `linux/arm64`

需要在 GitHub 仓库设置里添加 Secrets：

| 名称 | 说明 |
| ---- | ---- |
| `DOCKERHUB_USERNAME` | Docker Hub 用户名 |
| `DOCKERHUB_TOKEN` | Docker Hub Access Token |

可选添加 Repository Variable：

| 名称 | 默认值 | 说明 |
| ---- | ------ | ---- |
| `DOCKERHUB_REPOSITORY` | `linxi5013/roco-push-console` | 发布到 Docker Hub 的镜像名 |

如果没有配置 Docker Hub secrets，发布工作流会自动跳过推送，不会误报构建失败。

### GitHub Actions 免费定时推送

`.github/workflows/scheduled-push.yml` 可以不部署服务器，直接用 GitHub Actions 定时运行一次推送检查。默认 cron 对应北京时间 / 香港时间：

| 本地时间 | UTC cron |
| -------- | -------- |
| 08:05 | `5 0 * * *` |
| 12:05 | `5 4 * * *` |
| 16:05 | `5 8 * * *` |
| 20:05 | `5 12 * * *` |

最小配置是在 GitHub 仓库 `Settings -> Secrets and variables -> Actions` 里添加：

| 类型 | 名称 | 说明 |
| ---- | ---- | ---- |
| Secret | `ROCOM_API_KEY` | 数据源接口 Key |
| Secret | `SERVERCHAN_SENDKEY` | Server 酱 SendKey，或改用下面任一推送通道 Secret |

也可以使用其他推送通道，对应填写 `PUSHPLUS_TOKEN`、`WECOM_BOT_WEBHOOK`、`DINGTALK_WEBHOOK`、`FEISHU_WEBHOOK`、`BARK_DEVICE_KEY`、`NTFY_TOPIC`、`GOTIFY_APP_TOKEN` 等 Secrets；非敏感可选项如 `PUSHPLUS_TOPIC`、`DELIVERY_MODE`、`NOTIFY_EMPTY`、`HTTP_TIMEOUT` 可以放到 Repository Variables。

注意：GitHub Actions 的定时任务不是严格实时，实际执行可能延迟几分钟；定时任务只会在默认分支生效，仓库长期无活动也可能被 GitHub 暂停。想要最稳定的长期运行，仍建议使用 Docker 常驻托管。

### Cloudflare 等免费定时平台

Cloudflare Workers Cron Triggers 也可以做免费定时任务，但它不能像 GitHub Actions 一样直接执行本仓库的 `uv run python main.py` 或 Dockerfile。要接入 Cloudflare，需要单独写一个 Worker 适配器，或者让 Worker 定时调用一个已经部署好的 HTTP 接口。本仓库当前先提供 GitHub Actions 版定时推送，因为它能复用现有 Python 逻辑和全部推送通道。

## 常见问题

### 为什么打开控制台不需要密码？

`CONSOLE_PASSWORD` 为空时会关闭认证。部署到局域网或公网前请设置 `CONSOLE_PASSWORD`，或使用默认 `APP_MODE=auto` 并填齐 `ROCOM_API_KEY` 和推送通道 Key，让服务直接进入无控制台托管模式。

### 为什么没有启动 Web 控制台？

默认 `APP_MODE=auto` 会在配置齐全时只启动调度器，不监听 `19892`。如果你想强制使用页面配置，设置 `APP_MODE=web` 后重建或重启容器。

### 为什么提示缺少 `ROCOM_API_KEY`？

本项目不提供 API Key。请先按 [Entropy-Increase-Team](https://github.com/Entropy-Increase-Team/) 项目或相关社区的规则获取 `ROCOM_API_KEY`，再填入控制台或 `.env`。如果数据源项目后续开放官方注册入口，也可以按其官方流程自行获取。

### 为什么修改 `.env` 后页面没变？

控制台保存过配置后，会优先读取 `./data/config.json`。后续更推荐直接在 Web 控制台修改；如果要完全重新使用 `.env` 默认值，需要先备份并移走 `./data/config.json`。

### 为什么收不到推送？

先在“通道配置”里点击单通道“测试”。如果测试失败，检查 token / webhook 是否正确、服务商是否限流、服务器是否能访问对应推送服务。

### 配置文件损坏怎么办？

程序读取 `config.json` 失败时，会把损坏文件备份为 `config.json.invalid-时间戳.bak`，并在控制台状态区显示提示。

### 点击“保存配置”提示保存失败怎么办？

新版镜像启动时会自动修正 `/data` 目录权限。旧容器如果已经创建过 `./data`，尤其是在 Ubuntu WSL 里运行 Docker、并把项目目录 bind mount 到容器时，可能出现容器内应用用户无法写入 `/data/config.json.tmp` 的情况。

如果控制台保存时报 `Permission denied`，先在 WSL 的 Ubuntu 终端执行：

```bash
docker exec -u root roco-push-console chown -R app:app /data
```

然后刷新控制台再保存。长期建议更新到新版镜像并重建容器：

```bash
docker compose pull
docker compose up -d --force-recreate
```

## 路线图

- 支持更多推送平台
- 增加 Cloudflare Workers Cron 适配器
- 增加更完整的端到端测试

## 贡献

欢迎提交 issue 和 pull request。比较适合贡献的方向包括：

- 新推送通道
- 控制台交互优化
- Docker 部署文档
- 测试用例
- 不同平台的部署经验

提交 PR 前建议先运行：

```bash
uv run python -m unittest discover -s tests
uv run python -m compileall -q src main.py tests
docker compose config --quiet
```

## 免责声明

本项目是个人学习和自用工具，和游戏官方、WeGame、各推送平台均无从属关系。项目只保存使用者自行填写的接口 Key 和推送 token，不提供、不出售、不共享任何第三方 API Key。请遵守相关服务条款，不要滥用接口或推送能力。

## 许可

本项目使用 [MIT License](LICENSE)。
