// Cloudflare Workers console deployment file.
// Paste this whole file into the Cloudflare Worker editor.
// Source of truth lives in src/*.ts; run `npm run build:worker` after changing it.

var __defProp = Object.defineProperty;
var __name = (target, value) => __defProp(target, "name", { value, configurable: true });

// ../src/roco_serverchan_notifier/shared/provider_manifest.json
var provider_manifest_default = {
  providers: [
    {
      type: "serverchan",
      label: "Server \u9171",
      description: "\u901A\u8FC7 Server \u9171 SendKey \u63A8\u9001\u5230\u5FAE\u4FE1\u3002",
      envId: "serverchan-default",
      envVars: {
        sendkey: "SERVERCHAN_SENDKEY"
      },
      fields: [
        {
          name: "sendkey",
          label: "SendKey",
          secret: true,
          required: true
        }
      ]
    },
    {
      type: "pushplus",
      label: "PushPlus",
      description: "\u901A\u8FC7 PushPlus token \u63A8\u9001\uFF0C\u9ED8\u8BA4\u4F7F\u7528 markdown \u6A21\u677F\u3002",
      envId: "pushplus-env",
      envVars: {
        token: "PUSHPLUS_TOKEN",
        topic: "PUSHPLUS_TOPIC",
        channel: "PUSHPLUS_CHANNEL"
      },
      fields: [
        {
          name: "token",
          label: "Token",
          secret: true,
          required: true
        },
        {
          name: "topic",
          label: "\u7FA4\u7EC4\u7F16\u7801",
          required: false
        },
        {
          name: "channel",
          label: "\u6E20\u9053",
          required: false
        }
      ]
    },
    {
      type: "wecomchan",
      label: "Wecom \u9171 / \u4F01\u4E1A\u5FAE\u4FE1\u5E94\u7528",
      description: "\u4F7F\u7528\u4F01\u4E1A\u5FAE\u4FE1\u5E94\u7528\u53C2\u6570\u83B7\u53D6 access_token \u540E\u53D1\u9001\u6D88\u606F\u3002",
      envId: "wecomchan-env",
      envVars: {
        corpid: "WECOM_CORPID",
        secret: "WECOM_SECRET",
        agentid: "WECOM_AGENTID",
        touser: "WECOM_TOUSER"
      },
      fields: [
        {
          name: "corpid",
          label: "CorpID",
          secret: true,
          required: true
        },
        {
          name: "secret",
          label: "Secret",
          secret: true,
          required: true
        },
        {
          name: "agentid",
          label: "AgentID",
          required: true
        },
        {
          name: "touser",
          label: "\u63A5\u6536\u4EBA",
          required: true,
          default: "@all"
        }
      ]
    },
    {
      type: "wecom_bot",
      label: "\u4F01\u4E1A\u5FAE\u4FE1\u7FA4\u673A\u5668\u4EBA",
      description: "\u4F7F\u7528\u4F01\u4E1A\u5FAE\u4FE1\u7FA4\u673A\u5668\u4EBA webhook \u6216 key \u63A8\u9001 markdown\u3002",
      envId: "wecom-bot-env",
      envVars: {
        webhook: "WECOM_BOT_WEBHOOK",
        key: "WECOM_BOT_KEY"
      },
      fields: [
        {
          name: "webhook",
          label: "Webhook",
          secret: true,
          required: false
        },
        {
          name: "key",
          label: "Key",
          secret: true,
          required: false
        }
      ]
    },
    {
      type: "wxpusher",
      label: "WxPusher",
      description: "\u901A\u8FC7 WxPusher appToken \u63A8\u9001\u7ED9 UID \u6216\u4E3B\u9898\u3002",
      envId: "wxpusher-env",
      envVars: {
        app_token: "WXPUSHER_APP_TOKEN",
        uids: "WXPUSHER_UIDS",
        topic_ids: "WXPUSHER_TOPIC_IDS"
      },
      fields: [
        {
          name: "app_token",
          label: "AppToken",
          secret: true,
          required: true
        },
        {
          name: "uids",
          label: "UID \u5217\u8868",
          required: false
        },
        {
          name: "topic_ids",
          label: "Topic ID \u5217\u8868",
          required: false
        }
      ]
    },
    {
      type: "bark",
      label: "Bark",
      description: "\u901A\u8FC7 Bark server \u548C device key \u63A8\u9001\u5230 iOS\u3002",
      envId: "bark-env",
      envVars: {
        server_url: "BARK_SERVER_URL",
        device_key: "BARK_DEVICE_KEY",
        group: "BARK_GROUP"
      },
      fields: [
        {
          name: "server_url",
          label: "Server URL",
          required: true,
          default: "https://api.day.app"
        },
        {
          name: "device_key",
          label: "Device Key",
          secret: true,
          required: true
        },
        {
          name: "group",
          label: "\u5206\u7EC4",
          required: false,
          default: "\u6D1B\u514B\u738B\u56FD"
        }
      ]
    },
    {
      type: "dingtalk_bot",
      label: "\u9489\u9489\u7FA4\u673A\u5668\u4EBA",
      description: "\u4F7F\u7528\u9489\u9489 webhook \u63A8\u9001 markdown\uFF0C\u53EF\u9009 secret \u52A0\u7B7E\u3002",
      envId: "dingtalk-env",
      envVars: {
        webhook: "DINGTALK_WEBHOOK",
        secret: "DINGTALK_SECRET"
      },
      fields: [
        {
          name: "webhook",
          label: "Webhook",
          secret: true,
          required: true
        },
        {
          name: "secret",
          label: "Secret",
          secret: true,
          required: false
        }
      ]
    },
    {
      type: "feishu_bot",
      label: "\u98DE\u4E66\u7FA4\u673A\u5668\u4EBA",
      description: "\u4F7F\u7528\u98DE\u4E66 webhook \u63A8\u9001\u5BCC\u6587\u672C\uFF0C\u53EF\u9009 secret \u52A0\u7B7E\u3002",
      envId: "feishu-env",
      envVars: {
        webhook: "FEISHU_WEBHOOK",
        secret: "FEISHU_SECRET"
      },
      fields: [
        {
          name: "webhook",
          label: "Webhook",
          secret: true,
          required: true
        },
        {
          name: "secret",
          label: "Secret",
          secret: true,
          required: false
        }
      ]
    },
    {
      type: "ntfy",
      label: "ntfy",
      description: "\u53D1\u5E03\u5230 ntfy topic\uFF0C\u53EF\u9009 bearer token\u3002",
      envId: "ntfy-env",
      envVars: {
        base_url: "NTFY_BASE_URL",
        topic: "NTFY_TOPIC",
        token: "NTFY_TOKEN",
        priority: "NTFY_PRIORITY",
        tags: "NTFY_TAGS"
      },
      fields: [
        {
          name: "base_url",
          label: "Base URL",
          required: true,
          default: "https://ntfy.sh"
        },
        {
          name: "topic",
          label: "Topic",
          secret: true,
          required: true
        },
        {
          name: "token",
          label: "Token",
          secret: true,
          required: false
        },
        {
          name: "priority",
          label: "\u4F18\u5148\u7EA7",
          required: false,
          default: "default"
        },
        {
          name: "tags",
          label: "\u6807\u7B7E",
          required: false
        }
      ]
    },
    {
      type: "gotify",
      label: "Gotify",
      description: "\u901A\u8FC7 Gotify app token \u63A8\u9001\u6D88\u606F\u3002",
      envId: "gotify-env",
      envVars: {
        base_url: "GOTIFY_BASE_URL",
        app_token: "GOTIFY_APP_TOKEN",
        priority: "GOTIFY_PRIORITY"
      },
      fields: [
        {
          name: "base_url",
          label: "Base URL",
          required: true
        },
        {
          name: "app_token",
          label: "App Token",
          secret: true,
          required: true
        },
        {
          name: "priority",
          label: "\u4F18\u5148\u7EA7",
          required: false,
          default: "5"
        }
      ]
    }
  ]
};

