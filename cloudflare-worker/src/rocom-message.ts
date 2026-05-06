import type { MerchantProduct, ProcessedMerchantData, RoundInfo } from "./types";

function formatLuokeBay(value: number): string {
  if (value >= 10000) {
    const amount = value / 10000;
    const amountText = amount.toFixed(2).replace(/\.?0+$/, "");
    return `${amountText}万洛克贝`;
  }
  return `${value}洛克贝`;
}

function formatPrice(value: number): string {
  return value.toLocaleString("en-US");
}

function statusLine(roundInfo: RoundInfo): string {
  return `轮次：${roundInfo.current}/${roundInfo.total} · 剩余：${roundInfo.countdown}`;
}

function productLines(
  index: number,
  product: MerchantProduct,
  includePriceInfo: boolean
): string[] {
  const lines = [`${index}. ${product.name}`, `时段：${product.timeLabel}`];
  if (
    includePriceInfo &&
    typeof product.price === "number" &&
    typeof product.buyLimitNum === "number"
  ) {
    const total = product.price * product.buyLimitNum;
    lines.push(`数量：${product.buyLimitNum}`);
    lines.push(`单价：${formatPrice(product.price)}`);
    lines.push(`合计：${formatPrice(total)}（${formatLuokeBay(total)}）`);
    return lines;
  }
  if (includePriceInfo) {
    lines.push("价格：未收录");
  }
  return lines;
}

export function buildMerchantMarkdown(
  processed: ProcessedMerchantData,
  includePriceInfo = false
): string {
  const lines = [statusLine(processed.roundInfo)];

  if (processed.products.length > 0) {
    lines.push("");
    processed.products.forEach((product, index) => {
      if (index > 0) lines.push("");
      lines.push(...productLines(index + 1, product, includePriceInfo));
    });
  } else {
    lines.push("", "当前暂无活跃商品。");
  }

  return lines.join("\n");
}

function summary(products: MerchantProduct[]): string {
  if (products.length === 0) return "当前暂无活跃商品";
  const names = products.map((p) => p.name);
  return `${names.length}件商品：${names.join("、")}`;
}

export function buildMessage(processed: ProcessedMerchantData, includePriceInfo = false): {
  title: string;
  body: string;
  markdown: string;
} {
  const markdown = buildMerchantMarkdown(processed, includePriceInfo);
  const body = summary(processed.products);
  return {
    title: "远行商人已刷新",
    body,
    markdown,
  };
}
