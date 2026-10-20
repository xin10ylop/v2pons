# Census 2: every new ETH/WETH/USDG pool on Robinhood Chain over 7 days, behaviour first

Built 2026-10-11 15:27:55 UTC by one agent, from the public RPC `https://rpc.mainnet.chain.robinhood.com` only (no archive state, no traces, no Dwellir).
Nothing was sent to the chain and the repository was not modified. Code in `code/` (stages `f0`-`f7`, `build.py`, `report.py`), raw RPC
answers in `cache/` (append-only JSONL; every stage resumes; `build.py` + `report.py` rebuild every output from the cache without RPC in about
a minute). `load.py` has the loaders.

The first census (research/session_oct9_10/scanner/census) keyed launch families by the launch calldata (target|selector|length|fee|...),
covered 48 hours and Uniswap v4 ETH pools only. This one is meant to be fingerprint-agnostic: every pool gets its **token's bytecode family**
(three hashes: exact, immutables masked, opcode skeleton), its **launch wallet's funding source** (a sample, see below) and the first
census's **(launch contract code hash, selector)** key, plus the behaviour a detector needs (first buys, first real buy and its wallet, every
pull in 3,000 blocks with full/partial, outsider buys and the pull's delay after them). The first census's operator fingerprints are used
only as an annotation (`known_fp`), never for grouping.

## Window

| | block | UTC |
|---|---|---|
| from = block_at(now - 7 days) | 79,984,897 | 2026-10-04 13:52:42 |
| head at the start | 85,881,750 | 2026-10-11 13:52:41 |

5,896,854 blocks (0.1026 s). Every pool's events run from its launch block to launch + 3,000 blocks (about 5 minutes); the event fetch ran
at head 85,884,792, so the 3,000-block window is complete for 64,416 of 64,416 pools (`ev_complete`).

## Scope and counts per DEX

- **v4**: every PoolManager `0x8366a39c…` `Initialize` with ETH (currency 0x0), WETH `0x0bd7d308f8e1639fab988df18a8011f41eacad73`, USDG
  `0x5fc5360d0400a0fd4f2af552add042d716f1d168` (6 decimals) or USDG `0x386c702c290a954d1c0ba0efc12d51373e02d3f3` (18 decimals, called USDG2 here)
  on either side (38,853 `Initialize` logs in all; 6,437 have none of these on either side and are out of scope).
- **v2a / v2b**: `PairCreated` on the V2 factories `0x8bceaa40b9acdfaedf85adf4ff01f5ad6517937f` (v2a) and `0x0d1ebb179cdbca88d74c923c4255cb2b17474afd`
  (v2b) with WETH on a side. **v3**: `PoolCreated` on `0x1f7d7550b1b028f7571e69a784071f0205fd2efa` with WETH on a side.
- **bonding curve** `0x7ed598bcef8bd9edd8c97a195c6d13f40801ec7e`: counted and sampled only (`bonding.json`, below).

| dex | pools | quote pairs | with events | with liquidity | with swaps | with real buy | pulled (3,000 blocks) | first pull full | outsider bought | reactions | launch txs | launch wallets | token families | launcher families |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v2a (WETH 15947) | 15947 | 0 | 15947 | 2037 | 2028 | 1982 | 355 | 355 | 714 | 37 | 15947 | 2119 | 145 | 161 |
| v2b (WETH 13951) | 13951 | 0 | 13951 | 13909 | 13909 | 95 | 0 | 0 | 140 | 0 | 13951 | 127 | 1 | 23 |
| v3 (WETH 2102) | 2102 | 0 | 2102 | 2093 | 1994 | 1574 | 1331 | 1330 | 590 | 26 | 2102 | 1508 | 101 | 65 |
| v4 (ETH 22524, USDG 6792, WETH 2869, USDG2 231) | 32416 | 13 | 32416 | 31831 | 22283 | 12249 | 7203 | 6985 | 2862 | 703 | 27946 | 11971 | 854 | 920 |

"quote pairs" (both sides ETH/WETH/USDG) are rows in `pools.jsonl` but are left out of every family. "with real buy" = a buy of 0.005
ETH-equivalent or more by anyone but our own wallet/relay. Many v2a/v2b pairs are created in pairs by launchpads (one tx creates the token
and a pair on each factory; the liquidity goes to one of them), which is why most v2a pairs never get liquidity.

## Method, RPC load

