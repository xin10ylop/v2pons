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
