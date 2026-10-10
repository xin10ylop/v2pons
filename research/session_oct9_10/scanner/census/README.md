# Census: every ETH-paired Uniswap v4 pool on Robinhood Chain, 48 hours to Oct 10 18:20 UTC

Built 2026-10-10 18:20-18:45 UTC from the public RPC only (no archive, no traces). Code in `code/` (`fetch.py` stages, `build.py` output),
the raw RPC answers in `cache/` (append-only JSONL; a rerun of a stage resumes, `build.py` rebuilds every output without RPC in ~20 s).

## Window

| | block | UTC |
|---|---|---|
| from (block_at(now - 48 h)) | 83,520,210 | 2026-10-08 18:20:48 |
| head at start | 85,203,897 | 2026-10-10 18:20:47 |

1,683,688 blocks (0.1026 s per block). Pool events run from each pool's launch block to launch + 3,000 blocks (about 5 minutes); the event fetch
ran at head 85,207,218+, so **every pool's 3,000-block window is complete** (`events.complete` is true for all 6,865).

## Counts

| | |
|---|---|
| PoolManager `Initialize` logs in the window (any currency0) | 11,889 |
| ETH pools (currency0 = 0x0) = `pools.jsonl` | **6,865** |
| non-ETH v4 pools (`v4_other_pools.jsonl`: USDG 0x5fc5360d 1,436 + 0x386c702c 152, WETH 0x0bd7d308 1,025, SPCX 422, DJT 64, ...) | 5,024 |
| distinct launch transactions (59 of them initialize several pools: 708 pools; 38 are contract creations) | 6,216 |
| families (strict key) / with >= 5 launches (5,069 pools) / with >= 3 | 1,644 / 104 / 175 |
| pools fetched for events / with any event / with a swap / with a pull | 6,865 / 6,776 / 5,919 / 2,625 |
| transactions in `txs.jsonl` (launch 6,216, first-8-swap 29,912, first-2-pull 2,616; 185 overlap) | 38,559 |
| missing (null) transactions | 0 |
| known (evidence-checked): vbot-v2.433 / vbot-other / operator-A / none | 1,843 / 1,436 / 77 / 3,509 |
| known by the literal rule (`known_by_rule`) | 1,843 / 1,801 / 77 / 3,144 |

## Steps, time, RPC load

| step | what | seconds | notes |
|---|---|---|---|
| window | binary search for the start block | 5 | |
| inits | `eth_getLogs` PM + T_INIT, 17 x 100k blocks | 4 | 11,889 logs |
| ltx | 6,216 launch txs (`eth_getTransactionByHash`, 50 per POST) + 38 creation receipts | 191 | 37 HTTP 429s |
| blocks | 6,207 launch blocks (`eth_getBlockByNumber`, false) | 104 | 20 x 429 |
| codes | `eth_getCode` (latest) of 422 launch `to` / created contracts | 9 | |
| dex | no-address `eth_getLogs` (30k-block cap without an address: 57 chunks) + factory 0x7ed598bc (17 x 100k) | 38 | |
| events | Swap + ModifyLiquidity, topics `[[T_SWAP, T_ML], <20 pids>]`, pools grouped by launch order (<= 20 pids, launches within 6,000 blocks), range [first launch, last launch + 3,000] | 183 + 65 | 557 groups, 362 MB raw; families >= 5 first (5,069 pools), then the other 1,796 |
| stx | txs of each pool's first 8 swaps (29,912) and first 2 pulls (2,616) | 542 | 100 x 429 |
| build | outputs from the cache | 20 | |

About 1,800 POSTs (1,797 counted by the stages), 192 answered HTTP 429 (retried with backoff; every one recovered). Nothing failed:
0 null transactions, 0 unanswered batch items, no stage restarted.

## Files (all in this directory) and `load.py`

```python
import sys; sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *          # json only; big ints stay exact Python ints
P = load_pools()            # pid -> row                         (0.2 s)
E = load_events()           # pid -> row; load_events(pids) reads only those (1.4 s for all, 122 MB)
T = load_txs()              # tx hash -> row                     (0.8 s, 109 MB)
F = load_families()         # family key -> row
B = load_blocks()           # launch block (int) -> unix ts
# also: load_blocks_meta(), load_loose_families(), load_code_families(), load_to_families(), load_other_v4(), load_dex()
```

Conventions: addresses lowercase `0x…` (40 hex); hashes and pids `0x…` (64 hex); `selector` is 8 hex chars **without** 0x; wei and Q96
values are exact ints; `*_eth` floats are conveniences; `bn` = block number, `ti` = transaction index in the block, `li` = log index.

