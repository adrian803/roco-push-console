/** Cloudflare Worker environment bindings */
export interface Env {
  // Secrets
  ROCOM_API_KEY: string;
  SERVERCHAN_SENDKEY: string;
  PUSHPLUS_TOKEN: string;
  WECOM_CORPID: string;
  WECOM_SECRET: string;
  WECOM_AGENTID: string;
  WECOM_BOT_WEBHOOK: string;
  WECOM_BOT_KEY: string;
  WXPUSHER_APP_TOKEN: string;
  BARK_DEVICE_KEY: string;
  DINGTALK_WEBHOOK: string;
  DINGTALK_SECRET: string;
  FEISHU_WEBHOOK: string;
  FEISHU_SECRET: string;
  NTFY_TOPIC: string;
  NTFY_TOKEN: string;
  GOTIFY_APP_TOKEN: string;
  TRIGGER_TOKEN: string;

  // Vars (from wrangler.toml [vars])
  ROCOM_API_URL: string;
  NOTIFY_EMPTY: string;
  DELIVERY_MODE: string;
  SELECTED_PROVIDER: string;
  FAILOVER_ORDER: string;
  HTTP_TIMEOUT: string;
  INCLUDE_PRICE_INFO: string;
  PUSHPLUS_TOPIC: string;
  PUSHPLUS_CHANNEL: string;
  WECOM_TOUSER: string;
  WXPUSHER_UIDS: string;
  WXPUSHER_TOPIC_IDS: string;
  BARK_SERVER_URL: string;
  BARK_GROUP: string;
  NTFY_BASE_URL: string;
  NTFY_PRIORITY: string;
  NTFY_TAGS: string;
  GOTIFY_BASE_URL: string;
  GOTIFY_PRIORITY: string;
}

export interface ProviderField {
  name: string;
  label: string;
  secret?: boolean;
  required?: boolean;
  default?: string;
}

export interface ProviderSpec {
  label: string;
  description: string;
  fields: ProviderField[];
}

export interface ProviderConfig {
  id: string;
  type: string;
  name: string;
  enabled: boolean;
  config: Record<string, string>;
}

export interface NotificationMessage {
  title: string;
  body: string;
  markdown: string;
}

export interface PushResult {
  providerId: string;
  providerName: string;
  providerType: string;
  success: boolean;
  message: string;
  statusCode: number | null;
}

export interface DeliveryReport {
  success: boolean;
  mode: string;
  results: PushResult[];
}

export interface Config {
  rocomApiKey: string;
  gameApiUrl: string;
  notifyEmpty: boolean;
  httpTimeout: number;
  includePriceInfo: boolean;
  deliveryMode: string;
  selectedProvider: string;
  failoverOrder: string[];
  providers: ProviderConfig[];
}

export interface MerchantProduct {
  name: string;
  image: string;
  timeLabel: string;
  price?: number;
  buyLimitNum?: number;
}

export interface RoundInfo {
  current: number | string;
  total: number;
  countdown: string;
}

export interface ProcessedMerchantData {
  title: string;
  subtitle: string;
  productCount: number;
  roundInfo: RoundInfo;
  products: MerchantProduct[];
}

export interface PipelineResult {
  exitCode: number;
  summary: string;
}
