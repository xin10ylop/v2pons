# Brief for the line-finding analysts (read fully before starting)

## Rules
- Read-only on the repository /home/user/v2pons (never edit, never commit, never run git commands that change anything).
- No network at all: no RPC calls, no web. Everything you need is in the census cache. Never look for or print keys or secrets.
- Write only inside your own directory: /tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/analysis/<your angle letter>/
- Be economical: pools.jsonl is 216 MB and cache/ev.jsonl is 696 MB. Stream pools.jsonl once and keep only the rows you need; load events only for the pools you study (`load_events(set_of_pool_ids)`).
- Report what the data shows. "No tradable line in this angle" is a valid, valuable answer. Never invent a number: every figure in your report must come from a computation you ran, and your scripts must be left in your directory so a verifier can re-run them.

## The census (7 days, Oct 4 13:52 to Oct 11 13:52 UTC, 64,416 pools on Robinhood Chain)
Directory: /tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/census/
Read its README.md sections "Definitions", "pools.jsonl", "families_<grouping>.json", "cache/ev.jsonl" and "Problems and limits" first.
Loaders: `import sys; sys.path.insert(0, "<census dir>"); from load import *` -> load_pools(), load_families(g), load_top40(), load_events(ids), load_txs(). `code/evload.py` has `norm(pool_row, events)` -> swaps/adds/pulls on the quote side.
v4 swap event rows carry sqrtPriceX96 and liquidity after the swap, so a pool's exact price path is known. ETH = $2,570. USDG fixed at 2,570 per ETH.

## The engine we have (src/flip_engine.py, read-only) and what it can trade today
Our engine watches the sequencer feed (every transaction the instant it is sequenced, ~0.1 s) and trades Uniswap v4 pools on the PoolManager through our relay contract. It cannot trade V2 or V3 pools today.
Two modes:
1. **front**: a launch transaction recognised from its calldata alone, in block L: PositionManager 0x58daec3116aae6d93017baaea7749052e8a04fa7, selector ac9650d8 (multicall), calldata exactly 1,444 bytes, an ETH pair with no hook, keyed by msg.value (a "family" = one launch value, with fee, tick spacing, launch sqrt price, mint liquidity pinned). We fire at the end of block L and our buy lands at the head of block L+2 (measured on 3,000+ live trades). Optional delay: fire at L+fire_at (the 3.0 ETH line: fire at +12, hold 60). The exit: a sell sent `hold_blocks` after our buy, or earlier when a buy lands behind ours and the take-profit is reached (on the 2.4333 line we sell into the operator's own buy at +9..+12 for +9% average, 87% win, over 1,151 live trades at a $15 stake). Stakes are tiny: 0.002-0.006 ETH ($5-15). Our buy moves the price: an operator whose buy has a min-output check (the volume bot uses 0.95-0.99 of its quote) reverts if we buy too much ahead; the engine caps the ETH bought ahead per family (ahead_max_eth).
2. **follow**: any launch (recognised by receipt about a block later; the launcher's code hash must be known), then wait for the first buy >= a threshold by anyone, buy 2 blocks after that trigger, sell `HOLD_BLOCKS` later (or take-profit). It needs a wave of buys after the first one to pay. On operator A it lost money (45 trades, -5% average).
A line is **tradable today** if it is v4, an ETH pair without hook, launched through the PositionManager multicall of 1,444 bytes with a constant msg.value, fee, tick spacing, sqrt price and liquidity, and has a predictable buy after launch that lifts the price before any pull. A line that needs a new calldata decoder (another launcher contract, another calldata length, USDG quote) is "small engine change". A V2/V3 line is "new trading path" (days of work, new risk).

## The replay you must compute (so every analyst's numbers are comparable)
For a hypothetical trade in a pool: buy q ETH (default q = 0.0058 ETH, $15) at the head of block L+a (before every swap of that block), sell all tokens at the head of block L+b (before every swap of that block), where L is the launch block. Simulate the pool: start from the state after the last event before block L+a (v4: sqrtPriceX96 and liquidity from the last Swap event, else the launch price sqrt_p0 and the minted liquidity from the ModifyLiquidity add; use src/v4math.py from the repo for the v4 swap math: buy_out_int(sqrt_p, liq, eth_in, fee), sqrt_after_buy(sqrt_p, liq, eth_net_of_fee), sell_out_int(sqrt_p, liq, tokens, fee), net_of_fee), apply our buy, then re-apply every later swap by its quote amount (buys: ETH in; sells: token amount in) up to the sell point, then our sell. Concentrated/partial-range liquidity: if the pool's liquidity changes between events (ModifyLiquidity adds/pulls, or the Swap event's liquidity differs from the previous one), say so and use the event's liquidity; a full-range single position is the common case.
A pull (any liquidity removal) at or before our sell point counts as a total loss of the stake (-100%) and must be flagged separately ("pulled before sell" rate). Gas: subtract $0.02 per round trip. Report per rule: n pools, mean return, median, win rate (return > 0), worst, pulled-before-sell share, and $/day = mean $ per trade x launches per day x the share of launches that are tradable (e.g. that have the trigger).
Rules to try: front a=2 with b in {frb_off+1 ("sell into their buy": our sell lands in the block after their first real buy, so it benefits from it), fixed b in 10, 20, 40}, the delayed front (a = frb_off - k for k in 2..6, b = a + 60), and follow (a = frb_off + 2, b = a + 20 / a + 60). Also report the operator's buy itself: its offset distribution (p10/50/90), size, how often it is missing, and what it does to the price (sqrt price before/after -> % move).

## Regime checks (the operators change behaviour; the volume bot's 3.0 line changed on Oct 11 at 04:22 UTC)
Split every result by day (7 days) and show the last 24 hours separately. A pattern that only existed on some days is not a line.
Check reaction: the family's pull timing after outsider buys (outsider12_nf_reaction_rate vs baseline12_rate) and pulls before the first real buy. An operator that pulls when a stranger buys will pull on us.

## Report format (hand back <= 700 words; the detail goes in your directory's REPORT.md)
1. The ranked candidates (at most 10): family key, size (launches/day), the launch shape (launcher, selector, calldata length, value, fee/tick spacing, quote), the operator's buy (offset p10/50/90, median ETH, how identified as the operator's), the best rule and its replay numbers (n, mean, median, win, worst, pulled-before-sell, $/day at $15), regime stability (per-day), engine support (tradable today / small engine change / new trading path), and the top risk.
2. Lines examined and rejected, one line each, with the number that killed them.
3. Data limits that affect your conclusions.
Keep every script under your directory. Name the final report REPORT.md there.