// src/provider-specs.ts
function isRecord(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
__name(isRecord, "isRecord");
function validateProviderManifest(value) {
  if (!isRecord(value)) {
    throw new Error("Invalid provider manifest: root must be an object");
  }
  const providersValue = value.providers;
  if (!Array.isArray(providersValue)) {
    throw new Error("Invalid provider manifest: providers must be an array");
  }
  const providers = [];
  const seenTypes = /* @__PURE__ */ new Set();
  providersValue.forEach((providerValue, providerIndex) => {
    if (!isRecord(providerValue)) {
      throw new Error(`Invalid provider manifest: providers[${providerIndex}] must be an object`);
    }
    const { type, label, description, envId, envVars, fields } = providerValue;
    if (typeof type !== "string" || !type.trim()) {
      throw new Error(`Invalid provider manifest: providers[${providerIndex}].type must be a non-empty string`);
    }
    if (seenTypes.has(type)) {
      throw new Error(`Invalid provider manifest: duplicate provider type ${type}`);
    }
    seenTypes.add(type);
    if (typeof label !== "string" || !label.trim()) {
      throw new Error(`Invalid provider manifest: providers[${providerIndex}].label must be a non-empty string`);
    }
    if (typeof description !== "string" || !description.trim()) {
      throw new Error(
        `Invalid provider manifest: providers[${providerIndex}].description must be a non-empty string`
      );
    }
    if (typeof envId !== "string" || !envId.trim()) {
      throw new Error(`Invalid provider manifest: providers[${providerIndex}].envId must be a non-empty string`);
    }
    if (!isRecord(envVars)) {
      throw new Error(`Invalid provider manifest: providers[${providerIndex}].envVars must be an object`);
    }
    if (!Array.isArray(fields)) {
      throw new Error(`Invalid provider manifest: providers[${providerIndex}].fields must be an array`);
    }
    const fieldNames = /* @__PURE__ */ new Set();
    const normalizedFields = fields.map((fieldValue, fieldIndex) => {
      if (!isRecord(fieldValue)) {
        throw new Error(
          `Invalid provider manifest: providers[${providerIndex}].fields[${fieldIndex}] must be an object`
        );
      }
      const { name, label: label2, secret, required, default: defaultValue } = fieldValue;
      if (typeof name !== "string" || !name.trim()) {
        throw new Error(
          `Invalid provider manifest: providers[${providerIndex}].fields[${fieldIndex}].name must be a non-empty string`
        );
      }
      if (typeof label2 !== "string" || !label2.trim()) {
        throw new Error(
          `Invalid provider manifest: providers[${providerIndex}].fields[${fieldIndex}].label must be a non-empty string`
        );
      }
      if (fieldNames.has(name)) {
        throw new Error(
          `Invalid provider manifest: providers[${providerIndex}] contains duplicate field ${name}`
        );
      }
      fieldNames.add(name);
      if (secret !== void 0 && typeof secret !== "boolean") {
        throw new Error(
          `Invalid provider manifest: providers[${providerIndex}].fields[${fieldIndex}].secret must be a boolean`
        );
      }
      if (required !== void 0 && typeof required !== "boolean") {
        throw new Error(
          `Invalid provider manifest: providers[${providerIndex}].fields[${fieldIndex}].required must be a boolean`
        );
      }
      if (defaultValue !== void 0 && typeof defaultValue !== "string") {
        throw new Error(
          `Invalid provider manifest: providers[${providerIndex}].fields[${fieldIndex}].default must be a string`
        );
      }
      return {
        name,
        label: label2,
        ...secret !== void 0 ? { secret } : {},
        ...required !== void 0 ? { required } : {},
        ...defaultValue !== void 0 ? { default: defaultValue } : {}
      };
    });
    const normalizedEnvVars = {};
    for (const [envName, envValue] of Object.entries(envVars)) {
      if (typeof envName !== "string" || !envName.trim()) {
        throw new Error(
          `Invalid provider manifest: providers[${providerIndex}].envVars contains an empty key`
        );
      }
      if (typeof envValue !== "string" || !envValue.trim()) {
        throw new Error(
          `Invalid provider manifest: providers[${providerIndex}].envVars.${envName} must be a non-empty string`
        );
      }
      if (!fieldNames.has(envName)) {
        throw new Error(
          `Invalid provider manifest: providers[${providerIndex}].envVars.${envName} is not declared in fields`
        );
      }
      normalizedEnvVars[envName] = envValue;
    }
    providers.push({
      type,
      label,
      description,
      envId,
      envVars: normalizedEnvVars,
      fields: normalizedFields
    });
  });
  return { providers };
}
__name(validateProviderManifest, "validateProviderManifest");
var manifest = validateProviderManifest(provider_manifest_default);
var PROVIDER_TYPES = Object.fromEntries(
  manifest.providers.map(({ type, ...spec }) => [type, spec])
);
function providerSpec(providerType) {
  return PROVIDER_TYPES[providerType];
}
__name(providerSpec, "providerSpec");
function providerSecretFields(providerType) {
  const spec = providerSpec(providerType);
  if (!spec) return /* @__PURE__ */ new Set();
  return new Set(
    spec.fields.filter((f) => f.secret).map((f) => f.name)
  );
}
__name(providerSecretFields, "providerSecretFields");
function providerRequiredFields(providerType) {
  const spec = providerSpec(providerType);
  if (!spec) return /* @__PURE__ */ new Set();
  return new Set(
    spec.fields.filter((f) => f.required).map((f) => f.name)
  );
}
__name(providerRequiredFields, "providerRequiredFields");
function providerFieldDefault(providerType, fieldName) {
  const spec = providerSpec(providerType);
  const field = spec?.fields.find((item) => item.name === fieldName);
  return field && Object.prototype.hasOwnProperty.call(field, "default") ? field.default : void 0;
}
__name(providerFieldDefault, "providerFieldDefault");
function providerEnvFields(providerType) {
  const spec = providerSpec(providerType);
  if (!spec) return {};
  return { ...spec.envVars };
}
__name(providerEnvFields, "providerEnvFields");
function providerEnvId(providerType) {
  const spec = providerSpec(providerType);
  return spec?.envId || `${providerType}-env`;
}
__name(providerEnvId, "providerEnvId");

// src/config.ts
var DEFAULT_GAME_API_URL = "https://wegame.shallow.ink/api/v1/games/rocom/merchant/info";
function envStr(env, key) {
  return (env[key] || "").trim();
}
__name(envStr, "envStr");
function envBool(env, key, defaultValue) {
  const value = envStr(env, key);
  if (!value) return defaultValue;
  return ["1", "true", "yes", "on", "y"].includes(value.toLowerCase());
}
__name(envBool, "envBool");
function envInt(env, key, defaultValue) {
  const value = envStr(env, key);
  if (!value) return defaultValue;
  const parsed = parseInt(value, 10);
  return isNaN(parsed) ? defaultValue : parsed;
}
__name(envInt, "envInt");
function envCsv(env, key) {
  return envStr(env, key).split(",").map((item) => item.trim()).filter(Boolean);
}
__name(envCsv, "envCsv");
function buildProviderFromEnv(env, providerType) {
  const spec = PROVIDER_TYPES[providerType];
  if (!spec) return null;
  const config = {};
  let hasExplicitValue = false;
  const envVars = providerEnvFields(providerType);
  for (const field of spec.fields) {
    const envKey = envVars[field.name];
    const value = envKey ? envStr(env, envKey) : "";
    if (value) {
      config[field.name] = value;
      hasExplicitValue = true;
    } else if (Object.prototype.hasOwnProperty.call(field, "default") && field.default !== void 0) {
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
    config
  };
}
__name(buildProviderFromEnv, "buildProviderFromEnv");
function loadConfig(env) {
  const providers = [];
  for (const providerType of Object.keys(PROVIDER_TYPES)) {
    const provider = buildProviderFromEnv(env, providerType);
    if (provider) providers.push(provider);
  }
  const deliveryMode = envStr(env, "DELIVERY_MODE") || "all";
  const enabledProviderIds = providers.filter((p) => p.enabled).map((p) => p.id);
  const defaultProviderId = enabledProviderIds[0] || "";
  const requestedProviderId = envStr(env, "SELECTED_PROVIDER");
  const selectedProvider = enabledProviderIds.includes(requestedProviderId) ? requestedProviderId : defaultProviderId;
  const requestedFailoverOrder = envCsv(env, "FAILOVER_ORDER").filter(
    (id) => enabledProviderIds.includes(id)
  );
  return {
    rocomApiKey: envStr(env, "ROCOM_API_KEY"),
    gameApiUrl: envStr(env, "ROCOM_API_URL") || DEFAULT_GAME_API_URL,
    notifyEmpty: envBool(env, "NOTIFY_EMPTY", false),
    httpTimeout: envInt(env, "HTTP_TIMEOUT", 30),
    includePriceInfo: envBool(env, "INCLUDE_PRICE_INFO", false),
    deliveryMode: ["all", "single", "failover"].includes(deliveryMode) ? deliveryMode : "all",
    selectedProvider,
    failoverOrder: requestedFailoverOrder.length > 0 ? requestedFailoverOrder : enabledProviderIds,
    providers
  };
}
__name(loadConfig, "loadConfig");
function missingRequired(config) {
  const missing = [];
  if (!config.rocomApiKey) missing.push("ROCOM_API_KEY");
  if (!config.providers.some((p) => p.enabled)) missing.push("PUSH_PROVIDER");
  return missing;
}
__name(missingRequired, "missingRequired");

// src/rocom-client.ts
async function fetchWithTimeout(url, init, timeoutSec) {
  const ctrl = new AbortController();
  const id = setTimeout(() => ctrl.abort(), timeoutSec * 1e3);
  try {
    return await fetch(url, { ...init, signal: ctrl.signal });
  } finally {
    clearTimeout(id);
  }
}
__name(fetchWithTimeout, "fetchWithTimeout");
async function fetchMerchantData(apiUrl, apiKey, timeoutSec) {
  if (!apiKey) throw new Error("\u7F3A\u5C11 ROCOM_API_KEY");
  const resp = await fetchWithTimeout(
    apiUrl,
    { method: "GET", headers: { "X-API-Key": apiKey } },
    timeoutSec
  );
  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
  }
  const payload = await resp.json();
  if (payload.code !== 0) {
    throw new Error(payload.message || "\u63A5\u53E3\u8FD4\u56DE\u5931\u8D25");
  }
  if (!payload.data || typeof payload.data !== "object") {
    throw new Error("\u63A5\u53E3\u8FD4\u56DE data \u4E0D\u662F\u5BF9\u8C61");
  }
  return payload.data;
}
__name(fetchMerchantData, "fetchMerchantData");

// src/rocom-message.ts
function formatLuokeBay(value) {
  if (value >= 1e4) {
    const amount = value / 1e4;
    const amountText = amount.toFixed(2).replace(/\.?0+$/, "");
    return `${amountText}\u4E07\u6D1B\u514B\u8D1D`;
  }
  return `${value}\u6D1B\u514B\u8D1D`;
}
__name(formatLuokeBay, "formatLuokeBay");
function formatPrice(value) {
  return value.toLocaleString("en-US");
}
__name(formatPrice, "formatPrice");
function statusLine(roundInfo) {
  return `\u8F6E\u6B21\uFF1A${roundInfo.current}/${roundInfo.total} \xB7 \u5269\u4F59\uFF1A${roundInfo.countdown}`;
}
__name(statusLine, "statusLine");
function productLines(index, product, includePriceInfo) {
  const lines = [`${index}. ${product.name}`, `\u65F6\u6BB5\uFF1A${product.timeLabel}`];
  if (includePriceInfo && typeof product.price === "number" && typeof product.buyLimitNum === "number") {
    const total = product.price * product.buyLimitNum;
    lines.push(`\u6570\u91CF\uFF1A${product.buyLimitNum}`);
    lines.push(`\u5355\u4EF7\uFF1A${formatPrice(product.price)}`);
    lines.push(`\u5408\u8BA1\uFF1A${formatPrice(total)}\uFF08${formatLuokeBay(total)}\uFF09`);
    return lines;
  }
  if (includePriceInfo) {
    lines.push("\u4EF7\u683C\uFF1A\u672A\u6536\u5F55");
  }
  return lines;
}
__name(productLines, "productLines");
function buildMerchantMarkdown(processed, includePriceInfo = false) {
  const lines = [statusLine(processed.roundInfo)];
  if (processed.products.length > 0) {
    lines.push("");
    processed.products.forEach((product, index) => {
      if (index > 0) lines.push("");
      lines.push(...productLines(index + 1, product, includePriceInfo));
    });
  } else {
    lines.push("", "\u5F53\u524D\u6682\u65E0\u6D3B\u8DC3\u5546\u54C1\u3002");
  }
  return lines.join("\n");
}
__name(buildMerchantMarkdown, "buildMerchantMarkdown");
function summary(products) {
  if (products.length === 0) return "\u5F53\u524D\u6682\u65E0\u6D3B\u8DC3\u5546\u54C1";
  const names = products.map((p) => p.name);
  return `${names.length}\u4EF6\u5546\u54C1\uFF1A${names.join("\u3001")}`;
}
__name(summary, "summary");
function buildMessage(processed, includePriceInfo = false) {
  const markdown = buildMerchantMarkdown(processed, includePriceInfo);
  const body = summary(processed.products);
  return {
    title: "\u8FDC\u884C\u5546\u4EBA\u5DF2\u5237\u65B0",
    body,
    markdown
  };
}
__name(buildMessage, "buildMessage");

// src/random-goods-conf.json
var random_goods_conf_default = {
  RocoDataRows: {
    "67001": {
      id: 67001,
      goods_name: "\u9ED1\u6676\u7409\u7483",
      package_id: 1,
      enable: true,
      Type: 1,
      item_id: 100628,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 1e3,
      price: 1e3,
      buy_limit_num: 100,
      weight: 1
    },
    "67002": {
      id: 67002,
      goods_name: "\u9EC4\u77F3\u69B4\u77F3",
      package_id: 2,
      enable: true,
      Type: 1,
      item_id: 100675,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 1e3,
      price: 1e3,
      buy_limit_num: 100,
      weight: 1
    },
    "67003": {
      id: 67003,
      goods_name: "\u84DD\u6676\u78A7\u73BA",
      package_id: 3,
      enable: true,
      Type: 1,
      item_id: 100676,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 1e3,
      price: 1e3,
      buy_limit_num: 100,
      weight: 1
    },
    "67004": {
      id: 67004,
      goods_name: "\u7D2B\u83B2\u521A\u7389",
      package_id: 4,
      enable: true,
      Type: 1,
      item_id: 100677,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 1e3,
      price: 1e3,
      buy_limit_num: 100,
      weight: 1
    },
    "67005": {
      id: 67005,
      goods_name: "\u9B54\u529B\u679C",
      package_id: 5,
      enable: true,
      Type: 1,
      item_id: 100213,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 6e3,
      price: 6e3,
      buy_limit_num: 20,
      weight: 1
    },
    "67006": {
      id: 67006,
      goods_name: "\u8349\u7CFB\u7C89\u5C18",
      package_id: 6,
      enable: true,
      Type: 1,
      item_id: 100121,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 500,
      price: 500,
      buy_limit_num: 100,
      weight: 1
    },
    "67007": {
      id: 67007,
      goods_name: "\u706B\u7CFB\u7C89\u5C18",
      package_id: 7,
      enable: true,
      Type: 1,
      item_id: 100122,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 500,
      price: 500,
      buy_limit_num: 100,
      weight: 1
    },
    "67008": {
      id: 67008,
      goods_name: "\u6C34\u7CFB\u7C89\u5C18",
      package_id: 8,
      enable: true,
      Type: 1,
      item_id: 100123,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 500,
      price: 500,
      buy_limit_num: 100,
      weight: 1
    },
    "67009": {
      id: 67009,
      goods_name: "\u5149\u7CFB\u7C89\u5C18",
      package_id: 9,
      enable: true,
      Type: 1,
      item_id: 100124,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 500,
      price: 500,
      buy_limit_num: 100,
      weight: 1
    },
    "67010": {
      id: 67010,
      goods_name: "\u6076\u7CFB\u7C89\u5C18",
      package_id: 10,
      enable: true,
      Type: 1,
      item_id: 100125,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 500,
      price: 500,
      buy_limit_num: 100,
      weight: 1
    },
    "67011": {
      id: 67011,
      goods_name: "\u5E7D\u7CFB\u7C89\u5C18",
      package_id: 11,
      enable: true,
      Type: 1,
      item_id: 100126,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 500,
      price: 500,
      buy_limit_num: 100,
      weight: 1
    },
    "67012": {
      id: 67012,
      goods_name: "\u666E\u901A\u7C89\u5C18",
      package_id: 12,
      enable: true,
      Type: 1,
      item_id: 100127,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 500,
      price: 500,
      buy_limit_num: 100,
      weight: 1
    },
    "67013": {
      id: 67013,
      goods_name: "\u5730\u7CFB\u7C89\u5C18",
      package_id: 13,
      enable: true,
      Type: 1,
      item_id: 100129,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 500,
      price: 500,
      buy_limit_num: 100,
      weight: 1
    },
    "67014": {
      id: 67014,
      goods_name: "\u51B0\u7CFB\u7C89\u5C18",
      package_id: 14,
      enable: true,
      Type: 1,
      item_id: 100130,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 500,
      price: 500,
      buy_limit_num: 100,
      weight: 1
    },
    "67015": {
      id: 67015,
      goods_name: "\u9F99\u7CFB\u7C89\u5C18",
      package_id: 15,
      enable: true,
      Type: 1,
      item_id: 100131,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 500,
      price: 500,
      buy_limit_num: 100,
      weight: 1
    },
    "67016": {
      id: 67016,
      goods_name: "\u7535\u7CFB\u7C89\u5C18",
      package_id: 16,
      enable: true,
      Type: 1,
      item_id: 100132,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 500,
      price: 500,
      buy_limit_num: 100,
      weight: 1
    },
    "67017": {
      id: 67017,
      goods_name: "\u6BD2\u7CFB\u7C89\u5C18",
      package_id: 17,
      enable: true,
      Type: 1,
      item_id: 100133,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 500,
      price: 500,
      buy_limit_num: 100,
      weight: 1
    },
    "67018": {
      id: 67018,
      goods_name: "\u866B\u7CFB\u7C89\u5C18",
      package_id: 18,
      enable: true,
      Type: 1,
      item_id: 100134,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 500,
      price: 500,
      buy_limit_num: 100,
      weight: 1
    },
    "67019": {
      id: 67019,
      goods_name: "\u6B66\u7CFB\u7C89\u5C18",
      package_id: 19,
      enable: true,
      Type: 1,
      item_id: 100135,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 500,
      price: 500,
      buy_limit_num: 100,
      weight: 1
    },
    "67020": {
      id: 67020,
      goods_name: "\u7FFC\u7CFB\u7C89\u5C18",
      package_id: 20,
      enable: true,
      Type: 1,
      item_id: 100136,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 500,
      price: 500,
      buy_limit_num: 100,
      weight: 1
    },
    "67021": {
      id: 67021,
      goods_name: "\u840C\u7CFB\u7C89\u5C18",
      package_id: 21,
      enable: true,
      Type: 1,
      item_id: 100137,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 500,
      price: 500,
      buy_limit_num: 100,
      weight: 1
    },
    "67022": {
      id: 67022,
      goods_name: "\u673A\u68B0\u7C89\u5C18",
      package_id: 22,
      enable: true,
      Type: 1,
      item_id: 100138,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 500,
      price: 500,
      buy_limit_num: 100,
      weight: 1
    },
    "67023": {
      id: 67023,
      goods_name: "\u5E7B\u7CFB\u7C89\u5C18",
      package_id: 23,
      enable: true,
      Type: 1,
      item_id: 100139,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 500,
      price: 500,
      buy_limit_num: 100,
      weight: 1
    },
    "68001": {
      id: 68001,
      goods_name: "\u56FD\u738B\u7403",
      package_id: 24,
      enable: true,
      Type: 1,
      item_id: 100255,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 16e4,
      price: 16e4,
      buy_limit_num: 3,
      weight: 1
    },
    "68002": {
      id: 68002,
      goods_name: "\u68F1\u955C\u7403",
      package_id: 25,
      enable: true,
      Type: 1,
      item_id: 100286,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 32e5,
      price: 32e5,
      buy_limit_num: 1,
      enable_time: "2026-04-02 08:00:00",
      weight: 1
    },
    "68003": {
      id: 68003,
      goods_name: "\u795E\u5947\u7684\u86CB",
      package_id: 26,
      enable: true,
      Type: 1,
      item_id: 310049,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 36e3,
      price: 36e3,
      buy_limit_num: 5,
      weight: 1
    },
    "68004": {
      id: 68004,
      goods_name: "\u70AB\u5F69\u86CB",
      package_id: 27,
      enable: true,
      Type: 1,
      item_id: 310050,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 16e5,
      price: 16e5,
      buy_limit_num: 1,
      enable_time: "2026-03-27 08:00:00",
      weight: 1
    },
    "68005": {
      id: 68005,
      goods_name: "\u666E\u901A\u8840\u8109\u79D8\u836F",
      package_id: 28,
      enable: true,
      Type: 1,
      item_id: 102001,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 16e4,
      price: 16e4,
      buy_limit_num: 3,
      weight: 1
    },
    "68006": {
      id: 68006,
      goods_name: "\u8349\u7CFB\u8840\u8109\u79D8\u836F",
      package_id: 28,
      enable: true,
      Type: 1,
      item_id: 102002,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 16e4,
      price: 16e4,
      buy_limit_num: 3,
      weight: 1
    },
    "68007": {
      id: 68007,
      goods_name: "\u706B\u7CFB\u8840\u8109\u79D8\u836F",
      package_id: 28,
      enable: true,
      Type: 1,
      item_id: 102003,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 16e4,
      price: 16e4,
      buy_limit_num: 3,
      weight: 1
    },
    "68008": {
      id: 68008,
      goods_name: "\u6C34\u7CFB\u8840\u8109\u79D8\u836F",
      package_id: 28,
      enable: true,
      Type: 1,
      item_id: 102004,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 16e4,
      price: 16e4,
      buy_limit_num: 3,
      weight: 1
    },
    "68009": {
      id: 68009,
      goods_name: "\u5149\u7CFB\u8840\u8109\u79D8\u836F",
      package_id: 28,
      enable: true,
      Type: 1,
      item_id: 102005,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 16e4,
      price: 16e4,
      buy_limit_num: 3,
      weight: 1
    },
    "68010": {
      id: 68010,
      goods_name: "\u5730\u7CFB\u8840\u8109\u79D8\u836F",
      package_id: 28,
      enable: true,
      Type: 1,
      item_id: 102006,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 16e4,
      price: 16e4,
      buy_limit_num: 3,
      weight: 1
    },
    "68011": {
      id: 68011,
      goods_name: "\u51B0\u7CFB\u8840\u8109\u79D8\u836F",
      package_id: 28,
      enable: true,
      Type: 1,
      item_id: 102007,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 16e4,
      price: 16e4,
      buy_limit_num: 3,
      weight: 1
    },
    "68012": {
      id: 68012,
      goods_name: "\u9F99\u7CFB\u8840\u8109\u79D8\u836F",
      package_id: 28,
      enable: true,
      Type: 1,
      item_id: 102008,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 16e4,
      price: 16e4,
      buy_limit_num: 3,
      weight: 1
    },
    "68013": {
      id: 68013,
      goods_name: "\u7535\u7CFB\u8840\u8109\u79D8\u836F",
      package_id: 28,
      enable: true,
      Type: 1,
      item_id: 102009,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 16e4,
      price: 16e4,
      buy_limit_num: 3,
      weight: 1
    },
    "68014": {
      id: 68014,
      goods_name: "\u6BD2\u7CFB\u8840\u8109\u79D8\u836F",
      package_id: 28,
      enable: true,
      Type: 1,
      item_id: 102010,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 16e4,
      price: 16e4,
      buy_limit_num: 3,
      weight: 1
    },
    "68015": {
      id: 68015,
      goods_name: "\u866B\u7CFB\u8840\u8109\u79D8\u836F",
      package_id: 28,
      enable: true,
      Type: 1,
      item_id: 102011,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 16e4,
      price: 16e4,
      buy_limit_num: 3,
      weight: 1
    },
    "68016": {
      id: 68016,
      goods_name: "\u6B66\u7CFB\u8840\u8109\u79D8\u836F",
      package_id: 28,
      enable: true,
      Type: 1,
      item_id: 102012,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 16e4,
      price: 16e4,
      buy_limit_num: 3,
      weight: 1
    },
    "68017": {
      id: 68017,
      goods_name: "\u7FFC\u7CFB\u8840\u8109\u79D8\u836F",
      package_id: 28,
      enable: true,
      Type: 1,
      item_id: 102013,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 16e4,
      price: 16e4,
      buy_limit_num: 3,
      weight: 1
    },
    "68018": {
      id: 68018,
      goods_name: "\u840C\u7CFB\u8840\u8109\u79D8\u836F",
      package_id: 28,
      enable: true,
      Type: 1,
      item_id: 102014,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 16e4,
      price: 16e4,
      buy_limit_num: 3,
      weight: 1
    },
    "68019": {
      id: 68019,
      goods_name: "\u5E7D\u7CFB\u8840\u8109\u79D8\u836F",
      package_id: 28,
      enable: true,
      Type: 1,
      item_id: 102015,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 16e4,
      price: 16e4,
      buy_limit_num: 3,
      weight: 1
    },
    "68020": {
      id: 68020,
      goods_name: "\u6076\u7CFB\u8840\u8109\u79D8\u836F",
      package_id: 28,
      enable: true,
      Type: 1,
      item_id: 102016,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 16e4,
      price: 16e4,
      buy_limit_num: 3,
      weight: 1
    },
    "68021": {
      id: 68021,
      goods_name: "\u673A\u68B0\u8840\u8109\u79D8\u836F",
      package_id: 28,
      enable: true,
      Type: 1,
      item_id: 102017,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 16e4,
      price: 16e4,
      buy_limit_num: 3,
      weight: 1
    },
    "68022": {
      id: 68022,
      goods_name: "\u5E7B\u7CFB\u8840\u8109\u79D8\u836F",
      package_id: 28,
      enable: true,
      Type: 1,
      item_id: 102018,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 16e4,
      price: 16e4,
      buy_limit_num: 3,
      weight: 1
    },
    "68023": {
      id: 68023,
      goods_name: "\u5947\u5F02\u8840\u8109\u79D8\u836F",
      package_id: 29,
      enable: true,
      Type: 1,
      item_id: 102024,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 16e4,
      price: 16e4,
      buy_limit_num: 3,
      weight: 1
    },
    "68024": {
      id: 68024,
      goods_name: "\u9996\u9886\u8840\u8109\u79D8\u836F",
      package_id: 30,
      enable: true,
      Type: 1,
      item_id: 102023,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 32e4,
      price: 32e4,
      buy_limit_num: 1,
      weight: 1
    },
    "68025": {
      id: 68025,
      goods_name: "\u795D\u798F\u9879\u5760",
      package_id: 31,
      enable: true,
      Type: 2,
      item_id: 64,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 8e5,
      price: 8e5,
      buy_limit_num: 1,
      enable_time: "2026-04-02 08:00:00",
      weight: 1
    },
    "100001": {
      id: 100001,
      goods_name: "\u56FD\u738B\u7403",
      goods_group_id: 1,
      enable: true,
      Type: 1,
      item_id: 100255,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 16e4,
      price: 16e4,
      buy_limit_num: 3,
      is_special_good: true
    },
    "100002": {
      id: 100002,
      goods_name: "\u68F1\u955C\u7403",
      goods_group_id: 2,
      enable: true,
      Type: 1,
      item_id: 100286,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 32e5,
      price: 32e5,
      buy_limit_num: 1,
      is_special_good: true
    },
    "100003": {
      id: 100003,
      goods_name: "\u795E\u5947\u7684\u86CB",
      goods_group_id: 3,
      enable: true,
      Type: 1,
      item_id: 310049,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 36e3,
      price: 36e3,
      buy_limit_num: 5,
      is_special_good: true
    },
    "100004": {
      id: 100004,
      goods_name: "\u9ED1\u767D\u70AB\u5F69\u86CB",
      goods_group_id: 4,
      enable: true,
      Type: 1,
      item_id: 310051,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 16e6,
      price: 16e5,
      buy_limit_num: 1,
      is_special_good: true
    },
    "100005": {
      id: 100005,
      goods_name: "\u8D5B\u5B63\u70AB\u5F69\u86CB",
      goods_group_id: 5,
      enable: true,
      Type: 1,
      item_id: 310052,
      item_num: 1,
      price_goods_type: 2,
      price_goods_id: 1,
      origin_price: 16e6,
      price: 16e6,
      buy_limit_num: 1,
      is_special_good: true
    }
  },
  LocalizationStrings: {}
};

// src/rocom-time.ts
var BEIJING_OFFSET_MS = 8 * 60 * 60 * 1e3;
function getBeijingDate(now) {
  const d = now || /* @__PURE__ */ new Date();
  return new Date(d.getTime() + BEIJING_OFFSET_MS);
}
__name(getBeijingDate, "getBeijingDate");
function formatTimestamp(tsMs) {
  if (!tsMs) return "--:--";
  try {
    const ms = typeof tsMs === "string" ? parseInt(tsMs, 10) : Number(tsMs);
    if (isNaN(ms)) return "--:--";
    const d = new Date(ms);
    const bj = getBeijingDate(d);
    const hh = bj.getUTCHours().toString().padStart(2, "0");
    const mm = bj.getUTCMinutes().toString().padStart(2, "0");
    return `${hh}:${mm}`;
  } catch {
    return "--:--";
  }
}
__name(formatTimestamp, "formatTimestamp");
function getRoundInfo(now) {
  const bj = getBeijingDate(now);
  const hour = bj.getUTCHours();
  const minute = bj.getUTCMinutes();
  if (hour < 8) {
    return { current: "\u672A\u5F00\u653E", total: 4, countdown: "\u5C1A\u672A\u5F00\u5E02" };
  }
  const minutesSince8 = (hour - 8) * 60 + minute;
  const roundIndex = Math.floor(minutesSince8 / (4 * 60)) + 1;
  if (roundIndex > 4) {
    return { current: 4, total: 4, countdown: "\u4ECA\u65E5\u5DF2\u6536\u5E02" };
  }
  const roundEndMinutes = roundIndex * 4 * 60;
  const remainingMinutes = roundEndMinutes - minutesSince8;
  const hours = Math.floor(remainingMinutes / 60);
  const mins = remainingMinutes % 60;
  const countdown = hours > 0 ? `${hours}\u5C0F\u65F6${mins}\u5206\u949F` : `${mins}\u5206\u949F`;
  return { current: roundIndex, total: 4, countdown };
}
__name(getRoundInfo, "getRoundInfo");
function getBeijingNowMs() {
  return Date.now();
}
__name(getBeijingNowMs, "getBeijingNowMs");

// src/rocom-processing.ts
function isActiveItem(item, nowMs) {
  const startTime = item.start_time;
  const endTime = item.end_time;
  if (!startTime || !endTime) return true;
  try {
    const s = typeof startTime === "string" ? parseInt(startTime, 10) : startTime;
    const e = typeof endTime === "string" ? parseInt(endTime, 10) : endTime;
    return s <= nowMs && nowMs < e;
  } catch {
    return false;
  }
}
__name(isActiveItem, "isActiveItem");
var GOODS_PRICE_INFO_BY_NAME = buildGoodsPriceInfoByName(
  random_goods_conf_default
);
function buildGoodsPriceInfoByName(conf) {
  const result = /* @__PURE__ */ new Map();
  const rows = conf.RocoDataRows || {};
  for (const row of Object.values(rows)) {
    if (!row || row.enable === false) continue;
    const name = (row.goods_name || "").trim();
    const price = toInt(row.price);
    const buyLimitNum = toInt(row.buy_limit_num);
    if (name && price !== null && buyLimitNum !== null) {
      result.set(name, { price, buyLimitNum });
    }
  }
  return result;
}
__name(buildGoodsPriceInfoByName, "buildGoodsPriceInfoByName");
function toInt(value) {
  const parsed = typeof value === "string" ? parseInt(value, 10) : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}
__name(toInt, "toInt");
function catalogNameCandidates(name) {
  const normalized = name.trim();
  const candidates = normalized ? [normalized] : [];
  if (normalized.includes("\u7CBE\u7075\u86CB")) {
    candidates.push(normalized.replaceAll("\u7CBE\u7075\u86CB", "\u86CB"));
  }
  return [...new Set(candidates)];
}
__name(catalogNameCandidates, "catalogNameCandidates");
function priceInfoForName(name) {
  for (const candidate of catalogNameCandidates(name)) {
    const info = GOODS_PRICE_INFO_BY_NAME.get(candidate);
    if (info) return info;
  }
  return void 0;
}
__name(priceInfoForName, "priceInfoForName");
function enrichPriceInfo(product) {
  const info = priceInfoForName(product.name);
  if (!info) return product;
  return { ...product, price: info.price, buyLimitNum: info.buyLimitNum };
}
__name(enrichPriceInfo, "enrichPriceInfo");
function processMerchantData(data) {
  const nowMs = getBeijingNowMs();
  const roundInfo = getRoundInfo();
  const activities = data.merchantActivities || [];
  const activity = activities.length > 0 ? activities[0] : {};
  const props = activity.get_props || [];
  const pets = activity.get_pets || [];
  const allItems = [...props, ...pets].filter(
    (item) => typeof item === "object" && item !== null
  );
  const activeProducts = [];
  for (const item of allItems) {
    if (!isActiveItem(item, nowMs)) continue;
    let timeLabel;
    if (item.start_time && item.end_time) {
      timeLabel = `${formatTimestamp(item.start_time)} - ${formatTimestamp(item.end_time)}`;
    } else {
      timeLabel = "\u5168\u5929\u4F9B\u5E94";
    }
    activeProducts.push(
      enrichPriceInfo({
        name: String(item.name || "\u672A\u77E5"),
        image: String(item.icon_url || ""),
        timeLabel
      })
    );
  }
  return {
    title: activity.name || "\u8FDC\u884C\u5546\u4EBA",
    subtitle: activity.start_date || "\u6BCF\u65E5 08:00 / 12:00 / 16:00 / 20:00 \u5237\u65B0",
    productCount: activeProducts.length,
    roundInfo,
    products: activeProducts
  };
}
__name(processMerchantData, "processMerchantData");

// src/push-redaction.ts
var SENSITIVE_NAMES = "access_token|app_token|corpsecret|key|read_key|readkey|secret|sendkey|token|webhook";
var SENSITIVE_QUERY_RE = new RegExp(
  `(\\b(?:${SENSITIVE_NAMES})=)([^&\\s]+)`,
  "gi"
);
var SENSITIVE_FIELD_RE = new RegExp(
  `(['"]?\\b(?:${SENSITIVE_NAMES})\\b['"]?\\s*[:=]\\s*['"]?)([^'",\\s}&]+)(['"]?)`,
  "gi"
);
function redactSensitiveText(provider, text) {
  let r = text;
  for (const fieldName of providerSecretFields(provider.type)) {
    const v = (provider.config[fieldName] || "").trim();
    if (v) {
      r = r.replaceAll(v, "[\u5DF2\u8131\u654F]");
      r = r.replaceAll(encodeURIComponent(v), "[\u5DF2\u8131\u654F]");
    }
  }
  r = r.replace(SENSITIVE_QUERY_RE, "$1[\u5DF2\u8131\u654F]");
  r = r.replace(SENSITIVE_FIELD_RE, "$1[\u5DF2\u8131\u654F]$3");
  return r;
}
__name(redactSensitiveText, "redactSensitiveText");

// src/push-http.ts
function jsonResult(payload, successCodes) {
  const code = payload.code ?? payload.errcode;
  let success = successCodes.has(code);
  if (code === void 0 && Object.keys(payload).length === 0) {
    success = true;
  }
  const message = String(
    payload.message || payload.msg || payload.errmsg || JSON.stringify(payload)
  );
  return { success, message };
}
__name(jsonResult, "jsonResult");
async function readResponsePayload(resp) {
  const text = await resp.text();
  if (!text.trim()) return { payload: {}, text: "" };
  try {
    const parsed = JSON.parse(text);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return { payload: parsed, text };
    }
  } catch {
  }
  return { payload: {}, text };
}
__name(readResponsePayload, "readResponsePayload");
function resultFromParsedResponse(provider, resp, payload, text, successCodes) {
  let { success, message } = jsonResult(payload, successCodes);
  const textMessage = text.slice(0, 200);
  if (Object.keys(payload).length === 0 && textMessage) {
    message = textMessage;
  }
  if (resp.status >= 400) {
    success = false;
    message = textMessage || message;
  }
  return {
    providerId: provider.id,
    providerName: provider.name,
    providerType: provider.type,
    success,
    message: redactSensitiveText(provider, message),
    statusCode: resp.status
  };
}
__name(resultFromParsedResponse, "resultFromParsedResponse");
function providerErrorResult(provider, err) {
  return {
    providerId: provider.id,
    providerName: provider.name,
    providerType: provider.type,
    success: false,
    message: redactSensitiveText(provider, String(err)),
    statusCode: null
  };
}
__name(providerErrorResult, "providerErrorResult");
async function postJson(provider, url, payload, timeoutSec, options) {
  const successCodes = options?.successCodes ?? /* @__PURE__ */ new Set([0, "0"]);
  try {
    const resp = await fetchWithTimeout(
      url,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...options?.headers
        },
        body: JSON.stringify(payload)
      },
      timeoutSec
    );
    const { payload: respPayload, text } = await readResponsePayload(resp);
    return resultFromParsedResponse(
      provider,
      resp,
      respPayload,
      text,
      successCodes
    );
  } catch (err) {
    return providerErrorResult(provider, err);
  }
}
__name(postJson, "postJson");

