# Prompt for a new session: re-track the operator across all its lines

Paste everything below the line as the first message of a new Claude Code session on this repository (`v2pons`). It is
self-contained. Its job is to find where the operator is trading now, across every chain and line it has used, and to say
which (if any) is tradable again. It is read-only research until the owner decides to point an engine at a line.

---

You are picking up a cross-chain tracking job on the repository `v2pons`. One operator (called "the 2.433 line") runs a
pump-and-pull on Uniswap v4: it launches a token pool, adds liquidity, its own bot and a fleet of ~30 wallets buy, then it
removes the liquidity minutes later. We trade in front of its bot: buy right after the liquidity add, sell into the bot's
buy. The operator keeps moving chains and changing its launch fingerprint to shake off snipers like us. Your task is to
re-track it: find where it is launching now, whether the line is sellable, and report. Do not point any engine at a new line
without the owner's say-so. The repository is large; read only what is named here.

## Every line we have traded or tracked

| line | chain | what it is | engine / status |
|---|---|---|---|
| **follow** (operator A, launcher `0x3194e326`, call `0x2fcb9108`) | Robinhood | a separate operator; buy after its first crowd buy, sell on the next | `src/flip_engine.py` strategy `follow`, service `flip-engine`. Operator paused around Oct 12. |
| **front / the 2.433 line** (the volume bot) | Robinhood | launches of 2.4333285 ETH through the PositionManager; our best earner (+$700 by Oct 10) | `src/flip_engine.py` strategy `front`, service `flip-engine`. The operator left Robinhood Oct 12. |
| V3 families **v3crowd**, **c1**, **p356** | Robinhood | the volume bot's other shapes, traded through a V3 relay (`RELAY_V3`) | `flip_engine.py` `FRONT_FAMILIES`; probes, mostly dry. See `docs/HANDOFF.md` 16.16-16.18, 16.22. |
| the **BNB line** | BNB Chain | the 2.433 operator's 52-pool run of Oct 13 | `src/bnb_engine.py` / `bnb_live.py`, service `flip-bnb`. **A honeypot** (`research/session_oct14/bnbfreeze/`): stopped and disabled Oct 14. |
| the **Base line** | Base | where the 2.433 operator went on Oct 14 | `src/base_engine.py`, service `flip-base`. See `docs/BASE_PROMPT.md` and `docs/BASE_HANDOFF.md`. |

Lines checked and rejected (keep as negatives, do not re-trade without a fresh exit test): `flapv7` (BNB, edge gone),
`selfbuyer` (V3, half the pools sell-locked), `pm500` (wash-volume honeypot). Reports under `research/session_oct14/`.

## The 2.433 operator's path (this is the line worth the most)

Robinhood (until Oct 12) → cashed out Oct 12 (its hub `0x6c3bd8f6` bridged 9.3 ETH to Ethereum) → one test launch on
Ethereum Oct 12 → BNB Chain, 52 pools, Oct 13 → Base, live from Oct 14. The full trail is
`research/session_oct14/find2433/REPORT_FIND2433.md` and `research/session_oct14/base2433/REPORT_BASE2433.md`.

On Base the launch fingerprint changed three times: launcher code `225f9af97d88` (launch call `c3e0ff3d`), then
`53959585f666` (call `99dfa5c4`, from Oct 14 19:42 UTC), then `aee87105d146` (from Oct 15 07:16 UTC). **The third is a
honeypot**: its hook reverts every sell except from the operator's own wallets. The sellable token code is
`63ad5291cdef5d...`, the line's hook is 8,951 B, the honeypot hook is 8,957 B. The Base engine now carries both sellable
launchers and skips the honeypot (`BASE_LAUNCH_SELECTOR`, `BASE_LAUNCHER_CODEHASH_PREFIX`, `BASE_HOOK_CODE_SIZES`).

## The re-track tool