| stage | what | calls |
|---|---|---|
| f1 | `eth_getLogs` by address: PoolManager `Initialize`, the three factories, the bonding factory, 100k-block chunks | 3 x 59 |
| f2 | launch transactions `eth_getTransactionByHash` (50 per POST; the first census's 6,216 reused) + `eth_getTransactionReceipt` of the 271 contract-creation launches | |
| f3 | code hashes of every token and launch target: one `eth_call` per 25 addresses against a 409-byte EVM snippet injected by state override (`code/evmhash.py`) that returns EXTCODEHASH, EXTCODESIZE, the masked hash and the skeleton hash computed on the node (checked equal to the Python computation on 120 tokens) | ~1,650 items |
| f4 | events: v4 `Swap`+`ModifyLiquidity` by pool-id topic list; V2 `Swap`/`Mint`/`Burn`, V3 `Swap`/`Mint`/`Burn` by address list; groups of <= 50 pools launched within 6,000 blocks, range [first launch, last launch + 3,000]; the first census's raw v4 ETH events reused for its 48 h (557 groups) | 2,473 getLogs |
| f5 | transactions of every pull in the window, of the first 12 swaps of every pool, of the first real buy when later, and of up to 12 buys in the 200 blocks before the first pull (the closest ones); the first census's 32,343 swap/pull txs reused | 207,304 txs |
| f6 | funding sample: full blocks (`eth_getBlockByNumber`, true) scanned backwards from the launch (below) | 156,461 blocks |
| f7 | bonding factory sample: 60 create txs, 25 curves' logs | ~90 |
| f0 | a block-timestamp grid every 5,000 blocks (launch times are interpolated, error about a second) | 1,182 blocks |

RPC load over all stages (from the stage logs; killed-and-resumed runs counted to their last progress line): 12,183 POSTs, 357,548 batch items, 1,271 HTTP 429 answers (each retried after a back-off; none was lost: 0 transactions came back null), 2 other transport errors (retried), 651 MB on the wire (gzip) for 5,109 MB of JSON. At most three stages ran at once, each with a minimum gap of 0.45-0.8 s between its POSTs.

## Definitions

- **ETH-equivalent**: ETH and WETH as is; USDG at a fixed 1 ETH = 2,570 USDG (the Oct 11 price; `params.ETH_PER_USDG` in summary.json).
- **buy**: the quote (ETH/WETH/USDG) goes into the pool. v4: the swapper's quote delta < 0 in the `Swap` event; V2: `amountIn` on the WETH side
  with token out; V3: the pool's WETH delta > 0. Amounts are the quote side.
- **first real buy (frb)**: the first buy of >= 0.005 ETH-equivalent, our own wallet `0xab5a34c3…`/relay `0x2abb5653…` excluded (they appear
  in Oct 8-10 v2.433 and operator-A pools, `ours`).
- **pull**: v4 `ModifyLiquidity` with a negative delta; V2 `Burn`; V3 `Burn` with amount > 0. **full** = the pool's remaining liquidity after
  it is <= 1% of its peak (v4/V3: sum of liquidity deltas over all positions; V2: the WETH reserve rebuilt from Mint/Swap/Burn); `frac` = the
  share of the liquidity present before that pull which it removed. "who" = the pull transaction's `from` (and `to`, selector).
- **wallet seen in a pool**: the EOA (`from`) of a fetched swap transaction in that pool. Only fetched transactions count (first 12 swaps,
  the pre-pull buys, the first real buy, the pulls), so a wallet's pool count is a lower bound.
- **outsider**: a wallet seen in fewer than 3 pools of the whole census (and not ours) buying >= 0.0001 ETH-equivalent before the first pull
  (or anywhere in the window if never pulled). **reaction**: the first pull comes <= 30 blocks after the last outsider buy before it.
  `outsider` uses every fetched buy; `outsider12` only the first 12 swaps (fetched for every pool). **shared fingerprint**: a transaction
  fingerprint `to:selector:calldata_len:max_prio` used by >= 25 single-use wallets across the census (`shared_fps.json`: an operator's
  fresh-wallet crowd, decoys, or a popular front-end's default route); `nf_*` = outsiders without those fingerprints.
  **reaction baseline** (per family): among complete-window pools with buys but no outsider buy, the share whose first pull comes <= 30
  blocks after the last buy of anyone before it. A reaction rate well above its baseline is the "pulls on outsiders" signal; a family
  that always pulls a few blocks after its own buy (v2.433) has a high baseline.
- **token code keys** (`token_code`): `hash` = keccak of `eth_getCode(token, latest)` (the literal bytecode hash; immutables such as the
  pair address make it unique per token in most launchers, so it is reported but fragments: 11,189 families for 64,403 pools);
  `mask32` = keccak of the code with every PUSH32 operand zeroed and the CBOR metadata tail stripped (immutables are PUSH32 placeholders);
  `skel` = keccak of the opcode sequence with every PUSH operand dropped and the metadata stripped (also robust to hardcoded name/symbol
  strings and different metadata). **The token-code family key is `skel` (`fam.tok`)**; `mask32` (`fam.tokm`) is the finer variant. A key
  is a *template*: launchers that use the same token template share it.
- **launcher key** (`fam.lc`): `<code hash of the launch target> | <selector>` (target = the launch tx's `to`, or the created contract for a
  creation), the first census's code key without the calldata length/fee/tick spacing; `fam.strict` adds them back
  (`lc|calldata_len|fee|tick_spacing|hooks_zero-or-dex`).
- **funding root** (`fam.fund`): the launch wallet's first incoming transfer's sender; when that sender was itself fresh (nonce <= 20 at the
  funding) and its own funding was found, that sender's funder (`funding.hop2`). Sample only (below). `fam.fund1` = the direct funder.

## Families under each grouping (quote pairs excluded)

| grouping | key | families | >= 5 launches | pools in them | >= 20 | singletons |
|---|---|---|---|---|---|---|
| tok | token code skeleton (opcodes only) | 1050 | 184 | 63132 | 70 | 615 |
| tokm | token code, immutables masked (PUSH32 zeroed, metadata stripped) | 1317 | 264 | 62926 | 137 | 785 |
| tokx | token code, exact keccak | 11189 | 451 | 52364 | 75 | 9878 |
| lc | launch target code hash | selector | 1152 | 245 | 63148 | 122 | 672 |
| strict | lc | calldata length | fee | tick spacing | hooks | 8665 | 607 | 54859 | 146 | 7034 |
| fund | funding root (sample) | 166 | 6 | 4772 | 2 | 129 |
| fund1 | direct funder (sample) | 182 | 6 | 4772 | 2 | 157 |

How they overlap (for each family of A with >= 5 pools: into how many families of B its pools fall; for the funding groupings only
pools with a funding root count):

| A vs B | families of A (>= 5) | >= 90% of A's pools in one B family | A split over >= 3 B families | median B families per A family |
|---|---|---|---|---|
| tok vs lc | 184 | 65 | 91 | 2 |
| lc vs tok | 245 | 218 | 23 | 1 |
| tok vs fund | 25 | 12 | 12 | 2 |
| lc vs fund | 20 | 10 | 8 | 1.5 |
| fund vs tok | 6 | 6 | 0 | 1 |
| fund vs lc | 6 | 6 | 0 | 1 |
| tok vs tokm | 184 | 159 | 21 | 1 |
| tok vs strict | 184 | 29 | 156 | 7 |

`overlap.json` has the per-family rows (the top B key and its share) and a 15 x 15 count matrix of the top token-code vs launcher families.

## The funding sample

What was done: for each of the 45 largest token-code families and the 45 largest launcher families, 4 launches whose wallet had nonce <= 3
at the launch (two consecutive ones mid-window and the last two), plus 60 random such launches; for each, full blocks were read backwards
from the launch block (40 blocks per POST, at most 800 blocks, i.e. 82 s; the first 27 wallets with 1,200). A funding is a transaction
with `to` = the wallet and value > 0 (`direct`), or one whose calldata contains the wallet's address (`calldata`: a contract call such as a
multisend; `from` is the funder, `via` the contract, `value_eth` the whole call's value since internal transfers are invisible without
traces). For a wallet with launch nonce n > 0 the scan first finds the wallet's own nonce-0 transaction and takes the first funding before
it (`nonce0_not_found` when the nonce-0 tx is older than the scan). Funders that were fresh themselves (nonce <= 20) got the same scan
once more (hop 2). Then, without RPC, every other launch wallet (nonce <= 3) whose blocks back to its funding were already in the block cache
was resolved the same way (`from_cache`). Wallets launching again later inherit the funding of their sampled launch (`funding.sampled_pool`
false). L1 deposits (Arbitrum tx type 0x64) and retryables count as direct fundings (`type`).

Launch wallets with a funding scan: 350 (241 scanned over the RPC, 109 resolved from the cached blocks; status: {'no_funding_in_range': 78, 'found': 214, 'nonce0_not_found': 58}); funding kinds: {'calldata': 42, 'direct': 172}; blocks before the launch p10/p50/p90: 19/163/475; funder nonce p10/p50/p90: 0/5/4592; distinct funders 182, top: 0x3762da2e x7, 0xae6e9ca2 x5, 0xa3d18940 x5, 0x51820f0b x4, 0x168b921a x4, 0xbd84b08f x3. Hop 2 (fresh funders, nonce <= 20): {'nonce0_not_found': 13, 'found': 52, 'no_funding_in_range': 4}. Pools covered (their launch wallet sampled): 6839, with a funder: 4974; funding-root families with >= 5 pools: 6.

## Top 40 families (token-code `tok` and launcher `lc` groupings merged; a family that is the same set as one above it, Jaccard >= 0.8 on
its pools, is folded into it and named in parentheses)