// src/push-provider-senders/common.ts
function splitCsv(value) {
  if (!value) return [];
  return value.split(",").map((s) => s.trim()).filter(Boolean);
}
__name(splitCsv, "splitCsv");
function providerConfigText(provider, fieldName) {
  return (provider.config[fieldName] || providerFieldDefault(provider.type, fieldName) || "").trim();
}
__name(providerConfigText, "providerConfigText");

// src/push-provider-senders/token.ts
async function sendServerChan(provider, message, timeoutSec) {
  const sendkey = provider.config.sendkey;
  const url = `https://sctapi.ftqq.com/${sendkey}.send`;
  const body = new URLSearchParams({
    title: message.title,
    desp: message.markdown
  });
  try {
    const resp = await fetchWithTimeout(
      url,
      { method: "POST", body },
      timeoutSec
    );
    const successCodes = /* @__PURE__ */ new Set([0, "0", null, void 0]);
    const { payload, text } = await readResponsePayload(resp);
    return resultFromParsedResponse(provider, resp, payload, text, successCodes);
  } catch (err) {
    return providerErrorResult(provider, err);
  }
}
__name(sendServerChan, "sendServerChan");
async function sendPushPlus(provider, message, timeoutSec) {
  const payload = {
    token: provider.config.token,
    title: message.title,
    content: message.markdown,
    template: "markdown"
  };
  for (const key of ["topic", "channel"]) {
    const v = (provider.config[key] || "").trim();
    if (v) payload[key] = v;
  }
  return postJson(provider, "https://www.pushplus.plus/send", payload, timeoutSec, {
    successCodes: /* @__PURE__ */ new Set([200, "200", 0, "0"])
  });
}
__name(sendPushPlus, "sendPushPlus");
async function sendWxPusher(provider, message, timeoutSec) {
  const payload = {
    appToken: provider.config.app_token,
    content: message.markdown,
    summary: message.title,
    contentType: 3
  };
  const uids = splitCsv(provider.config.uids);
  const topicIds = splitCsv(provider.config.topic_ids);
  if (uids.length > 0) payload.uids = uids;
  if (topicIds.length > 0) {
    payload.topicIds = topicIds.map((id) => /^\d+$/.test(id) ? parseInt(id, 10) : id);
  }
  return postJson(
    provider,
    "https://wxpusher.zjiecode.com/api/send/message",
    payload,
    timeoutSec,
    { successCodes: /* @__PURE__ */ new Set([1e3, "1000", 0, "0"]) }
  );
}
__name(sendWxPusher, "sendWxPusher");
async function sendBark(provider, message, timeoutSec) {
  const serverUrl = providerConfigText(provider, "server_url").replace(/\/$/, "");
  const url = `${serverUrl}/${provider.config.device_key}`;
  const payload = {
    title: message.title,
    body: `${message.body}

${message.markdown}`
  };
  const group = providerConfigText(provider, "group");
  if (group) payload.group = group;
  return postJson(provider, url, payload, timeoutSec, {
    successCodes: /* @__PURE__ */ new Set([200, "200", 0, "0"])
  });
}
__name(sendBark, "sendBark");
async function sendNtfy(provider, message, timeoutSec) {
  const baseUrl = providerConfigText(provider, "base_url").replace(/\/$/, "");
  const url = `${baseUrl}/${provider.config.topic}`;
  const headers = {
    Title: message.title,
    Markdown: "yes"
  };
  for (const [cfgKey, headerName] of [
    ["priority", "Priority"],
    ["tags", "Tags"]
  ]) {
    const v = providerConfigText(provider, cfgKey);
    if (v) headers[headerName] = v;
  }
  const token = providerConfigText(provider, "token");
  if (token) headers["Authorization"] = `Bearer ${token}`;
  try {
    const resp = await fetchWithTimeout(
      url,
      {
        method: "POST",
        headers,
        body: message.markdown
      },
      timeoutSec
    );
    const success = resp.status >= 200 && resp.status < 300;
    const text = (await resp.text()).slice(0, 200) || resp.statusText;
    return {
      providerId: provider.id,
      providerName: provider.name,
      providerType: provider.type,
      success,
      message: text,
      statusCode: resp.status
    };
  } catch (err) {
    return {
      providerId: provider.id,
      providerName: provider.name,
      providerType: provider.type,
      success: false,
      message: String(err),
      statusCode: null
    };
  }
}
__name(sendNtfy, "sendNtfy");
async function sendGotify(provider, message, timeoutSec) {
  const baseUrl = (provider.config.base_url || "").replace(/\/$/, "");
  const appToken = encodeURIComponent(provider.config.app_token);
  const url = `${baseUrl}/message?token=${appToken}`;
  const priority = parseInt(providerConfigText(provider, "priority"), 10) || 5;
  const payload = {
    title: message.title,
    message: message.markdown,
    priority
  };
  try {
    const resp = await fetchWithTimeout(
      url,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      },
      timeoutSec
    );
    const success = resp.status >= 200 && resp.status < 300;
    const text = (await resp.text()).slice(0, 200) || resp.statusText;
    return {
      providerId: provider.id,
      providerName: provider.name,
      providerType: provider.type,
      success,
      message: text,
      statusCode: resp.status
    };
  } catch (err) {
    return {
      providerId: provider.id,
      providerName: provider.name,
      providerType: provider.type,
      success: false,
      message: String(err),
      statusCode: null
    };
  }
}
__name(sendGotify, "sendGotify");

