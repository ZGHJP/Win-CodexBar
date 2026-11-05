import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ProviderUsageSnapshot, QuotaWindowHistoryBridge } from "../types/bridge";
import { chartAccountKey, quotaHistoryScope, readQuotaHistory, saveQuotaHistory, validQuotaHistory } from "./quotaHistoryCache";

const now = Date.parse("2026-11-06T08:00:00Z");
const reset = new Date(now + 3 * 86_400_000).toISOString();
const snapshot = {
  providerId: "codex", accountEmail: "one@example.test", accountOrganization: "org-a",
  planName: "Pro", sourceLabel: "oauth", updatedAt: new Date(now).toISOString(), error: null,
  primary: { windowMinutes: 300, resetsAt: null },
  secondary: { windowMinutes: 10_080, resetsAt: reset },
} as ProviderUsageSnapshot;
const scope = quotaHistoryScope(snapshot)!;
const history: QuotaWindowHistoryBridge = {
  providerId: "codex", accountScope: "one@example.test", historyCoverageEstablished: false,
  windows: [{ offset: 0, start: new Date(Date.parse(reset) - 7 * 86_400_000).toISOString(), end: reset,
    totalTokens: 1200, totalCostUsd: null, tokensAreComplete: true, costIsComplete: false,
    entryCount: 2, boundariesAreEstimated: true }],
};

describe("quota history display snapshots", () => {
  beforeEach(() => { localStorage.clear(); vi.restoreAllMocks(); });

  it("restores only validated display aggregates and leaves unknown prices unknown", () => {
    saveQuotaHistory(scope, { ...history, credentials: "must-not-persist" }, now, now);
    const saved = readQuotaHistory(scope, now + 1000);
    expect(saved?.history.windows[0].totalCostUsd).toBeNull();
    expect(saved?.history).toEqual(history);
    expect(localStorage.getItem("codexbar.quota-history.v2")).not.toContain("must-not-persist");
  });

  it.each([
    { accountEmail: "two@example.test" }, { accountOrganization: "org-b" },
    { sourceLabel: "web" }, { planName: "Business" }, { providerId: "claude" },
  ])("isolates a different identity or data source: %j", (change) => {
    saveQuotaHistory(scope, history, now, now);
    expect(readQuotaHistory(quotaHistoryScope({ ...snapshot, ...change }), now)).toBeNull();
    expect(chartAccountKey({ ...snapshot, ...change })).not.toBe(scope.key);
  });

  it("accepts two-minute reset jitter but rejects a new cycle or duration", () => {
    saveQuotaHistory(scope, history, now, now);
    expect(readQuotaHistory({ ...scope, resetAt: scope.resetAt + 120_000 }, now)).not.toBeNull();
    expect(readQuotaHistory({ ...scope, resetAt: scope.resetAt + 86_400_000 }, now)).toBeNull();
    expect(readQuotaHistory({ ...scope, windowMinutes: 9_000 }, now)).toBeNull();
  });

  it("expires snapshots after 24 hours and rejects a backwards wall clock", () => {
    saveQuotaHistory(scope, history, now, now);
    expect(readQuotaHistory(scope, now + 86_400_001)).toBeNull();
    expect(readQuotaHistory(scope, now - 1)).toBeNull();
  });

  it("rejects stale late completions after a newer request has finished", () => {
    saveQuotaHistory(scope, { ...history, windows: [{ ...history.windows[0], totalTokens: 2400 }] }, now + 1, now + 10);
    expect(saveQuotaHistory(scope, history, now, now + 20)).toBeNull();
    expect(readQuotaHistory(scope, now + 30)?.history.windows[0].totalTokens).toBe(2400);
  });

  it("does not persist snapshots when the account is unknown", () => {
    const anonymous = quotaHistoryScope({ ...snapshot, accountEmail: null })!;
    expect(saveQuotaHistory(anonymous, { ...history, accountScope: null }, now, now)).toBeNull();
    expect(localStorage.length).toBe(0);
  });

  it.each([
    { totalTokens: -1 }, { totalTokens: Number.NaN }, { totalTokens: Number.MAX_SAFE_INTEGER + 1 },
    { totalCostUsd: -2 }, { costIsComplete: "true" }, { entryCount: -1 },
    { offset: 1 }, { start: "invalid" }, { end: "invalid" },
  ])("rejects malformed history fields: %j", (change) => {
    expect(validQuotaHistory(scope, { ...history, windows: [{ ...history.windows[0], ...change }] })).toBeNull();
  });

  it("rejects another account's result, excessive rows and discontinuous periods", () => {
    expect(validQuotaHistory(scope, { ...history, accountScope: "two@example.test" })).toBeNull();
    expect(validQuotaHistory(scope, { ...history, windows: Array(9).fill(history.windows[0]) })).toBeNull();
    expect(validQuotaHistory(scope, { ...history, windows: [history.windows[0], {
      ...history.windows[0], offset: 1, start: "2026-10-01T00:00:00Z", end: "2026-10-08T00:00:00Z",
    }] })).toBeNull();
  });

  it("survives corrupted or unavailable storage without interrupting live results", () => {
    localStorage.setItem("codexbar.quota-history.v2", "invalid json");
    expect(readQuotaHistory(scope, now)).toBeNull();
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("unavailable"); });
    expect(saveQuotaHistory(scope, history, now, now)?.history).toEqual(history);
    expect(readQuotaHistory(scope, now)).toBeNull();
  });
});