### pools.jsonl (one JSON per ETH pool, sorted by launch block, log index)

From the `Initialize` log: `pid`, `token` (currency1), `fee` (uint24 as in the PoolKey; 8388608 = 0x800000 the dynamic-fee flag), `tick_spacing`,
`hooks`, `hooks_zero`, `sqrt_p0` (sqrtPriceX96), `tick0`, `launch_block`, `launch_ts`, `launch_tx`, `tx_index`, `log_index`.
From the launch tx: `launch_to` (null for a contract creation), `launch_from`, `launch_nonce`, `launch_value_wei`, `launch_value_eth`
(the **transaction's** value: a tx that initializes several pools gives each the same value), `selector`, `calldata_len`, `created_contract`
(creation receipts only), `to_code_size`, `to_code_hash` (keccak of `eth_getCode(launch_to or created_contract, latest)`; null if empty now).
Labels: `family` (strict key below), `family_count`, `known` (evidence-checked), `known_by_rule` (the literal rule).
From the events (conveniences; every pool has them): `has_events`, `ev_to`, `ev_complete`, `n_swaps`, `n_buys` (a0 < 0), `n_sells`, `n_pulls`,
`n_adds`, `eth_in_buys` (ETH, all buys in the window), `first_buy_rel` / `first_buy_eth` (the first swap with a0 < 0, any size, **including
our own relay's buy and the dust/decoy wallets**), `first_pull_rel` (blocks after launch of the first negative ModifyLiquidity, null if none
within 3,000), `liq_launch` (`v4math.active_liquidity(tick0, adds of the launch tx)`), `buy_in_launch_tx`, `first8_swap_to` (the `to` of the
txs of the first 8 swaps, in order), `first_pull_to`, `first_pull_selector`, `first_pull_from`.

### events.jsonl (one JSON per pool; all 6,865, 89 of them with no event)

`{pid, launch_block, ev_from (= launch_block), ev_to (= launch_block + 3000), complete, swaps, pulls, adds, zero_mods}`
- `swaps`: `[{bn, ti, li, sender, a0, a1, sqrt_p, liq, tick, fee, tx}]` sorted by (bn, li). `a0`, `a1` are the signed int128 amounts of the
  Swap event (the swapper's balance delta as v4 emits it): **a0 < 0 = ETH into the pool = a buy**, a1 > 0 then = tokens out. `sqrt_p`, `liq`,
  `tick` are the pool state **after** the swap; `fee` the LP fee applied (ppm). `sender` = topics[2] = the contract that called the
  PoolManager (the Universal Router 0x88767899 for most buys, even the volume bot's router buys) - the EOA and the called contract are in
  `txs.jsonl` for the first 8 swaps only.
- `pulls`: ModifyLiquidity with liquidityDelta < 0: `[{bn, ti, li, lo, hi, dl, sender, tx}]` (`dl` negative).
- `adds`: liquidityDelta > 0: `[{bn, ti, li, lo, hi, dl, sender, tx}]` (the launch's mint is the first one, in the launch tx).
- `zero_mods`: liquidityDelta == 0 (fee collections), 183 in all.

### txs.jsonl (one JSON per fetched transaction, sorted by bn, ti)

`hash, from, to (null = creation), value_wei, value_eth, nonce, bn, ti, type, gas, gas_price, max_fee, max_prio, selector (8 hex, no 0x),
calldata_len (bytes), input512 ("0x" + the first 512 bytes), input (the full calldata, present only when calldata_len < 2048), auth (EIP-7702
authorization list, when present), kind (subset of ["launch", "swap", "pull"]), refs ([[pid, "launch"|"swap"|"pull", rank]]: rank 0-7 for
the swap's position among the pool's swaps, 0-1 for pulls)`. Receipts are not fetched (status unknown; a swap tx that emitted a Swap log
succeeded). The volume bot's buys: to 0x1cbaf24d, selector c1120e3d, minOut = calldata word 4 = `int(input[10+64*4:10+64*5], 16)`.

### families.json (key -> row, sorted by count)

Key = `launch_to (or "create") | selector | calldata_len | fee | tick_spacing | hooks_zero ("true"/"false")`, e.g.
`0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|2500|50|true`. Row: `count, pids (launch order), launch_to, selector, calldata_len,
values_eth (sorted distinct tx values, rounded to 6), value_counts (top 12 [value, n]), fee, tick_spacing, hooks_zero, hooks (top 5), known,
known_by_rule, vbot_router_buy_pools (pools where a first-8 swap tx went to the bot's router 0x1cbaf24d), vbot_router_pull_pools (first pull
through it), n_deployers, top_deployers, nonce_med, nonce0, first_block, last_block, to_code_size, to_code_hash, n_with_events,
swap_tx_to_top ([to, pools] over the first-8 swap txs), first_pull_to_sel_top (["to:selector", pools]), first_buy_rel_p10_50_90,
first_pull_rel_p10_50_90, first_buy_eth_p10_50_90, n_no_pull_in_window`.

Known labels: `operator-A` = to 0x3194e326 or selector 2fcb9108 (77 pools, all through the original launcher, 67 families because it varies
the fee); `vbot-v2.433` = to POSM, ac9650d8, 1,444 bytes, value exactly 2,433,328,500,000,000,000 wei (1,843); `vbot-other` = the same call
at another value **and** evidence that it is the bot: its router buys or pulls in the family's pools (the 3.0/5.0 ETH fee-1% family, 1,339
pools, 1,323 with its router; values 3.0 x 889, 5.0 x 434, 0 x 15, 1e-6 x 1) or the bot's incrementing fee tiers 10001-10300 of HANDOFF section 1 (97 pools, fees 10047-10224, tick spacing 200-204, values 9.333 x 60, 40 x 30, 33.333 x 5, 4.0 x 2; none of them shows the bot's router: 34 are pulled through the POSM, 63 not within 3,000 blocks, so this label rests on the handoff's description of those families only). The literal rule also tags
365 pools in 134 other POSM 1,444-byte families (fees 883131, 790000, 3000, 100, ...) that show no sign of the bot: the 1,444-byte
multicall (initializePool + MINT_POSITION, SETTLE_PAIR, SWEEP) is the standard create-and-mint layout; they are `known: none`,
`known_by_rule: vbot-other`.

### Regroupings (the strict key fragments some operators)

- `to_families.json`: `launch_to|selector|calldata_len` -> fees, values, deployers (operators that change the fee each launch).
  Notably `0x58daec31…|ac9650d8|54500` (420 pools from 6 txs, 70 pools per tx, fees 32500, 32510, … tick spacing 10, value 0.000735, three
  deployers 0xd0f769bd/0xdb625076/0xd0c2de03) and `…|46788` (180 pools, 3 txs, fees 33900, 33910, …, same deployers): one strict family per pool.
- `code_families.json`: the strict key with the launch contract's **code hash** in place of its address (one contract per launch):
  `f07d1c53…|e1e75b94|5572|2500|25|false` = 102 pools on 101 contracts, 100 deployers, value 0.00005.
- `loose_families.json`: `selector|calldata_len|fee|tick_spacing|hooks_zero` across launch contracts: `7fde822e` (490 pools on 27 contracts,
  26 code hashes, 5 deployers; calldata 644-964 bytes in steps of 32, fee 10000, ts 200, hooks 0x0), `ec64ddcf|196|0|60|false` (69 pools on 69 contracts).

### blocks.json, blocks_meta.json

`{"<block>": ts}` for every launch block (6,207); `blocks_meta.json` `{"<block>": [ts, baseFeePerGas wei, tx count]}`. `load_blocks()` turns keys into ints.

### Other DEXes: other_dex.json, dex_pairs.jsonl, bonding_creates.jsonl

No-address scans of the whole window for V2 `PairCreated(address,address,address,uint256)` (0x0d3648bd…), V3 `PoolCreated(address,address,
uint24,int24,address)` (0x783cca1c…), Solidly `PairCreated(address,address,bool,address,uint256)`, Algebra `Pool(address,address,address)`, and
v4 `Initialize` from any address other than the PoolManager (none found). `other_dex.json` has the emitters with counts and how many pairs
include WETH 0x0bd7d308, a sample of 40 creating txs per top factory, and the bonding-curve factory 0x7ed598bc creates (topic 0x8d4aad49…,
4,693 in the window, per 100k blocks). `dex_pairs.jsonl`: `{kind, factory, token0, token1, pair|pool, fee (v3), bn, tx}` (7,495 rows);
`bonding_creates.jsonl`: `{bn, tx, token, curve, creator}`.

| emitter | kind | events | with WETH |
|---|---|---|---|
| 0x8bceaa40b9acdfaedf85adf4ff01f5ad6517937f | V2 PairCreated | 3,753 | 3,708 |
| 0x0d1ebb179cdbca88d74c923c4255cb2b17474afd | V2 PairCreated | 2,986 | 2,982 |
| 0x1f7d7550b1b028f7571e69a784071f0205fd2efa | V3 PoolCreated | 645 | 565 |
| 0xe7fef2bc860b25bbdeb6f6ab96d88baaa77ddad7 | V3 PoolCreated | 33 | 24 |
| 0xe51960f1b45f1c9fb6d166e6a884f866fc70433b | V3 PoolCreated | 19 | 2 |
| 0xfc2e4da3edb2e18100473339c763705d263d20a9 | V2 PairCreated | 17 | 0 (VIRTUAL) |
| 0x221a6239e40709792b0d4bdc140fa36158cd41c7 | V3 PoolCreated | 10 | 1 (mostly GOO) |
| 0x43b2bf9f33036a02fc7a00935571c2a6b0108e66 | V2 PairCreated | 10 | 1 (mostly USDG) |
| 0x02a84c1b3bbd7401a5f7fa98a384ebc70bb5749e | V2 PairCreated | 7 | 6 |
| others (0xe0c4ceb9 4, Algebra 0xb7a5010d 3, 0x649fee51 2, 0x9a8442cb 2, 0x16494a80 1, 0x28be7b60 1, 0x0bfbcf9f 1, 0x28f1d678 1) | | 15 | |
| 0x7ed598bcef8bd9edd8c97a195c6d13f40801ec7e (bonding-curve factory) | create 0x8d4aad49 | 4,693 | |

The two big V2 factories' pairs are created mostly by txs to many contracts ending in `…f66` with selector f752ef6c (1,252 bytes) and to
0x26605f32 (8cb5772c, 1,156 bytes) / 0x89e5db8b (f305d719 = addLiquidityETH); the V3 factory's mostly by 0x73991a25 (ac9650d8, a V3
position-manager multicall). Not censused further here.

## Things an analyst must know

- **Our own trades are in the data.** Our relay `0x2abb5653352f6b2f3b4f4261877cd02d9e05a957` (buy 5ed06f60, sell 137f1fdd; wallet
  `0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8`) is among the first 8 swaps of 1,048 of the 1,843 v2.433 pools (front, 0.0058 ETH at launch + 1) and of 35 of operator A's 77;
  `first_buy_rel` there is ours. Exclude it when measuring an operator.
- The chain-wide dust bot `0xe71a69f4…` (2e-6 ETH via the Universal Router at + 3) and the volume bot's decoy routers `0x65050a9b…`,
  `0xfd1b271f…` buy in many pools: `first_buy_*` is "any buy", not "the first real buy".
- Only the first 8 swaps and first 2 pulls have their transaction; later swaps carry only `sender` (the router contract).
- `launch_value_*` is the tx value (multi-pool txs share it); the launch tx `input` is kept in full only below 2,048 bytes (the 1,444-byte
  POSM launches are complete; decode them with `research/session_oct9_10/vbot/launch_decode.py`).
- Code hashes are of the latest state (no archive): a launch contract that self-destructed or was replaced shows null / today's code.
- WETH- and USDG-paired v4 pools (2,613) are outside the currency0 = 0x0 filter; `v4_other_pools.jsonl` lists them (Initialize fields
  only, no events).

## Families with >= 5 launches (strict key; first buy / first pull: blocks after launch p10, p50, p90; deployers = distinct launch senders)

| n | key | values (ETH) | known | first buy | first pull | deployers |
|---|---|---|---|---|---|---|
| 1843 | `0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|2500|50|true` | 2.43333 | vbot-v2.433 | [1, 1, 3] | [11, 13, 126] | 1843 |
| 1339 | `0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|10000|200|true` | 0, 1e-06, 3, 5 | vbot-other | [3, 3, 9] | [42, 698, 2373] | 1339 |
| 245 | `0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2276|100|1|true` | 0 | none | [3, 3, 4] | [117, 350, 1913] | 245 |
| 192 | `0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|500|1|true` | 0 | none | [43, 44, 47] | [265, 747, 2527] | 192 |
| 143 | `0xc763b1795dabe2d2336eba214d16969ebc5db27f|f0e9eabf|1796|10000|200|false` | 0 | none | [4, 5, 9] | None | 40 |
| 101 | `0xfcd182416ca91a9e88e9fe44e4f78ea3cb2c15c7|6fe958d8|68|3000|60|false` | 0 | none | None | [11, 12, 17] | 1 |
| 83 | `0xfcd182416ca91a9e88e9fe44e4f78ea3cb2c15c7|6fe958d8|68|10000|100|false` | 0 | none | None | [11, 12, 18] | 1 |
| 76 | `0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|883131|200|true` | 0.001218 | none | [727, 727, 727] | None | 2 |
| 59 | `0x58daec3116aae6d93017baaea7749052e8a04fa7|f7020405|196|10000|200|false` | 0 | none | [36, 142, 454] | [92, 810, 1504] | 53 |
| 52 | `0xfcd182416ca91a9e88e9fe44e4f78ea3cb2c15c7|6fe958d8|68|30000|200|false` | 0 | none | None | [11, 12, 14] | 1 |
| 50 | `0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|790000|60|true` | 4e-05 | none | [1, 2, 2084] | None | 1 |
| 35 | `0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|836798|9303|true` | 0 | none | [23, 23, 23] | None | 1 |
| 32 | `0x16cf6788b762ee8969744586ed16fc5705140dd7|4101659e|388|0|200|false` | 0, 0.012 | none | [0, 0, 0] | None | 3 |
| 30 | `0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2020|3000|60|false` | 0 | none | [46, 49, 132] | [921, 1059, 1059] | 29 |
| 30 | `0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2020|600000|6000|true` | 0.0001, 0.000157, 0.000194, 0.000363 …(29) | none | [2, 2, 2] | None | 6 |
| 23 | `0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|500|1|false` | 0 | none | [111, 115, 208] | None | 23 |
| 22 | `0xfcd182416ca91a9e88e9fe44e4f78ea3cb2c15c7|6fe958d8|68|100000|200|false` | 0 | none | None | [11, 13, 45] | 1 |
| 20 | `0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|838974|9303|true` | 0 | none | [321, 321, 321] | None | 1 |
| 18 | `0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|3000|60|true` | 0, 1e-06, 1e-05, 0.0005 …(5) | none | [1, 3, 3] | None | 15 |
| 18 | `0x815542e8b392389a1389e22e588e4b62a67ade72|7c33638d|769|30000|200|true` | 0 | none | [57, 57, 57] | None | 9 |
| 17 | `0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|100|1|true` | 1.5, 1.8, 2 | none | [3, 3, 3] | [663, 2019, 2791] | 17 |
| 16 | `0x9f81695f2d705e81f8fb7a4f8831afe92c4e6b35|7fde822e|804|10000|200|true` | 0 | none | [3, 3, 4] | None | 1 |
| 16 | `0xb7758ae7102037e3db22fe472689e6598a78f639|7fde822e|804|10000|200|true` | 0 | none | [3, 3, 4] | None | 1 |
| 16 | `0xf6b59a71e1a3169bd418169ee20e37e6a7152b5c|7fde822e|804|10000|200|true` | 0 | none | [3, 3, 4] | None | 1 |
| 15 | `0x404700be6b535e6aa7fd744f242d8cf78135817c|7fde822e|804|10000|200|true` | 0 | none | [3, 3, 4] | None | 1 |
| 15 | `0xe696daf67fe25c5936187fc1edf38404353d5f72|7fde822e|804|10000|200|true` | 0 | none | [2, 3, 3] | None | 1 |
| 14 | `0xb40382548413c559ad7f0bb6e24410401238eded|7fde822e|804|10000|200|true` | 0 | none | [3, 3, 3] | None | 1 |
| 12 | `0x0000ffffbe8efe702c8703ae3477ff5de3d319c0|ac9650d8|1316|2500|25|true` | 0 | none | [3, 3, 3] | None | 8 |
| 12 | `0x31cc7ddef7ff0e92001b7507cc42097c0ff379e0|7fde822e|804|10000|200|true` | 0 | none | [3, 3, 3] | None | 1 |
| 12 | `0x57689a475c5941b855f989edf81d6ddbf10229e6|7fde822e|804|10000|200|true` | 0 | none | [2, 3, 3] | None | 1 |
| 12 | `0x9bd98b64980f273d5452e204a3e59a9ab5b4fad6|7fde822e|804|10000|200|true` | 0 | none | [3, 3, 3] | None | 1 |
| 12 | `0xb6ed4932f217c5eb6d21a9be81fc7e6def69a0a9|7fde822e|804|10000|200|true` | 0 | none | [3, 3, 3] | None | 1 |
| 12 | `0xcd1e2cbeda788d2c59b049b5f63810892614182e|7fde822e|804|10000|200|true` | 0 | none | [3, 3, 3] | None | 1 |
| 11 | `0x05d552391067389ee44fec3924157ed33f976000|ce5494bb|36|10000|200|true` | 0 | none | [3, 3, 4] | [744, 798, 878] | 1 |
| 11 | `0x2b0c777574bd65ed74b211e0f2bf79bd3c9bff20|7fde822e|804|10000|200|true` | 0 | none | [3, 3, 3] | None | 1 |
| 11 | `0x80521fc999a81e467696fd834d1df0a082d01894|7fde822e|804|10000|200|true` | 0 | none | [2, 3, 3] | None | 1 |
| 10 | `0x0000ffffbe8efe702c8703ae3477ff5de3d319c0|b6982b48|260|2500|25|true` | 0 | none | [2, 3, 3] | None | 1 |
| 10 | `0x3493ab3ec9358cb77b335507248c68fcaa84bf5e|7fde822e|804|10000|200|true` | 0 | none | [2, 3, 3] | None | 1 |
| 10 | `0xd912ed6ccd65370d2ef23c783bd2096e6ddbd68f|7fde822e|804|10000|200|true` | 0 | none | [2, 3, 3] | None | 1 |
| 10 | `create|60808060|3740|2500|25|true` | 2, 3.3, 3.4, 3.5 | none | [0, 0, 0] | None | 2 |
| 9 | `0x258dd351af960bc487532c0108d3f90e8d115369|7fde822e|804|10000|200|true` | 0 | none | [2, 3, 3] | None | 1 |
| 9 | `0x2a53386daf0bf3eedd9e715d162649764358c7b5|3d9ab7c9|292|0|200|false` | 0.15 | none | [0, 0, 0] | None | 1 |
| 9 | `0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2020|200000|2000|true` | 0.000434, 0.001044, 0.001056, 0.001071 …(9) | none | [1165, 1165, 1165] | None | 8 |
| 9 | `0x78ba8b21e8adbbc84f2e11f0e92c6f2299b78281|7fde822e|804|10000|200|true` | 0 | none | [3, 3, 4] | None | 1 |
| 9 | `0xa1c9c202b905d171b4517c877adce519bff04c03|7fde822e|772|10000|200|true` | 0 | none | [3, 3, 4] | None | 1 |
| 9 | `0xdf4ca4e1698260ea18aec40347be88310e4e93f4|7fde822e|804|10000|200|true` | 0 | none | [2, 3, 4] | None | 1 |
| 8 | `0x0000ffffbe8efe702c8703ae3477ff5de3d319c0|ac9650d8|1476|2500|25|true` | 0 | none | [2, 3, 4] | None | 4 |
| 8 | `0x387a453d75a1b8fa825a9b9d4ad87323c0f48755|54e231e6|1412|0|200|false` | 0.21777, 0.2777, 0.41655, 0.69425 | none | [0, 0, 0] | None | 1 |
| 8 | `0x575b952fd3c079b3e72f4cd45f546edd2486d8fa|7fde822e|804|10000|200|true` | 0 | none | [2, 3, 3] | None | 1 |
| 8 | `0x5bd1fbe78a78fe8236fa00cf48fbeba74ae34661|a80ac0c2|1156|0|200|false` | 0.0005, 0.001, 0.0025, 0.0105 …(5) | none | [0, 0, 0] | None | 7 |
| 8 | `0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|3000|60|true` | 0 | none | [72, 94, 499] | None | 1 |
| 8 | `0xa0ce0291c181f800e7a5096b433685c37cfbf4df|617ac5de|676|8388608|200|false` | 0 | none | [1, 1, 1] | None | 3 |
| 8 | `0xc97b9d2da8ec41ce090e8f3f8d7b664eda013da8|7fde822e|804|10000|200|true` | 0 | none | [2, 3, 4] | None | 1 |
| 8 | `0xe181b36e96e9cab0130707bcb513fc1401e0ba32|a25a9a3d|868|10000|200|true` | 0.000101 | none | [2, 3, 3] | None | 1 |
| 7 | `0x0000ffffbe8efe702c8703ae3477ff5de3d319c0|ac9650d8|3236|2500|25|true` | 1.5 | none | [0, 0, 0] | None | 7 |
| 7 | `0x3493ab3ec9358cb77b335507248c68fcaa84bf5e|7fde822e|772|10000|200|true` | 0 | none | [2, 3, 3] | None | 1 |
| 7 | `0x34c0d66f3a57a4cad3c5f792f5028d9c1da83d12|f03e0011|292|0|200|false` | 1e-05, 0.0005 | none | [0, 0, 0] | None | 2 |
| 7 | `0x575b952fd3c079b3e72f4cd45f546edd2486d8fa|7fde822e|772|10000|200|true` | 0 | none | [2, 3, 3] | None | 1 |
| 7 | `0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2020|500000|5000|true` | 0.00027, 0.000929, 0.002004, 0.002035 …(7) | none | None | None | 5 |
| 7 | `0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2020|810000|8100|true` | 6.6e-05, 8.9e-05, 0.000273, 0.000848 …(7) | none | None | [1573, 1573, 1573] | 6 |
| 7 | `0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2020|9000|90|true` | 0, 0.000434, 0.002085, 0.00215 …(7) | none | [3, 3, 4] | [1350, 1350, 1350] | 6 |
| 7 | `0xc763b1795dabe2d2336eba214d16969ebc5db27f|f0e9eabf|1828|10000|200|false` | 0 | none | [5, 5, 8] | None | 4 |
| 7 | `0xce4c6a284f1160cebaa56ac0d190f66983b09ae6|7fde822e|804|10000|200|true` | 0 | none | [3, 3, 4] | None | 1 |
| 7 | `0xd1e3060e2c00ccecddedcb802f45146531192bef|7fde822e|804|10000|200|true` | 0 | none | [3, 3, 3] | None | 1 |
| 7 | `0xe43be69cedf8c5190977e430a12befa2c6b2594e|7fde822e|772|10000|200|true` | 0 | none | [2, 3, 3] | None | 1 |
| 7 | `0xe43be69cedf8c5190977e430a12befa2c6b2594e|7fde822e|804|10000|200|true` | 0 | none | [2, 3, 3] | None | 1 |
| 6 | `0x1756c648a426a5a7548ac42350ce3fa980070e65|7fde822e|740|10000|200|true` | 0 | none | [2, 3, 3] | None | 1 |
| 6 | `0x1f3af76ce4c960299b85576371c161677dc1959d|ff734f50|1060|3000|60|true` | 0, 0.0001, 0.0002, 0.0004 | none | [0, 0, 3] | None | 4 |
| 6 | `0x3194e32622c5d860a0572c74edda99dcfd8fc827|2fcb9108|644|1500|200|true` | 1.55, 1.6, 2.35, 2.7 | operator-A | [3, 3, 3] | [28, 47, 51] | 6 |
| 6 | `0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|600000|6000|true` | 1.2e-05, 4.3e-05, 4.9e-05, 0.00019 …(6) | none | [441, 441, 441] | [2632, 2632, 2632] | 4 |
| 6 | `0x5bd1fbe78a78fe8236fa00cf48fbeba74ae34661|a80ac0c2|1284|0|200|false` | 0.0005, 0.0205, 0.0255, 0.3455 …(5) | none | [0, 0, 0] | None | 6 |
| 6 | `0x78ba8b21e8adbbc84f2e11f0e92c6f2299b78281|7fde822e|772|10000|200|true` | 0 | none | [3, 3, 3] | None | 1 |
| 6 | `0x80521fc999a81e467696fd834d1df0a082d01894|7fde822e|772|10000|200|true` | 0 | none | [3, 3, 3] | None | 1 |
| 6 | `0x815542e8b392389a1389e22e588e4b62a67ade72|7c33638d|833|30000|200|true` | 0 | none | [1902, 1902, 1902] | None | 3 |
| 6 | `0xcd1e2cbeda788d2c59b049b5f63810892614182e|7fde822e|772|10000|200|true` | 0 | none | [2, 3, 3] | None | 1 |
| 6 | `0xd912ed6ccd65370d2ef23c783bd2096e6ddbd68f|7fde822e|772|10000|200|true` | 0 | none | [2, 3, 3] | None | 1 |
| 6 | `0xdc416cabaed48edab4905176f4eec6a4b22b1366|7fde822e|804|10000|200|true` | 0 | none | [3, 3, 3] | None | 1 |
| 6 | `0xe43be69cedf8c5190977e430a12befa2c6b2594e|7fde822e|740|10000|200|true` | 0 | none | [2, 3, 3] | None | 1 |
| 5 | `0x0000ffffbe8efe702c8703ae3477ff5de3d319c0|ac9650d8|1508|2500|25|true` | 0 | none | [3, 3, 3] | None | 2 |
| 5 | `0x038ed9c750a8f7c5ff79a14421e3444929dfec1f|f03e0011|292|0|200|false` | 1e-06, 1e-05 | none | [0, 0, 0] | None | 1 |
| 5 | `0x1756c648a426a5a7548ac42350ce3fa980070e65|7fde822e|804|10000|200|true` | 0 | none | [3, 3, 3] | None | 1 |
| 5 | `0x1eef016f22a943abc7dd11422edee9d235942104|60956835|2980|8388608|8|false` | 0 | none | [95, 95, 95] | None | 5 |
| 5 | `0x258dd351af960bc487532c0108d3f90e8d115369|7fde822e|772|10000|200|true` | 0 | none | [3, 3, 3] | None | 1 |
| 5 | `0x2cf3de560af4e1922246cb867b4eabcc1ad3e4a0|aad1232c|1252|3000|60|false` | 0 | none | [2501, 2501, 2501] | None | 1 |
| 5 | `0x458cdbed885a516f2e32cc5e3e9b432589fa729f|d181e93a|420|0|1|true` | 0.01, 0.04, 0.06, 0.15 …(5) | none | [0, 0, 0] | None | 1 |
| 5 | `0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|200000|2000|true` | 4.3e-05, 0.000279, 0.000362, 0.002706 …(5) | none | [1, 612, 612] | [1081, 1081, 1081] | 5 |
| 5 | `0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|250000|2500|true` | 1.8e-05, 3.1e-05, 0.000158, 0.000484 …(5) | none | [1, 1, 1] | [2009, 2009, 2009] | 2 |
| 5 | `0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|500000|5000|true` | 0, 8.8e-05, 0.000137, 0.00029 …(5) | none | None | [1500, 1500, 1500] | 5 |
| 5 | `0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|500|10|true` | 1.8, 2 | none | [3, 4, 4] | [2025, 2427, 2631] | 5 |
| 5 | `0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|590000|60|true` | 0.001522, 0.001575, 0.001674, 0.001688 …(5) | none | [0, 1, 1] | None | 1 |
| 5 | `0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2020|3000|60|true` | 0 | none | [2, 3, 3] | [485, 1252, 1252] | 1 |
| 5 | `0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2020|790000|7900|true` | 0.0002, 0.000228, 0.000229, 0.000366 …(5) | none | [1, 1, 1] | None | 3 |
| 5 | `0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2020|800000|8000|true` | 9.5e-05, 0.00014, 0.000196, 0.00023 …(5) | none | [115, 115, 115] | None | 4 |
| 5 | `0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2020|870000|8700|true` | 2.4e-05, 4e-05, 0.000191, 0.000384 …(5) | none | None | None | 1 |
| 5 | `0x6d9ba28f614168f3241b302704ac478850bcbd43|aa7ec999|580|0|200|false` | 2e-06, 1.1e-05, 0.000225 | none | [0, 0, 0] | None | 2 |
| 5 | `0x78ba8b21e8adbbc84f2e11f0e92c6f2299b78281|7fde822e|740|10000|200|true` | 0 | none | [2, 3, 3] | None | 1 |
| 5 | `0x815542e8b392389a1389e22e588e4b62a67ade72|7c33638d|833|10000|200|true` | 0 | none | [2, 3, 3] | None | 4 |
| 5 | `0xb40382548413c559ad7f0bb6e24410401238eded|7fde822e|772|10000|200|true` | 0 | none | [3, 3, 3] | None | 1 |
| 5 | `0xc97b9d2da8ec41ce090e8f3f8d7b664eda013da8|7fde822e|740|10000|200|true` | 0 | none | [3, 3, 3] | None | 1 |
| 5 | `0xc97b9d2da8ec41ce090e8f3f8d7b664eda013da8|7fde822e|772|10000|200|true` | 0 | none | [3, 3, 3] | None | 1 |
| 5 | `0xce4c6a284f1160cebaa56ac0d190f66983b09ae6|7fde822e|836|10000|200|true` | 0 | none | [2, 3, 3] | None | 1 |
| 5 | `0xd1e3060e2c00ccecddedcb802f45146531192bef|7fde822e|740|10000|200|true` | 0 | none | [3, 3, 3] | None | 1 |
| 5 | `0xd1e3060e2c00ccecddedcb802f45146531192bef|7fde822e|772|10000|200|true` | 0 | none | [3, 3, 3] | None | 1 |
| 5 | `0xe181b36e96e9cab0130707bcb513fc1401e0ba32|a25a9a3d|900|10000|200|true` | 0.000101 | none | [2, 2, 3] | None | 1 |
