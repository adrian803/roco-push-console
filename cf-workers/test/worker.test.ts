import assert from "node:assert/strict";
import { afterEach, test } from "node:test";

import worker from "../src/index";
import { loadConfig } from "../src/config";
import { processMerchantData } from "../src/rocom";
import { sendDelivery } from "../src/push";
import type { Env, NotificationMessage, ProviderConfig } from "../src/types";

process.env.TZ = "UTC";

const originalFetch = globalThis.fetch;
const originalDate = globalThis.Date;

afterEach(() => {
  globalThis.fetch = originalFetch;
  globalThis.Date = originalDate;
});

function env(overrides: Partial<Env> = {}): Env {
  return {
    ROCOM_API_KEY: "",
    SERVERCHAN_SENDKEY: "",
    PUSHPLUS_TOKEN: "",
    WECOM_CORPID: "",
    WECOM_SECRET: "",
    WECOM_AGENTID: "",
    WECOM_BOT_WEBHOOK: "",
    WECOM_BOT_KEY: "",
    WXPUSHER_APP_TOKEN: "",
    BARK_DEVICE_KEY: "",
    DINGTALK_WEBHOOK: "",
    DINGTALK_SECRET: "",
    FEISHU_WEBHOOK: "",
    FEISHU_SECRET: "",
    NTFY_TOPIC: "",
    NTFY_TOKEN: "",
    GOTIFY_APP_TOKEN: "",
    TRIGGER_TOKEN: "",
    ROCOM_API_URL: "",
    NOTIFY_EMPTY: "",
    DELIVERY_MODE: "",
    SELECTED_PROVIDER: "",
    FAILOVER_ORDER: "",
    HTTP_TIMEOUT: "",
    PUSHPLUS_TOPIC: "",
    PUSHPLUS_CHANNEL: "",
    WECOM_TOUSER: "",
    WXPUSHER_UIDS: "",
    WXPUSHER_TOPIC_IDS: "",
    BARK_SERVER_URL: "",
    BARK_GROUP: "",
    NTFY_BASE_URL: "",
    NTFY_PRIORITY: "",
    NTFY_TAGS: "",
    GOTIFY_BASE_URL: "",
    GOTIFY_PRIORITY: "",
    ...overrides,
  };
}

function withFakeNow(iso: string, fn: () => void): void {
  const fixedMs = originalDate.parse(iso);
  class FakeDate extends originalDate {
    constructor(value?: string | number | Date) {
      super(value ?? fixedMs);
    }

    static now(): number {
      return fixedMs;
    }
  }
  globalThis.Date = FakeDate as DateConstructor;
  try {
    fn();
  } finally {
    globalThis.Date = originalDate;
  }
}

function jsonResponse(payload: unknown, init?: ResponseInit): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

const message: NotificationMessage = {
  title: "测试标题",
  body: "测试正文",
  markdown: "测试 Markdown",
};

async function assertHealthResponse(response: Response): Promise<void> {
  assert.equal(response.status, 200);
  const payload = (await response.json()) as { ok?: boolean; timestamp?: string };
  assert.equal(payload.ok, true);
  assert.equal(typeof payload.timestamp, "string");
}

test("processMerchantData filters by real epoch time in UTC environments", () => {
  withFakeNow("2026-04-26T00:05:00Z", () => {
    const processed = processMerchantData({
      merchantActivities: [
        {
          name: "远行商人",
          get_props: [
            {
              name: "当前商品",
              start_time: originalDate.parse("2026-04-26T00:00:00Z"),
              end_time: originalDate.parse("2026-04-26T04:00:00Z"),
            },
            {
              name: "未来商品",
              start_time: originalDate.parse("2026-04-26T08:00:00Z"),
              end_time: originalDate.parse("2026-04-26T12:00:00Z"),
            },
          ],
          get_pets: [],
        },
      ],
    });

    assert.equal(processed.productCount, 1);
    assert.equal(processed.products[0]?.name, "当前商品");
  });
});

test("_worker.js exports a pasteable worker module", async () => {
  const pasteWorker = (await import("../_worker.js")).default;

  assert.equal(typeof pasteWorker.fetch, "function");
  assert.equal(typeof pasteWorker.scheduled, "function");
});

test("root path and /health both return health status", async () => {
  const bindings = env();

  await assertHealthResponse(
    await worker.fetch(
      new Request("https://worker.example/"),
      bindings,
      {} as ExecutionContext
    )
  );
  await assertHealthResponse(
    await worker.fetch(
      new Request("https://worker.example/health"),
      bindings,
      {} as ExecutionContext
    )
  );
});

test("_worker.js root path returns health status", async () => {
  const pasteWorker = (await import("../_worker.js")).default;

  await assertHealthResponse(
    await pasteWorker.fetch(
      new Request("https://worker.example/"),
      env(),
      {} as ExecutionContext
    )
  );
});