Columns: first real buy and first pull are block offsets from the launch (median over the family's pools that have one); pulled = pools
with a pull within 3,000 blocks / pools; pull - frb = median blocks from the first real buy to the first pull; early-outsider reaction =
pools whose first pull came <= 30 blocks after the last outsider buy among the first 12 swaps / complete-window pools with such a buy
(`outsider12`, unbiased); the same with the shared fingerprints of `shared_fps.json` excluded (`outsider12.nf_*`); baseline = pools whose
first pull came <= 30 blocks after the last buy of anyone among the first 12 swaps / complete-window pools with buys there and no outsider;
the all-fetched outsider reaction and its baseline use every fetched buy before the pull (biased, see Problems 1); frb wallet also in family = pools whose first real buyer also bought in another pool of the same token-code family / pools with a first
real buy. The description is generated: [first-census fingerprint or "new"] dex, quote, fee/tick spacing; launches, launch wallets,
launch target:selector and value; first real buy offset, size and the contract it was sent to; pulls; reactions.

| # | grouping:key | n | /day | pools with a real buy | first real buy (med off) | first pull (med off) | pulled | pull - frb | early-outsider reaction | same, shared fingerprints excluded | baseline | all-fetched outsider reaction | baseline | frb wallet also in family | known | description |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `tok:fa4982d5acd820b3…4efad8a4830e` | 28547 | 4078.6 | 239 | 36 | 1103.5 | 22/28547 | 963 | 0/254 | 0/193 | 0/13983 | 1/255 | 0/13984 | 117/239 | - | v2b 13951/v2a 13883 WETH 27846/ETH 398 fee/ts 3000/None; 28547 launches (4078.6/d) by 440 wallets via 0x563b2841:f752ef6c value 6e-07,6.3e-07; first real buy +36 (n 239, med 0.0209 ETH, via 0x5bd1fbe7); pulled 22/28547 at +1103.5; early-outsider reaction 0/254 (baseline 0/13983) |
| 2 | `lc:c873e135dc9aaec8…0b2|ac9650d8` | 21018 | 3002.9 | 9386 | 9 | 204 | 5369/21018 | 122 | 260/1027 | 7/553 | 2127/13508 | 551/1365 | 3567/13194 | 9112/9386 | vbot-v3.0 3355,vbot-v2.433 3182,vbot-v5.0 1543 | v4 21018 ETH 15462/USDG 4921 fee/ts 10000/200; 21018 launches (3002.9/d) by 7990 wallets via POSM:ac9650d8 value 0.0,3.0; first real buy +9.0 (n 9386, med 0.125 ETH, via 0x1cbaf24d); pulled 5369/21018 at +204; early-outsider reaction 260/1027 (baseline 2127/13508) |
| 3 | `lc:49451fc9bcb24bce…475|f752ef6c` | 13780 | 1998.2 | 45 | 292 | - | 0/13780 | - | 0/56 | 0/41 | 0/6834 | 0/56 | 0/6834 | 26/45 | - | v2a 6890/v2b 6890 WETH 13780 fee/ts 3000/None; 13780 launches (1998.2/d) by 38 wallets via 0x67050116:f752ef6c value 6.3e-07,2.01e-07; first real buy +292 (n 45, med 0.0099 ETH, via 0x5399d94d); pulled 0/13780 at +None; early-outsider reaction 0/56 (baseline 0/6834) |
| 4 | `lc:e830de831f4cde39…a87|f752ef6c` | 11970 | 1710.2 | 30 | 251.5 | - | 0/11970 | - | 0/51 | 0/26 | 0/5934 | 0/51 | 0/5934 | 11/30 | - | v2a 5985/v2b 5985 WETH 11970 fee/ts 3000/None; 11970 launches (1710.2/d) by 5 wallets via 0x563b2841:f752ef6c value 2.48e-07,2.13e-07; first real buy +251.5 (n 30, med 0.0114 ETH, via 0x65050a9b); pulled 0/11970 at +None; early-outsider reaction 0/51 (baseline 0/5934) |
| 5 | `tok:16afd61e5922756d…12bc5b4114eb` | 8102 | 1158.6 | 222 | 1 | 99 | 457/8102 | 928 | 0/193 | 0/159 | 18/4387 | 1/199 | 22/4392 | 163/222 | - | v4 8101/v3 1 ETH 5832/USDG 2251 fee/ts 883131/200; 8102 launches (1158.6/d) by 508 wallets via POSM:ac9650d8 value 0.0,0.000735; first real buy +1.0 (n 222, med 0.03 ETH, via 0x2a53386d); pulled 457/8102 at +99; early-outsider reaction 0/193 (baseline 18/4387) |
| 6 | `tok:037449b17ce607be…9edb4000170a` | 5061 | 723.7 | 4889 | 9 | 517.5 | 2092/5061 | 512 | 4/8 | 3/6 | 765/4903 | 171/178 | 1821/4733 | 4886/4889 | vbot-v3.0 3355,vbot-v5.0 1543 | v4 5061 ETH 4938/USDG 118 fee/ts 10000/200; 5061 launches (723.7/d) by 2726 wallets via POSM:ac9650d8 value 3.0,5.0; first real buy +9 (n 4889, med 0.1237 ETH, via 0x1cbaf24d); pulled 2092/5061 at +517.5; early-outsider reaction 4/8 (baseline 765/4903) |
| 7 | `tok:aff2095fe75bb508…6b8df53d84bd` | 3207 | 458.4 | 3173 | 9 | 13 | 2028/3207 | 3 | 254/407 | 2/2 | 1330/2778 | 315/465 | 1581/2720 | 3173/3173 | vbot-v2.433 3182 | v4 3207 ETH 3189/USDG 18 fee/ts 2500/50; 3207 launches (458.4/d) by 3198 wallets via POSM:ac9650d8 value 2.4333285,0.0; first real buy +9 (n 3173, med 0.1732 ETH, via 0x1cbaf24d); pulled 2028/3207 at +13.0; early-outsider reaction 254/407 (baseline 1330/2778) |
| 8 | `tok:58d5932051387e18…7ab6de2a91f9` | 2772 | 396.1 | 160 | 133 | 1144 | 70/2772 | 369 | 1/128 | 0/83 | 0/206 | 2/128 | 0/209 | 100/160 | - | v4 2710/v3 62 WETH 1451/USDG 961 fee/ts 8388608/8; 2772 launches (396.1/d) by 708 wallets via 0x5ff137d4:1fad948c value 0.0,9.333333333; first real buy +133.0 (n 160, med 0.0495 ETH, via 0x65050a9b); pulled 70/2772 at +1144.0; early-outsider reaction 1/128 (baseline 0/206) |
| 9 | `lc:cecb292d9c022858…c35|8cb5772c` | 2003 | 287.8 | 12 | 0 | - | 0/2003 | - | 0/18 | 0/15 | 0/963 | 0/18 | 0/963 | 4/12 | - | v2b 1014/v2a 989 WETH 2003 fee/ts 3000/None; 2003 launches (287.8/d) by 52 wallets via 0x26605f32:8cb5772c value 6e-07,0.0; first real buy +0.0 (n 12, med 0.0158 ETH, via 0x26605f32); pulled 0/2003 at +None; early-outsider reaction 0/18 (baseline 0/963) |
| 10 | `tok:d4e7eae43daa222b…69dba24d672e` | 1991 | 284.6 | 1011 | 92 | 351 | 951/1991 | 230 | 6/252 | 0/114 | 63/1141 | 18/376 | 225/1023 | 954/1011 | C-1 37 | v3 1016/v4 970 WETH 1164/USDG 612 fee/ts 100/1; 1991 launches (284.6/d) by 1294 wallets via 0x73991a25:ac9650d8 value 0.0,0.0012177; first real buy +92 (n 1011, med 0.0594 ETH, via 0x80114879); pulled 951/1991 at +351; early-outsider reaction 6/252 (baseline 63/1141) |
| 11 | `lc:bd55ea26b2f8d42a…55e|f305d719` | 1834 | 262.2 | 1804 | 171 | 767.5 | 326/1834 | 615 | 26/641 | 0/38 | 0/1188 | 37/641 | 0/1188 | 1189/1804 | - | v2a 1834 WETH 1834 fee/ts 3000/None; 1834 launches (262.2/d) by 1819 wallets via 0x89e5db8b:f305d719 value 1.0,50.09; first real buy +171.0 (n 1804, med 0.1704 ETH, via 0x89e5db8b); pulled 326/1834 at +767.5; early-outsider reaction 26/641 (baseline 0/1188) |
| 12 | `lc:c93c806e738300b5…e70|1fad948c` | 1482 | 211.7 | 12 | 637.5 | 1818 | 8/1482 | 1035 | 0/8 | 0/7 | 0/79 | 0/8 | 0/79 | 9/12 | - | v4 1479/v2a 2 WETH 845/USDG 616 fee/ts 8388608/8; 1482 launches (211.7/d) by 105 wallets via 0x5ff137d4:1fad948c value 0.0; first real buy +637.5 (n 12, med 0.0101 ETH, via 0xf0b7eaaf); pulled 8/1482 at +1818.0; early-outsider reaction 0/8 (baseline 0/79) |
| 13 | `lc:bd3881180b547f5f…626|6276cbbe` | 1433 | 204.9 | 781 | 127 | 567 | 329/1433 | 472 | 0/95 | 0/32 | 70/819 | 6/123 | 200/794 | 733/781 | C-2 779 | v4 1433 ETH 1196/WETH 126 fee/ts 500/1; 1433 launches (204.9/d) by 902 wallets via PoolManager:6276cbbe value 0.0; first real buy +127 (n 781, med 0.0312 ETH, via 0xc9459a24); pulled 329/1433 at +567; early-outsider reaction 0/95 (baseline 70/819) |
| 14 | `tok:4e451d1aef8a2d19…3eb6e25b1489` | 1230 | 175.9 | 714 | 125 | 576 | 322/1230 | 545 | 0/51 | 0/36 | 52/816 | 6/79 | 182/790 | 708/714 | C-2 773 | v4 1230 ETH 827/USDG 403 fee/ts 500/1; 1230 launches (175.9/d) by 844 wallets via PoolManager:6276cbbe value 0.0,0.000375103; first real buy +125.0 (n 714, med 0.0312 ETH, via 0xc9459a24); pulled 322/1230 at +576.0; early-outsider reaction 0/51 (baseline 52/816) |
| 15 | `tok:70adce63e2b26b93…ff9bff162a22` | 1217 | 174.0 | 1180 | 202 | 1188 | 161/1217 | 956 | 0/28 | 0/25 | 0/1164 | 0/28 | 0/1164 | 1180/1180 | - | v2a 1184/v4 33 WETH 1184/USDG 24 fee/ts 3000/None; 1217 launches (174.0/d) by 1197 wallets via 0x89e5db8b:f305d719 value 50.09,40.09; first real buy +202.0 (n 1180, med 0.4952 ETH, via 0x89e5db8b); pulled 161/1217 at +1188; early-outsider reaction 0/28 (baseline 0/1164) |
| 16 | `lc:0a493d1af3d0f25f…d4f|ac9650d8` | 1155 | 165.1 | 915 | 86 | 290.5 | 840/1155 | 230 | 6/142 | 0/57 | 70/1002 | 19/261 | 231/883 | 891/915 | - | v3 1155 WETH 1155 fee/ts 100/1; 1155 launches (165.1/d) by 1118 wallets via 0x73991a25:ac9650d8 value 0.0,0.001; first real buy +86 (n 915, med 0.05 ETH, via 0x80114879); pulled 840/1155 at +290.5; early-outsider reaction 6/142 (baseline 70/1002) |
| 17 | `tok:cb79985db9ea3746…3962884c1248` | 960 | 137.2 | 739 | 116 | 370 | 597/960 | 374.5 | 1/62 | 1/56 | 28/844 | 63/161 | 155/746 | 734/739 | C-1 888 | v4 949/v3 11 ETH 714/WETH 201 fee/ts 100/1; 960 launches (137.2/d) by 923 wallets via POSM:ac9650d8 value 0.0,0.0012177; first real buy +116 (n 739, med 0.14 ETH, via 0xd6d35b56); pulled 597/960 at +370; early-outsider reaction 1/62 (baseline 28/844) |
| 18 | `tok:59571c748b9f1a44…11b3806933f3` (= lc:42544ef5d4) | 686 | 102.7 | 657 | 44 | 1476 | 600/686 | 1469 | 14/326 | 0/0 | 28/347 | 132/348 | 112/325 | 345/657 | operatorA 677 | v4 686 ETH 678/USDG 8 fee/ts 100/200; 686 launches (102.7/d) by 684 wallets via 0x3194e326:2fcb9108 value 1.0,0.442; first real buy +44 (n 657, med 0.0527 ETH, via 0x88767899); pulled 600/686 at +1476.0; early-outsider reaction 14/326 (baseline 28/347) |
| 19 | `lc:c873e135dc9aaec8…0b2|f7020405` | 627 | 89.7 | 163 | 164 | 160 | 403/627 | 946 | 0/52 | 0/12 | 306/470 | 1/54 | 314/468 | 146/163 | - | v4 627 ETH 519/USDG 76 fee/ts 10000/200; 627 launches (89.7/d) by 188 wallets via POSM:f7020405 value 0.0; first real buy +164 (n 163, med 0.1015 ETH, via 0x88767899); pulled 403/627 at +160; early-outsider reaction 0/52 (baseline 306/470) |
| 20 | `tok:0f34e3b5f0599dd7…02d24581092d` | 609 | 87.1 | 599 | 3 | 269.5 | 166/609 | 257 | 26/599 | 0/3 | 0/6 | 37/599 | 0/6 | 0/599 | - | v2a 603/v4 6 WETH 603/USDG 4 fee/ts 3000/None; 609 launches (87.1/d) by 608 wallets via 0x89e5db8b:f305d719 value 1.0,0.0; first real buy +3 (n 599, med 0.0453 ETH, via 0x89e5db8b); pulled 166/609 at +269.5; early-outsider reaction 26/599 (baseline 0/6) |
| 21 | `lc:cd37624e07828adc…f41|6fe958d8` | 516 | 350.5 | 0 | - | 12 | 230/516 | - | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | - | v4 516 ETH 258/USDG 258 fee/ts 3000/60; 516 launches (350.5/d) by 1 wallets via 0xfcd18241:6fe958d8 value 0.0; first real buy +None (n 0, med None ETH, via None); pulled 230/516 at +12.0; early-outsider reaction 0/0 (baseline 0/0) |
| 22 | `tok:65daaea0eb5368ee…4cb09f4ea15b` | 511 | 73.6 | 269 | 0 | 1143.5 | 38/511 | 156 | 1/206 | 1/138 | 1/216 | 3/209 | 4/215 | 138/269 | - | v4 511 ETH 444/USDG 64 fee/ts 2500/25; 511 launches (73.6/d) by 281 wallets via 0x0000ffff:ac9650d8 value 0.0,0.08; first real buy +0 (n 269, med 0.4 ETH, via 0x0000ffff); pulled 38/511 at +1143.5; early-outsider reaction 1/206 (baseline 1/216) |
| 23 | `lc:0a493d1af3d0f25f…d4f|13ead562` (= tok:203caacbe1) | 493 | 73.7 | 431 | 28 | 144.5 | 426/493 | 123.5 | 5/77 | 0/1 | 82/406 | 6/77 | 82/406 | 375/431 | - | v3 493 WETH 493 fee/ts 100/1; 493 launches (73.7/d) by 114 wallets via 0x73991a25:13ead562 value 0.0; first real buy +28 (n 431, med 0.05 ETH, via 0xcaf681a6); pulled 426/493 at +144.5; early-outsider reaction 5/77 (baseline 82/406) |
| 24 | `lc:86b37100cbe98417…7f8|882db707` | 486 | 70.3 | 107 | 124 | - | 0/486 | - | 0/68 | 0/33 | 0/84 | 0/68 | 0/84 | 79/107 | - | v4 486 WETH 472/ETH 7 fee/ts 8388608/200; 486 launches (70.3/d) by 285 wallets via 0xeb7c0347:882db707 value 0.0; first real buy +124 (n 107, med 0.0495 ETH, via 0x65050a9b); pulled 0/486 at +None; early-outsider reaction 0/68 (baseline 0/84) |
| 25 | `tok:c0b7d40078fadc4b…6bbd694734d5` | 458 | 75.1 | 126 | 150.5 | 810 | 31/458 | 702 | 0/32 | 0/5 | 0/107 | 1/33 | 0/107 | 118/126 | - | v4 458 USDG 249/ETH 209 fee/ts 10000/200; 458 launches (75.1/d) by 238 wallets via POSM:ac9650d8 value 0.0,0.000351895; first real buy +150.5 (n 126, med 0.1134 ETH, via 0x88767899); pulled 31/458 at +810; early-outsider reaction 0/32 (baseline 0/107) |
| 26 | `tok:695e20af24bc5d60…aa07cdc158c3` (= lc:724433a2b5) | 440 | 85.2 | 4 | 407 | - | 0/440 | - | 0/7 | 0/5 | 0/422 | 0/7 | 0/422 | 0/4 | - | v4 440 WETH 436/USDG 4 fee/ts 0/200; 440 launches (85.2/d) by 10 wallets via 0xc739229d:7866fa39 value 0.0; first real buy +407.0 (n 4, med 0.0106 ETH, via 0x9689992f); pulled 0/440 at +None; early-outsider reaction 0/7 (baseline 0/422) |
| 27 | `tok:564fe314d3b6bb72…2d5ae34c62f5` | 394 | 56.8 | 124 | 4 | 1198 | 19/394 | 1198 | 0/59 | 0/59 | 0/110 | 0/62 | 0/109 | 106/124 | C-1 119 | v4 394 USDG 198/WETH 160 fee/ts 100/1; 394 launches (56.8/d) by 174 wallets via POSM:ac9650d8 value 0.0,1.9558e-05; first real buy +4.0 (n 124, med 0.07 ETH, via 0x80e49ed1); pulled 19/394 at +1198; early-outsider reaction 0/59 (baseline 0/110) |
| 28 | `tok:6a2a8d4f6cd05942…d475d5a0ac38` | 383 | 56.8 | 10 | 493 | 723 | 7/383 | 615.5 | 0/9 | 0/9 | 0/8 | 0/9 | 0/9 | 2/10 | - | v4 383 USDG2 192/USDG 179 fee/ts 8388608/60; 383 launches (56.8/d) by 51 wallets via POSM:ac9650d8 value 0.0,2e-06; first real buy +493.0 (n 10, med 0.0715 ETH, via 0x7ddbd395); pulled 7/383 at +723; early-outsider reaction 0/9 (baseline 0/8) |
| 29 | `tok:d2b0116c7a1e2374…1429d6d4b044` | 345 | 59.5 | 0 | - | - | 0/345 | - | 0/0 | 0/0 | 0/345 | 0/0 | 0/345 | 0/0 | - | v4 345 ETH 345 fee/ts 10000/200; 345 launches (59.5/d) by 3 wallets via 0xcc23e1ab:7fde822e value 0.0; first real buy +None (n 0, med None ETH, via None); pulled 0/345 at +None; early-outsider reaction 0/0 (baseline 0/345) |
| 30 | `tok:2dfcf583297e76db…0ddfb76a2e94` | 340 | 340.0 | 3 | 158 | 159 | 317/340 | - | 0/0 | 0/0 | 306/335 | 0/0 | 314/335 | 3/3 | - | v4 340 ETH 337/USDG 3 fee/ts 10000/200; 340 launches (340.0/d) by 3 wallets via POSM:f7020405 value 0.0; first real buy +158 (n 3, med 0.0074 ETH, via 0x88767899); pulled 317/340 at +159; early-outsider reaction 0/0 (baseline 306/335) |
| 31 | `tok:59bf3559ebc157c0…c4dd15a78ffe` | 332 | 63.3 | 0 | - | - | 0/332 | - | 0/0 | 0/0 | 0/329 | 0/0 | 0/329 | 0/0 | - | v4 332 ETH 332 fee/ts 10000/200; 332 launches (63.3/d) by 2 wallets via 0xcd5892b5:7fde822e value 0.0; first real buy +None (n 0, med None ETH, via None); pulled 0/332 at +None; early-outsider reaction 0/0 (baseline 0/329) |
| 32 | `tok:e316fe94e950e745…9566b90177fe` | 300 | 69.9 | 0 | - | - | 0/300 | - | 0/1 | 0/1 | 0/298 | 0/1 | 0/298 | 0/0 | - | v4 300 ETH 300 fee/ts 10000/200; 300 launches (69.9/d) by 23 wallets via 0x6a57c49c:a25a9a3d value 0.000100683,0.018454156; first real buy +None (n 0, med None ETH, via None); pulled 0/300 at +None; early-outsider reaction 0/1 (baseline 0/298) |
| 33 | `lc:c3cd7006bbddf5bf…34b|f0e9eabf` | 285 | 72.0 | 25 | 1 | 1423 | 1/285 | 1422 | 0/24 | 0/16 | 0/143 | 1/24 | 0/143 | 15/25 | - | v4 285 ETH 191/USDG 94 fee/ts 10000/200; 285 launches (72.0/d) by 92 wallets via 0xc763b179:f0e9eabf value 0.0,0.011914465; first real buy +1 (n 25, med 0.0394 ETH, via 0xc763b179); pulled 1/285 at +1423; early-outsider reaction 0/24 (baseline 0/143) |
| 34 | `tok:99e0b5e818fba4d4…2412026e2ac2` | 283 | 42.5 | 38 | 1 | 2303 | 1/283 | - | 0/28 | 0/27 | 0/91 | 0/28 | 0/92 | 31/38 | - | v4 283 WETH 267/USDG 15 fee/ts 0/60; 283 launches (42.5/d) by 183 wallets via 0x18cab14c:603ed0bc value 0.0,0.0001; first real buy +1.0 (n 38, med 0.1214 ETH, via 0x8141fec0); pulled 1/283 at +2303; early-outsider reaction 0/28 (baseline 0/91) |
| 35 | `tok:a98b3b9e80a70b40…35675fddc854` | 269 | 41.4 | 123 | 52 | 1207.5 | 8/269 | 994 | 0/24 | 0/6 | 0/122 | 0/24 | 0/122 | 114/123 | - | v4 269 ETH 146/USDG 122 fee/ts 3000/60; 269 launches (41.4/d) by 156 wallets via POSM:ac9650d8 value 0.0,0.0012177; first real buy +52 (n 123, med 0.05 ETH, via 0x75379d5d); pulled 8/269 at +1207.5; early-outsider reaction 0/24 (baseline 0/122) |
| 36 | `lc:89885b75fd29af13…08a|d27d1e00` | 248 | 35.5 | 176 | 0 | 490 | 65/248 | 1103 | 1/176 | 1/127 | 0/67 | 1/177 | 0/66 | 34/176 | - | v3 248 WETH 248 fee/ts 100/1; 248 launches (35.5/d) by 151 wallets via 0xe85cbb49:d27d1e00 value 0.0,10.2; first real buy +0.0 (n 176, med 0.1724 ETH, via 0xcaf681a6); pulled 65/248 at +490; early-outsider reaction 1/176 (baseline 0/67) |
| 37 | `tok:97c7ba1b0d3f2de3…8ffc532271d0` | 240 | 35.4 | 106 | 0 | 557 | 67/240 | 1349 | 0/107 | 0/73 | 0/68 | 0/108 | 0/67 | 13/106 | - | v3 172/v4 68 WETH 174/USDG 52 fee/ts 100/1; 240 launches (35.4/d) by 127 wallets via POSM:d27d1e00 value 0.0,12.7; first real buy +0.0 (n 106, med 0.1634 ETH, via 0xcaf681a6); pulled 67/240 at +557; early-outsider reaction 0/107 (baseline 0/68) |
| 38 | `tok:e8df5d48f9f4fb5e…4f691f73fa4c` | 218 | 33.6 | 2 | 1387 | - | 0/218 | - | 0/2 | 0/1 | 0/195 | 0/2 | 0/195 | 0/2 | - | v4 218 ETH 218 fee/ts 10000/200; 218 launches (33.6/d) by 2 wallets via 0x1b161a02:7fde822e value 0.0; first real buy +1387.0 (n 2, med 0.0197 ETH, via 0xb300000b); pulled 0/218 at +None; early-outsider reaction 0/2 (baseline 0/195) |
| 39 | `lc:4a586d925c9d59ec…d80|ac9650d8` | 212 | 30.5 | 129 | 0 | - | 0/212 | - | 0/129 | 0/100 | 0/82 | 0/129 | 0/82 | 17/129 | - | v4 212 ETH 212 fee/ts 2500/25; 212 launches (30.5/d) by 171 wallets via 0x0000ffff:ac9650d8 value 0.0,0.08; first real buy +0 (n 129, med 0.08 ETH, via 0x0000ffff); pulled 0/212 at +None; early-outsider reaction 0/129 (baseline 0/82) |
| 40 | `lc:049a3b673e341750…706|603ed0bc` | 204 | 52.1 | 25 | 1 | - | 0/204 | - | 0/3 | 0/2 | 0/52 | 0/3 | 0/52 | 24/25 | - | v4 204 WETH 202/USDG 2 fee/ts 0/60; 204 launches (52.1/d) by 137 wallets via 0x18cab14c:603ed0bc value 0.0; first real buy +1 (n 25, med 0.4835 ETH, via 0x8141fec0); pulled 0/204 at +None; early-outsider reaction 0/3 (baseline 0/52) |

`top40.json` has these rows with every number; `families_<grouping>.json` has every family with >= 5 pools under each grouping, with the
full feature summary and its pool ids.

## Bonding-curve factory 0x7ed598bc (count and sample)

20,737 creates in the window (10-04: 2,043, 10-05: 4,555, 10-06: 3,525, 10-07: 2,854, 10-08: 2,299, 10-09: 2,333, 10-10: 2,330, 10-11: 798; the last day is partial), 16,246 distinct creators (top 0x0e1651aec67b2a049a4fa6aeb6c1c305aabfc35b x801). The event is `0x8d4aad49…` with topics [sig, token, curve, creator] and 3 data words (`(0, 0, 4.2e18)` in 17,538 creates). The sampled create txs go mostly to `0xe33e9e47…` (`f85f8e41`, the front contract studied in ops/bcurve*.py) or to the factory itself (`a72101af`, `f35abbcf`): [['0xe33e9e479df8802cb0866d5d05258bec4cf62948:f85f8e41', 38], ['0x7ed598bcef8bd9edd8c97a195c6d13f40801ec7e:a72101af', 14], ['0x7ed598bcef8bd9edd8c97a195c6d13f40801ec7e:f35abbcf', 4], ['0x9dcceb091218cdedbc2875514386615a8ce63961:f85f8e41', 1]]. 918 curve tokens appear as the token of a census pool (graduations: [['v4/USDG', 1853], ['v4/ETH', 1445], ['v4/WETH', 5], ['v3/WETH', 1]]; blocks from the create to the pool p10/p50/p90 [703, 9695, 590364]), so those launches are in `pools.jsonl` under their v4 families. The curves' own trading was not decoded (the 25 sampled curves' logs: `bonding.json` `sample_curve_event_topics`).

