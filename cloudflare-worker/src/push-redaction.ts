import type { ProviderConfig } from "./types";
import { providerSecretFields } from "./provider-specs";

const SENSITIVE_NAMES =
  "access_token|app_token|corpsecret|key|read_key|readkey|secret|sendkey|token|webhook";
const SENSITIVE_QUERY_RE = new RegExp(
  `(\\b(?:${SENSITIVE_NAMES})=)([^&\\s]+)`,
  "gi"
);
const SENSITIVE_FIELD_RE = new RegExp(
  `(['"]?\\b(?:${SENSITIVE_NAMES})\\b['"]?\\s*[:=]\\s*['"]?)([^'",\\s}&]+)(['"]?)`,
  "gi"
);

export function redactSensitiveText(provider: ProviderConfig, text: string): string {
  let r = text;
  for (const fieldName of providerSecretFields(provider.type)) {
    const v = (provider.config[fieldName] || "").trim();
    if (v) {
      r = r.replaceAll(v, "[已脱敏]");
      r = r.replaceAll(encodeURIComponent(v), "[已脱敏]");
    }
  }
  r = r.replace(SENSITIVE_QUERY_RE, "$1[已脱敏]");
  r = r.replace(SENSITIVE_FIELD_RE, "$1[已脱敏]$3");
  return r;
}
