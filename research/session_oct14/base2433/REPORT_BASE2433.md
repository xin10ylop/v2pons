# The 2.433 operator on Base, Oct 14 2026 (found by the 09:53 UTC watch)

**Verdict:** the operator that ran the 2.433 line on Robinhood (and 52 pools on BNB Chain on Oct 13) is setting up on **Base**. It made three test
launches between 09:32 and 09:42 UTC. All three were Uniswap v4 pools with fee 5000 / tick spacing 100 (the 2.433 line's pool setup), the
operator's own 777 token code, and a new launch wallet each time. Its buyer wallets were funded with 3.75 ETH on Base. Each pool was pulled
18-30 blocks (36-60 s) after its launch. Nothing new had launched as of about 10:10 UTC. This is the same pattern as the Ethereum test the day
before the BNB run (research/session_oct14/find2433/REPORT_FIND2433.md).

Data: public Base endpoints, read-only (base-rpc.publicnode.com for the latest state and blocks; Tenderly's public gateway
base.gateway.tenderly.co for logs older than ~20 minutes, since publicnode refuses those). Scripts b01-b05 in this folder, each with its `.out`.

## What moved (watch/0953_xchain.out)
- The 31 buyer wallets on Base: nonce sum 20,335 -> 20,405 since 09:09 UTC; balance 0.0006 -> 3.75 ETH. 21 of them hold 0.04-0.37 ETH.
- Every other chain (BNB, Ethereum, HyperEVM, Robinhood) and every other key: unchanged.

## The transactions (b01_2000.out, the last 2,000 Base blocks to 10:08 UTC)
- 09:36:39: 21 buyer wallets each send 0.004-0.010 ETH to `0x505b452d` (a new EOA).
- 09:39:57: the same 21 each send 0.004-0.010 ETH to `0x72d0cac5` (a new EOA). Both are launch wallets (below).
- 09:42:57-09:43:37: 11 buys of 0.099-0.272 ETH (2.10 ETH in all) by buyer wallets through `0x987d5db8` (selector 27f7e6ee, 356 B),
  approvals of the token and Permit2, and 6 sells through Uniswap's Universal Router `0x6ff5693b` (24856bc3, 1,028 B).
- 09:43:47: one buyer sends 0.067 ETH to `0x8f79d153`, an EOA with nonce 0 holding 3.66 ETH.
- **10:05:29-10:05:31: the buyers sweep their Base ETH to `0x8f79d153`** (22 transfers in this window, b01_sweep.out). At 10:11 UTC it
  holds 8.46 ETH at nonce 1; the buyers hold 0.0006. The same address has nonce 6 on BNB Chain and 8 on Robinhood. The tracker now
  reads it (`collect_8f79`) and the three Base launch wallets (`base_launch3`).

## The three launches (b03_24h.out, b04_hooks.out): the only fee-5000/ts-100 v4 launches on Base in 24 h (of 3,645)

| time (UTC) | block | launch wallet | launcher contract | token | hook | swaps | pulled |
|---|---|---|---|---|---|---|---|
| 09:32 | 52,590,492 | `0x4d40df2e` (nonce 11) | `0x32ab7e98` | `0xbe07c8c3…a777` | `0x0a37fce6…c080` | none | +18 |
| 09:37 | 52,590,658 | `0x505b452d` (nonce 10) | `0xeb8271d7` | `0xccc17382…e777` | `0x9e3653bb…c080` | (not read) | (not read) |
| 09:42 | 52,590,807 | `0x72d0cac5` (nonce 10) | `0xd93bef10` | `0x3a73002f…a777` | `0x1c888901…8080` | 16, all by buyer wallets: 2.10 ETH in, 0.84 out | +30 |

- **Token:** 1,526 B, code hash `63ad5291cdef`: the same code as the Robinhood 2.433 line's tokens. Addresses end in 777.
- **Launch:** a call `c3e0ff3d` (260 B, value 0) to a launcher contract deployed for that launch (11,031 B, code hash `225f9af97d88`,
  the same each time). Its arguments: the PoolManager, the token, fee 0x1388 (5000), tick spacing 0x64 (100), max uint160, 0xd89a0
  (887,200, the full-range tick), and a price. On Robinhood the line launched through the PositionManager multicall `0xac9650d8` (1,444 B,
  2.4333285 ETH, no hook). On Base the launch carries no ETH, adds liquidity 3 blocks later, and uses a hook.
- **Hook:** a new contract each launch (9,002 B; the code hash differs per launch, probably immutables). Its address bits enable
  **afterSwap only**. Its bytecode (b05_hookscan.out) holds the launcher's selectors (unlock, unlockCallback, take, transfer, approve) and the
  string "Output below minimum". It is a router and hook in one, not a plain hook. **Not known:** whether afterSwap refuses, taxes or reacts
  to an outsider's swap. An afterSwap hook can revert a swap, so an outsider's sell might fail. No outsider has swapped in these pools.
- **Buy contract `0x987d5db8`** (22,816 B, code hash `008737874a66`): it holds `c1120e3d` and `a0f7978d`, the Robinhood bot router's buy
  and pull selectors, plus V2 and V3 router selectors and `27f7e6ee`, the buy used here. It is a newer build of the same router.

## What this means for us
- **It is not tradable yet:** three tests in 10 minutes, each pulled within a minute, none with an outsider.
- **The next sign:** a run of launches like the BNB one (52 pools in 3.7 h, one every ~4 minutes). The 3-hour watch is too slow to catch the
  start of such a run; a watch every few minutes would be needed.
- **To trade it** the front engine needs Base:
  - a Base RPC and wallet;
  - FlipRelay deployed on Base (its v4 PoolKey must carry the hook address, which the Robinhood pools did not have);
  - the launch recognized by the `c3e0ff3d` call to a new launcher, plus the token's code hash;
  - the fire timed off the liquidity add at +3, not the launch.
- **Before any money:** an exit test that answers whether the afterSwap hook lets an outsider who bought sell again. The BNB line was a
  honeypot (research/session_oct14/bnbfreeze/REPORT_BNBFREEZE.md). The test is an eth_call of a buy and a sell through the pool at a live
  block, with the hook in place.

## Update, Oct 14 11:30 UTC (b09, b10, b12, b07 on the 10:30 pool)

**Five launches so far, all the same shape; the operator has been idle since 10:35.** Head 52,593,952 at 11:27:31 UTC (b12_now.out).

| # | UTC | block L | launch wallet | pool | add (block, ETH) | bot's first buy | pull | swaps |
|---|---|---|---|---|---|---|---|---|
| 1 | 09:32:11 | 52590492 | `0x4d40df2e` | `0x4719b41b…` | +3, 0.1333 | none | +18 | 0 |
| 2 | 09:37:43 | 52590658 | `0x505b452d` | `0x722c5de4…` | +2, 0.1333 | none | +32 | 0 |
| 3 | 09:42:41 | 52590807 | `0x72d0cac5` | `0x3085339d…` | +3, 2.1333 | +8, 0.150 ETH | +30 | 16 |
| 4 | 10:30:27 | 52592240 | `0x8f79d153` (the collector) | `0xb41ad027…` | +3, 2.1333 | +8, 0.200 ETH | +126 | 71 |
| 5 | 10:35:05 | 52592379 | `0x78f4b6cc` (new) | `0x909c1fda…` | +3, 2.1333 | +8, 0.1485 ETH | +128 | 68 |

(b09_census.out has every hash; b10_pools.out every event with its transaction.)

- **The launch sequence is fixed** (b12_now.out section 4): +0 `c3e0ff3d` to the per-launch launcher (value 0); +1 the launch wallet funds the
  buyer fleet through the bot contract `0x987d5db8` (`4977dff6`: a list of 25 addresses and amounts, 6.131 ETH on pools 3 and 4, 18
  addresses and 2.399 ETH on pool 5); +2 `approve(token -> hook)`; +3 the liquidity: the launch wallet -> hook `2346bb56` with 2.133329 ETH
  (pool 2 did this at +2), full range, liquidity 46141758126452008872416 (identical in pools 3, 4, 5; the 0.1333 ETH test pools:
  11535243517152119489536); +4/+5 the Permit2 and Universal Router approvals; the pull: launch wallet -> hook `f2f230a8`.
- **The bot's first buy is at +8 in all three real pools** (5 blocks, 10 s, after the add), 0.15-0.20 ETH, then a buy every 1-2 blocks
  (0.02-0.35 ETH) and sells through the Universal Router from +12. **Its price tolerance is 5%**: calldata minOut / tokens received =
  0.9500 on every one of the 90 bot buys decoded (Robinhood's line and the BNB line ran at 0.99).
- **The pull is a timer, about 4.1 minutes**: +126 and +128 on the two real pools (the 09:42 test was cut at +30).
- **The Swap event's `sender` is the Universal Router `0x6ff5693b` for every swap**, the bot's buys included (the bot contract routes them
  through it). So the bot's buy cannot be told apart in the PoolManager's logs by its sender; it can by its transaction (to `0x987d5db8`,
  selector `27f7e6ee`, the token in the calldata), which the Flashblocks stream shows before the block is sealed.
- **No outsider has traded in any pool.** b10 tagged 21 swaps in pools 4 and 5 as OUTSIDER because their wallets (`0x5f0190f1`,
  `0xa2deb9f0`, `0xaab209e7`, `0xf7b323ba`) are not among the 31 known buyers. They are the operator's: the +1 funding call of pools 3, 4
  and 5 lists them with the others (b12 section 1), they buy through the bot contract with the same 0.95 tolerance and sell through the
  Universal Router like the rest, and they sit at nonce 600-701 on Base, 9,421-9,759 on BNB Chain, 144-250 on Ethereum and 18,397-18,491
  on Robinhood. The fleet on Base is 35 wallets (the 31 plus these 4). **The operator's reaction to an outsider therefore remains
  unknown** (on BNB it pulled 6-7 blocks, about 3 s, after an outsider's buy; on Robinhood it never did).
- **Exit test on the 10:30 pool** (b07_exittest_1030.out): the same as on the 09:42 pool: an outsider's buy and sell through our relay's
  code go through at every block from +3 to +29 at -1.00% (the two 0.5% fees; the hook takes nothing); a sell alone at +8, after the
  bot's first buy, returns +18.1% on 0.002 ETH bought at +4.
- **Correction**: the hooks' address flags are `0x0080` = **beforeSwap** only (b09; bit 7). The 10:11 text above says afterSwap; that was a
  decoding error in b04. The hook's bytecode carries the beforeSwap selector `575e24b4`.
- **The operator's money at 11:27**: the collector `0x8f79d153` is empty (nonce 11: it launched pool 4, funded the fleet with 6.131 ETH and
  the pool with 2.133); the 35 buyer wallets hold about 3.1 ETH (the 31: 3.108, nonce sum 20,603); the five launch wallets are empty. No
  fee-5000/ts-100 Initialize after block 52,593,544. Gaps: 5.5, 5.0, 47.8, 4.6 minutes; 52 minutes since the last launch at 11:27.

**For the engine (docs/BASE.md)**: fire on the add (seen at +2 or +3; the bot's first buy follows 5 blocks later), hold at most 5 blocks after
our buy, sell on the bot's buy seen pending (to `0x987d5db8` carrying the token) or on the first paying buy behind ours, `BASE_BOT_SENDERS`
off (the Swap sender is the Universal Router for everyone), skip pools whose add carries under 1 ETH (the two 0.1333 test pools). The stake:
the owner sets it; the first live trade is the test of the reaction (RUNBOOK 4l).
