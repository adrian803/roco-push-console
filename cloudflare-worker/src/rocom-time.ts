import type { RoundInfo } from "./types";

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
