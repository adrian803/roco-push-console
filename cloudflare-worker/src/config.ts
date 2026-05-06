import type { Config, Env, ProviderConfig } from "./types";
import {
  PROVIDER_TYPES,
  providerEnvFields,
  providerEnvId,
} from "./provider-specs";

const DEFAULT_GAME_API_URL =
  "https://wegame.shallow.ink/api/v1/games/rocom/merchant/info";

function envStr(env: Env, key: string): string {
  return (env[key] || "").trim();
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

function buildProviderFromEnv(env: Env, providerType: string): ProviderConfig | null {
  const spec = PROVIDER_TYPES[providerType];
  if (!spec) return null;

  const config: Record<string, string> = {};
  let hasExplicitValue = false;
  const envVars = providerEnvFields(providerType);

  for (const field of spec.fields) {
    const envKey = envVars[field.name];
    const value = envKey ? envStr(env, envKey) : "";
    if (value) {
      config[field.name] = value;
      hasExplicitValue = true;
    } else if (
      Object.prototype.hasOwnProperty.call(field, "default") &&
      field.default !== undefined
    ) {
      config[field.name] = field.default;
    }
  }

  if (!hasExplicitValue) return null;
  const requiredFields = spec.fields.filter((f) => f.required);
  for (const field of requiredFields) {
    if (!(config[field.name] || "").trim()) return null;
  }

  return {
    id: providerEnvId(providerType),
    type: providerType,
    name: spec.label,
    enabled: true,
    config,
  };
}

export function loadConfig(env: Env): Config {
  const providers: ProviderConfig[] = [];
  for (const providerType of Object.keys(PROVIDER_TYPES)) {
    const provider = buildProviderFromEnv(env, providerType);
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
    includePriceInfo: envBool(env, "INCLUDE_PRICE_INFO", false),
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
