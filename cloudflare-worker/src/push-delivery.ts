import type {
  DeliveryReport,
  NotificationMessage,
  ProviderConfig,
  PushResult,
} from "./types";
import { sendProvider } from "./push-providers";

function deliveryTargets(
  providers: ProviderConfig[],
  mode: string,
  selectedProvider: string,
  failoverOrder: string[]
): ProviderConfig[] {
  const enabled = providers.filter((p) => p.enabled);
  if (mode === "single") {
    return enabled.filter((p) => p.id === selectedProvider);
  }
  if (mode === "failover") {
    const order =
      failoverOrder.length > 0
        ? failoverOrder
        : enabled.map((p) => p.id);
    const providerMap = new Map(enabled.map((p) => [p.id, p]));
    return order
      .map((id) => providerMap.get(id))
      .filter((p): p is ProviderConfig => p !== undefined);
  }
  return enabled;
}

export async function sendDelivery(
  providers: ProviderConfig[],
  message: NotificationMessage,
  mode: string,
  selectedProvider: string,
  failoverOrder: string[],
  timeoutSec: number
): Promise<DeliveryReport> {
  const validMode = ["all", "single", "failover"].includes(mode) ? mode : "all";
  const targets = deliveryTargets(
    providers,
    validMode,
    selectedProvider,
    failoverOrder
  );

  let results: PushResult[];
  if (validMode === "all") {
    results = await Promise.all(
      targets.map((provider) => sendProvider(provider, message, timeoutSec))
    );
  } else {
    results = [];
    for (const provider of targets) {
      const result = await sendProvider(provider, message, timeoutSec);
      results.push(result);
      if (validMode === "failover" && result.success) break;
    }
  }

  return {
    success: results.some((r) => r.success),
    mode: validMode,
    results,
  };
}

export function deliverySummary(report: DeliveryReport): string {
  if (report.results.length === 0) return "没有可用推送通道";
  const okCount = report.results.filter((r) => r.success).length;
  return `${okCount}/${report.results.length} 个通道成功`;
}
