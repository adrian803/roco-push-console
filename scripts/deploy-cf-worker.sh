#!/usr/bin/env bash
set -euo pipefail

deploy_mode=""
worker_name=""
cloudflare_api_token=""
rocom_api_key=""
serverchan_sendkey=""
trigger_token=""
configure_secrets=0
non_interactive=0
skip_checks=0
skip_token_verify=0
dry_run=0

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
worker_dir="${repo_root}/cloudflare-worker"
wrangler_toml="${worker_dir}/wrangler.toml"
worker_js_path="${worker_dir}/_worker.js"
worker_js_temp_config="${worker_dir}/.wrangler-worker-js.tmp.toml"

usage() {
  cat <<'EOF'
用法：bash scripts/deploy-cf-worker.sh [选项]

默认交互式运行。常用选项：
  --mode source|worker-js       部署方式：source 为 npx 编译/项目部署，worker-js 为直接部署项目内 _worker.js
  --worker-name NAME            覆盖 wrangler.toml 中的 Worker 名称
  --configure-secrets           配置并上传 Worker secrets
  --non-interactive             非交互模式，不询问；缺少必要值时直接失败
  --cloudflare-api-token TOKEN  Cloudflare API Token
  --rocom-api-key KEY           ROCOM_API_KEY secret
  --serverchan-sendkey KEY      SERVERCHAN_SENDKEY secret
  --trigger-token TOKEN         可选 TRIGGER_TOKEN secret
  --skip-checks                 source 模式跳过 npm test、tsc 和 _worker.js 同步检查
  --skip-token-verify           跳过 Cloudflare Token 验证
  --dry-run                     只构建/预演部署，不发布 Worker
  -h, --help                    显示帮助
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --mode) shift; deploy_mode="${1:-}" ;;
    --worker-name) shift; worker_name="${1:-}" ;;
    --configure-secrets) configure_secrets=1 ;;
    --non-interactive) non_interactive=1 ;;
    --cloudflare-api-token) shift; cloudflare_api_token="${1:-}" ;;
    --rocom-api-key) shift; rocom_api_key="${1:-}" ;;
    --serverchan-sendkey) shift; serverchan_sendkey="${1:-}" ;;
    --trigger-token) shift; trigger_token="${1:-}" ;;
    --skip-checks) skip_checks=1 ;;
    --skip-token-verify) skip_token_verify=1 ;;
    --dry-run) dry_run=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "未知选项：$1" >&2; usage; exit 2 ;;
  esac
  shift
done

step() {
  printf '\n==> %s\n' "$1"
}

ask_yes_no() {
  prompt="$1"
  default="${2:-yes}"
  if [ "$default" = "yes" ]; then
    suffix="[Y/n]"
  else
    suffix="[y/N]"
  fi
  while true; do
    printf '%s %s ' "$prompt" "$suffix" >&2
    IFS= read -r answer
    answer="$(printf '%s' "$answer" | tr '[:upper:]' '[:lower:]')"
    if [ -z "$answer" ]; then
      [ "$default" = "yes" ]
      return
    fi
    case "$answer" in
      y|yes) return 0 ;;
      n|no) return 1 ;;
      *) echo "请输入 y 或 n。" >&2 ;;
    esac
  done
}

read_deploy_mode() {
  while true; do
    printf '\n请选择部署方式：\n' >&2
    printf '  1. npx 编译/项目部署（src/index.ts + wrangler.toml，推荐）\n' >&2
    printf '  2. 直接部署项目内 _worker.js（不重新生成 _worker.js）\n' >&2
    printf '请输入 1 或 2，直接回车默认 1: ' >&2
    IFS= read -r answer
    case "$answer" in
      ""|1) printf 'source'; return ;;
      2) printf 'worker-js'; return ;;
      *) echo "输入无效，请输入 1 或 2。" >&2 ;;
    esac
  done
}

read_secret() {
  prompt="$1"
  optional="${2:-no}"
  printf '%s: ' "$prompt" >&2
  IFS= read -r -s value
  printf '\n' >&2
  if [ "$optional" != "yes" ] && [ -z "$value" ]; then
    echo "$prompt 不能为空。" >&2
    exit 1
  fi
  printf '%s' "$value"
}

run_cmd() {
  "$@"
}

