import type { MerchantProduct, ProcessedMerchantData } from "./types";
import randomGoodsConf from "./random-goods-conf.json";
import { formatTimestamp, getBeijingNowMs, getRoundInfo } from "./rocom-time";

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

function catalogNameCandidates(name: string): string[] {
  const normalized = name.trim();
  const candidates = normalized ? [normalized] : [];
  if (normalized.includes("精灵蛋")) {
    candidates.push(normalized.replaceAll("精灵蛋", "蛋"));
  }
  return [...new Set(candidates)];
}

function priceInfoForName(name: string): GoodsPriceInfo | undefined {
  for (const candidate of catalogNameCandidates(name)) {
    const info = GOODS_PRICE_INFO_BY_NAME.get(candidate);
    if (info) return info;
  }
  return undefined;
}

function enrichPriceInfo(product: MerchantProduct): MerchantProduct {
  const info = priceInfoForName(product.name);
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