`research/session_oct14/watch/track_2433_xchain.py` reads the nonces and balances of the operator's known wallets on BNB,
Ethereum, Base, HyperEVM and Robinhood, compares them with the last run (`track_2433_xchain.json`) and prints what moved. A
rising nonce on its **buyer wallets** or a **launch collector emptying its balance** means the line is trading there again.
The keys it watches (from `REPORT_FIND2433.md`): admins `0x0152c954` and `0x5b2b20e1`, hub `0x6c3bd8f6`, next-launch
`0x8b499c5a`, consolidation `0x31c8cf1c` (Binance-bound), the 31 bot-buyer wallets, the 52 BNB launch wallets, the Base
collector `0x8f79d153`, the 3 Base launch wallets.

It reads through `research/session_oct14/find2433/skeptic/xr.py` (public endpoints, read-only). **From a cloud session,
`xr.py`'s `urllib` transport gets HTTP 403 through the proxy; replace `xr._post` with a `curl` transport** (curl reaches the
endpoints). On the box it runs as-is. publicnode serves only recent logs/receipts and refuses older blocks with "Archive
requests require a personal token".

## How to re-track, step by step

1. **Run the tracker.** See which chains show movement on the buyer wallets or the collector since the last run. That tells
   you which chain to look at, not whether the line is sellable.
2. **Scan that chain for the operator's live pools.** On Base: the last ~1,000 blocks of the PoolManager's `Initialize` with
   currency0 = ETH, fee 5000, tick spacing 100, token code `63ad5291cdef5d...`. Read the launcher's code hash and the hook's
   code size on each. Templates: the `b*` scripts in `research/session_oct14/base2433/`. On another chain, find the
   PoolManager and the operator's fingerprint first (the reports show how it was done for BNB and Ethereum).
3. **Run the exit test on a live pool**, between its liquidity add and its pull: `deploy/base_relay_sim.py <poolId>` on the
   box, or the same `eth_call` round trip from your session. **A sell that gets ETH back = sellable. A revert (`0x90bfb865`)
   = honeypot: do not trade it, and do not try to get around the hook.** Chain measurement of the token, add, bot and pull is
   not enough; the honeypot matched all of them and only a simulated sell revealed it.
4. **Report to the owner**: which chain and launcher is live, whether it is sellable, the pool size and the bot's timing, and
   your recommendation. If it is a known sellable Base launcher, the running engine trades it already with no change. If it is
   a new sellable fingerprint, say exactly which setting to add (and give the owner the box command). If it is a honeypot or
   a non-line, say so and stop.

## The box and the services

The owner runs the engines on their own AWS box and pastes commands in and output back; you cannot reach the box. Three
services: `flip-engine` (Robinhood, follow + front), `flip-bnb` (stopped and disabled since Oct 14), `flip-base` (Base, live,
branch `claude/brave-gauss-55iyg8`, release `base-0.2`). The Base wallet is `0x492a40b43ce221ec2c952cda473f441e365dea62` and
its relay `0x0e24493c662e62b33d371376e0ac181eb193a31d`. Each engine's state is its `results.py`
(`sudo python3 ~/v2pons/deploy/base_results.py` for Base). Start there to see what each is doing now.

## As of the last look (Oct 20 ~11:08 UTC)

The tracker showed the operator alive and concentrated on Base: the Base collector `0x8f79d153` had emptied its 8.46 ETH and
the Base buyer wallets had risen ~15k nonces since Oct 14; BNB buyer wallets also moved; Robinhood was dead. A one-hour Base
scan found no operator pool of the known shape, so it had either paused or changed its pool shape again. Re-run the tracker
and a wider Base scan to pick up from here. The Base engine was idle and safe (skipping the honeypot), relay ~0.045 ETH; the
owner had taken $500 out to their own address.

## Rules

- Read-only until the owner decides. Point an engine at a line only on the owner's word.
- **Never trade a pool whose exit test fails, and never try to defeat a hook that blocks sells.** Sit it out; wait for a
  sellable line, or let the owner pick a different one.
- Never print, paste or commit any private key.
- Run `python3 tests/test_base_engine.py` before any push that changes engine code.
- Save every chain read under `research/` beside the existing scripts, so the next session can repeat it.
