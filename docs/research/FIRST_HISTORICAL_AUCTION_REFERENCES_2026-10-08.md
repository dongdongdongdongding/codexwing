# Historical opening-auction references and a recovered quote request

Issues `swing-main-65d8` and `swing-main-gz0u`; whole-source reconciliation
remains in `swing-main-01n3`.

The same 38 complete primary search windows contain fourteen auction-method
notices for thirteen securities. Each specifies that the first opening-auction
price becomes the reference, within published bounds. Evaluated prices differ
from actual references in every case below.

| Code | Effective date | Evaluated price | Verified opening reference |
| --- | --- | ---: | ---: |
| 001080 | 2024-09-23 | 47,150 | 45,000 |
| 001140 | 2024-02-02 | 3,150 | 3,600 |
| 001230 | 2026-05-29 | 2,280 | 2,545 |
| 001340 | 2024-04-22 | 7,790 | 9,090 |
| 002070 | 2026-05-06 | 10,650 | 14,000 |
| 002210 | 2025-06-24 | 2,780 | 1,390 |
| 002880 | 2023-12-20 | 966 | 1,130 |
| 003060 | 2024-04-16 | 1,900 | 1,818 |
| 003060 | 2026-05-08 | 3,765 | 4,000 |
| 003620 | 2025-05-09 | 3,260 | 3,490 |
| 004380 | 2026-04-09 | 9,960 | 13,000 |
| 004710 | 2025-09-26 | 5,490 | 5,730 |
| 004800 | 2024-07-29 | 59,000 | 45,450 |
| 006740 | 2026-05-29 | 7,070 | 6,820 |

`audit_first_historical_auction_references.py` revalidates the preceding fixed
batch and its cached search/body evidence, then matches each method to the
original candidate inventory, nominal receipt identity, source boundary and
official viewer's company/code header. The actual reference must equal both
nominal open and close minus signed change, match source open, have positive
volume and lie within the official bounds. Notice and listing publication must
precede or equal the effective date.

Ten capital-change events also have final listing evidence. Reviewed share
counts match source values on both sides. The other four are resumption notices
with unchanged outstanding shares. In particular:

- 001140 combines a tenfold split with a one-tenth consolidation, leaving
  12,589,769 outstanding shares. Its earlier cumulative adjustment is preserved.
- 001230 combines a cancellation, par-value reduction and fivefold split:
  31,800,483 → 31,101,543 → 155,507,715 outstanding shares.
- 003620 adds 5,952,380 conversion shares to reach 202,356,634. Its separate
  5,000-to-1,000 par-value reduction leaves that share count unchanged.
- 004710's 5,000-to-1,000 par-value reduction leaves 32,109,878 shares unchanged.
- 004800's surviving company falls from 20,466,334 to 16,740,407 shares.
  New-company shares and other distributions remain outside this price overlay.

Historical names 백광산업/대유에이텍 remain in their original notices; current
official viewer headers bind those same documents to PKC (001340) and
디와이에이 (002880). The nominal 001140 response has no company name. This
specific exception requires the indexed request code plus official viewer and
final listing identity; it remains explicitly marked as missing provider-name
metadata. Other missing or conflicting names fail validation. These current
identity bindings do not establish historical information availability.

## V13 verification

V13 adds 51 nonoverlapping rules affecting 4,667 rows. Independent verification
of all 5,360,785 rows confirms identical schema/metadata and raw fields, including
stocks, with all fields identical in the other 5,356,118 rows. A separate
75-digit calculation reproduces every corrected factor after float conversion
and checks 18,668 adjusted prices; maximum relative representation error is
2.66e-16.

The unchanged 1,353-code / 872,671-date comparison confirms all four tables are
exact for the other 1,340 codes, and entire nominal/provider-basis tables remain
exact. Seven corrected securities now have no comparable differences above one
KRW, including exact zero differences for 001340 and 002210. The diagnostic queue
falls **200 to 193 codes**, with the same three anchorless securities unresolved.

Six corrected codes remain in that queue. Four have maxima above one only by
roughly 1e-13 to 1e-12 KRW; these flags are retained. 003060 retains 1.007731 KRW
across six flagged cells. 002880 still has eleven flagged cells across December
15–21, 2023, with maximum 1,455.681180 KRW. Its source factor changes again on
December 22 despite unchanged listed shares. That separate boundary remains
unreconciled; the verified December 20 auction does not certify the whole code.

Actual verifier/normalizer replay reused v13, made zero network calls, and
preserved 2,248 existing files' bytes, sizes and modification times. 93 related
tests pass, including method/class/bounds rejection, identity binding, unchanged
share counts under par-value reduction, concurrent conversion shares, existing
cumulative factors, and the recovery protocol.

## 102460 request recovery

The original nominal request for June 7–September 4, 2025 ended in
`KISOpenAPIError` without a payload. Its cause is unknown. Before retrying, the
paired adjusted response was verified to contain exactly the 63 scoped dates,
June 9–September 4, with all 378 OHLC/volume/amount values identical to nominal
source values. `recover_reviewed_history_102460.py` pins that paired receipt,
the original failure, the scope, v13 and unchanged collector dependencies.

A separate epoch made **one** same-identity request with automatic retries
disabled. The response is complete and matches all 378 source and paired values.
Independent Decimal checks confirm every value. Replay makes zero requests and
preserves all six existing files, including the original error. The opt-in
resolver verifies the new plan and both provenance hashes. This supplement is
available for a future frozen coverage index; the existing fixed 30,936-request
comparison is unchanged. The CLI returns nonzero for an unaccepted recovery.

Evidence under production `runtime_state/audit/`:

- `first_historical_auction_evidence_20261008/verification.json`
- `kr_verified_events_v13_20261008/` and `independent_verification.json`
- `lowliq_history_indexed_comparison_v13_20261008/`
- `first_historical_auction_replay_20261008.json`
- `lowliq_history_102460_recovery_20261008/`

Auction proof SHA: `0b4aa1ab38a5a48cb7ec1ef89de1e924650ca025a769eb530cc214321accca51`.
V13 SHA: `b574338c410d620dd6802473aa9066254838158dac2604bd57692ea470c28116`.
Recovery plan SHA: `afafb1c787dccc69a81303de56bcfaf2d1bfa4011c194102e221d73a392cebb1`.
Recovery response SHA: `22b5e309f6a23bcc531ef35a9be391d4ff3198630cc43d107d94b387baca077c`.

No whole-source, point-in-time, investor-wealth or publication certificate is
issued. Official outstanding shares are preserved, not treated as an investor's
entitlement ratio. There is no Q3 outcome calculation, refit or live lane switch.