get_configured_worker_name() {
  sed -nE 's/^[[:space:]]*name[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/p' "$wrangler_toml" | head -n 1
}

create_temp_wrangler_config() {
  main_file="$1"
  sed -E \
    -e "s#^[[:space:]]*name[[:space:]]*=.*#name = \"${worker_name}\"#" \
    -e "s#^[[:space:]]*main[[:space:]]*=.*#main = \"${main_file}\"#" \
    "$wrangler_toml" > "$worker_js_temp_config"
  printf '%s' "$worker_js_temp_config"
}

set_worker_secret() {
  name="$1"
  value="$2"
  if [ -z "$value" ]; then
    return
  fi
  step "写入 Worker secret：wrangler secret put ${name}"
  printf '%s' "$value" | npx wrangler secret put "$name" --name "$worker_name"
}

extract_worker_host() {
  sed -nE 's#.*https://([A-Za-z0-9.-]+\.workers\.dev).*#\1#p' "$1" | head -n 1
}

cleanup() {
  rm -f "$worker_js_temp_config"
  if [ "$had_token" -eq 1 ]; then
    export CLOUDFLARE_API_TOKEN="$previous_token"
  elif [ "$token_was_set_by_script" -eq 1 ]; then
    unset CLOUDFLARE_API_TOKEN
  fi
}

if [ ! -d "$worker_dir" ]; then
  echo "找不到 cloudflare-worker 目录：$worker_dir" >&2
  exit 1
fi
if [ ! -f "$wrangler_toml" ]; then
  echo "找不到 wrangler.toml：$wrangler_toml" >&2
  exit 1
fi

case "$deploy_mode" in
  ""|source|worker-js) ;;
  Source) deploy_mode="source" ;;
  WorkerJs|workerjs|worker-js) deploy_mode="worker-js" ;;
  *) echo "--mode 只能是 source 或 worker-js。" >&2; exit 2 ;;
esac

had_token=0
previous_token=""
token_was_set_by_script=0
if [ "${CLOUDFLARE_API_TOKEN+x}" = "x" ]; then
  had_token=1
  previous_token="$CLOUDFLARE_API_TOKEN"
fi
trap cleanup EXIT

has_secret_input=0
if [ -n "$rocom_api_key" ] || [ -n "$serverchan_sendkey" ] || [ -n "$trigger_token" ]; then
  has_secret_input=1
fi

if [ -z "$deploy_mode" ]; then
  if [ "$non_interactive" -eq 1 ]; then
    deploy_mode="source"
  else
    deploy_mode="$(read_deploy_mode)"
  fi
fi

default_worker_name="$(get_configured_worker_name)"
if [ -z "$worker_name" ]; then
  worker_name="$default_worker_name"
fi
if [ -z "$worker_name" ]; then
  echo "无法从 wrangler.toml 读取 Worker 名称。" >&2
  exit 1
fi

if [ "$non_interactive" -eq 0 ]; then
  if [ "$deploy_mode" = "worker-js" ]; then
    mode_label="直接部署项目内 _worker.js"
  else
    mode_label="npx 编译/项目部署"
  fi
  printf '\nCloudflare Worker 交互式部署\n'
  printf '部署方式：%s\n' "$mode_label"
  printf 'Worker 名称：%s\n' "$worker_name"
  printf '如需修改 Worker 名称请输入新名称，直接回车保持不变: ' >&2
  IFS= read -r custom_name
  if [ -n "$custom_name" ]; then
    worker_name="$custom_name"
  fi

  if [ "$deploy_mode" = "source" ] && [ "$skip_checks" -eq 0 ]; then
    if ! ask_yes_no "部署前运行测试和检查吗？" yes; then
      skip_checks=1
    fi
  fi
  if [ "$dry_run" -eq 0 ] && [ "$configure_secrets" -eq 0 ] && [ "$has_secret_input" -eq 0 ]; then
    if ask_yes_no "现在配置 Worker secrets 吗？" yes; then
      configure_secrets=1
    fi
  fi
fi