// src/push-provider-auth.ts
var wecomTokenCache = /* @__PURE__ */ new Map();
async function getWecomToken(corpid, secret, timeoutSec) {
  const key = `${corpid}:${secret}`;
  const cached = wecomTokenCache.get(key);
  const now = Math.floor(Date.now() / 1e3);
  if (cached && cached.expiresAt > now + 60) return cached.token;
  const url = `https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=${encodeURIComponent(corpid)}&corpsecret=${encodeURIComponent(secret)}`;
  const resp = await fetchWithTimeout(url, { method: "GET" }, timeoutSec);
  const payload = await resp.json();
  if (resp.status >= 400 || payload.errcode !== 0 && payload.errcode !== "0") {
    throw new Error(payload.errmsg || JSON.stringify(payload));
  }
  const token = payload.access_token;
  const expiresIn = payload.expires_in || 7200;
  wecomTokenCache.set(key, { token, expiresAt: now + expiresIn });
  return token;
}
__name(getWecomToken, "getWecomToken");
async function hmacSha256Base64(keyData, messageData) {
  const key = await crypto.subtle.importKey(
    "raw",
    keyData,
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, messageData);
  const bytes = new Uint8Array(sig);
  let binary = "";
  for (const b of bytes) binary += String.fromCharCode(b);
  return btoa(binary);
}
__name(hmacSha256Base64, "hmacSha256Base64");
async function appendDingTalkSign(webhook, secret) {
  if (!secret) return webhook;
  const timestamp = Date.now().toString();
  const stringToSign = `${timestamp}
${secret}`;
  const encoder = new TextEncoder();
  const sign = await hmacSha256Base64(
    encoder.encode(secret),
    encoder.encode(stringToSign)
  );
  const sep = webhook.includes("?") ? "&" : "?";
  return `${webhook}${sep}timestamp=${timestamp}&sign=${encodeURIComponent(sign)}`;
}
__name(appendDingTalkSign, "appendDingTalkSign");
async function feishuSign(secret, timestamp) {
  const stringToSign = `${timestamp}
${secret}`;
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(stringToSign),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, new Uint8Array(0));
  const bytes = new Uint8Array(sig);
  let binary = "";
  for (const b of bytes) binary += String.fromCharCode(b);
  return btoa(binary);
}
__name(feishuSign, "feishuSign");

