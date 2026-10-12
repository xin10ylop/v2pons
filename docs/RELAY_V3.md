# FlipRelayV3: the Uniswap V3 relay (HANDOFF 16.16, option (b))

The relay that trades the V3 lines (p356, the self-buyer, the 836-byte crowd) the way `FlipRelay` trades the v4 lines: the owner's
buy at nonce n, a presigned sell-everything at nonce n+1, no router, no approval, the stake kept in the contract. Nothing here is
deployed; the owner deploys it from the box (section 4). Built and simulated on Oct 12, 2026 (about 10:00 UTC), revised after the
security review the same day (the sweep's amount, the callback paying from a record, the deploy and ops guards) and simulated again at
about 11:47 UTC; nothing was sent.

## 1. The contract (`contracts/FlipRelayV3.sol`, 142 lines, solc 0.8.26, optimizer 1000 runs, cancun)

| | |
|---|---|
| `constructor(address owner_)` | `owner` immutable (refuses address 0). `FACTORY` `0x1f7d7550...2efa`, `WETH` `0x0bd7d308...ad73`, `POOL_INIT_CODE_HASH` `e34f199b...8b54` are constants |
| `buy(token, fee, amountIn, minOut, deadline) -> out` `a0328eb2` | owner only; `block.timestamp <= deadline`; the pool is the factory's CREATE2 address for (WETH, token, fee), sorted as Uniswap does; no code there: `NoPool`; less ETH than `amountIn`: `Insufficient`; records the swap (the pool, WETH, at most `amountIn`), wraps `amountIn` (`WETH.deposit`), `pool.swap` exact-in WETH -> token with the price limit at `MIN_SQRT_RATIO + 1` (WETH token0) or `MAX_SQRT_RATIO - 1` (WETH token1); `out` = the relay's token balance after less before; `out < minOut`: `TooLittleOut`; the tokens stay in the relay. If the price limit cuts the fill short, the WETH the pool did not take is unwrapped back to ETH |
| `sell(token, fee, minOut, deadline) -> out` `13318338` | owner only; the relay's ENTIRE balance of `token` (0: `NothingToSell`); deadline; records the swap (the pool, the token, at most that balance); exact-in token -> WETH at the extreme limit; `out` = the WETH the pool sent; `out < minOut`: `TooLittleOut`; `WETH.withdraw(out)`; the ETH stays in the relay |
| `uniswapV3SwapCallback(d0, d1, data)` `fa461e33` | `msg.sender` must be the recorded pool (else `NotPool`; the record is written just before `pool.swap` and cleared just after, so at any other time every caller is refused). Pays the positive delta with a plain `transfer` of the recorded token (WETH on a buy, the token on a sell), never more than the recorded maximum, which it lowers by what it paid (`Overpay(owed, max)` otherwise). `data` is not read |
| `withdraw(amount)` `2e1a7d4d` | owner only; ETH to the owner (0 = all) |
| `sweep(token, amount)` `6ea056a9` | owner only; `amount` of a token (WETH included) to the owner, 0 = all of it (an amount for a token whose transfers are capped or whose `balanceOf` lies) |
| `receive()` | open (WETH's `withdraw` sends ETH in) |
| views | `owner()`, `WETH()`, `FACTORY()`, `POOL_INIT_CODE_HASH()` |

The record is three storage slots (0: the pool, 1: the token to pay, 2: the most it may be paid), all 0 between swaps; `buy`/`sell`
revert `Busy` while slot 0 is set. No delegatecall, no call to an address the caller chooses except the token itself (`balanceOf`,
`transfer`) and the CREATE2 pool; ERC20 transfers are low-level calls that accept an empty return and refuse `false` or a revert
(`TransferFailed`). Errors: `NotOwner` 30cd7471, `NotPool(address)` 4a1576a2, `Busy` 3ef33375, `TooLate(uint256,uint256)` 388b0173,
`NoPool(address)` d0dc3f10, `Insufficient(uint256,uint256)` e8620800, `NothingToSell(address)` cb72d3db, `TooLittleOut(uint256,uint256)`
e20a4c5d (the same as FlipRelay's), `Overpay(uint256,uint256)` d7573691, `TransferFailed(address)` 39f1c8d9.

**Differences from FlipRelay (v4) the engine must know:**
- The owner is the constructor's argument (v4: the deployer).
- `deadline` is strict: `block.timestamp <= deadline`, and 0 is in the past (v4: 0 = no deadline). Sign every buy and sell with a real
  deadline.
- The pool is named by `(token, fee)`, not a PoolKey; WETH may be token0 or token1, the contract sorts.
- The relay holds ETH only between trades: WETH is wrapped inside a buy and unwrapped inside a sell (and after a cut-short buy).
- `sweep` takes an amount (0 = all).

`contracts/compile.py FlipRelayV3` writes `contracts/FlipRelayV3.json`: runtime **4,672 bytes**, one immutable reference (`owner`),
source sha256 **`8530afefe65ac92c2bfb2956cf1f9cb00c9dafa71e638c2f7965f990b40bc57e`**. `contracts/compile.py` with no argument still
builds `FlipRelay.json` byte for byte as before (the file is unchanged).

**What the security review verified** (Oct 12, on the first build; the fixes it asked for are in this one): `FACTORY` is the canonical
UniswapV3Factory 1.0.1 and `POOL_INIT_CODE_HASH` its pools' init code hash; WETH's implementation behind the proxy; QuoterV2 is Uniswap
periphery 1.4.4; malicious-token re-entry attempts all revert; every leg equals QuoterV2. Verdict: safe to deploy with a small balance.

## 2. The simulator (`deploy/relay_v3_sim.py`, `contracts/RoundTripHarnessV3.sol`)

eth_call with state overrides on the public RPC: the relay's runtime code (owner = the harness's address) at `0xf3f3...` with 0.01 ETH,
the harness (test only, never deployed) at `0xa3a3...`. In one call on one block's state the harness takes QuoterV2's quote, buys 0.002
ETH, reads the relay's balance, takes QuoterV2's quote of the sell, sells everything and requires: the relay's ETH down by exactly
`amountIn` after the buy, up by exactly the sell's `out` after it, no token and no WETH left. Python recomputes both legs with the exact
V3 swap math (SqrtPriceMath, one range) from the pool's slot0 and liquidity as the harness read them. Then the failure paths, each with
its exact expected error and arguments, the owner's calls that must go through, and a partial then a full sweep.

QuoterV2 on Robinhood Chain: `0x33e885ed0ec9bf04ecfb19341582aadcb4c8a9e7` (the V3 factory's deployer `0x9701fb0a...3a52`: the factory is
its nonce 2, the PositionManager nonce 11, SwapRouter02 nonce 18, QuoterV2 nonce 6; its `factory()` and `WETH9()` are ours).

    python3 deploy/relay_v3_sim.py                       # the newest live pool of each line in the last 24 h, one with WETH as token1, one pulled
    python3 deploy/relay_v3_sim.py 0xPOOL [0xPOOL ...]   # given pools; --eth 0.05 for another size

Exit status: 0 all as expected, 1 something is not (do not deploy), 2 no live pool was found (only pulled or sell-locked ones: nothing
wrong, nothing proven; give a live pool or a longer `--hours`).

### Results of this build (Oct 12 about 11:47 UTC, blocks 86,649,149-86,649,803; 0.002 ETH)

| line | pool | WETH | fee | buy: tokens out | = QuoterV2 | = one-range math | sell: wei back | = QuoterV2 | round trip | 2 fees | gas buy tx / sell tx (≈) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| p356 (356 B, launcher code 89885b75, never bought) | `0x26c29066e33f97d67f158463b5e9201a3733529c` | token0 | 0.01% | 1,995,803,888,074,217,441,493,979 | exact | exact | 1,999,600,419,081,123 | exact | -0.0200% | -0.0200% | 235,283 / 163,416 |
| self-buyer (13ead562, no own buy), as in round 1 | `0x5f224e675cbe6845cb37545bb7a248795da1b03a` | token0 | 1% | 3,549,911,499,662,906,957,259,727 | exact | exact | 1,960,277,320,457,562 | exact | -1.9861% | -1.9900% | 252,355 / 163,007 |
| self-buyer, the newest (13ead562, launched 0.2 h before) | `0xf7640bb8e0ae2e35941157371feac814f0c38bd9` | token0 | 1% | 832,305,189,505,428,922,938,658 | exact | exact | 1,960,232,642,108,416 | exact | -1.9884% | -1.9900% | 252,670 / 180,902 |
| crowd (836 B, launched 0.1 h before) | `0x8dffdfe644151fb831b75973e168ccccf7e961d6` | token0 | 0.01% | 74,056,191,984,141,745,177,595 | exact | exact | 1,999,600,061,126,508 | exact | -0.0200% | -0.0200% | 230,010 / 162,572 |
| WETH as token1 (launcher 0x2b933199, 772 B) | `0x0d2cfcb4d89a1b363840d09c33077c0d69606444` | token1 | 1% | 2,174,097,450,048,912,375,280,662 | exact | exact | 1,960,242,617,584,763 | exact | -1.9879% | -1.9900% | 285,607 / 179,800 |
| p356, the buy crosses an initialized tick | `0x780f875d65502fe694f37e9d511897556df153b5` | token0 | 0.01% | 1,995,804,832,070,193,977,260,966 | exact (1 tick) | n/a (two ranges) | 1,999,600,419,081,217 | exact | -0.0200% | -0.0200% | 333,010 / 183,755 |

Round 1's crowd pool `0x59a6ba5d...8ccf` and the sell-locked pool `0xa72dfd49...8e47` were pulled between the two rounds; both were run
again as pulled pools (below). Round 1's numbers on the pools still live are the same to the wei; the gas is about 44k higher per buy
and 40k per sell (the record's three storage slots).

- **Round trip = two fees.** At constant liquidity the buy's price impact is undone by the sell, so a round trip with nobody trading in
  between costs the two fees (1 - (1 - fee)^2) less a second-order term (+0.00002% to +0.004% at 0.002 ETH; +0.05% at 0.05 ETH and
  +0.5% at 1 ETH on the 1% pool). Price impact matters only through others' trades between our buy and our sell.
- **minOut needs a relative slack.** At 0.002 ETH the one-range math equals the pool to the wei on every pool above. Larger buys
  (0.05 ETH on the never-bought p356 pool; 0.2 and 1 ETH on it, on the crowd pool and on the 1% pool) cross tick-bitmap words (256
  ticks each); the pool computes one step per word and rounds each down, so the one-range math overshoots the real output by 6e-19 to
  9.5e-17 relative (4.5e9 raw units on a 4.8e25 output; QuoterV2 and the relay still agree to the unit). A few wei of slack is not
  enough on these tokens' scale: take minOut = math x (1 - slip) with any slip above 1e-12.
- **Failure paths, 21 per live pool, all as expected (86 of 86 in the automatic run, 94 of 94 on the given pools):**
  a stranger's buy, sell, `withdraw(0)` and `sweep(WETH, 0)`: `NotOwner()`; the callback called by a stranger: `NotPool(stranger)`; by
  the pool itself with no swap in progress: `NotPool(pool)`; by a stranger while a buy's record is set (state override): `NotPool(stranger)`;
  by the pool during a buy asking 1 wei over the recorded maximum: `Overpay(amountIn + 1, amountIn)`; by the pool during a buy, owed
  within the maximum, with `data` naming the token: it pays the recorded WETH (none there: `TransferFailed(WETH)`), not the token `data`
  names; the owner's buy while the record is set (re-entry): `Busy()`; the owner's sell with nothing to sell: `NothingToSell(token)`; a
  buy whose deadline is the block's second - 1: `TooLate(t, t-1)`; a buy, and a sell, with minOut one above the output:
  `TooLittleOut(out, out+1)`; a buy on a fee tier with no pool: `NoPool(the CREATE2 address)`; a buy of the relay's balance + 1 wei:
  `Insufficient(balance, balance+1)`; the owner's sweep of 1 wei of WETH with none there: `TransferFailed(WETH)`. Going through: a buy with
  the deadline equal to the block's second (same output), the owner's `withdraw(0)` and `sweep(WETH, 0)`, and a buy then
  `sweep(token, a third)` then `sweep(token, 0)` (the relay holds two thirds then 0; the owner gets a third then all, to the unit).
- **Pulled pools** (no liquidity anywhere): a buy with minOut 0 returns 0 tokens and the relay's ETH is back to the wei, no WETH left (the
  cut-short branch); with minOut 1: `TooLittleOut(0, 1)`. The swap walks every empty tick word to the price limit, and what that costs
  depends on the tick spacing: on the 0.01% pools (spacing 1) **30.8-31.7 million gas** (5 pools: `0x05f8cb3e`, `0x74b3a357` WETH token1,
  `0x59a6ba5d`, `0xa72dfd49`, `0x4a3748aa`); on a 1% pool (spacing 200, `0xeafa6cdf`) 330,341 gas inside the harness. The review
  measured 3.4M on a 0.05% pool and found the 0.3% and 1% walks cheap, where a pulled pool's sell with minOut 0 goes through for about
  0 ETH.
- **Gas limits (this build, round 2's numbers).** Buys of 0.002-0.004 ETH are 235k-286k as transactions, plus about 48k for each
  initialized tick the buy crosses (the tick-crossing pool's 0.002 ETH buy: 333k); a 0.05 ETH buy is up to 364k (230-286k on the pools
  above); sells 215k-273k as transactions on live pools, up to about 415k on a 1% pool (the review's round-2 measurements; the sim's
  sell figure above is the harness's inner gas plus the buy's overhead, a lower bound). **The engine's V3 legs use 500,000** for the buy
  and the sell, which covers these. Larger buys on the 0.01% pools need more: 0.2 ETH 348k, 1 ETH 658k (a buy) and about 591k (its
  sell) on the never-bought p356 pool; on the 1% pool 1 ETH is 293k. Set the limit from the size, never from a fresh eth_estimateGas (a pulled 0.01% pool would make it 31M; with a 500k limit
  such a buy runs out of gas and reverts for about 500k gas, 0.00001 ETH at 0.02 gwei).
- **A sell-locked token**: the pool `0xa72dfd49bb136834d2f70881a477abb22dc28e47`, whose token is `0x7399605a3b127dc670ab5dba91946dd55bfa1185`
  (round 1, while it was live): the buy went through and equalled QuoterV2 (107,193,561,789,085,926,109,185 tokens at block 86,595,250);
  the sell reverted `TransferFailed(0x7399605a...1185)`: the token refuses any transfer into its pool from an outside address (`verkoop
  vergrendeld`, Dutch for "sale locked"; also through SwapRouter02's `transferFrom`; still so with the clock moved 30 days on; still so
  now that the pool is pulled). The simulator names such pools and skips them. See section 3.

## 3. Found on the way (for the engine and the research, not the relay)

- **Sell-locked self-buyer tokens.** Of the 94 pools launched by a direct `createAndInitializePoolIfNecessary` (13ead562) in the 72 h to
  Oct 12 10:20 UTC, 12 tokens refuse a transfer into their pool from an outside address today (`salg spaerret`, `vente bloquée`,
  `verkoop vergrendeld`: one template in several languages). Among the 28 launches where the launch wallet made its own buy of 0.05 ETH
  (REPORT_S's line), **10 are locked**, including 4 of the last 8 (pools `0x12323d67`, `0x9c03d2d1`, `0x45eeecd3`, `0xa72dfd49`). In
  the pool `0xa72dfd49` (2 h old then: the launch wallet's own 0.05 ETH buy at + 24, then 695 swaps, 18.9 ETH in, 16.7 ETH out) every one
  of the 20 addresses that sold is among the 23 that bought (the eight most active sellers bought 23 times each): a fleet trading with
  itself. Whether the lock is on from the launch or switched on later is not known: the node keeps no state that old, and REPORT_S's one
  precedent (a sniper sold one block after the own buy on Oct 9) shows sells went through then. If it is on when our sell goes, the
  trade is -100% and the tokens stay in the relay. REPORT_S priced the ride's sells from the pool's events and did not test a transfer.
  Before any live trade on that line the engine needs a sell check on the armed pool (an eth_call of `token.transfer(pool, 0)` from an
  outside address, what `sell_lock` in `relay_v3_sim.py` does, or the relay's own sell simulated after its buy), and the research a
  look at when the lock goes on (a forward watch of the next launches: the transfer check every few blocks from the mint).
- **The p356 line's calldata grew.** Every `d27d1e00` launch of the 24 h to Oct 12 10:20 UTC goes to a launcher with the line's code
  keccak `89885b75`, but only 32 are 356 bytes, the last one at about Oct 11 19:55 UTC; from about 14:00 UTC that day the same launcher
  code also came with 420, 548, 612, 676, 996, 1124, 1636 and 1828 bytes, and since 19:55 only with those. The engine's p356 family pins
  `calldata_len` 356 (RUNBOOK 4g's object), so its dry run has not armed this line since Oct 11 about 19:55 UTC.

## 4. Deploy and fund (the owner, on the box)

Nothing to do until the engine has its V3 live path; the relay can be deployed before. The engine must be stopped for both (same wallet,
same nonce); the scripts refuse to run while `flip-engine` is active.

    cd ~/v2pons && git pull
    /opt/flip-venv/bin/python3 deploy/relay_v3_sim.py          # must end with "all as expected" (needs py-solc-x, as relay_sim.py)
    sudo systemctl stop flip-engine
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_v3_deploy.py --write-env
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py deposit_v3 0.005
    sudo /opt/flip-venv/bin/python3 ~/v2pons/deploy/relay_ops.py status
    sudo systemctl start flip-engine

`relay_v3_deploy.py` reads WALLET, PRIVATE_KEY and RPC_URL from `/etc/flip/engine.env` (the key is never printed; WALLET, a public
address, is). If the file already has a `RELAY_V3` that still holds ETH or WETH it refuses (empty it first with `withdraw_v3` and
`sweep_v3 WETH`, or pass `--force`). It refuses an artifact whose `source_sha256` is not the source's, checks the chain id, prints the
wallet's balance and the deployment's estimate (about 1.07M gas with the L1 component; at most about 0.00006 ETH at twice the current
0.02 gwei), asks for a typed `yes`, deploys with the wallet as `owner_`, waits for the receipt, compares the code on the chain byte for
byte with the artifact's runtime (the owner filled in), reads `owner()`, simulates a 0.0001 ETH buy through the new relay on the newest
live, not sell-locked V3 pool against QuoterV2, and prints two lines: `RELAY_V3=0x...` and `RELAY_V3_CODEHASH=0x...` (the keccak of
the deployed runtime), always before any write, so the operator has them even if the write fails. With `--write-env` it writes both into
the env file and keeps the previous `RELAY_V3` and `RELAY_V3_CODEHASH` lines as comments (`# previous RELAY_V3=0x...`). The rewrite works
on bytes: every other line is kept byte for byte (CRLF endings, control characters such as \x0b or \x1c inside a quoted value, non-UTF-8
bytes); only lines that start with `RELAY_V3=` or `RELAY_V3_CODEHASH=` change. It unlinks a stale `engine.env.tmp`, creates a fresh one
with `O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW` and mode 600, flushes and fsyncs it, renames it over the env file and fsyncs the directory; on
any error after the `.tmp` exists (a full disk, an I/O error, Ctrl-C) it unlinks the `.tmp`, which holds the key, and raises the error
again, the env file untouched. Only a `kill -9` between the create and the rename can leave the `.tmp` (mode 600, root's), and the next
run unlinks it. Without `--write-env`, add the two lines by hand.

`relay_ops.py`: `status` adds a line for the V3 relay when `RELAY_V3` is set (its ETH, any WETH, its owner against the wallet).
`deposit_v3 <eth>`, `withdraw_v3 [eth]` (no amount = all) and `sweep_v3 <token|WETH> [raw amount]` (the word WETH, any case, for WETH's
address; none = all; the amount in the token's
smallest units, for a token whose transfers are capped) first check the code at `RELAY_V3`: its keccak against `RELAY_V3_CODEHASH` when
the env file has that line (so a later recompile of the artifact never locks them out of the deployed relay), otherwise byte for byte
against the artifact's runtime for this wallet; then that its `owner()` is the wallet. `sweep_v3` refuses a token that is not a
0x-prefixed address (a mixed-case one must pass its checksum) or has no code on the chain, and an amount that is not a whole number of
raw units below 2**256 (ASCII digits only, at most 78 of them: no traceback on a huge input). `payout` refuses `RELAY_V3` as a destination as it refuses `RELAY`. The other commands are unchanged. Profit
leaves as for the v4 relay: `withdraw_v3`, then `payout`.

**Round 3 (scripts only; the contract and its artifact are as the final review passed them, 8801311):** `sweep_v3`'s argument checks;
`--write-env` keeps the previous `RELAY_V3` (and `RELAY_V3_CODEHASH`) as comments; `RELAY_V3_CODEHASH` written at the deployment and
checked by the `_v3` commands, with the byte-for-byte comparison as the fallback; the env file written through an exclusive, no-follow,
fsynced temporary file. Tested with a throwaway key and an RPC stub that intercepts every send: two deployments in a row over a stale
`.tmp` that was a symlink to another file (the symlink removed, its target untouched, mode 600, both previous lines commented), the
`_v3` commands with a matching, a wrong and a missing codehash (and with the artifact changed under them), and 14 `sweep_v3` argument
cases.

**Round 4 (scripts and docs only; contract and artifact unchanged):** the env rewrite on bytes; the `.tmp` unlinked on any error; the two
new lines printed before the write; `sweep_v3 WETH` and the amount's length bound. Tested with the review's suites (synthetic env files
with placeholder secrets; every RPC mocked or stubbed, every send intercepted): 39 of 39 env-file checks (byte preservation with LF and
CRLF, nine line-separator characters inside a value, a non-UTF-8 byte, empty and blank-line files, five kinds of stale `.tmp`, `kill -9`
at seven points, ENOSPC at fsync, an I/O error at the rename, Ctrl-C in the write), 84 of 84 ops and deploy checks (codehash forms, 33
`sweep_v3` argument cases, a deploy whose write fails after printing its lines), a 23-case byte matrix on `write_env` itself, and the
throwaway-key deploy and ops run of round 3 again.

## 5. For the engine (built: HANDOFF 16.22 on its branch)

- Buy: `a0328eb2` + token, fee, amountIn, minOut, deadline (5 words, 164 bytes). Sell: `13318338` + token, fee, minOut, deadline. Both to
  `RELAY_V3`, value 0 (the stake is the relay's ETH). The sell can be presigned at the buy's nonce + 1: it sells whatever the buy got.
- minOut: the buy's from the one-range math on the price copy less a relative slip (section 2: the math can overshoot by up to ~1e-16
  relative once the buy crosses a tick-bitmap word); the sell's from the expected ETH less the slip.
- Gas: the engine's V3 legs use 500,000 for the buy and the sell (section 2: buys 235k-364k, sells 215k-415k at the stakes in use), never
  a live estimate.
- A sell that reverts (`TooLittleOut`, a pull, a sell-locked token) leaves the tokens in the relay; the next `sell` of the same token sells
  them all, or the owner sweeps them (`relay_ops.py sweep_v3 0xTOKEN [raw amount]`).

## 6. Risks

- **The owner key is hot** (on the box): whoever holds it can withdraw everything; the relay adds no limit. Keep the stake small.
- **Sell-locked and taxed tokens.** A token can refuse the sell (section 3) or take a fee on transfer (the pool then reverts the sell:
  it checks its balance rose by what it asked). The relay cannot tell before the buy; the engine must check the token on the armed pool.
- **A pull between the buy and the sell**: on a 0.01% pool the sell walks the empty range (about 31M gas) and reverts out of gas under a
  sane limit; on 0.3%/1% pools it goes through for about 0 ETH (with minOut 0) or reverts `TooLittleOut`. Either way the tokens are worth
  nothing.
- **WETH is an upgradeable proxy** (implementation `0xc6b81b42...947e`, aeWETH-like, `withdraw` sends ETH by call): its admin could
  change it, as for every WETH user on the chain.
- **No price limit but minOut**: the swap runs to the extreme limit; a buy or sell signed with minOut 0 accepts any fill. The engine must
  always sign a real minOut and a real deadline.
- **Deadline 0 is not "none"**: a call with deadline 0 always reverts `TooLate`.
- **The CREATE2 check binds the relay to this factory and init code hash**: a pool of another V3 fork on the chain cannot be traded (by
  design); a wrong `fee` gives `NoPool` (or another pool of the same pair if that fee tier exists).
- **The simulator covers the paths listed above on live pools**, not every token behaviour (rebasing, blacklists, tokens that change
  `balanceOf` between calls); `sweep(token, amount)` is the way out for a token whose balance or transfers misbehave.
