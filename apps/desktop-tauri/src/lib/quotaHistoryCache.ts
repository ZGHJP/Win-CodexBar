import type { ProviderUsageSnapshot, QuotaWindowHistoryBridge } from "../types/bridge";

export const QUOTA_HISTORY_EVENT = "codexbar:quota-history-saved";
const STORAGE_KEY = "codexbar.quota-history.v2";
const DAY_MS = 24 * 60 * 60_000;
const TOLERANCE_MS = 2 * 60_000;
const MAX_ENTRIES = 16;
let lastRequestAt = 0;

export interface QuotaHistoryScope {
  key: string;
  providerId: string;
  account: string | null;
  resetAt: number;
  windowMinutes: number;
}

export interface SavedQuotaHistory {
  key: string;
  resetAt: number;
  windowMinutes: number;
  savedAt: number;
  requestAt: number;
  history: QuotaWindowHistoryBridge;
}

/** Account, organization, source and plan changes immediately isolate UI data. */
export function chartAccountKey(provider: ProviderUsageSnapshot): string {
  const account = provider.accountEmail?.trim().toLowerCase() || null;
  return JSON.stringify([provider.providerId, account, provider.accountOrganization,
    provider.sourceLabel, provider.planName, account ? null : provider.updatedAt]);
}

export function quotaHistoryScope(provider: ProviderUsageSnapshot): QuotaHistoryScope | null {
  if (provider.providerId !== "codex" || provider.error) return null;
  const weekly = [provider.secondary, provider.primary].find((window) =>
    window?.windowMinutes != null && window.windowMinutes >= 6 * 24 * 60 && window.windowMinutes <= 8 * 24 * 60);
  const resetAt = Date.parse(weekly?.resetsAt ?? "");
  if (!weekly?.windowMinutes || !Number.isFinite(resetAt)) return null;
  return { key: chartAccountKey(provider), providerId: provider.providerId,
    account: provider.accountEmail?.trim().toLowerCase() || null, resetAt,
    windowMinutes: weekly.windowMinutes };
}

const record = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);
const finite = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
const count = (value: unknown): value is number => finite(value) && Number.isSafeInteger(value) && value >= 0;

/** Validate and copy only display aggregates; never persist a full chart or provider. */
export function validQuotaHistory(scope: QuotaHistoryScope, value: unknown): QuotaWindowHistoryBridge | null {
  if (!record(value) || value.providerId !== scope.providerId ||
      typeof value.historyCoverageEstablished !== "boolean" ||
      !(value.accountScope === null || typeof value.accountScope === "string") ||
      (typeof value.accountScope === "string" && value.accountScope.trim().toLowerCase() !== scope.account) ||
      !Array.isArray(value.windows) || value.windows.length < 1 || value.windows.length > 8) return null;
  const windows: QuotaWindowHistoryBridge["windows"] = [];
  for (const [offset, item] of value.windows.entries()) {
    if (!record(item) || item.offset !== offset || typeof item.start !== "string" || typeof item.end !== "string") return null;
    const start = Date.parse(item.start), end = Date.parse(item.end);
    if (!finite(start) || !finite(end) || start >= end ||
        (offset === 0 && (Math.abs(end - scope.resetAt) > TOLERANCE_MS ||
          Math.abs(end - start - scope.windowMinutes * 60_000) > TOLERANCE_MS)) ||
        (offset > 0 && end !== Date.parse(windows[offset - 1].start)) ||
        !(item.totalTokens === null || count(item.totalTokens)) ||
        !(item.totalCostUsd === null || (finite(item.totalCostUsd) && item.totalCostUsd >= 0)) ||
        !count(item.entryCount) || typeof item.tokensAreComplete !== "boolean" ||
        typeof item.costIsComplete !== "boolean" || typeof item.boundariesAreEstimated !== "boolean") return null;
    windows.push({ offset, start: item.start, end: item.end, totalTokens: item.totalTokens,
      totalCostUsd: item.totalCostUsd, entryCount: item.entryCount,
      tokensAreComplete: item.tokensAreComplete, costIsComplete: item.costIsComplete,
      boundariesAreEstimated: item.boundariesAreEstimated });
  }
  return { providerId: scope.providerId, accountScope: value.accountScope,
    historyCoverageEstablished: value.historyCoverageEstablished, windows };
}

function entries(): unknown[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw || raw.length > 128_000) return [];
    const value: unknown = JSON.parse(raw);
    return record(value) && value.version === 2 && Array.isArray(value.snapshots) &&
      value.snapshots.length <= MAX_ENTRIES ? value.snapshots : [];
  } catch { return []; }
}

export function readQuotaHistory(scope: QuotaHistoryScope | null, now = Date.now()): SavedQuotaHistory | null {
  if (!scope?.account) return null;
  const value = entries().find((entry) => record(entry) && entry.key === scope.key);
  if (!record(value) || !finite(value.savedAt) || value.savedAt > now || now - value.savedAt > DAY_MS ||
      !finite(value.requestAt) || value.requestAt > now + 10_000 || value.requestAt <= 0 ||
      !finite(value.resetAt) || Math.abs(value.resetAt - scope.resetAt) > TOLERANCE_MS ||
      value.windowMinutes !== scope.windowMinutes) return null;
  const history = validQuotaHistory(scope, value.history);
  if (!history) return null;
  lastRequestAt = Math.max(lastRequestAt, value.requestAt);
  return { key: scope.key, resetAt: value.resetAt, windowMinutes: scope.windowMinutes,
    savedAt: value.savedAt, requestAt: value.requestAt, history };
}

/** A request's start order, rather than completion order, decides which result wins. */
export function nextChartRequestAt(): number {
  lastRequestAt = Math.max(Date.now(), lastRequestAt + 1);
  return lastRequestAt;
}

export function saveQuotaHistory(scope: QuotaHistoryScope | null, value: unknown,
  requestAt: number, now = Date.now()): SavedQuotaHistory | null {
  if (!scope?.account) return null;
  const history = validQuotaHistory(scope, value);
  if (!history || !finite(requestAt) || requestAt <= 0 || requestAt > now + 10_000) return null;
  const existing = entries().filter(record);
  const previous = existing.find((entry) => entry.key === scope.key);
  if (previous && finite(previous.requestAt) && finite(previous.savedAt) &&
      previous.savedAt <= now && now - previous.savedAt <= DAY_MS &&
      previous.requestAt <= now + 10_000 && previous.requestAt > requestAt) return null;
  const saved = { key: scope.key, resetAt: scope.resetAt, windowMinutes: scope.windowMinutes,
    savedAt: now, requestAt, history };
  try {
    const snapshots = [...existing.filter((entry) => entry.key !== scope.key), saved]
      .sort((a, b) => Number(b.savedAt) - Number(a.savedAt)).slice(0, MAX_ENTRIES);
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ version: 2, snapshots }));
    window.dispatchEvent(new CustomEvent(QUOTA_HISTORY_EVENT, { detail: scope.key }));
  } catch { /* Real-time querying still works when storage is unavailable. */ }
  return saved;
}