if [ "$dry_run" -eq 0 ]; then
  if [ -n "$cloudflare_api_token" ]; then
    export CLOUDFLARE_API_TOKEN="$cloudflare_api_token"
    token_was_set_by_script=1
  elif [ -z "${CLOUDFLARE_API_TOKEN:-}" ]; then
    if [ "$non_interactive" -eq 1 ]; then
      echo "非交互模式需要先设置 CLOUDFLARE_API_TOKEN，或传入 --cloudflare-api-token。" >&2
      exit 1
    fi
    export CLOUDFLARE_API_TOKEN="$(read_secret "Cloudflare API Token" no)"
    token_was_set_by_script=1
  fi

  if [ "$skip_token_verify" -eq 0 ]; then
    step "验证 Cloudflare API Token"
    curl -fsS \
      -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
      "https://api.cloudflare.com/client/v4/user/tokens/verify" |
      grep -q '"success":true'
  fi
fi

cd "$worker_dir"

step "安装 Worker 依赖：npm ci"
run_cmd npm ci

active_config="$wrangler_toml"
if [ "$deploy_mode" = "source" ]; then
  if [ "$worker_name" != "$default_worker_name" ]; then
    active_config="$(create_temp_wrangler_config "src/index.ts")"
  fi
  if [ "$skip_checks" -eq 0 ]; then
    step "运行 Worker 单元测试：npm test"
    run_cmd npm test

    step "运行 TypeScript 类型检查：npx tsc --noEmit"
    run_cmd npx tsc --noEmit

    step "检查 _worker.js 是否同步：npm run check:worker"
    run_cmd npm run check:worker
  fi
else
  if [ ! -f "$worker_js_path" ]; then
    echo "_worker.js 不存在：$worker_js_path" >&2
    exit 1
  fi
  step "使用现有 _worker.js，不重新生成"
  active_config="$(create_temp_wrangler_config "_worker.js")"
fi

if [ "$dry_run" -eq 1 ] && { [ "$configure_secrets" -eq 1 ] || [ "$has_secret_input" -eq 1 ]; }; then
  echo "Dry Run 会跳过 Worker secrets 配置。" >&2
fi

if [ "$dry_run" -eq 0 ] && { [ "$configure_secrets" -eq 1 ] || [ "$has_secret_input" -eq 1 ]; }; then
  if [ -z "$rocom_api_key" ] && [ "$configure_secrets" -eq 1 ]; then
    if [ "$non_interactive" -eq 1 ]; then
      echo "非交互模式使用 --configure-secrets 时必须传入 --rocom-api-key。" >&2
      exit 1
    fi
    rocom_api_key="$(read_secret "ROCOM_API_KEY" no)"
  fi
  if [ -z "$serverchan_sendkey" ] && [ "$configure_secrets" -eq 1 ] && [ "$non_interactive" -eq 0 ]; then
    serverchan_sendkey="$(read_secret "SERVERCHAN_SENDKEY（可留空跳过）" yes)"
  fi
  if [ -z "$trigger_token" ] && [ "$configure_secrets" -eq 1 ] && [ "$non_interactive" -eq 0 ]; then
    trigger_token="$(read_secret "TRIGGER_TOKEN（可留空跳过）" yes)"
  fi

  set_worker_secret "ROCOM_API_KEY" "$rocom_api_key"
  set_worker_secret "SERVERCHAN_SENDKEY" "$serverchan_sendkey"
  set_worker_secret "TRIGGER_TOKEN" "$trigger_token"
fi

if [ "$dry_run" -eq 1 ]; then
  step "执行 Wrangler Dry Run：wrangler deploy --dry-run"
  run_cmd npx wrangler deploy --config "$active_config" --dry-run --outdir dist
  printf '\nDry Run 完成，没有发布 Worker。\n'
  exit 0
fi

step "发布 Cloudflare Worker：wrangler deploy"
deploy_log="$(mktemp)"
npx wrangler deploy --config "$active_config" 2>&1 | tee "$deploy_log"
worker_host="$(extract_worker_host "$deploy_log")"
rm -f "$deploy_log"

if [ -n "$worker_host" ]; then
  step "检查 Worker 根路径健康状态"
  curl -fsS "https://${worker_host}/" | grep -q '"ok":true'
  printf '\n部署成功：https://%s/\n' "$worker_host"
else
  printf '\n部署成功。Wrangler 没有输出 workers.dev 地址，已跳过自动健康检查。\n'
fi
