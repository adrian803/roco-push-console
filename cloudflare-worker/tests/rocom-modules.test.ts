import assert from "node:assert/strict";
import { test } from "node:test";

import { fetchWithTimeout } from "../src/rocom-client";
import { buildMessage, buildMerchantMarkdown } from "../src/rocom-message";
import { processMerchantData } from "../src/rocom-processing";
import { getRoundInfo } from "../src/rocom-time";

test("split rocom modules expose time, client, processing, and message boundaries", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ code: 0, data: { ok: true } }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });

  try {
    assert.equal(typeof getRoundInfo, "function");
    assert.equal(typeof processMerchantData, "function");
    assert.equal(typeof buildMerchantMarkdown, "function");
    assert.equal(typeof buildMessage, "function");

    const response = await fetchWithTimeout("https://example.com", { method: "GET" }, 1);
    assert.equal(response.status, 200);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