// src/push-provider-senders/webhook.ts
async function sendDingTalkBot(provider, message, timeoutSec) {
  const webhook = await appendDingTalkSign(
    provider.config.webhook,
    provider.config.secret || ""
  );
  const payload = {
    msgtype: "markdown",
    markdown: { title: message.title, text: message.markdown }
  };
  return postJson(provider, webhook, payload, timeoutSec);
}
__name(sendDingTalkBot, "sendDingTalkBot");
async function sendFeishuBot(provider, message, timeoutSec) {
  const payload = {
    msg_type: "post",
    content: {
      post: {
        zh_cn: {
          title: message.title,
          content: [
            [{ tag: "text", text: `${message.body}

${message.markdown}` }]
          ]
        }
      }
    }
  };
  const secret = (provider.config.secret || "").trim();
  if (secret) {
    const timestamp = Math.floor(Date.now() / 1e3).toString();
    payload.timestamp = timestamp;
    payload.sign = await feishuSign(secret, timestamp);
  }
  return postJson(provider, provider.config.webhook, payload, timeoutSec);
}
__name(sendFeishuBot, "sendFeishuBot");

// src/push-provider-senders/wecom.ts
async function sendWecomChan(provider, message, timeoutSec) {
  try {
    const token = await getWecomToken(
      provider.config.corpid,
      provider.config.secret,
      timeoutSec
    );
    const url = `https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=${token}`;
    const payload = {
      touser: provider.config.touser || "@all",
      msgtype: "text",
      agentid: parseInt(provider.config.agentid, 10),
      text: {
        content: `${message.title}

${message.body}

${message.markdown}`
      },
      safe: 0
    };
    return postJson(provider, url, payload, timeoutSec);
  } catch (err) {
    return providerErrorResult(provider, err);
  }
}
__name(sendWecomChan, "sendWecomChan");
async function sendWecomBot(provider, message, timeoutSec) {
  let webhook = (provider.config.webhook || "").trim();
  if (!webhook) {
    const key = (provider.config.key || "").trim();
    if (!key) {
      return {
        providerId: provider.id,
        providerName: provider.name,
        providerType: provider.type,
        success: false,
        message: "\u7F3A\u5C11 webhook \u6216 key",
        statusCode: null
      };
    }
    webhook = `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=${key}`;
  }
  const payload = {
    msgtype: "markdown",
    markdown: { content: message.markdown }
  };
  return postJson(provider, webhook, payload, timeoutSec);
}
__name(sendWecomBot, "sendWecomBot");

