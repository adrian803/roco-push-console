/** Cloudflare Worker bindings that are not owned by provider_manifest.json. */
export interface CoreEnv {
  ROCOM_API_KEY: string;
  TRIGGER_TOKEN: string;

  // Vars (from wrangler.toml [vars])
  ROCOM_API_URL: string;
  NOTIFY_EMPTY: string;
  DELIVERY_MODE: string;
  SELECTED_PROVIDER: string;
  FAILOVER_ORDER: string;
  HTTP_TIMEOUT: string;
  INCLUDE_PRICE_INFO: string;
}

export type Env = CoreEnv & Record<string, string | undefined>;

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
  envId: string;
  envVars: Record<string, string>;
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
