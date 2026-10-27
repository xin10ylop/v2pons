# The dust seat on the volume-bot line — dissected

**Question (Oct 27).** `REPORT_COPY.md` found one seat that is consistently profitable *and* survives being
copied: `0x7ae81404` ("D65"), a 0.00002 ETH buy at +0.4 s on the volume bot's 3 / 5 ETH pools (Robinhood,
v4, fee 10000, ts 200), sold ~200–300 s later. Before any live test: how does it make money, why does it lose
42% of its entries, can the exit be engineered, what is the real ceiling, and — the question that decides
everything — **does the line let a new wallet sit there?**

**Answer.** The seat is real, mechanical and worth ~0.4–0.7 ETH per six days at a 0.00009 stake with an
engineered exit — **and it is closed to us.** The line pulls on any wallet it does not already know: 520
buys by other bots landed in exactly the residents' slot over the six days (same timing, same Universal
Router calldata, smaller size) and 477 (92%) were pulled within 5 s, each pull taking the residents' stake
too. The residents are an allowlist of one crew, not an age or size rule: the twin wallet `0x68936d46` had
zero history before Oct 24 and was tolerated from its first pool. The only window a new wallet gets is
after ~200 s of pool age, where dust is ignored — and that window pays ~+0.03–0.05 ETH per six days.

All figures: tapes Oct 21–26 (every swap with reserves, 3,699 line pools), buyer identity from the pool
tokens' Transfer logs (`cpdump.py`), the seat's 3,618 entries (`entries.py`). Scripts: `seatlab.py`,
`tripwire.py`, `tolmodel.py`, `seatprofile.py`; outputs `seatlab_rh_7ae81404.out`,
`tripwire_rh_7ae81404.out`, `tolmodel_rh_volume.out`, `seatprofile_rh_7ae81404.out`. Read-only.

---

## 1. How the seat makes money

The line is one machine: `0x1cbaf24d` (the 2.433 operator's own bot router, `FRONT_BOT_ROUTERS` in
`docs/HANDOFF.md`) buys into every pool it launches, 0.12 ETH median first buy, one buy every ~2.9 s,
until it removes the liquidity. 17 helper wallets buy 0.002–0.005. The pump is mechanical:

| pool | price path after the seat's entry (median multiple) | peak before the pull | price at the pull |
|---|---|---|---|
| x3 (3 ETH) | 30 s 1.41× · 60 s 1.86× · 120 s 2.71× · 180 s 3.43× · 300 s 4.43× · 360 s 4.79× | **5.6×** (p75 8.2×, p95 10.6×) | 5.4× |
| x5 (5 ETH) | 60 s 1.43× · 120 s 1.86× · 180 s 2.23× · 300 s 2.74× · 360 s 2.91× | **3.4×** (p75 3.7×) | 3.3× |

The seat's execution (`seatprofile_rh_7ae81404.out`):

- **Entry:** add +3 blocks (0.3 s) in 1,146 of 3,618 entries, +2 to +5 in 2,149; the first swap of the pool
  in its block 3,343 of 3,618 times. Through the public **Universal Router** (`execute`, command 0x10
  V4_SWAP, 1,124 bytes, deadline +120 s, gas limit 600k) at base-fee gas (0.0221 gwei). Nothing exotic:
  our old engine landed at launch +1 block on this same operator (`HANDOFF.md` §16), so latency is not the
  constraint.
- **Exit:** not a timer. It sells at a **fixed take-profit: 4.44× on x3 pools (p5–p95 4.1–4.7×), 2.85× on
  x5 (2.80–2.93×)** — 1 trip in 2,105 outside those bands — reached at ~194 s / ~300 s. It leaves money on
  the table: the pool goes on to 5.4× / 3.3× at the pull.
- **Win rate:** 2,104 of 2,105 sells profitable; 1,513 of 3,618 entries never sold (42%) and lost the stake.
  Net +0.069 ETH over six days at 0.00002.

