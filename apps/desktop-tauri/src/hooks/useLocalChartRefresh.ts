import { useEffect, useState } from "react";

/** Local logs can change while the remote quota snapshot stays unchanged. */
export function useLocalChartRefresh(enabled: boolean): number {
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    if (!enabled) return;
    let lastRefresh = Date.now();
    const refresh = () => {
      if (Date.now() - lastRefresh < 60_000) return;
      lastRefresh = Date.now();
      setRevision((value) => value + 1);
    };
    const visible = () => { if (document.visibilityState === "visible") refresh(); };
    const timer = window.setInterval(refresh, 60_000);
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", visible);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", refresh);
      document.removeEventListener("visibilitychange", visible);
    };
  }, [enabled]);
  return revision;
}
