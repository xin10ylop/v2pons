# REPORT_FLAPV7: the flap.sh v7 line on BNB Chain, exit test first (Oct 14, 2026)

Verdict: **SAFE TO EXIT, but the edge is mostly gone.** One Opus agent; read-only; logs and archive reads from keyless sentio and
blockmachine (the public dataseeds and publicnode serve no history), head calls on the public endpoints. Scripts in `code/` (s01-s13),
outputs in `data/` (numbers in `data/summary.json`).

## Exit test (Oct 11 07:45 to Oct 14 08:00 UTC, blocks 126,982,000-127,560,792; 56 launches of the census shape, 18.6 a day)

| group | pairs (holders, launches) | held >= 200 then sold | moved out < 200 | never moved | head checks: transfer / Portal sell | failed txs |
|---|---|---|---|---|---|---|
| Outsiders, bought < +100 | 123 (41, 48) | **83** (hold p50 668) | 40 | **0** | 6/6 and 6/6 | 0 of 223 |
| of them entry +20..+99 | 37 (27) | 19 | 18 | 0 | | |
| Outsiders, bought >= +100 | 192 (168, 35) | 116 | 61 | 15 | 22/22 and 22/22 | 11 (bot router calls, slippage/gas) |
| Crowd | 234 (164, 37) | 148 | 68 | 18 | 20/20 and 20/20 | 3 |
| Dev | 56 (53, 56) | 34 | 20 | 2 | 3/3 and 3/3 | - |

Every failure found re-runs fine at its parent block (slippage or gas, not a block on the holder); the 4 involving a family token were
followed by a successful sell. Examples of outsiders in the engine's band who held and sold: 0xf7cd6b7a (bought +40, sold 646 blocks
later), 0x785e8778 (0.1485 BNB at +57, sold 1,664 later), 0x6d6613e4 (+51, sold 252 later).

## Code

- Token: EIP-1167 clones of the v7 implementation 0x88881b6f... (OpenZeppelin ERC20 + Ownable + Permit), owner the Portal on all 56;
  per-address storage only balances, allowances, permit nonces and an init-only pools flag; no blacklist, no allowance-parity check, no
  tax, max-wallet, cooldown or trading switch; the after-transfer dividend hook has no per-holder revert. The launcher has no role.
- Portal (proxy 0xe2ce6ab8, implementation 0x27a0f9da, ProxyAdmin owned by a multisig-like proxy): a global trading flag and a per-token
  "unable to trade" flag (0 of 56 set); no per-seller block; no admin events in the window. Only the platform could halt a token or all
  trading, which would hit the operator's crowd too.

## The rule now (K80; sell at the first buy >= $100, else +200; exact curve replay, gas and dev drains included)

| slice ($5) | n | mean | median | win |
|---|---|---|---|---|
| All recent launches | 50 (6 drained before +78) | +1.2% | -1.4% | 48% |
| 0.07475-gwei launches | 28 | +4.0% | +6.8% | 68% |
| 0.0715-gwei | 14 | -2.1% | | |
| other priorities | 8 | -3.3% | | |
| census week | 114 | +10.2% | | 77% |

The dev's drain hit 36% of trades (census 16%); the 0.07475-gwei launches fell to 10-12 a day and the crowd now comes mostly on those.
About $2 a day at $5. No freeze-like reaction to an outside buyer near +80 (small sample).

## What trading it would take

A new venue in the BNB engine (it trades PancakeSwap V2 only): the Portal's TokenCreated logs and launch-shape filter (priority exactly
74,750,000 wei), TokenBought/TokenSold following, the bonding-curve pricing (census `curve.py`), Portal `swapExactInput` buys and
permit-signed sells, and the exit gate (a daily family exit test, and an eth_call of our own sell every block while holding).
