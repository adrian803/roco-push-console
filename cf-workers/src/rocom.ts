import type { MerchantProduct, ProcessedMerchantData, RoundInfo } from "./types";
import randomGoodsConf from "./random-goods-conf.json";

const BEIJING_OFFSET_MS = 8 * 60 * 60 * 1000;

export function getBeijingDate(now?: Date): Date {
  const d = now || new Date();
  return new Date(d.getTime() + BEIJING_OFFSET_MS);
}

export function formatTimestamp(tsMs: unknown): string {
  if (!tsMs) return "--:--";
  try {
    const ms = typeof tsMs === "string" ? parseInt(tsMs, 10) : Number(tsMs);
    if (isNaN(ms)) return "--:--";
    const d = new Date(ms);
    const bj = getBeijingDate(d);
    const hh = bj.getUTCHours().toString().padStart(2, "0");
    const mm = bj.getUTCMinutes().toString().padStart(2, "0");
    return `${hh}:${mm}`;
  } catch {
    return "--:--";
  }
}

export function getRoundInfo(now?: Date): RoundInfo {
  const bj = getBeijingDate(now);
  const hour = bj.getUTCHours();
  const minute = bj.getUTCMinutes();

  if (hour < 8) {
    return { current: "未开放", total: 4, countdown: "尚未开市" };
  }

  const minutesSince8 = (hour - 8) * 60 + minute;
  const roundIndex = Math.floor(minutesSince8 / (4 * 60)) + 1;

  if (roundIndex > 4) {
    return { current: 4, total: 4, countdown: "今日已收市" };
  }

  const roundEndMinutes = roundIndex * 4 * 60;
  const remainingMinutes = roundEndMinutes - minutesSince8;
  const hours = Math.floor(remainingMinutes / 60);
  const mins = remainingMinutes % 60;
  const countdown =
    hours > 0 ? `${hours}小时${mins}分钟` : `${mins}分钟`;

  return { current: roundIndex, total: 4, countdown };
}

export function getBeijingNowMs(): number {
  return Date.now();
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

interface MerchantItem {
  name?: string;
  icon_url?: string;
  start_time?: number | string;
  end_time?: number | string;
}

interface RandomGoodsRow {
  goods_name?: string;
  enable?: boolean;
  price?: number | string;
  buy_limit_num?: number | string;
}

interface RandomGoodsConf {
  RocoDataRows?: Record<string, RandomGoodsRow>;
}

interface GoodsPriceInfo {
  price: number;
  buyLimitNum: number;
}

interface MerchantActivity {
  name?: string;
  start_date?: string;
  get_props?: MerchantItem[];
  get_pets?: MerchantItem[];
}

function isActiveItem(item: MerchantItem, nowMs: number): boolean {
  const startTime = item.start_time;
  const endTime = item.end_time;
  if (!startTime || !endTime) return true;

  try {
    const s = typeof startTime === "string" ? parseInt(startTime, 10) : startTime;
    const e = typeof endTime === "string" ? parseInt(endTime, 10) : endTime;
    return s <= nowMs && nowMs < e;
  } catch {
    return false;
  }
}

const GOODS_PRICE_INFO_BY_NAME = buildGoodsPriceInfoByName(
  randomGoodsConf as RandomGoodsConf
);

function buildGoodsPriceInfoByName(conf: RandomGoodsConf): Map<string, GoodsPriceInfo> {
  const result = new Map<string, GoodsPriceInfo>();
  const rows = conf.RocoDataRows || {};
  for (const row of Object.values(rows)) {
    if (!row || row.enable === false) continue;
    const name = (row.goods_name || "").trim();
    const price = toInt(row.price);
    const buyLimitNum = toInt(row.buy_limit_num);
    if (name && price !== null && buyLimitNum !== null) {
      result.set(name, { price, buyLimitNum });
    }
  }
  return result;
}

function toInt(value: unknown): number | null {
  const parsed = typeof value === "string" ? parseInt(value, 10) : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function enrichPriceInfo(product: MerchantProduct): MerchantProduct {
  const info = GOODS_PRICE_INFO_BY_NAME.get(product.name.trim());
  if (!info) return product;
  return { ...product, price: info.price, buyLimitNum: info.buyLimitNum };
}

export function processMerchantData(
  data: Record<string, unknown>
): ProcessedMerchantData {
  const nowMs = getBeijingNowMs();
  const roundInfo = getRoundInfo();

  const activities = (data.merchantActivities || []) as MerchantActivity[];
  const activity: MerchantActivity =
    activities.length > 0 ? activities[0] : {};

  const props = activity.get_props || [];
  const pets = activity.get_pets || [];
  const allItems = [...props, ...pets].filter(
    (item): item is MerchantItem => typeof item === "object" && item !== null
  );

  const activeProducts: MerchantProduct[] = [];
  for (const item of allItems) {
    if (!isActiveItem(item, nowMs)) continue;

    let timeLabel: string;
    if (item.start_time && item.end_time) {
      timeLabel = `${formatTimestamp(item.start_time)} - ${formatTimestamp(item.end_time)}`;
    } else {
      timeLabel = "全天供应";
    }

    activeProducts.push(
      enrichPriceInfo({
        name: String(item.name || "未知"),
        image: String(item.icon_url || ""),
        timeLabel,
      })
    );
  }

  return {
    title: activity.name || "远行商人",
    subtitle:
      activity.start_date || "每日 08:00 / 12:00 / 16:00 / 20:00 刷新",
    productCount: activeProducts.length,
    roundInfo,
    products: activeProducts,
  };
}

function formatLuokeBay(value: number): string {
  if (value >= 10000) {
    const amount = value / 10000;
    const amountText = amount.toFixed(2).replace(/\.?0+$/, "");
    return `${amountText}万洛克贝`;
  }
  return `${value}洛克贝`;
}

function productLine(product: MerchantProduct, includePriceInfo: boolean): string {
  if (
    includePriceInfo &&
    typeof product.price === "number" &&
    typeof product.buyLimitNum === "number"
  ) {
    const total = product.price * product.buyLimitNum;
    return `${product.name}*${product.buyLimitNum}（${product.timeLabel}）单价${product.price} 合计${total.toLocaleString("en-US")}（${formatLuokeBay(total)}）`;
  }
  return `${product.name}（${product.timeLabel}）`;
}

export function buildMerchantMarkdown(
  processed: ProcessedMerchantData,
  includePriceInfo = false
): string {
  const ri = processed.roundInfo;
  const lines = [
    "### 远行商人刷新详情",
    "",
    `- 当前轮次：${ri.current}/${ri.total}`,
    `- 剩余时间：${ri.countdown}`,
    `- 商品数量：${processed.productCount}`,
    "",
  ];

  if (processed.products.length > 0) {
    lines.push("#### 当前售卖");
    for (const p of processed.products) {
      lines.push(`- ${productLine(p, includePriceInfo)}`);
    }
  } else {
    lines.push("当前暂无活跃商品。");
  }

  return lines.join("\n");
}

function summary(products: MerchantProduct[]): string {
  if (products.length === 0) return "当前暂无活跃商品";
  const names = products.map((p) => p.name);
  return `当前售卖: ${names.join("、")}`;
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
    markdown: `${body}\n\n${markdown}`,
  };
}

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
