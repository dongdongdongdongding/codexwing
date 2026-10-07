# Historical price-reference repair v8

The first independently captured historical prefix exposed discrepancies outside the earlier Q3 window. v8 corrects **nine events across seven codes / 3,271 source rows**, using published KRX reference prices, independently corroborated reopening references, and explicit nontrading quote evidence. It is a separate immutable research panel. The prior study, six models, scores, raw fields and live producer remain unchanged.

| Code | Date | Verified price-reference treatment |
|---|---|---|
| 000040 | 2024-03-18 | Capital-reduction auction: previous close 465, executed opening/reference 1,624. The notice's evaluated 1,534 is not the reference. |
| 000040 | 2024-03-20 | Published rights reference 1,042, previous close 1,261. |
| 000070 | 2025-11-24 | Spin-off reopening: previous close 104,600, executed opening/reference 69,800; replaces the old close-ratio heuristic. |
| 000100 | 2023-12-27 | Published common-share reference 66,900, previous close 69,900. |
| 000105 | 2023-12-27 | Published first-preferred reference 62,200, previous close 65,200; the security's own KIS request/name also matches. |
| 000500 | 2026-06-30 | Published bonus reference 190,600, previous close 343,000. |
| 000145 | 2024-01-18 | Remove false administrative adjustment. Keep nominal close 12,200 and its −30 quote change; reference remains previous close 12,230. |
| 000325 | 2025-03-21 | Remove false administrative adjustment. Keep close 28,600 and −100 quote change. |
| 000325 | 2026-09-11 | Remove false administrative adjustment. Keep close 27,600 and −200 quote change. |

The three nontrading cases require unchanged share counts, zero current volume/amount, positive preceding volume, a signed quote change whose reference is the previous nominal close, zero provider adjustment-rate marker, and a reproduced `admin` algorithm event. Every captured nominal/adjusted close of those two codes agrees. The correction preserves the observed price change instead of smoothing it away. A missing disclosure search result is not used as proof that no event occurred.

For each event, the overlay multiplier is the exact rational expression `before_factor / old_event_factor * previous_close / verified_reference`. Multiple events compose before final conversion to float; 19 disjoint rules preserve subsequent relative adjustments and guard original factors, share counts, dates and row counts.

Primary evidence was captured in eight fixed windows: **181 search disclosures, 40 selected documents, 54 body resources, 155 HTTP 200 receipts**. Bodies include disclosure revisions where the viewer exposes them. An independent byte/hash/text verification passed, and actual replay preserved **483 files** without network calls. These are captured viewer body resources, not a claim that every appendix or every company-history disclosure was collected. A supplemental preferred-code-only search returned zero results; it does not establish absence of corporate actions.

Key official references: [KR모터스 감자 listing](https://kind.krx.co.kr/common/disclsviewer.do?method=search&acptno=20240313000218), [KR모터스 auction method](https://kind.krx.co.kr/common/disclsviewer.do?method=search&acptno=20240315000616), [KR모터스 rights reference](https://kind.krx.co.kr/common/disclsviewer.do?method=search&acptno=20240319000562), [삼양홀딩스 reopening method](https://kind.krx.co.kr/common/disclsviewer.do?method=search&acptno=20251121000436), [유한양행 common reference](https://kind.krx.co.kr/common/disclsviewer.do?method=search&acptno=20231226000728), [유한양행 preferred reference](https://kind.krx.co.kr/common/disclsviewer.do?method=search&acptno=20231226000734), [가온전선 reference](https://kind.krx.co.kr/common/disclsviewer.do?method=search&acptno=20260629000820).

Validation completed:

- **64 tests passed**, including ambiguous quote signs, changed share counts, nontrading volume, provider-basis disagreement, wrong algorithm rules, composed overlays and preserved later factors.
- Independent Decimal-70 reconstruction checked all **5,360,785 rows**. All raw fields/schema and the other **5,357,514 rows** are exact. Corrected rows by code: 000040 619; 000070 210; 000100 672; 000105 672; 000145 658; 000325 375; 000500 65.
- Actual normalization replay returned `REUSED`; panel/manifest/receipt hashes, sizes and mtimes were unchanged, with no network calls.
- Full fixed Q3 cohort recheck: **1,310 codes / 85,104 dates / 2,620 responses**, 336,234 comparable adjusted cells. Nominal differences and provider-basis diagnostics are unchanged. Maximum comparable difference remains `1.000000000000551599031226` KRW; 1,296 nonempty half-open coefficient intervals, one closed-boundary-only case and 13 tiny storage gaps. These remain diagnostics, not certification tolerances.
- The **same first 43-code / 27,520-row historical prefix with 972 pinned responses** has 41 nonempty coefficient intervals after correction. All nominal close/volume/amount cells still agree; 2,148 nominal OHL differences are the unchanged zero-volume convention. Two exceptions remain explicitly unresolved.

The first exception is **000300 (DH오토넥스), 2026-01-14**. Its official listing records a real 2:1 capital reduction while trading remains suspended. The amended notice calls 4,200 an *evaluated price*, and the provider quote has sign code 0 and zero volume. There is no executed auction reference to justify treating 4,200 as one. The source retains its share factor; removing it merely to match KIS would confuse quote representation and shareholder wealth. This remains a substantial 2,100-KRW comparable discrepancy and blocks whole-source qualification.

The second is **000500 (가온전선)**. The exact published reference overlay leaves a maximum comparable residual of **1.0583090378848024254104 KRW** and an empty coefficient interval (relative gap `2.2639e-7`). Rounding the published ratio `953/1715` to `0.555685` and truncating reproduces 2,455 of 2,456 pre-event provider OHLC cells. One cell remains unexplained; all 260 post-event provider cells are nominal. The provider's exact precision mechanism is unproved. The published reference is retained, and the discrepancy is neither hidden nor accepted through a relaxed threshold.

Production artifacts:

| Artifact | SHA256 |
|---|---|
| `kr_verified_events_v8_20261007/panel.parquet` | `2a5cf80053751670294f253c68ad67c68219e84a26df9291c15d5882e720e02e` |
| `lowliq_history_reference_evidence_20261007/verification.json` | `1fa0fa0b6e505c61a6b1581cc24f267977757a60096fa3cbaa5bce08e476e8ef` |

All paths are below `runtime_state/audit`. Supporting corpus: `lowliq_history_actions_20261007`; historical comparisons: `lowliq_history_capture_20261007/diagnostics/prefix_972` and `prefix_v8_972`; Q3 recheck: `kr_v8_full_cohort_20261007`. The all-code 65,796-request historical collection remains active under `swing-main-d277`. The first eight-code reconciliation remains open under `swing-main-jsan` for the unresolved cases. No test outcomes were calculated, no strategy passed qualification, and no live lane was replaced.
