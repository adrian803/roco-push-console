# GitHub Actions 定时推送说明

GitHub Actions 版适合已经在用 GitHub 仓库、又不想单独维护服务器的场景。它可以免费定时运行，但 cron 不保证精确执行，仓库长期不活跃时还可能被暂停。

如果你更看重长期稳定性，优先考虑 [Cloudflare Workers 完整部署指南](cloudflare-workers.md)。

## 目录

[适用场景](#适用场景) · [默认调度](#默认调度) · [配置步骤](#配置步骤) · [查看日志与排错](#查看日志与排错) · [其他工作流](#仓库里的其他-github-actions-工作流) · [限制与建议](#限制与建议) · [迁移到 Cloudflare Workers](#迁移到-cloudflare-workers)

## 适用场景

- 仓库已经托管在 GitHub
- 能接受执行时间偶发延迟几分钟
- 不需要 Web 控制台
- 希望用 GitHub 自带的 Secrets / Variables 管配置

## 默认调度

默认 cron 对应北京时间：

| 本地时间 | UTC cron |
|:--------:|:--------:|
| 08:05 | `5 0 * * *` |
| 12:05 | `5 4 * * *` |
| 16:05 | `5 8 * * *` |
| 20:05 | `5 12 * * *` |

如需调整，请修改 `.github/workflows/scheduled-push.yml` 中的 cron 表达式。

## 配置步骤

1. 进入仓库 → **Settings** → **Secrets and variables** → **Actions**
2. 至少添加下面这些 Secret：

| 名称 | 说明 |
|------|------|
| `ROCOM_API_KEY` | 数据源接口 Key（必需） |
| 一个推送通道 Secret | 例如 `SERVERCHAN_SENDKEY`、`PUSHPLUS_TOKEN`、`TELEGRAM_BOT_TOKEN` |

如果你还没确定先用哪条通道，建议先配 [Server 酱](https://sct.ftqq.com/r/1636)。当前仓库维护者主要实测的也是 Server 酱；该链接包含推荐参数，如后续发生付费订阅，可能为项目维护者带来佣金。

3. 需要时再添加 Repository Variables，例如：

| 名称 | 说明 |
|------|------|
| `DELIVERY_MODE` | `all` / `single` / `failover` |
| `NOTIFY_EMPTY` | 没有商品时是否仍发送通知 |
| `INCLUDE_PRICE_INFO` | 是否在推送正文里附带价格和限购信息 |
| `HTTP_TIMEOUT` | 请求超时秒数 |

4. 确认默认分支启用了 `.github/workflows/scheduled-push.yml`
5. 等待下一次 cron，或在 Actions 页面手动触发工作流进行验证

完整变量命名和推送通道字段说明见：

- [环境变量参考](../reference/environment-variables.md)
- [推送通道与发送策略](../reference/providers-and-delivery.md)

## 查看日志与排错

- GitHub 仓库 → **Actions**
- 点开 `scheduled-push.yml` 的某次运行，查看每个 step 的输出

排查时建议优先确认：

1. `ROCOM_API_KEY` 是否正确
2. 推送通道的 Secret 名是否和文档一致
3. 目标推送平台自身是否限流或拒绝请求
4. 如果用 `single` / `failover`，相关变量是否填了正确的 provider id

## 仓库里的其他 GitHub Actions 工作流

- `ci.yml`：PR 和 push 时运行测试 + 编译检查
- `docker-publish.yml`：自动构建并发布多架构镜像（`amd64` / `arm64`）到 Docker Hub
- `worker-release.yml`：发布 GitHub Release 时上传 `releases/cloudflare-worker/_worker.js` 附件

## 限制与建议

- GitHub Actions 的 cron 不保证精确执行，可能延迟几分钟
- 仓库长期不活跃时，定时任务可能被 GitHub 暂停
- 不支持 Web 控制台
- 如果你想免费长期托管并减少这类限制，推荐迁移到 [Cloudflare Workers](cloudflare-workers.md)

## 迁移到 Cloudflare Workers

1. 在 Cloudflare 控制台创建 Worker，并粘贴 [releases/cloudflare-worker/_worker.js](../../releases/cloudflare-worker/_worker.js)
2. 将 GitHub Actions Secrets 中的值迁移到 Worker 的 Variables and Secrets
3. 在 Triggers → Cron Triggers 中添加 `5 0,4,8,12 * * *`
4. 访问根路径 `/` 验证服务状态，再手动访问 `/trigger` 验证推送
5. 确认正常后，删除或停用 `.github/workflows/scheduled-push.yml`
