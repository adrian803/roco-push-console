import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { deliverySummary } from "../src/push-delivery";
import {
  providerRequiredFields,
  providerSecretFields,
  providerEnvFields,
  providerEnvBindingNames,
  providerEnvId,
  validateProviderManifest,
  PROVIDER_TYPES,
} from "../src/provider-specs";
import { buildMerchantMarkdown } from "../src/rocom";
import type { DeliveryReport } from "../src/types";

const fixture = JSON.parse(
  readFileSync(
    new URL("../../tests/fixtures/cross_runtime_cases.json", import.meta.url),
    "utf8"
  )
) as {
  provider_specs: Array<{
    type: string;
    secret_fields: string[];
    required_fields: string[];
  }>;
  price_markdown: {
    worker_processed: Parameters<typeof buildMerchantMarkdown>[0];
    expected_lines: string[];
  };
  delivery_summary: {
    worker_report: DeliveryReport;
    expected: string;
  };
};

test("shared fixture keeps provider specs aligned with Python", () => {
  for (const provider of fixture.provider_specs) {
    assert.deepEqual(
      [...providerSecretFields(provider.type)].sort(),
      [...provider.secret_fields].sort()
    );
    assert.deepEqual(
      [...providerRequiredFields(provider.type)].sort(),
      [...provider.required_fields].sort()
    );
  }
});

test("shared manifest keeps env mappings aligned with Python", () => {
  for (const [providerType, spec] of Object.entries(PROVIDER_TYPES)) {
    assert.equal(providerEnvId(providerType), spec.envId);
    assert.deepEqual(providerEnvFields(providerType), spec.envVars);
  }
});

test("provider env binding list is derived from manifest env vars", () => {
  const expected = [
    ...new Set(
      Object.values(PROVIDER_TYPES).flatMap((spec) => Object.values(spec.envVars))
    ),
  ];

  assert.deepEqual(providerEnvBindingNames(), expected);
});

test("provider manifest validation rejects env mappings without matching fields", () => {
  assert.throws(
    () =>
      validateProviderManifest({
        providers: [
          {
            type: "broken",
            label: "Broken",
            description: "Broken provider",
            envId: "broken-env",
            envVars: { token: "BROKEN_TOKEN" },
            fields: [{ name: "other", label: "Other" }],
          },
        ],
      }),
    /envVars/
  );
});

test("shared fixture keeps price markdown aligned with Python", () => {
  const markdown = buildMerchantMarkdown(
    fixture.price_markdown.worker_processed,
    true
  );

  for (const expectedLine of fixture.price_markdown.expected_lines) {
    assert.ok(markdown.includes(expectedLine));
  }
});

test("shared fixture keeps delivery summaries aligned with Python", () => {
  assert.equal(
    deliverySummary(fixture.delivery_summary.worker_report),
    fixture.delivery_summary.expected
  );
});
