export async function fetchWithTimeout(
  url: string,
  init: RequestInit,
  timeoutSec: number
): Promise<Response> {
  const ctrl = new AbortController();
  const id = setTimeout(() => ctrl.abort(), timeoutSec * 1000);
  try {
    return await fetch(url, { ...init, signal: ctrl.signal });
  } finally {
    clearTimeout(id);
  }
}

export async function fetchMerchantData(
  apiUrl: string,
  apiKey: string,
  timeoutSec: number
): Promise<Record<string, unknown>> {
  if (!apiKey) throw new Error("缺少 ROCOM_API_KEY");

  const resp = await fetchWithTimeout(
    apiUrl,
    { method: "GET", headers: { "X-API-Key": apiKey } },
    timeoutSec
  );

  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
  }

  const payload = (await resp.json()) as {
    code: number;
    message?: string;
    data?: Record<string, unknown>;
  };

  if (payload.code !== 0) {
    throw new Error(payload.message || "接口返回失败");
  }

  if (!payload.data || typeof payload.data !== "object") {
    throw new Error("接口返回 data 不是对象");
  }

  return payload.data;
}