## Files

| file | what |
|---|---|
| `pools.jsonl` | one row per pool (64,416), sorted by launch block; the schema below |
| `families_tok.json`, `families_tokm.json`, `families_lc.json`, `families_strict.json`, `families_fund.json`, `families_fund1.json` | every family with >= 5 pools under that grouping, by count; the family schema below |
| `top40.json` | the merged top 40 (above) |
| `overlap.json` | how the groupings overlap |
| `shared_fps.json` | transaction fingerprints shared by >= 25 single-use buyer wallets (fleets, decoys, front-end defaults) |
| `summary.json` | counts, per-DEX counts, family counts, funding-sample counts, parameters |
| `bonding.json` | the bonding-curve factory: counts per day, creators, graduations into census pools, the sample |
| `report_tables.md` | the generated tables of this README |
| `load.py` | loaders: `load_pools()`, `load_families(g)`, `load_top40()`, `load_summary()`, `load_events(ids)`, `load_txs()` |
| `cache/ev.jsonl` | every pool's raw events (compact rows, below), one line per fetch group |
| `cache/tx_launch.jsonl`, `cache/tx_swap.jsonl`, `cache/tx_swap_b.jsonl` | the fetched transactions (trimmed: hash, from, to, value_wei, nonce, bn, ti, type, gas, gas_price, max_fee, max_prio, selector, calldata_len, input (launch txs below 4,096 bytes) or input_head (swap txs: selector + 6 words)) |
| `cache/codes.jsonl` | `{addr, h (exact), size, m (mask32), sk (skeleton)}` for every token and launch target |
| `cache/funding.jsonl`, `funding_cache.jsonl`, `funding_hop2.jsonl` | the funding scans (rows: wallet, launch_block, launch_nonce, nonce0_block, scan_from/to, status, first, latest_before_launch, fundings) |
| `cache/fblocks.jsonl` | the full blocks read for the funding scans (txs: hash, from, to, value, nonce, input, type, index) |
| `cache/inits.jsonl`, `factory.jsonl`, `bonding.jsonl` | the raw creation logs; `window.json`, `tsgrid.json`, `timing.json`, `f*.log` |

