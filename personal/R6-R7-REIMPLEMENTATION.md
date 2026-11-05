# Personal 0.70.0-jp.4

The R6/R7 maintenance notes were synced, but their original local commits were
not present on this fork. This version implements the documented behaviors on
the archived personal/stable R5 source; it does not claim byte-identical recovery
of the unavailable R6/R7 source.

## Changes

- Preserve reset observation capture times. Expired predictions never become
  confirmed historical resets simply because time passes.
- Keep the current weekly interval aligned to the live reset. Merge jitter
  before clipping; reconstruct sparse older windows from the recent anchor.
- Keep the previous table during same-account refresh. Account, organization,
  source, plan, and period changes cannot reuse another scope's table.
- Persist only validated quota display aggregates for 24 hours. Restore them
  during remount/restart; discard stale request completions and malformed data.
- Keep table headers and explicit loading, empty, and error states. Unknown
  amounts remain unknown rather than displaying a fabricated zero.

No pricing, Fast pricing, credits calculation, authentication permission,
Codex configuration, or proxy changes are included. Dollar values remain API
equivalent estimates, not subscription invoices.

## Validation

The four component regressions were first run against R5: three failed. After
the implementation all four passed. The focused frontend suite passed 74 tests,
including 21 cache validation/isolation tests. Cloud Rust checks and installed
Windows UI verification are recorded separately after the build completes.