// src/push-provider-senders/registry.ts
var PROVIDER_SENDERS = {
  serverchan: sendServerChan,
  pushplus: sendPushPlus,
  wecomchan: sendWecomChan,
  wecom_bot: sendWecomBot,
  wxpusher: sendWxPusher,
  bark: sendBark,
  dingtalk_bot: sendDingTalkBot,
  feishu_bot: sendFeishuBot,
  ntfy: sendNtfy,
  gotify: sendGotify
};

// src/push-providers.ts
function configuredOrDefault(provider, fieldName) {
  return (provider.config[fieldName] || providerFieldDefault(provider.type, fieldName) || "").trim();
}
__name(configuredOrDefault, "configuredOrDefault");
function missingRequired2(provider) {
  return [...providerRequiredFields(provider.type)].filter(
    (name) => !configuredOrDefault(provider, name)
  );
}
__name(missingRequired2, "missingRequired");
async function sendProvider(provider, message, timeoutSec) {
  const missing = missingRequired2(provider);
  if (missing.length > 0) {
    return {
      providerId: provider.id,
      providerName: provider.name,
      providerType: provider.type,
      success: false,
      message: `\u7F3A\u5C11\u914D\u7F6E: ${missing.join(", ")}`,
      statusCode: null
    };
  }
  const sender = PROVIDER_SENDERS[provider.type];
  if (!sender) {
    return {
      providerId: provider.id,
      providerName: provider.name,
      providerType: provider.type,
      success: false,
      message: `\u672A\u77E5\u901A\u9053\u7C7B\u578B: ${provider.type}`,
      statusCode: null
    };
  }
  try {
    const result = await sender(provider, message, timeoutSec);
    return {
      ...result,
      message: redactSensitiveText(provider, result.message)
    };
  } catch (err) {
    return {
      providerId: provider.id,
      providerName: provider.name,
      providerType: provider.type,
      success: false,
      message: redactSensitiveText(provider, String(err)),
      statusCode: null
    };
  }
}
__name(sendProvider, "sendProvider");

