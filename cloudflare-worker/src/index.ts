import type { Env, PipelineResult } from "./types";
import { loadConfig, missingRequired } from "./config";
import { fetchMerchantData } from "./rocom-client";
import { buildMessage } from "./rocom-message";
import { processMerchantData } from "./rocom-processing";
import { sendDelivery, deliverySummary } from "./push";

function triggerTokenFromRequest(request: Request): string {
  const url = new URL(request.url);
  const auth = request.headers.get("Authorization") || "";
  const bearerMatch = auth.match(/^Bearer\s+(.+)$/i);
  return (
    url.searchParams.get("token") ||
    request.headers.get("X-Trigger-Token") ||
    bearerMatch?.[1] ||
    ""
  ).trim();
}

function isTriggerAuthorized(request: Request, env: Env): boolean {
  const expected = (env.TRIGGER_TOKEN || "").trim();
  if (!expected) return true;
  return triggerTokenFromRequest(request) === expected;
}

function healthResponse(): Response {
  return Response.json({ ok: true, timestamp: new Date().toISOString() });
}

async function runPipeline(env: Env): Promise<PipelineResult> {
  const config = loadConfig(env);

  const missing = missingRequired(config);
  if (missing.length > 0) {
    const msg = `缺少必要环境变量: ${missing.join(", ")}`;
    console.error(msg);
    return { exitCode: 2, summary: msg };
  }

  let rawData: Record<string, unknown>;
  try {
    rawData = await fetchMerchantData(
      config.gameApiUrl,
      config.rocomApiKey,
      config.httpTimeout
    );
  } catch (err) {
    const errMsg = `无法获取远行商人数据: ${err}`;
    console.error(errMsg);

    const report = await sendDelivery(
      config.providers,
      { title: "远行商人监控异常", body: errMsg, markdown: errMsg },
      config.deliveryMode,
      config.selectedProvider,
      config.failoverOrder,
      config.httpTimeout
    );
    console.log(`推送结果：${deliverySummary(report)}`);
    return { exitCode: 1, summary: deliverySummary(report) };
  }

  const processed = processMerchantData(rawData);
  const { products } = processed;

  if (products.length === 0 && !config.notifyEmpty) {
    const msg = "当前暂无活跃商品，已按 NOTIFY_EMPTY=false 跳过推送";
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

  const summary = deliverySummary(report);
  console.log(`推送结果：${summary}`);
  for (const r of report.results) {
    const status = r.success ? "成功" : "失败";
    console.log(`  - ${r.providerName}(${r.providerType}): ${status} ${r.message}`);
  }

  return { exitCode: report.success ? 0 : 1, summary };
}

export default {
  // Cron trigger handler
  async scheduled(
    _event: ScheduledEvent,
    env: Env,
    _ctx: ExecutionContext
  ): Promise<void> {
    const result = await runPipeline(env);
    console.log(`Pipeline: exit ${result.exitCode}, ${result.summary}`);
  },

  // HTTP handler (manual trigger + health check)
  async fetch(
    request: Request,
    env: Env,
    _ctx: ExecutionContext
  ): Promise<Response> {
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
  },
};
