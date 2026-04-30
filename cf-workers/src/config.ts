import type { Config, Env, ProviderConfig } from "./types";
import { PROVIDER_TYPES } from "./provider-specs";

const DEFAULT_GAME_API_URL =
  "https://wegame.shallow.ink/api/v1/games/rocom/merchant/info";

interface EnvProviderMapping {
  type: string;
  envVars: Record<string, string>;
  envId: string;
}

const ENV_PROVIDER_MAPPINGS: EnvProviderMapping[] = [
  {
    type: "serverchan",
    envVars: { sendkey: "SERVERCHAN_SENDKEY" },
    envId: "serverchan-default",
  },
  {
    type: "pushplus",
    envVars: {
      token: "PUSHPLUS_TOKEN",
      topic: "PUSHPLUS_TOPIC",
      channel: "PUSHPLUS_CHANNEL",
    },
    envId: "pushplus-env",
  },
  {
    type: "wecomchan",
    envVars: {
      corpid: "WECOM_CORPID",
      secret: "WECOM_SECRET",
      agentid: "WECOM_AGENTID",
      touser: "WECOM_TOUSER",
    },
    envId: "wecomchan-env",
  },
  {
    type: "wecom_bot",
    envVars: { webhook: "WECOM_BOT_WEBHOOK", key: "WECOM_BOT_KEY" },
    envId: "wecom-bot-env",
  },
  {
    type: "wxpusher",
    envVars: {
      app_token: "WXPUSHER_APP_TOKEN",
      uids: "WXPUSHER_UIDS",
      topic_ids: "WXPUSHER_TOPIC_IDS",
    },
    envId: "wxpusher-env",
  },
  {
    type: "bark",
    envVars: {
      server_url: "BARK_SERVER_URL",
      device_key: "BARK_DEVICE_KEY",
      group: "BARK_GROUP",
    },
    envId: "bark-env",
  },
  {
    type: "dingtalk_bot",
    envVars: { webhook: "DINGTALK_WEBHOOK", secret: "DINGTALK_SECRET" },
    envId: "dingtalk-env",
  },
  {
    type: "feishu_bot",
    envVars: { webhook: "FEISHU_WEBHOOK", secret: "FEISHU_SECRET" },
    envId: "feishu-env",
  },
  {
    type: "ntfy",
    envVars: {
      base_url: "NTFY_BASE_URL",
      topic: "NTFY_TOPIC",
      token: "NTFY_TOKEN",
      priority: "NTFY_PRIORITY",
      tags: "NTFY_TAGS",
    },
    envId: "ntfy-env",
  },
  {
    type: "gotify",
    envVars: {
      base_url: "GOTIFY_BASE_URL",
      app_token: "GOTIFY_APP_TOKEN",
      priority: "GOTIFY_PRIORITY",
    },
    envId: "gotify-env",
  },
];

function envStr(env: Env, key: string): string {
  return (env[key as keyof Env] || "").trim();
}

function envBool(env: Env, key: string, defaultValue: boolean): boolean {
  const value = envStr(env, key);
  if (!value) return defaultValue;
  return ["1", "true", "yes", "on", "y"].includes(value.toLowerCase());
}

function envInt(env: Env, key: string, defaultValue: number): number {
  const value = envStr(env, key);
  if (!value) return defaultValue;
  const parsed = parseInt(value, 10);
  return isNaN(parsed) ? defaultValue : parsed;
}

function envCsv(env: Env, key: string): string[] {
  return envStr(env, key)
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildProviderFromEnv(
  env: Env,
  mapping: EnvProviderMapping
): ProviderConfig | null {
  const spec = PROVIDER_TYPES[mapping.type];
  if (!spec) return null;

  const config: Record<string, string> = {};
  let hasExplicitValue = false;

  for (const field of spec.fields) {
    const envKey = mapping.envVars[field.name];
    const value = envKey ? envStr(env, envKey) : "";
    if (value) {
      config[field.name] = value;
      hasExplicitValue = true;
    } else if (field.default) {
      config[field.name] = field.default;
    }
  }

  // Special case: wecom_bot needs webhook OR key
  if (mapping.type === "wecom_bot") {
    if (!config.webhook && !config.key) return null;
  } else {
    if (!hasExplicitValue) return null;
    const requiredFields = spec.fields.filter((f) => f.required);
    for (const field of requiredFields) {
      if (!(config[field.name] || "").trim()) return null;
    }
  }

  return {
    id: mapping.envId,
    type: mapping.type,
    name: spec.label,
    enabled: true,
    config,
  };
}

export function loadConfig(env: Env): Config {
  const providers: ProviderConfig[] = [];
  for (const mapping of ENV_PROVIDER_MAPPINGS) {
    const provider = buildProviderFromEnv(env, mapping);
    if (provider) providers.push(provider);
  }

  const deliveryMode = envStr(env, "DELIVERY_MODE") || "all";
  const enabledProviderIds = providers.filter((p) => p.enabled).map((p) => p.id);
  const defaultProviderId = enabledProviderIds[0] || "";
  const requestedProviderId = envStr(env, "SELECTED_PROVIDER");
  const selectedProvider = enabledProviderIds.includes(requestedProviderId)
    ? requestedProviderId
    : defaultProviderId;
  const requestedFailoverOrder = envCsv(env, "FAILOVER_ORDER").filter((id) =>
    enabledProviderIds.includes(id)
  );

  return {
    rocomApiKey: envStr(env, "ROCOM_API_KEY"),
    gameApiUrl: envStr(env, "ROCOM_API_URL") || DEFAULT_GAME_API_URL,
    notifyEmpty: envBool(env, "NOTIFY_EMPTY", false),
    httpTimeout: envInt(env, "HTTP_TIMEOUT", 30),
    deliveryMode: ["all", "single", "failover"].includes(deliveryMode)
      ? deliveryMode
      : "all",
    selectedProvider,
    failoverOrder:
      requestedFailoverOrder.length > 0
        ? requestedFailoverOrder
        : enabledProviderIds,
    providers,
  };
}

export function missingRequired(config: Config): string[] {
  const missing: string[] = [];
  if (!config.rocomApiKey) missing.push("ROCOM_API_KEY");
  if (!config.providers.some((p) => p.enabled)) missing.push("PUSH_PROVIDER");
  return missing;
}
