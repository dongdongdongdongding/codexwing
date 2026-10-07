# Actual daily archive recovery

The premarket daily worker finished at 07:18:06 UTC with exit code 9. Its two
reported failures were `archive_us_daily_panels(rc=1)` and `us_daily_panel(rc=1)`.
The independent KR close scan finished with exit code 0 at 07:17:08 UTC, and the
queued post-close daily worker started automatically at 07:19:06 UTC. These actual
receipts close scheduling issue `l64n`; they do not certify data completeness.

The archive journal held group `693f16f928c347f68256319dd00e366b`. Both original
hardlink aliases retained the planned device/inode/size/nanosecond-mtime identity.
The external target did not exist. Source SHA256 matched
`d56dbede437f47b5cb16bb81d79f5c3cb094ba08a5455c607f0eb3bdd575f6b7`.

A resume under the shared US writer lock completed at 07:31:34 UTC with exit 0.
It archived five immutable panels (18,918,492,776 bytes) and preserved nine existing
paths as symlinks. Separate verification checked every target hash, every alias
target and original mtime, and readable Parquet metadata. The pending journal was
cleared. Repeating the deployed CLI planned and moved zero groups; available local
space was 39,976,472,576 bytes at that check. Nothing was pruned or reclassified.

The original detailed exception was lost from the daily worker's final 6,000-character
stderr tail. Manual recovery did not reproduce it, so its root cause remains unknown.
Commit `5212c2a` adds durable per-invocation receipts under
`~/research_cache/us_daily/NASDAQ/.refresh/panel_archive/runs/`, including failures,
tracebacks and the observed pending journal. Logging failure cannot mask the actual
exception. The archive and shell portability suite passed 62 tests, including
failed-copy preservation, recovery, repeat no-op and an unwritable diagnostic path.
The next natural worker invocation is tracked in `swing-main-rixl`.

The separate US refresh at 15:55 KST remained **partial**: 342 raw files updated,
3,491 skipped as fresh, 137 failed, none unvisited. Failure categories were 19
incomplete adjustment histories, 73 absent requested sessions and 45 empty replies.
Coverage was 3,838/3,970 symbols through October 6. Network/DNS/sqlite messages do
not establish that empty symbols are delisted. The generated panel contains
5,598,633 rows / 3,947 symbols, with 23 feature-symbol failures. Existing unresolved
source and split-basis cases remain tracked in `va65`, `thec`, `foju` and `kc3g`.

Evidence: production `runtime_state/audit/us_panel_archive_recovery_20261007/` and
`runtime_state/audit/daily_batch_terminal_20261007/`; refresh audit
`~/research_cache/us_daily/NASDAQ/.refresh/audit/20261007T155500_19df119d18e142dab098ac8efe185958/`.
