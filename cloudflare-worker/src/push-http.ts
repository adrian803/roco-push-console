import type { ProviderConfig, PushResult } from "./types";
import { fetchWithTimeout } from "./rocom-client";
import { redactSensitiveText } from "./push-redaction";

export function jsonResult(
  payload: Record<string, unknown>,
  successCodes: Set<unknown>
): { success: boolean; message: string } {
  const code = payload.code ?? payload.errcode;
  let success = successCodes.has(code);
  if (code === undefined && Object.keys(payload).length === 0) {
    success = true;
  }
  const message = String(
    payload.message || payload.msg || payload.errmsg || JSON.stringify(payload)
  );
  return { success, message };
}

export async function readResponsePayload(resp: Response): Promise<{
  payload: Record<string, unknown>;
  text: string;
}> {
  const text = await resp.text();
  if (!text.trim()) return { payload: {}, text: "" };
  try {
    const parsed = JSON.parse(text) as unknown;
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return { payload: parsed as Record<string, unknown>, text };
    }
  } catch {
    // non-json response body
  }
  return { payload: {}, text };
}

export function resultFromParsedResponse(
  provider: ProviderConfig,
  resp: Response,
  payload: Record<string, unknown>,
  text: string,
  successCodes: Set<unknown>
): PushResult {
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
    statusCode: resp.status,
  };
}

export function providerErrorResult(provider: ProviderConfig, err: unknown): PushResult {
  return {
    providerId: provider.id,
    providerName: provider.name,
    providerType: provider.type,
    success: false,
    message: redactSensitiveText(provider, String(err)),
    statusCode: null,
  };
}

export async function postJson(
  provider: ProviderConfig,
  url: string,
  payload: Record<string, unknown>,
  timeoutSec: number,
  options?: { headers?: Record<string, string>; successCodes?: Set<unknown> }
): Promise<PushResult> {
  const successCodes = options?.successCodes ?? new Set([0, "0"]);
  try {
    const resp = await fetchWithTimeout(
      url,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...options?.headers,
        },
        body: JSON.stringify(payload),
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
