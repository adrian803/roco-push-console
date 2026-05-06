import type { NotificationMessage, ProviderConfig, PushResult } from "../types";
import { providerFieldDefault } from "../provider-specs";

export type Sender = (
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
) => Promise<PushResult>;

export function splitCsv(value: string | undefined): string[] {
  if (!value) return [];
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

export function providerConfigText(
  provider: ProviderConfig,
  fieldName: string
): string {
  return (
    provider.config[fieldName] ||
    providerFieldDefault(provider.type, fieldName) ||
    ""
  ).trim();
}
