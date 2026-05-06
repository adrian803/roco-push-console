import type { NotificationMessage, ProviderConfig, PushResult } from "../types";
import { fetchWithTimeout } from "../rocom-client";
import {
  postJson,
  providerErrorResult,
  readResponsePayload,
  resultFromParsedResponse,
} from "../push-http";
import { providerConfigText, splitCsv } from "./common";

export async function sendServerChan(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  const sendkey = provider.config.sendkey;
  const url = `https://sctapi.ftqq.com/${sendkey}.send`;
  const body = new URLSearchParams({
    title: message.title,
    desp: message.markdown,
  });

  try {
    const resp = await fetchWithTimeout(
      url,
      { method: "POST", body },
      timeoutSec
    );
    const successCodes = new Set([0, "0", null, undefined]);
    const { payload, text } = await readResponsePayload(resp);
    return resultFromParsedResponse(provider, resp, payload, text, successCodes);
  } catch (err) {
    return providerErrorResult(provider, err);
  }
}

export async function sendPushPlus(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  const payload: Record<string, unknown> = {
    token: provider.config.token,
    title: message.title,
    content: message.markdown,
    template: "markdown",
  };
  for (const key of ["topic", "channel"]) {
    const v = (provider.config[key] || "").trim();
    if (v) payload[key] = v;
  }
  return postJson(provider, "https://www.pushplus.plus/send", payload, timeoutSec, {
    successCodes: new Set([200, "200", 0, "0"]),
  });
}

export async function sendWxPusher(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  const payload: Record<string, unknown> = {
    appToken: provider.config.app_token,
    content: message.markdown,
    summary: message.title,
    contentType: 3,
  };
  const uids = splitCsv(provider.config.uids);
  const topicIds = splitCsv(provider.config.topic_ids);
  if (uids.length > 0) payload.uids = uids;
  if (topicIds.length > 0) {
    payload.topicIds = topicIds.map((id) => (/^\d+$/.test(id) ? parseInt(id, 10) : id));
  }
  return postJson(
    provider,
    "https://wxpusher.zjiecode.com/api/send/message",
    payload,
    timeoutSec,
    { successCodes: new Set([1000, "1000", 0, "0"]) }
  );
}

export async function sendBark(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  const serverUrl = providerConfigText(provider, "server_url").replace(/\/$/, "");
  const url = `${serverUrl}/${provider.config.device_key}`;
  const payload: Record<string, unknown> = {
    title: message.title,
    body: `${message.body}\n\n${message.markdown}`,
  };
  const group = providerConfigText(provider, "group");
  if (group) payload.group = group;
  return postJson(provider, url, payload, timeoutSec, {
    successCodes: new Set([200, "200", 0, "0"]),
  });
}

export async function sendNtfy(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  const baseUrl = providerConfigText(provider, "base_url").replace(/\/$/, "");
  const url = `${baseUrl}/${provider.config.topic}`;
  const headers: Record<string, string> = {
    Title: message.title,
    Markdown: "yes",
  };
  for (const [cfgKey, headerName] of [
    ["priority", "Priority"],
    ["tags", "Tags"],
  ] as const) {
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
        body: message.markdown,
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
      statusCode: resp.status,
    };
  } catch (err) {
    return {
      providerId: provider.id,
      providerName: provider.name,
      providerType: provider.type,
      success: false,
      message: String(err),
      statusCode: null,
    };
  }
}

export async function sendGotify(
  provider: ProviderConfig,
  message: NotificationMessage,
  timeoutSec: number
): Promise<PushResult> {
  const baseUrl = (provider.config.base_url || "").replace(/\/$/, "");
  const appToken = encodeURIComponent(provider.config.app_token);
  const url = `${baseUrl}/message?token=${appToken}`;
  const priority = parseInt(providerConfigText(provider, "priority"), 10) || 5;
  const payload = {
    title: message.title,
    message: message.markdown,
    priority,
  };

  try {
    const resp = await fetchWithTimeout(
      url,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
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
      statusCode: resp.status,
    };
  } catch (err) {
    return {
      providerId: provider.id,
      providerName: provider.name,
      providerType: provider.type,
      success: false,
      message: String(err),
      statusCode: null,
    };
  }
}