## 2. Why it loses 42% of its entries — and whether that is predictable

Split by what happened in the pool (`seatlab_rh_7ae81404.out` §2):

| loss type | entries | what it is | pull after the seat's entry |
|---|---|---|---|
| **dead pool** | 486 (436 x3, 50 x5) | the machine never buys at all; the operator launches and pulls | p50 **2.1 s**, p95 3.6 s; 97% within 4 s |
| **mid-pump pull** | 1,023 (718 x3, 305 x5) | the pump starts, then the operator pulls early | p50 51 s; peak reached 1.7× (p75 2.65×) |

**Dead pools cannot be dodged.** The machine's first buy comes at p25 2.9 s / p50 3.9 s in good pools and
the dead ones are pulled at p50 2.1 s — so any "no machine buy yet, sell" rule fires after the pull in most
dead pools and misfires on half the good ones. Simulated: `dead 4 s` turns +0.408 into +0.168; `dead 2 s`
into −0.018. Mirror (just sell when the seat sells) beats every dead-pool rule.

**Mid-pump pulls are mostly reactions to something visible on chain** (`tripwire_rh_7ae81404.out` §2).
Of the 1,509 never-sold entries, in the 5 s before the pull:

| what landed | entries | pull came after it |
|---|---|---|
| an outside buy ≥ 0.0001 ETH (a stranger) | 502 | p50 **1.36 s** (p5 0.42, p95 2.3) |
| a 4th outside wallet (a new dust bot) | 520 | same |
| nothing visible | 487 (the dead pools, essentially) | — |

1.36 s is ~13 blocks on this chain. A bot that sells the moment it sees either trigger lands before the pull
in nearly all of them. There is **no tell in the machine itself**: it pulls a median 3 s after a perfectly
normal buy (cadence 2.9 s) and never sells before pulling (0% of pools).

## 3. The engineered exit (if one had the seat)

Copy at 0.00009 ETH, entry at the end of the seat's buy block (+1), all 3,618 entries, on the recorded
reserve paths, gas 0.000006 a round trip (`tripwire_rh_7ae81404.out` §3):

| exit rule | won | pulled | P&L / 6 days |
|---|---|---|---|
| mirror the seat's sell | 2,132 | 1,479 | +0.408 |
| mirror + sell on a ≥0.0001 outside buy | 2,507 | 968 | +0.489 |
| mirror + sell on a 4th outside wallet | 2,475 | 605 | +0.519 |
| mirror + both tripwires | 2,603 | 442 | +0.543 |
| both tripwires + take-profit **5.5×** (x3; ×0.65 on x5) instead of mirroring | 2,506 | 539 | +0.632 |
| both tripwires + take-profit **6.5×** | 2,456 | 589 | +0.673 |
| both tripwires + take-profit **7.5×** | 2,440 | 605 | **+0.698** |

So the seat, played well, is ~**+0.70 ETH per six days (~0.115 ETH/day) at a 0.00009 stake**: tripwires
on any stranger buy or any new wallet (sell the next block), and a take-profit well above the seat's own
4.4× because the pump continues to 5–8×. Two caveats on that number: the stake is an extrapolation (the
residents never buy above 0.00002; at 0.00002 the same rules give roughly +0.16), and it assumes the
operator ignores our wallet — which section 5 says it will not.

## 4. The line's rule set, measured

Every outside wallet's first buy in every line pool, 11,389 of them (`tolmodel_rh_volume.out`):

| who buys | size | pool age | pulled within 5 s |
|---|---|---|---|
| anyone | **≥ 0.0001 ETH** | any | **97–100%** (183/183 at rank 3 after 10 s; 312 at rank 4: 97%) |
| residents (ranks 1–3) | dust | any | 17–26% — the dead-pool base rate, not a reaction |
| a **4th wallet** | dust, even 0 ETH | < 10 s | **99%** (441 buys) |
| a 4th wallet | dust | 10–200 s | 47–94% |
| a 4th wallet | dust | **≥ 200 s** | **5–12%** (69 buys by 27 wallets) — tolerated |