### pools.jsonl

Addresses lowercase; amounts in ETH-equivalent floats unless `_wei`; offsets (`off`) are blocks after `launch_block`.

- identity: `dex` (v4 | v2a | v2b | v3), `pool` (v4 pool id or the pair/pool address), `factory`, `token`, `quote` (ETH | WETH | USDG | USDG2),
  `quote_side` (0/1), `quote_pair`, `fee` (v4: the PoolKey fee, 8388608 = dynamic; V2: 3000 nominal; V3: the pool fee), `tick_spacing`,
  `hooks`, `sqrt_p0`, `tick0` (v4 only), `launch_block`, `launch_ts`, `launch_utc`, `launch_tx`, `launch_ti`.
- `launch`: `from`, `to` (null = creation), `nonce`, `value_wei`, `value_eth`, `selector` (8 hex, no 0x), `calldata_len` (bytes),
  `gas_price` (effective, wei), `max_prio`, `type`, `created_contract`, `target`, `target_code_hash` (exact, latest), `target_code_size`,
  `n_pools_in_tx`. For V2/V3 the launch tx is the PairCreated/PoolCreated tx (the liquidity can come later: `liq_off`).
- `token_code`: `hash`, `mask32`, `skel`, `size` (latest state; null hashes = no code now).
- `known_fp`: operatorA | vbot-v2.433 | vbot-v3.0 | vbot-v5.0 | smallpot | C-1 | C-2 | hooked-f07d1c53 | null (first-census fingerprints, annotation only).
- events: `has_events`, `ev_to`, `ev_complete`, `n_swaps`, `n_buys`, `n_sells`, `buy_eth_total`, `n_adds`, `liq_off` (first liquidity add),
  `liq_in_launch_tx`.
