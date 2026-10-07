# Bonus listing dates: exchange notice and instrument-trading evidence

Issue `swing-main-blej` remains in progress. This closes the fixed six-event
exchange-listing subquestion; it does not establish complete action coverage or
position-specific share availability.

`research/audit_bonus_listing_evidence.py` consumes the immutable prior six-event
schedule and disclosure corpus. No new search or strategy outcomes are involved.
It verifies each notice's captured HTML/text, security code, common-share class,
additional share count and listing date. The prior decision dates agree with all
six exchange notices. The four past listing dates have positive nominal KIS
instrument volume; the two future dates are retained as announced only.

| Code | Exchange listing date | Additional common shares | Instrument volume on date | Status on Oct 7 |
|---|---|---:|---:|---|
| [002070](https://kind.krx.co.kr/external/2026/08/14/000192/20260814000490/68154.htm) | Aug 20 | 2,397,456 | 253,234 | Listing notice + instrument trade verified |
| [220100](https://kind.krx.co.kr/external/2026/10/07/000606/20261007001448/70791.htm) | Oct 13 | 5,162,404 | unavailable | Future announced |
| [240600](https://kind.krx.co.kr/external/2026/08/20/000363/20260820000970/70791.htm) | Aug 25 | 1,371,259 | 50,232 | Listing notice + instrument trade verified |
| [340570](https://kind.krx.co.kr/external/2026/08/25/000520/20260825001358/70791.htm) | Aug 28 | 7,942,120 | 97,973 | Listing notice + instrument trade verified |
| [475460](https://kind.krx.co.kr/external/2026/10/07/000420/20261007001139/70791.htm) | Oct 13 | 11,293,050 | unavailable | Future announced; some shares locked |
| [494120](https://kind.krx.co.kr/external/2026/08/05/000675/20260805001723/70791.htm) | Aug 10 | 7,629,882 | 208,920 | Instrument traded; some shares restricted |

475460's notice identifies 2,313,250 shares subject to mandatory holding.
494120 identifies 2,824,131 mandatory-holding shares and 41,190 employee-plan
mandatory-deposit shares. These notices do not imply that every share or every
account is restricted, nor do positive instrument volumes identify which newly
issued shares traded. The program preserves these distinctions and does not
promote `listing confirmed` into `account unrestricted credit verified`.

All six final notices were published after the relevant ex-date. They can support
retrospective settlement timing but cannot be used as information already known
at a pre-ex-date signal. Captured decision versions and their later corrections
must be considered separately for point-in-time selection.

A research model may declare an ordinary secondary-market holder assumption and
exchange-listing-based availability in a new protocol. That is a modeled
availability contract, not proof of actual broker credit or fills. This audit
neither adopts that assumption nor changes the previous study. Unknown rights,
cash dividends, fractional claims, other action coverage, tick/capacity and
holder restrictions remain explicit work under `blej`; they are not reasons to
request access to a user's brokerage account.

Validation: 48 related tests passed. Actual replay preserved the result's bytes,
size and modification time. Six identity/date/share counts were also checked
against the inspected source bodies; all six final notices postdate their
ex-date. Result:
`runtime_state/audit/bonus_listing_evidence_20261007/result.json`, SHA-256
`57de471351162b62333808f794f565424191baed2d0103fff15cc53fb4384a11`.
The audit has no database, order, model, ledger or publication writes.
