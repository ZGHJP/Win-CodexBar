import type { useLocale } from "../hooks/useLocale";
import type { QuotaWindowHistoryBridge } from "../types/bridge";

type T = ReturnType<typeof useLocale>["t"];

interface Props {
  history: QuotaWindowHistoryBridge | null | undefined;
  t: T;
  state?: "loading" | "error" | "empty";
  updatedAt?: number | null;
}

function shortTimestamp(value: string): string {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return value;
  const pad = (part: number) => String(part).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function formatTokens(value: number | null, complete: boolean, estimatedBoundary: boolean): string {
  if (value == null) return "—";
  const formatted = value.toLocaleString("en-US");
  return complete && !estimatedBoundary ? formatted : `~${formatted}`;
}

function formatCost(value: number | null, complete: boolean, estimatedBoundary: boolean): string {
  if (value == null) return "—";
  const formatted = `$${value.toFixed(2)}`;
  return complete && !estimatedBoundary ? formatted : `~${formatted}`;
}

/**
 * Compact, display-only history for the provider's recent quota windows.
 * Tilde-prefixed values are known subtotals whose source or boundary is not
 * complete; the component never turns them into live quota state.
 */
export function QuotaWindowHistory({ history, t, state, updatedAt }: Props) {
  const windows = history?.windows ?? [];
  if (!windows.length && state === undefined) return null;

  return (
    <section
      className="menu-card__group quota-window-history"
      aria-label={t("PanelUsageDetails")}
      data-history-coverage={history?.historyCoverageEstablished ? "complete" : "partial"}
      data-provider-id={history?.providerId}
    >
      <div className="menu-card__group-title">{t("PanelUsageDetails")}</div>
      {updatedAt != null && <div className="menu-card__cost-line menu-card__cost-line--muted">
        {t("LastUpdated")}: {shortTimestamp(new Date(updatedAt).toISOString())}
      </div>}
      {(state === "loading" || state === "error" || !windows.length) && <div role="status">
        {t(state === "loading" ? "QuotaHistoryRefreshing" : state === "error" ? "QuotaHistoryUnavailable" : "QuotaHistoryEmpty")}
      </div>}
      <div
        className="quota-window-history__rows"
        role="table"
        data-history-coverage={history?.historyCoverageEstablished ? "complete" : "partial"}
      >
        <div className="quota-window-history__row quota-window-history__row--header" role="row">
          <span role="columnheader">{t("UsageSpendColTokens")}</span>
          <span role="columnheader">{t("UsageSpendColCost")}</span>
        </div>
        {windows.map((window) => (
          <div
            className="quota-window-history__row"
            key={`${window.start}-${window.end}-${window.offset}`}
            role="row"
            data-boundaries-estimated={window.boundariesAreEstimated ? "true" : "false"}
          >
            <span role="cell">
              <span className="quota-window-history__range">
                {shortTimestamp(window.start)} → {shortTimestamp(window.end)}
              </span>
              <span className="quota-window-history__value">
                {formatTokens(
                  window.totalTokens,
                  window.tokensAreComplete,
                  window.boundariesAreEstimated,
                )}
              </span>
            </span>
            <span role="cell" className="quota-window-history__value">
              {formatCost(
                window.totalCostUsd,
                window.costIsComplete,
                window.boundariesAreEstimated,
              )}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