// src/push-delivery.ts
function deliveryTargets(providers, mode, selectedProvider, failoverOrder) {
  const enabled = providers.filter((p) => p.enabled);
  if (mode === "single") {
    return enabled.filter((p) => p.id === selectedProvider);
  }
  if (mode === "failover") {
    const order = failoverOrder.length > 0 ? failoverOrder : enabled.map((p) => p.id);
    const providerMap = new Map(enabled.map((p) => [p.id, p]));
    return order.map((id) => providerMap.get(id)).filter((p) => p !== void 0);
  }
  return enabled;
}
__name(deliveryTargets, "deliveryTargets");
async function sendDelivery(providers, message, mode, selectedProvider, failoverOrder, timeoutSec) {
  const validMode = ["all", "single", "failover"].includes(mode) ? mode : "all";
  const targets = deliveryTargets(
    providers,
    validMode,
    selectedProvider,
    failoverOrder
  );
  let results;
  if (validMode === "all") {
    results = await Promise.all(
      targets.map((provider) => sendProvider(provider, message, timeoutSec))
    );
  } else {
    results = [];
    for (const provider of targets) {
      const result = await sendProvider(provider, message, timeoutSec);
      results.push(result);
      if (validMode === "failover" && result.success) break;
    }
  }
  return {
    success: results.some((r) => r.success),
    mode: validMode,
    results
  };
}
__name(sendDelivery, "sendDelivery");
function deliverySummary(report) {
  if (report.results.length === 0) return "\u6CA1\u6709\u53EF\u7528\u63A8\u9001\u901A\u9053";
  const okCount = report.results.filter((r) => r.success).length;
  return `${okCount}/${report.results.length} \u4E2A\u901A\u9053\u6210\u529F`;
}
__name(deliverySummary, "deliverySummary");