Read as the operator's logic: *harvest* any real-size buy (the pull collects the stranger's ETH with the
liquidity — 44 buys of 0.01+ lost 2.3 ETH to it in six days); *deny* any unknown bot during the pump; stop
watching for dust after ~200 s. `0xe74fcc81` lives in that late window (0.00006 at ~200 s as the 4th
wallet, pulled on 6%) and it made **+0.003 ETH on 393 entries** — a late entry buys at 4.4× launch with a
median 1.84× left and ~376 s of life. Simulated at our size with the tripwires and take-profit, entering
only live pools at 200 s: **+0.04–0.05 ETH per six days**, falling to ~0 by 300 s. Not a seat worth having.

## 5. Can a new wallet take the early seat? No — it is an allowlist

The direct evidence, six days of other bots trying exactly what we would try:

| newcomer buys in the residents' slot (dust, before the machine's first buy) | buys | pulled within 5 s |
|---|---|---|
| age 0–0.35 s (as early as D65) | 51 by 13 wallets | 69% |
| age 0.35–2 s | 272 by 19 wallets | 91–93% |
| age 2–5 s | 196 by 5 wallets | 96% |
| **all, in the slot** | **520** | **477 (92%)** |

while the four residents, at the same ages, sit at 17–22% (the base rate). The pulled newcomers used the
same Universal Router `execute` / V4_SWAP, 1,124-byte calldata as D65 (29 of 50 sampled; deadline +300 s,
gas 900k vs D65's +120 s / 600k), at base-fee gas, with **smaller** buys (0.000001–0.000009 ETH). Two of
them tried hard: `0x93b07902` 347 pools on Oct 23 (93% pulled — that is why Oct 23 was the seat's worst
day, 59% losses: every attempt killed a pool the residents were in), `0x613765d5` 85 pools on Oct 25 (97%).

What distinguishes the residents is not age, size, path or gas. The twin `0x68936d46` received **no token
on this chain in the 13 days before Oct 21**, first appears on Oct 24 — the day `0x24919ef8` left — and was
tolerated from its first pool (13% within 15 s, same as D65). The crew swapped one resident for a fresh one
and the line accepted it on day one. That is a list the operator keeps (or the residents are the
operator's own seat-fillers — the data cannot tell those apart, and for us it makes no difference).

## 6. Risk if we tried anyway

- **Cost of a probe:** one dust buy in the slot, ~0.00002 ETH + gas. Expected result: pulled within ~1.4 s
  (92–97%). It would also kill that pool for the residents.
- **Cost of a standing bot there:** every entry loses its stake at ~92%, i.e. −0.00009 × ~600 pools/day
  ≈ **−0.05 ETH/day**, bounded by the stake × entries, not open-ended.
- **What would reopen it:** a resident vacating without replacement (the crew refilled the last vacancy the
  same day), or the operator dropping the newcomer rule. Both are observable from a daily `tripwire.py`
  §1 table (newcomer wallets, their pools, their pull rate) with no capital at risk.

## Bottom line

| | |
|---|---|
| the seat's edge | mechanical: 0.3 s entry, fixed 4.4× / 2.85× take-profit on a deterministic pump; 42% dead or early-pulled |
| engineered exit | tripwire on any stranger buy or new wallet (13 blocks to act) + take-profit 6.5–7.5×: **+0.70 ETH/6d** at 0.00009 on paper |
| ceiling | dust only (≥ 0.0001 is harvested, 100%); residents never exceed 0.00002 |
| open to us | **no** — 477 of 520 newcomer attempts in the slot pulled; the allowlist is the crew's |
| late window (≥ 200 s) | tolerated, pays **+0.03–0.05 ETH/6d** |
| recommendation | **do not trade it.** Watch for a vacancy or a rule change with `tripwire.py` §1 on a day's tapes; no engine, no probe, unless the owner wants the 8% tail checked for 0.00002 ETH |