test("delivery preserves non-json HTTP error bodies without reading the body twice", async () => {
  const providers: ProviderConfig[] = [
    {
      id: "serverchan-default",
      type: "serverchan",
      name: "Server 酱",
      enabled: true,
      config: { sendkey: "send-key" },
    },
    {
      id: "pushplus-env",
      type: "pushplus",
      name: "PushPlus",
      enabled: true,
      config: { token: "push-token" },
    },
  ];
  globalThis.fetch = async () =>
    new Response("server exploded", {
      status: 500,
      statusText: "Internal Server Error",
    });

  const report = await sendDelivery(providers, message, "all", "", [], 30);

  assert.deepEqual(
    report.results.map((r) => r.statusCode),
    [500, 500]
  );
  assert.deepEqual(
    report.results.map((r) => r.message),
    ["server exploded", "server exploded"]
  );
});

test("loadConfig reads selected provider and failover order from worker vars", () => {
  const config = loadConfig(
    env({
      ROCOM_API_KEY: "rocom-key",
      SERVERCHAN_SENDKEY: "send-key",
      PUSHPLUS_TOKEN: "push-token",
      DELIVERY_MODE: "single",
      SELECTED_PROVIDER: "pushplus-env",
      FAILOVER_ORDER: "pushplus-env, serverchan-default, missing-provider",
    })
  );

  assert.equal(config.selectedProvider, "pushplus-env");
  assert.deepEqual(config.failoverOrder, [
    "pushplus-env",
    "serverchan-default",
  ]);
});

test("loadConfig defaults to cached RoCom merchant endpoint when API URL is blank", () => {
  const config = loadConfig(env({ ROCOM_API_URL: "" }));

  assert.equal(
    config.gameApiUrl,
    "https://wegame.shallow.ink/api/v1/games/rocom/merchant/info"
  );
});

test("trigger endpoint rejects invalid token while health remains public", async () => {
  const bindings = env({ TRIGGER_TOKEN: "secret-token" });

  const health = await worker.fetch(
    new Request("https://worker.example/health"),
    bindings,
    {} as ExecutionContext
  );
  const unauthorized = await worker.fetch(
    new Request("https://worker.example/trigger?token=wrong"),
    bindings,
    {} as ExecutionContext
  );

  assert.equal(health.status, 200);
  assert.equal(unauthorized.status, 401);
  assert.deepEqual(await unauthorized.json(), {
    ok: false,
    error: "Unauthorized",
  });
});

test("trigger endpoint accepts query, header, and bearer tokens", async () => {
  const bindings = env({
    TRIGGER_TOKEN: "secret-token",
    ROCOM_API_KEY: "rocom-key",
    SERVERCHAN_SENDKEY: "send-key",
    NOTIFY_EMPTY: "true",
  });
  globalThis.fetch = async (input) => {
    const url = String(input);
    if (url.includes("/merchant/info")) {
      return jsonResponse({
        code: 0,
        data: {
          merchantActivities: [
            {
              name: "远行商人",
              get_props: [{ name: "全天商品" }],
              get_pets: [],
            },
          ],
        },
      });
    }
    return jsonResponse({ code: 0, message: "ok" });
  };

  const requests = [
    new Request("https://worker.example/trigger?token=secret-token"),
    new Request("https://worker.example/trigger", {
      headers: { "X-Trigger-Token": "secret-token" },
    }),
    new Request("https://worker.example/trigger", {
      headers: { Authorization: "Bearer secret-token" },
    }),
  ];

  for (const request of requests) {
    const response = await worker.fetch(
      request,
      bindings,
      {} as ExecutionContext
    );
    assert.equal(response.status, 200);
    assert.equal((await response.json()).exitCode, 0);
  }
});

test("all delivery mode starts enabled providers concurrently", async () => {
  const providers: ProviderConfig[] = [
    {
      id: "pushplus-env",
      type: "pushplus",
      name: "PushPlus",
      enabled: true,
      config: { token: "push-token" },
    },
    {
      id: "dingtalk-env",
      type: "dingtalk_bot",
      name: "钉钉",
      enabled: true,
      config: { webhook: "https://example.com/dingtalk" },
    },
  ];
  let callCount = 0;
  let secondStarted = false;
  let releaseFirst: () => void = () => {};

  globalThis.fetch = async () => {
    callCount += 1;
    if (callCount === 1) {
      await new Promise<void>((resolve) => {
        releaseFirst = resolve;
      });
      return jsonResponse({ code: 200, message: "ok" });
    }
    secondStarted = true;
    return jsonResponse({ errcode: 0, errmsg: "ok" });
  };

  const delivery = sendDelivery(providers, message, "all", "", [], 30);
  try {
    await new Promise((resolve) => setTimeout(resolve, 20));
    assert.equal(secondStarted, true);
  } finally {
    releaseFirst();
    await delivery;
  }
});
