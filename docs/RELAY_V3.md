# FlipRelayV3: the Uniswap V3 relay (HANDOFF 16.16, option (b))

The relay that trades the V3 lines (p356, the self-buyer, the 836-byte crowd) the way `FlipRelay` trades the v4 lines: the owner's
buy at nonce n, a presigned sell-everything at nonce n+1, no router, no approval, the stake kept in the contract. Nothing here is
deployed; the owner deploys it from the box (section 4). Built and simulated on Oct 12, 2026 (about 10:00 UTC); nothing was sent.

## 1. The contract (`contracts/FlipRelayV3.sol`, 125 lines, solc 0.8.26, optimizer 1000 runs, cancun)

| | |
|---|---|
| `constructor(address owner_)` | `owner` immutable (refuses address 0). `FACTORY` `0x1f7d7550...2efa`, `WETH` `0x0bd7d308...ad73`, `POOL_INIT_CODE_HASH` `e34f199b...8b54` are constants |
| `buy(token, fee, amountIn, minOut, deadline) -> out` `a0328eb2` | owner only; `block.timestamp <= deadline`; the pool is the factory's CREATE2 address for (WETH, token, fee), sorted as Uniswap does; no code there: `NoPool`; less ETH than `amountIn`: `Insufficient`; wraps `amountIn` (`WETH.deposit`), `pool.swap` exact-in WETH -> token with the price limit at `MIN_SQRT_RATIO + 1` (WETH token0) or `MAX_SQRT_RATIO - 1` (WETH token1); `out` = the relay's token balance after less before; `out < minOut`: `TooLittleOut`; the tokens stay in the relay. If the price limit cuts the fill short, the WETH the pool did not take is unwrapped back to ETH |
| `sell(token, fee, minOut, deadline) -> out` `13318338` | owner only; deadline; the relay's ENTIRE balance of `token` (0: `NothingToSell`), exact-in token -> WETH at the extreme limit; `out` = the WETH the pool sent; `out < minOut`: `TooLittleOut`; `WETH.withdraw(out)`; the ETH stays in the relay |
| `uniswapV3SwapCallback(d0, d1, data)` `fa461e33` | `msg.sender` must equal the storage slot `swapping` (the pool of the swap in progress, set in `buy`/`sell` just before `pool.swap`, cleared just after; 0 at any other time): else `NotPool`. Pays the positive delta with a plain `transfer` of the token named in `data` (WETH on a buy, the token on a sell, encoded by the relay itself) |
| `withdraw(amount)` `2e1a7d4d`, `sweep(token)` `01681a62` | owner only; ETH (0 = all) or all of a token (WETH included) to the owner |
| `receive()` | open (WETH's `withdraw` sends ETH in) |
| views | `owner()`, `WETH()`, `FACTORY()`, `POOL_INIT_CODE_HASH()` |

The guard: `buy`/`sell` revert `Busy` while `swapping` is set. No delegatecall, no call to an address the caller chooses except
the token itself (`balanceOf`, `transfer`) and the CREATE2 pool; ERC20 transfers are low-level calls that accept an empty return and
refuse `false` or a revert (`TransferFailed`). Errors: `NotOwner` 30cd7471, `NotPool(address)` 4a1576a2, `Busy` 3ef33375,
`TooLate(uint256,uint256)` 388b0173, `NoPool(address)` d0dc3f10, `Insufficient(uint256,uint256)` e8620800, `NothingToSell(address)`
cb72d3db, `TooLittleOut(uint256,uint256)` e20a4c5d (the same as FlipRelay's), `TransferFailed(address)` 39f1c8d9.

**Differences from FlipRelay (v4) the engine must know:**
- The owner is the constructor's argument (v4: the deployer).
- `deadline` is strict: `block.timestamp <= deadline`, and 0 is in the past (v4: 0 = no deadline). Sign every buy and sell with a real
  deadline.
- The pool is named by `(token, fee)`, not a PoolKey; WETH may be token0 or token1, the contract sorts.
- The relay holds ETH only between trades: WETH is wrapped inside a buy and unwrapped inside a sell (and after a cut-short buy).

`contracts/compile.py FlipRelayV3` writes `contracts/FlipRelayV3.json` (abi, bytecode, runtime 4,464 bytes, one immutable reference:
`owner`, selectors, source sha256 `6228a0a22856...`). `contracts/compile.py` with no argument still builds `FlipRelay.json` byte for byte
as before (checked: the file is unchanged).

## 2. The simulator (`deploy/relay_v3_sim.py`, `contracts/RoundTripHarnessV3.sol`)

eth_call with state overrides on the public RPC: the relay's runtime code (owner = the harness's address) at `0xf3f3...` with 0.01 ETH,
the harness (test only, never deployed) at `0xa3a3...`. In one call on one block's state the harness takes QuoterV2's quote, buys 0.002
ETH, reads the relay's balance, takes QuoterV2's quote of the sell, sells everything and requires: the relay's ETH down by exactly
`amountIn` after the buy, up by exactly the sell's `out` after it, no token and no WETH left. Python recomputes both legs with the exact
V3 swap math (SqrtPriceMath, one range) from the pool's slot0 and liquidity as the harness read them. Then the failure paths, each with
its exact expected error and arguments, and the owner's calls that must go through.

QuoterV2 on Robinhood Chain: `0x33e885ed0ec9bf04ecfb19341582aadcb4c8a9e7` (found from the V3 factory's deployer `0x9701fb0a...3a52`: the
factory is its nonce 2, the PositionManager nonce 11, SwapRouter02 nonce 18, QuoterV2 nonce 6; its `factory()` and `WETH9()` are ours).

    python3 deploy/relay_v3_sim.py                       # the newest live pool of each line in the last 24 h, one with WETH as token1, one pulled
    python3 deploy/relay_v3_sim.py 0xPOOL [0xPOOL ...]   # given pools; --eth 0.005 for another size

### Results (Oct 12 about 10:18 UTC, blocks 86,597,371-86,597,527; 0.002 ETH)

| line | pool | WETH | fee | buy: tokens out | = QuoterV2 | = one-range math | sell: wei back | = QuoterV2 | round trip | 2 fees | gas buy tx / sell tx |
|---|---|---|---|---|---|---|---|---|---|---|---|
| p356 (356 B, launcher code 89885b75, launched 15 h before, never bought) | `0x26c29066e33f97d67f158463b5e9201a3733529c` | token0 | 0.01% | 1,995,803,888,074,217,441,493,979 | exact | exact | 1,999,600,419,081,123 | exact | -0.0200% | -0.0200% | 191,657 / ~124,000 |
| self-buyer (13ead562, launched 8 h before; no own buy by its wallet) | `0x5f224e675cbe6845cb37545bb7a248795da1b03a` | token0 | 1% | 3,549,911,499,662,906,957,259,727 | exact | exact | 1,960,277,320,457,562 | exact | -1.9861% | -1.9900% | 208,805 / ~123,700 |
| crowd (836 B, launched 1.5 h before) | `0x59a6ba5ded94e86c598ff92390230f8355af8ccf` | token0 | 0.01% | 68,731,172,366,057,253,383,169 | exact | exact | 1,999,600,056,169,245 | exact | -0.0200% | -0.0200% | 191,726 / ~123,700 |
| WETH as token1 (launcher 0x2b933199, 772 B) | `0x0d2cfcb4d89a1b363840d09c33077c0d69606444` | token1 | 1% | 2,174,097,450,048,912,375,280,662 | exact | exact | 1,960,242,617,584,763 | exact | -1.9879% | -1.9900% | 242,477 / ~140,900 |
| p356, the buy crosses an initialized tick (given by hand, block 86,595,198) | `0x780f875d65502fe694f37e9d511897556df153b5` | token0 | 0.01% | 1,995,804,832,070,193,977,260,966 | exact (1 tick crossed) | n/a (two ranges) | 1,999,600,419,081,217 | exact | -0.0200% | -0.0200% | 284,096 / ~139,100 |

- **Round trip = two fees.** At constant liquidity the buy's price impact is undone by the sell, so a round trip with nobody trading in
  between costs the two fees (1 - (1 - fee)^2) less a second-order term (+0.00002% to +0.004% here: the price ends at 0.99996 to
  1.00002 of its start). Price impact matters only through others' trades between our buy and our sell.
- **Gas.** The buy transaction is eth_estimateGas from the owner on the same state (it includes the chain's L1 component). The sell
  cannot be estimated on that state alone (the buy is not in it), so it is the sell's gas inside the harness plus the buy's transaction
  overhead. A gas limit of 400,000 for each covers every case seen with room; do not use a fresh eth_estimateGas as the limit (see the
  pulled pool below).
- **The failure paths, on each of the four pools, all as expected (68 of 68; 17 of 17 on the tick-crossing pool):** a stranger's buy, sell, withdraw(0) and sweep(WETH):
  `NotOwner()`; the callback called by a stranger: `NotPool(stranger)`; by the pool itself with no swap in progress: `NotPool(pool)`; by a
  stranger while the slot holds the pool (set by state override): `NotPool(stranger)`; the owner's buy while the slot is set (re-entry):
  `Busy()`; the owner's sell with nothing to sell: `NothingToSell(token)`; a buy whose deadline is the block's second - 1:
  `TooLate(t, t-1)`; a buy with minOut one above its output: `TooLittleOut(out, out+1)`; a sell with minOut one above its output:
  `TooLittleOut(out, out+1)`; a buy on a fee tier with no pool: `NoPool(the CREATE2 address)`; a buy of the relay's balance + 1 wei:
  `Insufficient(balance, balance+1)`. And going through: a buy with the deadline equal to the block's second (same output), the owner's
  `withdraw(0)`, the owner's `sweep(WETH)` with nothing there.
- **A pulled pool** (no liquidity anywhere; `0x05f8cb3e...d408`, WETH token0, and `0x74b3a357...ec50`, WETH token1): a buy with minOut 0
  returns 0 tokens and the relay's ETH is back to the wei, no WETH left (the cut-short branch); with minOut 1: `TooLittleOut(0, 1)`. But
  the swap walks every empty tick word to the price limit: **30.8-31.6 million gas**. A transaction with a 400k limit runs out of gas and
  reverts (cost: 400k gas, about 0.000008 ETH at 0.02 gwei); one with an estimated limit would pay the 31M.
- **A sell-locked token** (`0xa72dfd49...8e47`, the newest live self-buyer pool and the only live one with the wallet's own 0.05 ETH buy):
  the buy goes through and equals QuoterV2 (107,193,561,789,085,926,109,185 tokens at block 86,595,250); the sell
  reverts `TransferFailed(token)`: the token itself refuses any transfer into its pool from an outside address (`verkoop vergrendeld`,
  Dutch for "sale locked"; also through SwapRouter02's `transferFrom`; still so with the clock moved 30 days on). The simulator names
  such pools and skips them. See section 3.

## 3. Found on the way (for the engine and the research, not the relay)

- **Sell-locked self-buyer tokens.** Of the 94 pools launched by a direct `createAndInitializePoolIfNecessary` (13ead562) in the 72 h to
  Oct 12 10:20 UTC, 12 tokens refuse a transfer into their pool from an outside address today (`salg spaerret`, `vente bloquée`,
  `verkoop vergrendeld`: one template in several languages). Among the 28 launches where the launch wallet made its own buy of 0.05 ETH
  (REPORT_S's line), **10 are locked**, including 4 of the last 8 (`0x12323d67`, `0x9c03d2d1`, `0x45eeecd3`, `0xa72dfd49`). In
  `0xa72dfd49` (2 h old: the launch wallet's own 0.05 ETH buy at + 24, then 695 swaps, 18.9 ETH in, 16.7 ETH out) every one of the 20
  addresses that sold is among the 23 that bought (the eight most active sellers bought 23 times each): a fleet trading with itself.
  Whether the lock is on from the launch or switched on later is not known: the node keeps no state that old, and REPORT_S's one
  precedent (a sniper sold one block after the own buy on Oct 9) shows sells went through then. If it is on when our sell goes, the
  trade is -100% and the tokens stay in the relay. REPORT_S priced the ride's sells from the pool's events and did not test a transfer.
  Before any live trade on that line the engine needs a sell check on the armed pool (an eth_call of `token.transfer(pool, 0)` from an
  outside address, what `sell_lock` in `relay_v3_sim.py` does, or the relay's own sell simulated after its buy), and the research a
  look at when the lock goes on (a forward watch of the next launches: the transfer check every few blocks from the mint).
- **The p356 line's calldata grew.** Every `d27d1e00` launch of the last 24 h goes to a launcher with the line's code keccak `89885b75`,
  but only 32 are 356 bytes, the last one at about Oct 11 19:55 UTC; from about 14:00 UTC that day the same launcher code also came
  with 420, 548, 612, 676, 996, 1124, 1636 and 1828 bytes, and since 19:55 only with those (the last 3 hours: 996 and 1828 only). The
  engine's p356 family pins `calldata_len` 356 (RUNBOOK 4g's object), so its dry run has not armed this line since Oct 11 about
  19:55 UTC.

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

`relay_v3_deploy.py` reads WALLET, PRIVATE_KEY and RPC_URL from `/etc/flip/engine.env` (prints none of them), refuses an artifact whose
`source_sha256` is not the source's, checks the chain id, prints the wallet's balance and the deployment's estimate (about 1.03M gas with
the L1 component; at most about 0.00006 ETH at twice the current 0.02 gwei), asks for a typed `yes`, deploys with the wallet as `owner_`,
waits for the receipt, compares the code on the chain byte for byte with the artifact's runtime (the owner filled in), reads `owner()`,
simulates a 0.0001 ETH buy through the new relay on the newest live, not sell-locked V3 pool against QuoterV2, and prints the line
`RELAY_V3=0x...` (written into the env file, mode 600 kept, with `--write-env`). Without `--write-env`, add that line by hand.

`relay_ops.py`: `status` adds a line for the V3 relay when `RELAY_V3` is set (its ETH, any WETH, its owner against the wallet);
`deposit_v3 <eth>`, `withdraw_v3 [eth]` (no amount = all) and `sweep_v3 <token>` (a token or WETH left in it) check first that
`RELAY_V3` is a contract whose `owner()` is the wallet. The existing commands are unchanged. Profit leaves as for the v4 relay:
`withdraw_v3`, then `payout`.

## 5. For the engine (not built here)

- Buy: `a0328eb2` + token, fee, amountIn, minOut, deadline (5 words, 164 bytes). Sell: `13318338` + token, fee, minOut, deadline. Both to
  `RELAY_V3`, value 0 (the stake is the relay's ETH). The sell can be presigned at the buy's nonce + 1: it sells whatever the buy got.
- minOut: the buy's from the one-range math on the price copy (exact on all four pools); the sell's from the expected ETH less the slip.
- Fixed gas limits (400k each), never a live estimate (a pulled pool costs 31M gas to walk).
- A sell that reverts (`TooLittleOut`, a pull, a sell-locked token) leaves the tokens in the relay; the next `sell` of the same token sells
  them all, or the owner sweeps them (`relay_ops.py sweep_v3 0xTOKEN`).

## 6. Risks

- **The owner key is hot** (on the box): whoever holds it can withdraw everything; the relay adds no limit. Keep the stake small.
- **Sell-locked and taxed tokens.** A token can refuse the sell (section 3) or take a fee on transfer (the pool then reverts the sell:
  it checks its balance rose by what it asked). The relay cannot tell before the buy; the engine must check the token on the armed pool.
- **A pull between the buy and the sell** leaves the sell with no WETH to take: with a 400k limit it reverts out of gas; the tokens stay
  (worth nothing).
- **WETH is an upgradeable proxy** (implementation `0xc6b81b42...947e`, aeWETH-like, `withdraw` sends ETH by call): its admin could
  change it, as for every WETH user on the chain.
- **No price limit but minOut**: the swap runs to the extreme limit; a buy or sell signed with minOut 0 accepts any fill. The engine must
  always sign a real minOut and a real deadline.
- **Deadline 0 is not "none"**: a call with deadline 0 always reverts `TooLate`.
- **The CREATE2 check binds the relay to this factory and init code hash**: a pool of another V3 fork on the chain cannot be traded (by
  design); a wrong `fee` gives `NoPool` (or another pool of the same pair if that fee tier exists).
- **Not reviewed by a second party yet**; the simulator covers the paths listed above on live pools, not every token behaviour (rebasing,
  blacklists, tokens that change `balanceOf` between calls).
