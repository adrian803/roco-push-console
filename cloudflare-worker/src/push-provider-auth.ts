import { fetchWithTimeout } from "./rocom-client";

const wecomTokenCache = new Map<
  string,
  { token: string; expiresAt: number }
>();

export function clearWecomTokenCache(): void {
  wecomTokenCache.clear();
}

export async function getWecomToken(
  corpid: string,
  secret: string,
  timeoutSec: number
): Promise<string> {
  const key = `${corpid}:${secret}`;
  const cached = wecomTokenCache.get(key);
  const now = Math.floor(Date.now() / 1000);
  if (cached && cached.expiresAt > now + 60) return cached.token;

  const url = `https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=${encodeURIComponent(corpid)}&corpsecret=${encodeURIComponent(secret)}`;
  const resp = await fetchWithTimeout(url, { method: "GET" }, timeoutSec);
  const payload = (await resp.json()) as {
    errcode: number | string;
    access_token?: string;
    expires_in?: number;
    errmsg?: string;
  };

  if (resp.status >= 400 || (payload.errcode !== 0 && payload.errcode !== "0")) {
    throw new Error(payload.errmsg || JSON.stringify(payload));
  }

  const token = payload.access_token!;
  const expiresIn = payload.expires_in || 7200;
  wecomTokenCache.set(key, { token, expiresAt: now + expiresIn });
  return token;
}

async function hmacSha256Base64(
  keyData: BufferSource,
  messageData: BufferSource
): Promise<string> {
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

export async function appendDingTalkSign(
  webhook: string,
  secret: string
): Promise<string> {
  if (!secret) return webhook;
  const timestamp = Date.now().toString();
  const stringToSign = `${timestamp}\n${secret}`;
  const encoder = new TextEncoder();
  const sign = await hmacSha256Base64(
    encoder.encode(secret),
    encoder.encode(stringToSign)
  );
  const sep = webhook.includes("?") ? "&" : "?";
  return `${webhook}${sep}timestamp=${timestamp}&sign=${encodeURIComponent(sign)}`;
}

export async function feishuSign(secret: string, timestamp: string): Promise<string> {
  const stringToSign = `${timestamp}\n${secret}`;
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