// src/index.ts
function triggerTokenFromRequest(request) {
  const url = new URL(request.url);
  const auth = request.headers.get("Authorization") || "";
  const bearerMatch = auth.match(/^Bearer\s+(.+)$/i);
  return (url.searchParams.get("token") || request.headers.get("X-Trigger-Token") || bearerMatch?.[1] || "").trim();
}
__name(triggerTokenFromRequest, "triggerTokenFromRequest");
function isTriggerAuthorized(request, env) {
  const expected = (env.TRIGGER_TOKEN || "").trim();
  if (!expected) return true;
  return triggerTokenFromRequest(request) === expected;
}
__name(isTriggerAuthorized, "isTriggerAuthorized");
function healthResponse() {
  return Response.json({ ok: true, timestamp: (/* @__PURE__ */ new Date()).toISOString() });
}
__name(healthResponse, "healthResponse");
async function runPipeline(env) {
  const config = loadConfig(env);
  const missing = missingRequired(config);
  if (missing.length > 0) {
    const msg = `\u7F3A\u5C11\u5FC5\u8981\u73AF\u5883\u53D8\u91CF: ${missing.join(", ")}`;
    console.error(msg);
    return { exitCode: 2, summary: msg };
  }
  let rawData;
  try {
    rawData = await fetchMerchantData(
      config.gameApiUrl,
      config.rocomApiKey,
      config.httpTimeout
    );
  } catch (err) {
    const errMsg = `\u65E0\u6CD5\u83B7\u53D6\u8FDC\u884C\u5546\u4EBA\u6570\u636E: ${err}`;
    console.error(errMsg);
    const report2 = await sendDelivery(
      config.providers,
      { title: "\u8FDC\u884C\u5546\u4EBA\u76D1\u63A7\u5F02\u5E38", body: errMsg, markdown: errMsg },
      config.deliveryMode,
      config.selectedProvider,
      config.failoverOrder,
      config.httpTimeout
    );
    console.log(`\u63A8\u9001\u7ED3\u679C\uFF1A${deliverySummary(report2)}`);
    return { exitCode: 1, summary: deliverySummary(report2) };
  }
  const processed = processMerchantData(rawData);
  const { products } = processed;
  if (products.length === 0 && !config.notifyEmpty) {
    const msg = "\u5F53\u524D\u6682\u65E0\u6D3B\u8DC3\u5546\u54C1\uFF0C\u5DF2\u6309 NOTIFY_EMPTY=false \u8DF3\u8FC7\u63A8\u9001";
    console.log(msg);
    return { exitCode: 0, summary: msg };
  }
  const { title, body, markdown } = buildMessage(
    processed,
    config.includePriceInfo
  );
  const report = await sendDelivery(
    config.providers,
    { title, body, markdown },
    config.deliveryMode,
    config.selectedProvider,
    config.failoverOrder,
    config.httpTimeout
  );
  const summary2 = deliverySummary(report);
  console.log(`\u63A8\u9001\u7ED3\u679C\uFF1A${summary2}`);
  for (const r of report.results) {
    const status = r.success ? "\u6210\u529F" : "\u5931\u8D25";
    console.log(`  - ${r.providerName}(${r.providerType}): ${status} ${r.message}`);
  }
  return { exitCode: report.success ? 0 : 1, summary: summary2 };
}
__name(runPipeline, "runPipeline");
var index_default = {
  // Cron trigger handler
  async scheduled(_event, env, _ctx) {
    const result = await runPipeline(env);
    console.log(`Pipeline: exit ${result.exitCode}, ${result.summary}`);
  },
  // HTTP handler (manual trigger + health check)
  async fetch(request, env, _ctx) {
    const url = new URL(request.url);
    if (url.pathname === "/" || url.pathname === "/health") {
      return healthResponse();
    }
    if (url.pathname === "/trigger") {
      if (!isTriggerAuthorized(request, env)) {
        return Response.json(
          { ok: false, error: "Unauthorized" },
          { status: 401 }
        );
      }
      const result = await runPipeline(env);
      return Response.json(result);
    }
    return new Response("Not Found", { status: 404 });
  }
};
export {
  index_default as default
};
