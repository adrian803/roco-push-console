import type { NotificationMessage, ProviderConfig, PushResult } from "./types";
import { providerFieldDefault, providerRequiredFields } from "./provider-specs";
import { redactSensitiveText } from "./push-redaction";
import { PROVIDER_SENDERS } from "./push-provider-senders/registry";

function configuredOrDefault(provider: ProviderConfig, fieldName: string): string {
  return (
    provider.config[fieldName] ||
    providerFieldDefault(provider.type, fieldName) ||
    ""
  ).trim();
}

function missingRequired(provider: ProviderConfig): string[] {
  return [...providerRequiredFields(provider.type)].filter(
    (name) => !configuredOrDefault(provider, name)
  );
}

export async function sendProvider(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  const missing = missingRequired(provider);
  if (missing.length > 0) {
    return {
      providerId: provider.id,
      providerName: provider.name,
      providerType: provider.type,
      success: false,
      message: `缺少配置: ${missing.join(", ")}`,
      statusCode: null,
    };
  }

  const sender = PROVIDER_SENDERS[provider.type];
  if (!sender) {
    return {
      providerId: provider.id,
      providerName: provider.name,
      providerType: provider.type,
      success: false,
      message: `未知通道类型: ${provider.type}`,
      statusCode: null,
    };
  }

  try {
    const result = await sender(provider, message, timeoutSec);
    return {
      ...result,
      message: redactSensitiveText(provider, result.message),
    };
  } catch (err) {
    return {
      providerId: provider.id,
      providerName: provider.name,
      providerType: provider.type,
      success: false,
      message: redactSensitiveText(provider, String(err)),
      statusCode: null,
    };
  }
}