- `swaps12`: the first 12 swaps, each `[off, "B"|"S", eth, eoa, to (the contract the tx called), selector, calldata_len, gas_price, max_prio,
  router (the contract that called the pool / PoolManager: the Swap event's sender), in_launch_tx]`.
- `first_buys`: `[[off, eth]]` the first 5 buys by anyone; `first_buy_off`, `first_buy_eth`.
- `first_real_buys`: `[[off, eth, eoa]]` the first 3 real buys; `frb`: `off, eth, eoa, to, sel, clen, router, idx` (its index among the
  pool's swaps), `gp`, `prio`, `eoa_is_launch_wallet`, `eoa_npools_bought`, `eoa_npools_seen`, `also_in_tok_family`, `also_in_lc_family`,
  `also_in_fund_family` (how many *other* pools of the same family that wallet bought in; null when the pool has no key in that grouping).
- `pulls`: every pull in the window, `[off, eoa, to, selector, full, frac, via (the contract that called the pool / PoolManager), tx]`;
  `n_pulls`, `first_pull_off`, `first_pull_full`, `first_full_pull_off`, `pull_by_launch_wallet`, `pull_minus_frb` (first pull - frb, blocks),
  `pull_before_frb`, `pull_after_last_buy` (first pull - the last buy of anyone before it).
- `outsider`: `n_buys_before_pull` (all buys before the first pull, or in the window if never pulled), `n_with_eoa` (of those, with a fetched
  tx), `n_outsider_buys`, `outsider_eth`, and when > 0: `first_off`, `last_off`, `last_eoa`, `last_eth`, `max_eth`, `last_fp` and `fps` (the
  outsider buys' transaction fingerprints `to:selector:calldata_len:max_prio`, to tell an operator's single-use crowd wallets from real
  outsiders), `pull_after_first`,
  `pull_after_last` (null if never pulled), `reaction` (bool; null when the window is incomplete and no pull).
- `outsider`, also: `n_win200`, `n_win200_with_eoa` (buys in the 200 blocks before the first pull and how many have their tx), `nf_n`,
  `nf_last_off`, `nf_last_fp`, `nf_pull_after_last`, `nf_reaction`. `outsider12`: `n`, `n_buys12_before_pull`, `last_off`, `last_eth`, `last_fp`,
  `pull_after_last`, `reaction`, `nf_n`, `nf_last_off`, `nf_last_eth`, `nf_pull_after_last`, `nf_reaction`; `pull_after_last_buy12`.
- `ours`: null or `{bought, first_off, bought_before_pull, pull_after_ours}`.
- `funding`: null (launch wallet not resolved) or `{status, sampled_pool, from_cache, scan_blocks, launch_nonce_at_sample, nonce0_block, funder, via,
  kind (direct | calldata), blocks_before_launch, value_eth, funder_nonce, funding_tx, latest_funder, hop2 {status, funder, via,
  blocks_before_hop1, value_eth, funder_nonce}, root}`.
- `fam`: `tok` (skeleton), `tokm` (mask32), `tokx` (exact), `lc`, `strict`, `fund` (root), `fund1` (direct funder); `fam_n`: the size of each.

### families_<grouping>.json (families with >= 5 pools, by count)

`key, grouping, count, n_with_events, n_with_liq, first_utc, last_utc, per_day, dex, quote, fee_ts, n_tokens, n_deployers, deployer_top,
launch_target, selector, calldata_len, value_eth, nonce_med, tok_size, known_fp` (top values as `[value, n]`), `first_buy_off_med`, `frb_n`,
`frb_off_p10_50_90`, `frb_eth_med`, `frb_to`, `frb_sel_clen`, `frb_eoa_top`, `frb_by_launch_wallet`, `frb_eoa_in_same_tok_family`,
`frb_eoa_in_same_lc_family`, `frb_eoa_in_same_fund_family`, `frb_distinct_eoas`, `frb_router_top`, `frb_fp_top` and `outsider_fp_top`
(`to:selector:calldata_len:max_prio` of the first real buy / of the last outsider buy, top values), `n_pulled`, `pulled_share`,
`pull_off_p10_50_90`, `full_pull_share`, `pull_minus_frb_med`, `pull_before_frb`, `pull_by_launch_wallet`, `pull_via` (`to:selector` of the
first pull tx), `outsider_pools`, `outsider_reactions`, `outsider_reaction_rate`, `pull_after_outsider_med`, `reaction_baseline_pools`,
`reaction_baseline_quick`, `reaction_baseline_rate`, `outsider12_pools`, `outsider12_reactions`, `outsider12_reaction_rate`,
`pull_after_outsider12_med`, `outsider12_nf_pools`, `outsider12_nf_reactions`, `outsider12_nf_reaction_rate`, `pull_after_outsider12_nf_med`,
`baseline12_pools`, `baseline12_quick`, `baseline12_rate`, `outsider12_fp_top`, `pulled_share_with_outsider`, `pulled_share_without_outsider`, `ours_in`,
`funded_sampled`, `funder_top`, `desc`, `pools` (pool ids in launch order).

### cache/ev.jsonl (raw events, compact rows; `load_events` trims them to [launch, launch + 3,000] and sorts)

Group row `{kind, ids, launch {id: block}, a, b, head, ev}`. Event rows (amounts exact ints, raw units):
v4 swap `["s", bn, ti, li, pool_id, sender, amount0, amount1, sqrtPriceX96, liquidity, tick, fee, tx]` (amounts are the swapper's deltas:
negative = paid in), v4 liquidity `["m", bn, ti, li, pool_id, sender, tickLower, tickUpper, liquidityDelta, salt, tx]`;
V2 `["s", bn, ti, li, pair, sender, amount0In, amount1In, amount0Out, amount1Out, to, tx]`, `["mi", bn, ti, li, pair, sender, amount0, amount1, tx]`,
`["b", bn, ti, li, pair, sender, amount0, amount1, to, tx]`; V3 `["s", bn, ti, li, pool, sender, recipient, amount0, amount1, sqrtPriceX96,
liquidity, tick, tx]` (the pool's deltas: positive = into the pool), `["mi", bn, ti, li, pool, owner, tickLower, tickUpper, amount, amount0,
amount1, tx]`, `["b", bn, ti, li, pool, owner, tickLower, tickUpper, amount, amount0, amount1, tx]`. `code/evload.py` `norm()` turns them into
buys/sells/adds/pulls on the quote side.

## Problems and limits

1. **Outsiders are only as good as the transactions fetched.** The EOA is known for the first 12 swaps of every pool, the first real buy,
   every pull, and the 12 buys closest before the first pull (within 200 blocks); that is 192,455 of 1,014,047 (19%) of all buys before the first pull
   (114,256 of 810,446 (14%) in never-pulled pools; busy wash-traded pools have hundreds of swaps). `outsider.*` therefore undercounts outsiders in busy
   pools and biases the all-fetched reaction rate upward (an outsider that bought late in a never-pulled pool is missed from the denominator).
   The `outsider12` block and the "early-outsider" family columns use the first 12 swaps only, which are fetched for every pool, so they
   are not biased by the pull; use those for rates.
2. **The wallet rule ("seen in fewer than 3 pools") marks single-use crowd and decoy wallets as outsiders.** Operator A's crowd (Universal
   Router, 1,124-byte calldata, 0.02 gwei tip: 3,195 single-use wallets in 328 pools), the volume bot's decoy router `0x65050a9b`, a V2
   router fleet (`swapExactETHForTokens`, 228 bytes, tip 0: 5,072 single-use wallets in 602 pools) and others all pass it. `shared_fps.json`
   lists the 42 transaction fingerprints (`to:selector:calldata_len:max_prio`) used by >= 25 single-use wallets; the `nf_*` fields and
   the "shared fingerprints excluded" column drop buys with those fingerprints. That filter can also drop real retail users who share a
   front-end's default route; both variants are kept. Wallet pool counts are lower bounds (fetched txs only).
3. **Funding is a sample, and incomplete.** 241 launch wallets were scanned over the RPC (a funding found for 105) and 109 more resolved from the cached blocks; status {'no_funding_in_range': 78, 'found': 214, 'nonce0_not_found': 58}; 69 fresh funders got a second hop (52 found). 4,974 pools (6,839 covered) have a funder. Fundings older than the scan (800 blocks, 82 s; 1,200 for the first 27 wallets) are
   missed (`no_funding_in_range`, `nonce0_not_found` when the wallet's nonce-0 tx is older); a contract that forwards ETH without the
   wallet's address in its calldata (an internal transfer computed on chain) is invisible without traces; `calldata` fundings carry the
   whole call's value, not the wallet's share. The funding grouping covers only the pools of sampled (or cache-resolved) wallets, so its
   family counts are not comparable with the other groupings.
4. **The launcher key (`lc`) lumps shared entry points.** Every launch through the Uniswap v4 PositionManager multicall is one `lc` family
   (`c873e135…|ac9650d8`, 21,018 pools from about 8,000 wallets: the volume bot, C-1, small pot and dozens of others), likewise the V2 router's
   `addLiquidityETH` and the V3 position manager. `strict` (adding calldata length, fee, tick spacing, hooks) separates them but splits
   operators that vary the fee.
5. **The token-code key is a template key.** The skeleton (`tok`) merges every token compiled from the same source (one launchpad template
   covers 28,547 V2 pairs from about 440 wallets); `tokm` (immutables masked) is finer; the exact keccak (`tokx`) is useless as a family key
   (11,189 distinct values for 64,403 pools) because immutables (the pair, the deployer, the supply) differ per token. Code is read at the
   latest state; 118 launch targets have no code now (self-destructed or EIP-7702 accounts), their key falls back to the address.
6. **V2/V3 "launch" = pair/pool creation.** The liquidity can come later (596 V2/V3 pools have `liq_off` > 0); the 3,000-block window
   starts at the creation. Most v2a pairs never get liquidity (launchpads create a pair on each factory and fund one).
7. **Full/partial pulls** are from liquidity accounting: v4/V3 sum of liquidity deltas over all positions (ranges are not weighted); V2 a
   WETH reserve rebuilt from Mint/Swap/Burn (direct transfers, `skim` and `sync` are not seen). Hooked v4 pools can move amounts the events
   do not show.
8. **USDG** is converted at a fixed 1 ETH = 2,570 USDG for the 0.005 ETH real-buy threshold and every `eth` field of USDG pools; the raw
   amounts are in `cache/ev.jsonl`.
9. **Our own engine's trades** (Oct 8-10) are in 1,091 pools (`ours`); they are excluded from the first real buy and from outsiders, but
   they are part of the swaps that triggered some pulls in those pools.
10. **Multi-pool launch txs**: one tx can initialise or create several pools (v4 batches of up to 70; the V2 launchpads create a pair on each
    factory); each pool carries the same `launch` (`n_pools_in_tx`).
11. **Rate limits**: 1,271 HTTP 429 answers over 12,183 POSTs, all retried with back-off; no item was lost. The public RPC keeps state for only about the last 1,000 blocks (`eth_getBalance` at older blocks answers
    "historical state ... is not available"), so balance-based funding search was impossible; the full-block scan is the only method without
    traces.
12. **The bonding curve** was only counted and sampled (`bonding.json`); its tokens that graduated to v4 pools are in `pools.jsonl` like any
    other launch.
13. The event fetch ran at a head 3,042 blocks after the window's head, so every pool's 3,000-block window is complete (`ev_complete` false
    for 0 pools). Launch times are interpolated from a 5,000-block timestamp grid (about a second of error).
14. **The `known_fp` labels** come from the first census's fingerprints and are only annotations; a family "contains" a label when some of
    its pools match it (the counts are given), e.g. the token template `d4e7eae4` is shared by 1,016 V3 launches, 970 v4 launches (several launchers)
    and 37 pools matching the C-1 fingerprint, so a label in a family does not make the family that operator.
15. **Account-abstraction and EIP-7702 launches.** 1,496 pools were launched through an ERC-4337 EntryPoint (`0x5ff137d4…` `handleOps`
    1,482, `0x00000000…71727de2` 14; e.g. launcher family `c93c806e…|1fad948c`): their `launch.from` is the bundler, not the operator, so
    their deployer counts and funding say nothing about the operator (the smart account is inside the calldata). 94 launches are type-4
    (EIP-7702) transactions and 503 of the first-12 swaps went through an EntryPoint (their `eoa` is the bundler).

