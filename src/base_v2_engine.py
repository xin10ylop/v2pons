#!/usr/bin/env python3
"""base_v2_engine: the seat on the V2 pump-and-pull line on Base (docs/BASE_V2.md, the design; release base-v2-0.1). A separate service
beside src/base_engine.py (the v4 line's front), whose feeds, transport and conventions it keeps and whose code it copies, never imports.

The line (measured Oct 15-20, 2026, 749 pairs; tests/data/base_v2_pair.json is one real 15 ETH pair's whole event stream): a hub funds a
fresh wallet with exactly the tier plus gas; at nonce 0 the wallet creates the token by plain CREATE (3,553 B of runtime, 5.6e27 supply,
no tax: the token's address is keccak(rlp([creator, 0]))[12:]); at nonce 1 it approves the router; at nonce 2, block N, it calls the
Uniswap V2 router's addLiquidityETH (f305d719) with msg.value the tier (1.2, 1.4-2.2, 13.79, 15.0, 17.79 ETH) and the whole supply on the
1.2-2.2 tiers: the factory's PairCreated, then the pair's Transfer, Sync and Mint in one receipt. A probe (0xe71a69f4..., legacy, 0.012
gwei) buys 0.000003 ETH inside the creation block on 414 of 742 pairs and never triggers anything. A fleet of about 143 wallets (type-2,
a 0.001 gwei tip, 7ff36ab5 / b6f9de95 straight to the router) buys dust at +2 and real amounts from +8; on the 1.4-2.2 tier it buys 30-40%
of the pool over 5-10 minutes and the price is +13% at +60, +34% at +180; it barely sells. The pull, removeLiquidityETH (02751cec) from
the creator, is a Burn on the pair on a per-tier schedule (1.4-2.2: +198 at the earliest on Oct 20, median +217-540). On the 1.2, 13.79,
15.0 and 17.79 tiers every non-fleet buy, dust included, is followed by the pull 2-8 blocks later (-60% to -100% for the buyer); on the
1.4-2.2 tier about 40 outsider buys drew no reaction. The paper seat (0.1 ETH at N+1, out at +180): +28.8% mean, 96% win, 9 of 219 pulled.

THE TRADE, on the tolerant tier only (BASE_V2_TIER_BAND, 1.3-2.3 ETH by default; BASE_V2_TIER_EXCLUDE never). THE CREATION is seen pending in a
Flashblock (a raw transaction to BASE_V2_ROUTER with BASE_V2_CREATE_SELECTOR; the sender recovered, its nonce BASE_V2_CREATOR_NONCE, the token
in the calldata equal to keccak(rlp([sender, 0]))[12:]; the pair's address by CREATE2 from the factory; the Mint's reserves are msg.value and
amountTokenDesired, which a fresh pair takes whole) or confirmed (PairCreated on BASE_V2_FACTORY with BASE_V2_WETH on either side; the creation
transaction and its receipt read for the same shape and the Mint): one `creation` line with its class, tradable (the value in the band) or
watched (any other value), a shape mismatch one `skip`. Every pair of the line, tradable or watched, is followed (its logs subscribed) to its
Burn or BASE_V2_WATCH_BLOCKS: their `outsider_buy` and `pull` lines are the data the tiers are re-qualified from, by the owner, never by the
engine. THE GUARD, before any buy, in the dry run too: in the pending window (the token exists blocks before N) eth_getCode(token)'s size in
BASE_V2_TOKEN_CODE_SIZES and totalSupply() so that the pool holds >= BASE_V2_MIN_SUPPLY_IN_POOL of it; once N is sealed, the exit test:
contracts/V2RoundTrip.sol's runtime placed by a state override at 0xa2..a2 with twice the stake, roundTrip(router, weth, token, stake, true)
by eth_call at block N on BASE_V2_ARCHIVE_URL and BASE_V2_READ_ALT_URL at once (an endpoint without N yet is asked again every 100 ms; the
first verdict counts), exactly as deploy/base_v2_sim.py does: refused unless the tokens bought equal the constant-product expectation from
the reserves at N (a buy tax) and the ETH back is >= BASE_V2_EXIT_MIN of the quote (a sell tax); a reverted sell is a honeypot; one `guard`
line. THE ARM reads the pair's logs at block N once (eth_getLogs): the creation block's own swaps are the probe's; anyone else's is an
outsider before our fire, which skips the pair. THE FIRE, aimed at N+1 (the fleet's dust comes at +2): FlipRelayV2.buy(token, stake, minOut,
deadline) with stake = min(BASE_V2_STAKE_ETH, BASE_V2_STAKE_CAP_ETH, BASE_V2_SHARE_CAP x the ETH reserve), minOut = the constant-product
output on the Mint's reserves x (1 - BASE_V2_BUY_SLIP), a type-2 transaction at BASE_V2_PRIO_GWEI, maxFee 2 x the base fee + the priority
(at most BASE_V2_MAX_FEE_GWEI), at the wallet's next nonce, to every BASE_V2_SEND_URLS at once; refused (a `skip` line) once the confirmed
head is at N + BASE_V2_LAND_MAX, on a pull or an outsider before ours, at BASE_V2_MAX_POSITIONS open, halted, stopped (the day, or the tier for
the day), at BASE_V2_MAX_PER_DAY, or with the relay under the stake + BASE_V2_RELAY_MARGIN_ETH beyond the open positions' stakes. With
BASE_V2_BACKRUN=1 the guard runs at the `pending` tag on BASE_V2_PENDING_URL as soon as the creation is seen and the buy goes into the creation
block itself, above the creation's priority (off by default). THE SELL, FlipRelayV2.sell(token, minOut, deadline), everything the relay holds,
on the first of: an outsider's buy (pending: a transaction carrying our token with value > 0 whose sender is not in the roster, not the probe,
not the creator, not our wallet; confirmed: a Swap with ETH in >= BASE_V2_OUTSIDER_MIN_ETH whose `to` is none of those and not the relay;
`exit: outsider`, minOut 0, at once); the reserves after a Sync valuing the position at >= the stake x (1 + BASE_V2_TAKE_PROFIT)
(`take_profit`, minOut = the output x (1 - BASE_V2_SELL_SLIP)); the fleet's first sell on our pair (`fleet_sell`, the same minOut); the head at
N + BASE_V2_SELL_SEND_BLOCK (`hard`, minOut 0), sent again at the same nonce with twice the priority when unseen by N + BASE_V2_SELL_RESEND_BLOCK,
and from the wall clock at the creation block's timestamp + BASE_V2_SELL_FALLBACK_S when no head came; a Burn on our pair, or the creator's
pending pull carrying our token, before our sell (`pulled`: -100%; the sell at minOut 0 still goes once, a partial pull would strand the
tokens). A position is never held past N + BASE_V2_HARD_BLOCK. A sell that reverted or was refused on a pair not pulled is sent again at the
next nonce with minOut 0, twice at most, then the line halts (sold none); a buy that filled with no tokens halts the same way. THE SETTLEMENT
from the receipts: the stake in, the tokens from the token's Transfer to the relay, the ETH out from our sell's Swap, the gas of both (gasUsed
x effectiveGasPrice + l1Fee), the return, the pull's block against our sell's, the first outsider's block, the fleet's ETH behind us: one
`trade_done`. Up to BASE_V2_MAX_POSITIONS positions at once, one per pair, one wallet, one nonce counter (the trader thread is the only
signer; it signs at the send, re-reads the nonce on "nonce too low"); the open positions are in base_v2_positions.json beside the log and
taken back at a start (sold at once).

THE HALTS (HALTED.base_v2 beside the log, held across restarts until the owner removes it; no new buy, the open positions still sold; the dry
run halts in memory): a Burn on a pair of ours before our sell, or within BASE_V2_REACT_BLOCKS after our buy even when our sell landed first,
when no outsider bought before it (we were the trigger); BASE_V2_LOSS_STREAK_HALT live losses in a row; BASE_V2_LATE_HALT live buys mined past
N + LAND_MAX; sold none twice, or a buy that filled with no tokens. THE TIER ENDED FOR THE DAY (`stop`, what: tier; cleared at 00:00 UTC): a
Burn earlier than BASE_V2_SCHEDULE_MIN on any pair of the tier, a Burn within REACT_BLOCKS after an outsider's buy on any pair of the tier, or
a sell taking >= BASE_V2_PULL_SHARE of the ETH reserve on any pair of the tier. THE DAY STOPPED (`stop`, what: day): the live net P&L at
-BASE_V2_DAILY_STOP_ETH, or BASE_V2_MAX_PER_DAY buys; both restored from the log's own lines at a restart.

THE DRY RUN (BASE_V2_DRY_RUN=1, the default): everything but sign and send, the guard included; no key is read. A dry buy is priced on the
reserves at the end of block N+1 as recorded, under its minOut it reverts; our own impact is applied to every later Sync for the valuation,
and the sell rules run on the recorded events; the dry sell is priced at the recorded reserves at the end of the block behind its trigger
(a Burn there first: pulled). Gas: DRY_GAS_UNITS x (the base fee + the priority) + L1_FEE_EST_WEI. `would_fire`, `sell_sent` and `trade_done`
carry dry: true; `ready_ms` is measured as live.

THE FEEDS. Confirmed, required: one websocket (BASE_V2_WS_URL): eth_subscribe newHeads (the clock), logs on the factory (PairCreated), and
one logs subscription per followed pair ([Mint, Burn, Swap, Sync]), unsubscribed at its Burn or WATCH_BLOCKS; logs deduped by (blockHash,
logIndex), a removed log's effect dropped; a pair's reserves are folded from its events in (block, logIndex) order (the last Sync is exact).
Silent for BASE_V2_WS_SILENT_S: the poller reads eth_getBlockByNumber("latest") and eth_getLogs (the factory and the followed pairs) one block
behind the head over BASE_V2_RPC_URL for every block missed (the start reads 12 blocks back) and the websocket reconnects, its gap read whole.
Flashblocks, optional (BASE_V2_FLASH_URL; 0 = off): brotli JSON every 200 ms; the raw transactions carrying the create selector or a followed
token are decoded (types 0, 1, 2, 4; 0x7e deposits skipped), their senders recovered only when they match; silent for 10 s: reconnected. It
advances the creation, an outsider's or the creator's pull transaction and our own transactions' inclusion; everything it does the confirmed
feed does a little later. Sends: BASE_V2_SEND_URLS at once over warm connections with the browser User-Agent (the sequencer's Cloudflare
refuses Python's); the first "ok" or "already known" counts; "nonce too low" everywhere re-reads the nonce and signs once more. Reads:
BASE_V2_RPC_URL, BASE_V2_READ_ALT_URL once when it fails; the guard's reads on BASE_V2_ARCHIVE_URL (single requests, only its host logged)
and BASE_V2_READ_ALT_URL. The roster (BASE_V2_ROSTER_FILE, {"built", "wallets"}, written daily by deploy/base_v2_roster.py) is read at the
start and when its mtime changes, never added to; a live start refuses without it. Threads: the asyncio loop (both websockets, the 1 s
ticker); the poller; one guard thread per tradable pair; the trader (the only signer); one settlement per position; one lock on the state.

SETTINGS from the environment (/etc/flip/base_v2.env; docs/BASE_V2.md section 5): each checked at the start, a wrong one stops it by name; ETH
and gwei amounts become exact integer wei (decimal text, never a float). A live start needs BASE_V2_WALLET, its key in BASE_V2_KEY_FILE
(flock'ed while the engine runs: with the Base engine's key file a live start while that engine is live is refused), BASE_V2_RELAY with owner()
the wallet and router()/weth() the settings, the roster file, chain 8453 on every endpoint, and the guard's self-test (the exit test on the
newest pair of the line answering SELLABLE on BASE_V2_ARCHIVE_URL).

LOG: JSONL (BASE_V2_LOG_PATH), "ev" and "t": start, flow (every 60 s), creation, arm, skip, guard, fire / would_fire, buy_sent, sell_sent,
outsider_buy, pull, trade_done, halt, stop, alarm (one a key every 10 min at most). No key, no URL beyond its host.
    python3 src/base_v2_engine.py                                      # from the environment (dry unless BASE_V2_DRY_RUN=0)
    BASE_V2_LOG_PATH=/tmp/base_v2.jsonl python3 src/base_v2_engine.py  # a dry run anywhere
"""
import os, sys, json, time, ssl, socket, queue, types, fcntl, asyncio, decimal, datetime, threading, traceback, signal, collections
import urllib.request, urllib.parse, urllib.error, http.client
import rlp
from eth_utils import keccak, to_checksum_address

RELEASE = "base-v2-0.1"
CHAIN_ID = 8453
T_PC = "0x" + keccak(text="PairCreated(address,address,address,uint256)").hex()
T_MINT = "0x" + keccak(text="Mint(address,uint256,uint256)").hex()
T_BURN = "0x" + keccak(text="Burn(address,uint256,uint256,address)").hex()
T_SWAP = "0x" + keccak(text="Swap(address,uint256,uint256,uint256,uint256,address)").hex()
T_SYNC = "0x" + keccak(text="Sync(uint112,uint112)").hex()
T_TRANSFER = "0x" + keccak(text="Transfer(address,address,uint256)").hex()
PAIR_TOPICS = [T_MINT, T_BURN, T_SWAP, T_SYNC]
SEL_BUY, SEL_SELL, SEL_OWNER, SEL_ROUTER, SEL_WETH = "1622dbe4", "6a272462", "8da5cb5b", "f887ea40", "3fc8cef3"    # contracts/FlipRelayV2.json
SEL_TOTAL_SUPPLY, SEL_BALANCE_OF = "18160ddd", "70a08231"
SEL_ROUND_TRIP = "62119846"                                                     # V2RoundTrip.roundTrip(address,address,address,uint256,bool)
HARNESS_AT = "0x" + "a2" * 20; CALLER = "0x" + "c0" * 20; HARNESS_GAS = "0x7a1200"     # deploy/base_v2_sim.py's harness address, caller and gas
# contracts/V2RoundTrip.sol's runtime (solc 0.8.26, optimizer 200 runs, cancun; the source's sha256 eecbbc1dc405f1b7461f898dc13c0c9a18bd11008d2414df17b5e8f58d9484c0),
# as deploy/base_v2_sim.py compiles it: placed by a state override, never deployed
HARNESS_CODE = "0x608060405260043610610020575f3560e01c8063621198461461002b575f80fd5b3661002757005b5f80fd5b348015610036575f80fd5b5061004a6100453660046104b1565b610069565b6040805193845260208401929092529082015260600160405180910390f35b6040805160028082526060820183525f9283928392839260208301908036833701905050905087815f815181106100a2576100a2610523565b60200260200101906001600160a01b031690816001600160a01b03168152505086816001815181106100d6576100d6610523565b6001600160a01b0392831660209182029290920101526040516370a0823160e01b81523060048201525f918916906370a0823190602401602060405180830381865afa158015610128573d5f803e3d5ffd5b505050506040513d601f19601f8201168201806040525081019061014c9190610537565b90506001600160a01b038a1663b6f9de95885f853061016c42603c610562565b6040518663ffffffff1660e01b815260040161018b94939291906105be565b5f604051808303818588803b1580156101a2575f80fd5b505af11580156101b4573d5f803e3d5ffd5b50506040516370a0823160e01b81523060048201528493506001600160a01b038c1692506370a082319150602401602060405180830381865afa1580156101fd573d5f803e3d5ffd5b505050506040513d601f19601f820116820180604052508101906102219190610537565b61022b91906105f2565b94508561024057505f925082915061047b9050565b6040805160028082526060820183525f9260208301908036833701905050905088815f8151811061027357610273610523565b60200260200101906001600160a01b031690816001600160a01b03168152505089816001815181106102a7576102a7610523565b6001600160a01b03928316602091820292909201015260405163d06ca61f60e01b81525f918d169063d06ca61f906102e5908a908690600401610605565b5f60405180830381865afa1580156102ff573d5f803e3d5ffd5b505050506040513d5f823e601f3d908101601f191682016040526103269190810190610625565b90508060018151811061033b5761033b610523565b602090810291909101015160405163095ea7b360e01b81526001600160a01b038e81166004830152602482018a9052919650908b169063095ea7b3906044016020604051808303815f875af1158015610396573d5f803e3d5ffd5b505050506040513d601f19601f820116820180604052508101906103ba91906106ed565b6103fb5760405162461bcd60e51b815260206004820152600e60248201526d185c1c1c9bdd994819985a5b195960921b604482015260640160405180910390fd5b476001600160a01b038d1663791ac947895f863061041a42603c610562565b6040518663ffffffff1660e01b815260040161043a95949392919061070f565b5f604051808303815f87803b158015610451575f80fd5b505af1158015610463573d5f803e3d5ffd5b50505050804761047391906105f2565b965050505050505b955095509592505050565b80356001600160a01b038116811461049c575f80fd5b919050565b80151581146104ae575f80fd5b50565b5f805f805f60a086880312156104c5575f80fd5b6104ce86610486565b94506104dc60208701610486565b93506104ea60408701610486565b9250606086013591506080860135610501816104a1565b809150509295509295909350565b634e487b7160e01b5f52604160045260245ffd5b634e487b7160e01b5f52603260045260245ffd5b5f60208284031215610547575f80fd5b5051919050565b634e487b7160e01b5f52601160045260245ffd5b808201808211156105755761057561054e565b92915050565b5f8151808452602084019350602083015f5b828110156105b45781516001600160a01b031686526020958601959091019060010161058d565b5093949350505050565b848152608060208201525f6105d6608083018661057b565b6001600160a01b03949094166040830152506060015292915050565b818103818111156105755761057561054e565b828152604060208201525f61061d604083018461057b565b949350505050565b5f60208284031215610635575f80fd5b815167ffffffffffffffff81111561064b575f80fd5b8201601f8101841361065b575f80fd5b805167ffffffffffffffff8111156106755761067561050f565b8060051b604051601f19603f830116810181811067ffffffffffffffff821117156106a2576106a261050f565b6040529182526020818401810192908101878411156106bf575f80fd5b6020850194505b838510156106e2578451808252602095860195909350016106c6565b509695505050505050565b5f602082840312156106fd575f80fd5b8151610708816104a1565b9392505050565b85815284602082015260a060408201525f61072d60a083018661057b565b6001600160a01b039490941660608301525060800152939250505056fea2646970667358221220c9729cbdd79275487245dc621dab473d385ea2028f61bda65e3163d82936626e64736f6c634300081a0033"
PAIR_INIT_HASH = bytes.fromhex("96e8ac4277198ff8b6f785478aa9a39f403cb768dd02cbee326c3e7da348845f")   # UniswapV2Pair's init code hash: the Base factory's CREATE2 (checked on the fixture's pair)
UA = "Mozilla/5.0 Chrome/128"                                                   # mainnet-sequencer.base.org's Cloudflare refuses Python's own (error 1010)
DRY_GAS_UNITS = 250_000                  # the round trip's gas, estimated (the fleet's router buys use about 119k; the relay's buy and sell about 125k each)
L1_FEE_EST_WEI = 4_200_000_000           # two L1 data fees (Oct 14: 2.09e9 wei a 356 B transaction)
READ_TIMEOUT_S = 3.0; SEND_TIMEOUT_S = 4.0; SLOW_TIMEOUT_S = 10.0
GUARD_TIMEOUT_S = 2.0; GUARD_WAIT_S = 3.0; GUARD_RETRY_S = 0.1                 # the exit test: one call's timeout, how long an endpoint without block N is asked again, its pause
RECEIPT_GRACE_S = 60.0; BLOCK_S = 2.0; SELL_RETRIES = 2                        # a receipt's wait past a deadline; a block; a failed sell's re-sends
RECEIPT_POLL_S = 0.25; POLL_S = 0.5; POLL_LAG = 1; MAX_RANGE = 20; FLASH_SILENT_S = 10.0; FLOW_S = 60.0
LOGS_SILENT_S = 300.0; YOUNG_BLOCKS = 400    # heads flowing but no log of a pair under +400 blocks for this long: the logs subscriptions are dead, reconnect
START_BACK = 12                          # the start reads this many blocks back (a restart mid-launch still arms)
SEAL_GRACE = 5                           # a creation seen pending whose block never sealed by N + this is dropped
START_WAIT_S = 300; DEFAULT_LOG = "/var/log/flip/base_v2.jsonl"
END = 1 << 62                            # a logIndex after every real one: (block, END) is the end of a block
# GAP: the back-run (BASE_V2_BACKRUN=1: the guard at the `pending` tag on BASE_V2_PENDING_URL, the buy into the creation block above the creation's
#      priority) is written but has not been exercised against a node or a stub; stage 0 measures the N+1 delay before it is considered.
# GAP: tests/test_base_v2_engine.py (the box's test file against tests/data/base_v2_pair.json) is not written here; the dry and live paths were
#      replayed from a scratch harness (the stream at 15 and 2.0 ETH, via the logs and via a Flashblock; the guard's four verdicts; the outsider,
#      take-profit, fleet-sell, hard and pulled exits; a reverted sell's re-sends to "sold none"; a restart taking a position back).
# GAP: deploy/base_v2_roster.py (the roster the engine reads), base_v2_relay_deploy.py, base_v2_results.py, base_v2_setup.sh and the unit are the
#      box's other items, not this module's.
# GAP: a creation transaction the node cannot answer (eth_getTransactionByHash empty three times) is an `alarm` and the pair is dropped, not a `skip`
#      line: the design's `why` list has no value for it.
# GAP: `seen_ms` of a creation seen on the logs feed needs the block's timestamp: the log's `blockTimestamp` field (publicnode carries it on Base) or
#      the head's when the head is that block; otherwise it is null.
# GAP: the confirmed feed's `fleet_sell` exit needs the seller: a Swap's `to` is the router for every router sell, so an unknown seller costs one
#      eth_getTransactionByHash off the feed thread (the Flashblocks copy, when seen, makes it free).


# ---------------------------------------------------------------- settings
def env(k, d=""):
    v = os.environ.get(k)
    return d if v is None or v.strip() == "" else v.split(" #", 1)[0].strip()


def _setting(name, default, lo, hi, integer=False):
    """a number within [lo, hi]; anything else stops the start naming it (base_engine's rule)"""
    raw = env(name, default)
    try:
        v = int(raw, 0) if integer else float(raw)
    except ValueError:
        raise SystemExit(f"{name} must be a {'whole number' if integer else 'number'}, not {raw!r}")
    if v != v or not lo <= v <= hi:
        raise SystemExit(f"{name} {raw!r} is not in {lo}..{hi}")
    return v


def _exact(name, default, lo, hi, scale, v=None):
    """a decimal setting as an exact integer of 1/scale units (ETH -> wei: 10**18; gwei -> wei: 10**9; a fraction -> ppm: 10**6), never via a float"""
    raw = env(name, default) if v is None else v
    try:
        d = decimal.Decimal(raw)
    except decimal.InvalidOperation:
        raise SystemExit(f"{name} must be a number, not {raw!r}")
    if not d.is_finite() or not decimal.Decimal(str(lo)) <= d <= decimal.Decimal(str(hi)):
        raise SystemExit(f"{name} {raw!r} is not in {lo}..{hi}")
    x = d * scale
    if x != x.to_integral_value():
        raise SystemExit(f"{name} {raw!r} is finer than its unit (1/{scale})")
    return int(x)


def _hex(name, default, n=None, empty_ok=False):
    v = env(name, default).lower()
    v = v[2:] if v.startswith("0x") else v
    if v == "" and empty_ok:
        return ""
    if not v or any(c not in "0123456789abcdef" for c in v) or (n and len(v) != n) or len(v) > 64:
        raise SystemExit(f"{name} {env(name, default)!r} is not {'%d hex digits' % n if n else 'hex'}")
    return v


_addr = lambda name, default, empty_ok=False: (lambda v: "0x" + v if v else "")(_hex(name, default, 40, empty_ok))


def _sizes(name, default):
    """code sizes in bytes, comma-separated; 0 alone = any"""
    out = set()
    for x in [x.strip() for x in env(name, default).split(",") if x.strip()]:
        if not x.isdigit() or len(x) > 6:
            raise SystemExit(f"{name} must be a comma list of code sizes in bytes (0 = any), not {env(name, default)!r}")
        out.add(int(x))
    return set() if out == {0} else out


def env_list(k, d):
    """a comma list that may be empty: a variable set to "" is an empty list, not the default (env() treats "" as unset)"""
    v = os.environ.get(k)
    return d if v is None else v.split(" #", 1)[0].strip()


def _hexlist(name, default, n):
    out = []
    for x in [x.strip().lower() for x in env_list(name, default).split(",") if x.strip()]:
        v = x[2:] if x.startswith("0x") else x
        if len(v) != n or any(c not in "0123456789abcdef" for c in v):
            raise SystemExit(f"{name} must be a comma list of {n}-digit hex values, not {env(name, default)!r}")
        out.append("0x" + v)
    return out


def _ethlist(name, default, lo, hi):
    """ETH values, comma-separated, each an exact wei amount; may be empty"""
    return [_exact(name, default, lo, hi, 10 ** 18, v=x.strip()) for x in env_list(name, default).split(",") if x.strip()]


def _band(name, default):
    """two ETH values lo,hi with 0 < lo <= hi <= 1000, as exact wei"""
    parts = [x.strip() for x in env(name, default).split(",")]
    if len(parts) != 2 or not all(parts):
        raise SystemExit(f"{name} must be two ETH values lo,hi, not {env(name, default)!r}")
    lo, hi = (_exact(name, default, "0.000001", 1000, 10 ** 18, v=x) for x in parts)
    if lo > hi:
        raise SystemExit(f"{name} {env(name, default)!r}: lo is over hi")
    return lo, hi, f"{parts[0]}-{parts[1]}"


def _url(name, default, schemes, v=None):
    v = env(name, default) if v is None else v
    if urllib.parse.urlparse(v).scheme not in schemes or not urllib.parse.urlparse(v).hostname:
        raise SystemExit(f"{name} must be a {'/'.join(schemes)} URL, not {host(v)!r}")
    return v


def _flag(name, default):
    v = env(name, default)
    if v not in ("0", "1"):
        raise SystemExit(f"{name} must be 0 or 1, not {v!r}")
    return v == "1"


def need(ok, why):
    if not ok:
        raise SystemExit(why)


def settings():
    s = types.SimpleNamespace()
    s.DRY = _flag("BASE_V2_DRY_RUN", "1")
    s.LOG_PATH = env("BASE_V2_LOG_PATH", DEFAULT_LOG); here = os.path.dirname(os.path.abspath(s.LOG_PATH))
    s.WS_URL = _url("BASE_V2_WS_URL", "wss://base-rpc.publicnode.com", ("wss", "ws"))
    s.RPC_URL = _url("BASE_V2_RPC_URL", "https://base-rpc.publicnode.com", ("https", "http"))    # mainnet.base.org answers eth_getLogs with 429
    s.READ_ALT_URL = "" if env("BASE_V2_READ_ALT_URL") == "0" else _url("BASE_V2_READ_ALT_URL", "https://mainnet.base.org", ("https", "http"))   # 0: none
    s.SEND_URLS = [_url("BASE_V2_SEND_URLS", "", ("https", "http"), x.strip()) for x in
                   env("BASE_V2_SEND_URLS", "https://mainnet-sequencer.base.org,https://mainnet.base.org").split(",") if x.strip()]
    need(s.SEND_URLS, "BASE_V2_SEND_URLS is empty")
    flash = env("BASE_V2_FLASH_URL", "wss://mainnet.flashblocks.base.org/ws")
    s.FLASH_URL = None if flash == "0" else _url("BASE_V2_FLASH_URL", flash, ("wss", "ws"))
    s.ARCHIVE_URL = _url("BASE_V2_ARCHIVE_URL", "https://open-platform.nodereal.io/64a9df0874fb4a93b9d0a3849de012d3/base", ("https", "http"))
    s.PENDING_URL = _url("BASE_V2_PENDING_URL", "https://mainnet.base.org", ("https", "http"))
    s.WALLET = _addr("BASE_V2_WALLET", "", empty_ok=True); s.RELAY = _addr("BASE_V2_RELAY", "", empty_ok=True)
    s.KEY_FILE = env("BASE_V2_KEY_FILE", "/etc/flip/base.key")
    s.FACTORY = _addr("BASE_V2_FACTORY", "0x8909dc15e40173ff4699343b6eb8132c65e18ec6")
    s.ROUTER = _addr("BASE_V2_ROUTER", "0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24")
    s.WETH = _addr("BASE_V2_WETH", "0x4200000000000000000000000000000000000006")
    s.HALT_FILE = env("BASE_V2_HALT_FILE", os.path.join(here, "HALTED.base_v2")); s.POSITIONS_FILE = os.path.join(here, "base_v2_positions.json")
    s.ROSTER_FILE = env("BASE_V2_ROSTER_FILE", "/etc/flip/base_v2_roster.json")
    s.WS_SILENT_S = _setting("BASE_V2_WS_SILENT_S", "10", 1, 600)
    # the fingerprint
    s.CREATE_SELECTOR = _hex("BASE_V2_CREATE_SELECTOR", "f305d719", 8); s.PULL_SELECTOR = _hex("BASE_V2_PULL_SELECTOR", "02751cec", 8)
    s.CREATOR_NONCE = _setting("BASE_V2_CREATOR_NONCE", "2", 0, 100, True)
    s.TOKEN_CODE_SIZES = _sizes("BASE_V2_TOKEN_CODE_SIZES", "3553")
    s.MIN_SUPPLY_PPM = _exact("BASE_V2_MIN_SUPPLY_IN_POOL", "0.99", 0, 1, 10 ** 6)
    s.BAND_LO_WEI, s.BAND_HI_WEI, s.TIER_LABEL = _band("BASE_V2_TIER_BAND", "1.3,2.3")
    s.EXCLUDE_MILLI = {(w + 5 * 10 ** 14) // 10 ** 15 for w in _ethlist("BASE_V2_TIER_EXCLUDE", "1.2", 0, 1000)}   # a value rounds to one at 0.001 ETH: never traded
    s.PROBE = set(_hexlist("BASE_V2_PROBE", "0xe71a69f434a719cd5afa411568b69716aab3b84a", 40))
    s.OUTSIDER_MIN_WEI = _exact("BASE_V2_OUTSIDER_MIN_ETH", "0", 0, 1, 10 ** 18)
    s.WATCH_BLOCKS = _setting("BASE_V2_WATCH_BLOCKS", "1400", 200, 5000, True)
    s.LAND_MAX = _setting("BASE_V2_LAND_MAX", "1", 0, 10, True)
    s.BACKRUN = _flag("BASE_V2_BACKRUN", "0")
    s.EXIT_MIN_PPM = _exact("BASE_V2_EXIT_MIN", "0.98", "0.5", 1, 10 ** 6)
    # the trade
    s.STAKE_ETH_WEI = _exact("BASE_V2_STAKE_ETH", "0.02", "0.000001", 10, 10 ** 18); s.STAKE_CAP_WEI = _exact("BASE_V2_STAKE_CAP_ETH", "0.02", "0.000001", 10, 10 ** 18)
    s.SHARE_CAP_PPM = _exact("BASE_V2_SHARE_CAP", "0.05", "0.001", "0.5", 10 ** 6)
    s.BUY_SLIP_PPM = _exact("BASE_V2_BUY_SLIP", "0.03", "0.0001", "0.5", 10 ** 6); s.BUY_DEADLINE_S = _setting("BASE_V2_BUY_DEADLINE_S", "6", 2, 600, True)
    s.HARD_BLOCK = _setting("BASE_V2_HARD_BLOCK", "180", 1, 200, True)
    s.SELL_SEND_BLOCK = _setting("BASE_V2_SELL_SEND_BLOCK", "176", 1, 5000, True); s.SELL_RESEND_BLOCK = _setting("BASE_V2_SELL_RESEND_BLOCK", "178", 1, 5000, True)
    need(s.SELL_SEND_BLOCK < s.SELL_RESEND_BLOCK <= s.HARD_BLOCK, "BASE_V2_SELL_SEND_BLOCK < BASE_V2_SELL_RESEND_BLOCK <= BASE_V2_HARD_BLOCK does not hold")
    s.SELL_FALLBACK_S = _setting("BASE_V2_SELL_FALLBACK_S", "370", 10, 3600, True)
    s.TP_PPM = _exact("BASE_V2_TAKE_PROFIT", "0.25", "0.01", 100, 10 ** 6); s.SELL_SLIP_PPM = _exact("BASE_V2_SELL_SLIP", "0.05", 0, "0.99", 10 ** 6)
    s.SELL_DEADLINE_S = _setting("BASE_V2_SELL_DEADLINE_S", "6", 2, 600, True)
    s.MAX_POSITIONS = _setting("BASE_V2_MAX_POSITIONS", "3", 1, 10, True); s.MAX_PER_DAY = _setting("BASE_V2_MAX_PER_DAY", "20", 0, 100000, True)
    s.DAILY_STOP_WEI = _exact("BASE_V2_DAILY_STOP_ETH", "0.15", 0, 1000, 10 ** 18)
    s.SCHEDULE_MIN = _setting("BASE_V2_SCHEDULE_MIN", "220", s.HARD_BLOCK + 1, 5000, True)
    s.PULL_SHARE_PPM = _exact("BASE_V2_PULL_SHARE", "0.30", "0.01", 1, 10 ** 6)
    s.REACT_BLOCKS = _setting("BASE_V2_REACT_BLOCKS", "10", 1, 100, True)
    s.LOSS_STREAK_HALT = _setting("BASE_V2_LOSS_STREAK_HALT", "2", 0, 100, True); s.LATE_HALT = _setting("BASE_V2_LATE_HALT", "2", 0, 100, True)
    s.ETH_USD = _setting("BASE_V2_ETH_USD", "2570", 1, 1e6)
    s.PRIO_WEI = _exact("BASE_V2_PRIO_GWEI", "0.03", 0, 100, 10 ** 9); s.MAX_FEE_WEI = _exact("BASE_V2_MAX_FEE_GWEI", "0.5", "0.000001", 1000, 10 ** 9)
    need(s.MAX_FEE_WEI >= s.PRIO_WEI, "BASE_V2_MAX_FEE_GWEI is under BASE_V2_PRIO_GWEI: no transaction could pay its priority")
    s.BUY_GAS = _setting("BASE_V2_BUY_GAS", "250000", 50_000, 5_000_000, True); s.SELL_GAS = _setting("BASE_V2_SELL_GAS", "250000", 50_000, 5_000_000, True)
    s.MARGIN_WEI = _exact("BASE_V2_RELAY_MARGIN_ETH", "0.0005", 0, 10, 10 ** 18)
    return s


def host(url):
    """only an endpoint's host is ever logged: a provider's URL may carry its key in the path or the query"""
    try:
        return urllib.parse.urlparse(url).hostname or "?"
    except ValueError:
        return "?"


S = settings()
now = time.time                                                                  # the clocks, by name: the tests stub them
mono = time.monotonic
lock = threading.RLock(); _log_lock = threading.RLock()                       # reentrant: a line written from a handler that interrupted one
state, pairs, positions, orphans, seen, flash_txs = {}, {}, {}, {}, {}, collections.OrderedDict()
orders = queue.Queue(); SIGNER = None; SENDERS = {}; KEY_LOCK = None


def reset():
    """the engine's state at a start (the tests call it between cases)"""
    for d in (state, pairs, positions, orphans, seen, flash_txs):
        d.clear()
    state.update({"head": None, "head_ts": None, "base_fee": 0, "head_src": None, "lag_s": None, "lag_max_s": None, "logs_to": None, "started_at": mono(),
                  "ws": False, "ws_subs": 0, "ws_last": 0.0, "ws_log_at": 0.0, "ws_from": None, "flash": False, "flash_at": 0.0, "flash_block": None, "flash_base_fee": 0,
                  "flash_ts": {}, "flash_msgs": 0, "flash_total": 0, "flash_reconnects": 0, "flash_bad": 0, "creations": 0, "tradable": 0, "watched": 0,
                  "nonce": None, "relay_wei": None, "wallet_wei": None, "halted": None, "stopped": None, "tiers_ended": {},
                  "day": None, "trades_today": 0, "pnl_today_wei": 0, "loss_streak": 0, "late_count": 0, "sold_none": 0, "trades_done": 0, "dups": 0, "reorgs": 0,
                  "filled": 0, "ours": {}, "our_hashes": {}, "tx_from": collections.OrderedDict(), "roster": set(), "roster_built": None, "roster_mtime": None,
                  "roster_at": 0.0, "ready_ms_last": None, "guard_ms_last": None, "alarms_quiet": {}, "flow_at": mono()})


reset()


# ---------------------------------------------------------------- log, alarm, halt
def log(ev):
    """one JSON line; never raises (a full disk or a bad value must not end the thread that logs): stderr, once a key"""
    try:
        ev["t"] = round(now(), 3)
        line = json.dumps(ev, separators=(",", ":"), default=str)
        with _log_lock:
            with open(S.LOG_PATH, "a") as f:
                f.write(line + "\n")
    except Exception as e:
        if type(e).__name__ not in state.setdefault("log_errors", set()):
            state["log_errors"].add(type(e).__name__)
            print(f"base_v2_engine: the log line was not written ({type(e).__name__}: {str(e)[:120]})", file=sys.stderr, flush=True)


def alarm(what, quiet_key=None, every_s=600, **kw):
    """an alarm line; with quiet_key, at most one per every_s seconds for that key"""
    if quiet_key is not None:
        t = mono(); last = state["alarms_quiet"].get(quiet_key)
        if last is not None and t - last < every_s:
            return
        state["alarms_quiet"][quiet_key] = t
    log({"ev": "alarm", "what": what, **kw})


def scrub(text, n=200):
    s = str(text)
    for u in [S.WS_URL, S.RPC_URL, S.READ_ALT_URL, S.FLASH_URL or "", S.ARCHIVE_URL, S.PENDING_URL] + S.SEND_URLS:
        if u:
            s = s.replace(u, host(u))
            x = urllib.parse.urlparse(u)
            for part, mark in ((x.query, "<query>"), (x.path if len(x.path) > 1 else "", "/<path>")):
                if part:
                    s = s.replace(part, mark)
    return s[:n]


def halt(reason, tier=None, pair=None):
    """live: HALTED.base_v2 written (a halt holds across restarts until the owner removes the file); dry: in memory. No new buy after it;
    what is open is still sold"""
    state["halted"] = reason; path = None if S.DRY else S.HALT_FILE
    try:
        path and open(path, "w").write(reason + "\n")
    except Exception as e:
        alarm(f"the halt file {path} could not be written ({str(e)[:80]}): the halt holds in memory until a restart")
    log({"ev": "halt", "reason": reason, "tier": tier, "pair": pair, "dry": S.DRY, "file": path})


today = lambda: datetime.datetime.fromtimestamp(now(), datetime.timezone.utc).strftime("%Y-%m-%d")


def read_halt_file():
    try:
        return (open(S.HALT_FILE).read().strip() or "HALTED.base_v2")[:200]
    except OSError as e:
        return f"HALTED.base_v2 ({e.strerror})"


def roll_day():
    """00:00 UTC: the day's count and P&L, the day stop and the tiers ended clear"""
    d = today()
    if state["day"] != d:
        state.update({"day": d, "trades_today": 0, "pnl_today_wei": 0, "stopped": None, "late_count": 0})
        state["tiers_ended"] = {k: v for k, v in state["tiers_ended"].items() if v == d}


pnl_eth = lambda: round(state["pnl_today_wei"] / 1e18, 6)


def stop_day(reason):
    if state["stopped"]:
        return
    state["stopped"] = state["day"]
    log({"ev": "stop", "what": "day", "day": state["day"], "tier": None, "reason": reason, "pnl_today_eth": pnl_eth(), "trades_today": state["trades_today"]})


def tier_end(tier, reason):
    """the tier ended for the day (section 7): cleared at 00:00 UTC, never by the engine before"""
    roll_day()
    if tier is None or state["tiers_ended"].get(tier) == state["day"]:
        return
    state["tiers_ended"][tier] = state["day"]
    log({"ev": "stop", "what": "tier", "day": state["day"], "tier": tier, "reason": reason, "pnl_today_eth": pnl_eth(), "trades_today": state["trades_today"]})


# ---------------------------------------------------------------- reads and sends
def http_json(url, payload, timeout):
    """one JSON-RPC POST (urllib: the environment's proxy and CA); an HTTP error's body is read, as the sequencer answers 400/403 in JSON"""
    req = urllib.request.Request(url, json.dumps(payload).encode(), {"Content-Type": "application/json", "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body, code = e.read(), e.code
    try:
        return json.loads(body)
    except ValueError:
        raise RuntimeError(f"HTTP {code}: {body[:80]!r}")


def read_from(urls, method, params, timeout=READ_TIMEOUT_S, tries=1):
    """a read from the first URL, then each next one once when it fails; a JSON null is a result"""
    last = None
    for k in range(tries):
        for u in urls:
            try:
                d = http_json(u, {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, timeout)
                if "result" in d:
                    return d["result"]
                last = json.dumps(d.get("error"))
            except Exception as e:
                last = f"{type(e).__name__}: {e}"
        if k < tries - 1:
            time.sleep(min(4.0, 0.5 * 2 ** k))
    raise RuntimeError(f"{method}: {scrub(last, 160)}")


def read(method, params, timeout=READ_TIMEOUT_S, tries=1):
    """a read: BASE_V2_RPC_URL, then BASE_V2_READ_ALT_URL once when it fails (3 s each on the trade path)"""
    return read_from([S.RPC_URL] + ([S.READ_ALT_URL] if S.READ_ALT_URL else []), method, params, timeout, tries)


def guard_read(method, params, timeout=GUARD_TIMEOUT_S):
    """the guard's reads (eth_getCode, totalSupply): BASE_V2_ARCHIVE_URL, then BASE_V2_READ_ALT_URL; single requests, never a batch"""
    return read_from([S.ARCHIVE_URL] + ([S.READ_ALT_URL] if S.READ_ALT_URL else []), method, params, timeout)


class Sender:
    """a warm HTTPS connection to one send endpoint (keep-alive, TCP_NODELAY, the environment's https proxy if one is set), reopened once
    when a post fails"""
    def __init__(self, url):
        u = urllib.parse.urlparse(url); self.host = u.hostname; self.tls = u.scheme == "https"; self.port = u.port or (443 if self.tls else 80)
        self.path = (u.path or "/") + ("?" + u.query if u.query else ""); self.conn = None; self.lock = threading.Lock(); self.last = 0.0

    def _open(self):
        proxy = urllib.request.getproxies().get("https" if self.tls else "http")
        via = urllib.parse.urlparse(proxy) if proxy and not urllib.request.proxy_bypass(self.host) else None
        h, port = (via.hostname, via.port or 80) if via else (self.host, self.port)
        c = http.client.HTTPSConnection(h, port, timeout=SEND_TIMEOUT_S, context=ssl.create_default_context()) if self.tls else \
            http.client.HTTPConnection(h, port, timeout=SEND_TIMEOUT_S)
        if via:
            c.set_tunnel(self.host, self.port)
        c.connect(); c.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1); self.conn = c
        return c

    def post(self, body):
        with self.lock:
            err = None
            for _ in (0, 1):
                try:
                    c = self.conn or self._open()
                    c.request("POST", self.path, body, {"Content-Type": "application/json", "User-Agent": UA, "Connection": "keep-alive"})
                    data = c.getresponse().read(); self.last = mono()
                    return json.loads(data)
                except Exception as e:
                    err = e; c, self.conn = self.conn, None
                    try:
                        c and c.close()
                    except Exception:
                        pass
            return {"error": {"message": f"send failed: {type(err).__name__}: {scrub(err, 120)}"}}


def post_one(url, body):
    snd = SENDERS.get(url) or SENDERS.setdefault(url, Sender(url))
    return snd.post(body)


def upkeep():
    """thread (live): an idle send connection gets a cheap request every 15 s (a send never pays the TLS handshake); the relay's and the
    wallet's balances every 60 s (a deposit lifts the fire's refusal)"""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []}); t_bal = mono()
    for u in S.SEND_URLS:
        SENDERS.setdefault(u, Sender(u))
    while True:
        time.sleep(5)
        for snd in list(SENDERS.values()):
            if mono() - snd.last > 15:
                snd.post(body)
        if mono() - t_bal > 60:
            t_bal = mono()
            try:
                b = int(read("eth_getBalance", [S.RELAY, "latest"]), 16); w = int(read("eth_getBalance", [S.WALLET, "latest"]), 16)
                with lock:
                    if not any(not p["closed"] for p in positions.values()):
                        state["relay_wei"] = b
                    state["wallet_wei"] = w
            except Exception as e:
                alarm(f"the balances were not read: {scrub(e, 100)}", quiet_key="balance")


def reply_kind(reply):
    """an eth_sendRawTransaction reply: "ok", "known" (the node has it), "nonce_low", "rejected", "unknown" (no answer: it may be in)"""
    err = reply.get("error") or {}; msg = str(err.get("message", "")).lower()
    return ("ok" if "result" in reply else "unknown" if "code" not in err else "nonce_low" if "nonce too low" in msg else
            "known" if any(x in msg for x in ("already known", "already exists", "known transaction", "already imported")) else "rejected")


def post_all(raw_hex):
    """the signed transaction to every BASE_V2_SEND_URLS at once; the first "ok"/"known" wins; else nonce_low, unknown, rejected in that order"""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_sendRawTransaction", "params": [raw_hex]})
    q = queue.Queue()
    for u in S.SEND_URLS:
        threading.Thread(target=lambda u=u: q.put((u, post_one(u, body))), daemon=True).start()
    replies = {}; t_end = mono() + 2 * SEND_TIMEOUT_S + 1
    while len(replies) < len(S.SEND_URLS):
        try:
            u, r = q.get(timeout=max(0.01, t_end - mono()))
        except queue.Empty:
            break
        k = reply_kind(r); replies[host(u)] = {"kind": k, "reply": scrub(r.get("result") or r.get("error"), 120)}
        if k in ("ok", "known"):
            return k, replies
    kinds = [v["kind"] for v in replies.values()]
    return next((k for k in ("nonce_low", "unknown", "rejected") if k in kinds), "unknown"), replies


# ---------------------------------------------------------------- words, transactions, the constant product
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
A = lambda d, i: "0x" + d[2 + 64 * i + 24: 2 + 64 * (i + 1)].lower()
topic_addr = lambda t: "0x" + t[-40:].lower()
word = lambda x: "%064x" % (x % (1 << 256))
aword = lambda a: "%064x" % int(a, 16)
buy_data = lambda token, stake, min_out, deadline: "0x" + SEL_BUY + aword(token) + word(stake) + word(min_out) + word(deadline)
sell_data = lambda token, min_out, deadline: "0x" + SEL_SELL + aword(token) + word(min_out) + word(deadline)
base_fee = lambda: max(state["base_fee"] or 0, state["flash_base_fee"] or 0)             # the head's or the pending block's, the higher
gas_est_wei = lambda: DRY_GAS_UNITS * (base_fee() + S.PRIO_WEI) + L1_FEE_EST_WEI
cp_out = lambda x, r_in, r_out: x * 997 * r_out // (r_in * 1000 + x * 997) if x > 0 and r_in > 0 else 0   # Uniswap V2: out = in x 997 x R_out / (R_in x 1000 + in x 997)


def create_address(sender, nonce=0):
    """the address CREATE gives `sender` at `nonce`: keccak(rlp([sender, nonce]))[12:]"""
    return "0x" + keccak(rlp.encode([bytes.fromhex(sender[2:]), nonce]))[12:].hex()


def pair_address(token):
    """the factory's pair for (token, WETH): CREATE2 with the sorted tokens' hash as the salt and UniswapV2Pair's init code hash"""
    t0, t1 = sorted([S.WETH, token])
    salt = keccak(bytes.fromhex(t0[2:] + t1[2:]))
    return "0x" + keccak(b"\xff" + bytes.fromhex(S.FACTORY[2:]) + salt + PAIR_INIT_HASH)[12:].hex()


def tx_dict(data, gas, nonce, prio=None, max_fee=None):
    """a type-2 transaction to the relay: priority BASE_V2_PRIO_GWEI (or the one given), max fee 2 x the base fee (the head's or the pending
    block's, the higher) + the priority, at most BASE_V2_MAX_FEE_GWEI (a given max fee: a replacement's bump); all integers"""
    prio = S.PRIO_WEI if prio is None else prio
    return {"type": 2, "chainId": CHAIN_ID, "nonce": nonce, "to": to_checksum_address(S.RELAY), "value": 0, "data": data, "gas": gas,
            "maxFeePerGas": max(min(2 * base_fee() + prio, max(S.MAX_FEE_WEI, prio)), max_fee or 0), "maxPriorityFeePerGas": prio}


def sign(tx):
    raw = bytes(SIGNER.sign_transaction(tx).raw_transaction)
    return "0x" + raw.hex(), "0x" + keccak(raw).hex()


# ---------------------------------------------------------------- the raw transactions of a Flashblock
def decode_tx(raw):
    """{type, to, value, data, nonce, prio, max_fee, gas} of a raw signed transaction: legacy (rlp [nonce, gasPrice, gas, to, value, data, v,
    r, s]), 0x01 ([chainId, nonce, gasPrice, gas, to, value, data, accessList, ...]), 0x02 and 0x04 ([chainId, nonce, maxPriorityFeePerGas,
    maxFeePerGas, gas, to, value, data, accessList, ...]); None for a deposit (0x7e), anything else or a malformed one"""
    try:
        t = raw[0]
        if t >= 0xc0 or t == 1:                                                    # legacy, 2930: one gas price
            f = rlp.decode(raw) if t >= 0xc0 else rlp.decode(raw[1:])[1:]; nonce, gp, gas, to, value, data = f[:6]; prio = mx = gp
            t = 0 if t >= 0xc0 else 1
        elif t in (2, 4):
            _c, nonce, prio, mx, gas, to, value, data = rlp.decode(raw[1:])[:8]
        else:
            return None
        n = lambda b: int.from_bytes(b, "big")
        return {"type": t, "to": "0x" + to.hex() if to else None, "value": n(value), "data": bytes(data), "nonce": n(nonce), "prio": n(prio), "max_fee": n(mx), "gas": n(gas)}
    except Exception:
        return None


def tx_sender(raw_hex):
    from eth_account import Account
    try:
        return Account.recover_transaction(raw_hex).lower()
    except Exception:
        return None


def remember_sender(h, sender):
    """the sender of a transaction, by its hash (recovered from its Flashblocks copy, or read): a Swap's `to` is the recipient, not the sender"""
    if sender:
        state["tx_from"][h] = sender
        while len(state["tx_from"]) > 4096:
            state["tx_from"].popitem(last=False)
    return sender


def tx_from(h, raw_hex=None):
    s = state["tx_from"].get(h)
    if s is None and raw_hex is not None:
        s = remember_sender(h, tx_sender(raw_hex))
    return s


def read_sender(h):
    """the sender of a confirmed transaction the Flashblocks copy did not show: one eth_getTransactionByHash (off the feed threads)"""
    s = state["tx_from"].get(h)
    if s is not None:
        return s
    try:
        t = read("eth_getTransactionByHash", [h], tries=2)
        return remember_sender(h, (t or {}).get("from", "").lower() or None)
    except Exception as e:
        alarm(f"a transaction's sender was not read: {scrub(e, 100)}", quiet_key="txfrom", every_s=60, tx=h); return None


# ---------------------------------------------------------------- the roster
def load_roster(at_start=False):
    """BASE_V2_ROSTER_FILE ({"built": <utc>, "wallets": [...]}) read at the start and again when its mtime changes; never added to"""
    try:
        st = os.stat(S.ROSTER_FILE)
    except OSError as e:
        if at_start or state["roster_mtime"] is not None:
            alarm(f"the roster file {S.ROSTER_FILE} is not readable ({e.strerror}): " + ("the fleet is unknown, every buy an outsider's" if S.DRY else "no live start without it"),
                  quiet_key="roster")
        state["roster_mtime"] = None
        return False
    if st.st_mtime == state["roster_mtime"]:
        return True
    try:
        d = json.load(open(S.ROSTER_FILE)); ws = d.get("wallets") if isinstance(d, dict) else None
        need(isinstance(ws, list) and all(isinstance(w, str) and len(w) == 42 for w in ws), "wallets must be a list of addresses")
        with lock:
            state["roster"] = {w.lower() for w in ws}; state["roster_built"] = d.get("built"); state["roster_mtime"] = st.st_mtime
        return True
    except Exception as e:
        alarm(f"the roster file {S.ROSTER_FILE} was not understood ({str(e)[:80]}): the last roster holds", quiet_key="roster"); return False


# ---------------------------------------------------------------- the pairs
def tier_of(value):
    """(tier label, class, why): the band's label and `tradable` inside BASE_V2_TIER_BAND; the value at 0.01 ETH and `watched` otherwise, an
    excluded value (BASE_V2_TIER_EXCLUDE, at 0.001 ETH) first"""
    label = f"{round(value / 1e18, 2):g}"
    if (value + 5 * 10 ** 14) // 10 ** 15 in S.EXCLUDE_MILLI:
        return label, "watched", "excluded tier"
    if S.BAND_LO_WEI <= value <= S.BAND_HI_WEI:
        return S.TIER_LABEL, "tradable", None
    return label, "watched", "value outside the band"


def new_pair(pair, token, weth_is0, creator, N, via):
    return {"pair": pair, "token": token, "weth_is0": weth_is0, "creator": creator, "N": N, "sealed": via == "logs", "via": via, "creation_tx": None, "nonce": None,
            "value": 0, "r_eth0": 0, "r_tok0": 0, "supply": None, "supply_share": None, "code_size": None, "tier": None, "cls": None, "status": "pending", "ev": {},
            "seen_at": mono(), "seen_wall": now(), "ts": None, "tx_type": None, "prio": None, "max_fee": None, "gas": None, "announced": False, "guard": None,
            "pull_logged": False, "pull_pending": None, "buys": [], "last_buy": None, "last_outsider": None, "first_outsider": None, "fleet_first": None,
            "logged_txs": set(), "kick": False, "trade": None, "ended": False, "sub": None, "backfilled": None, "halt_checked": False}


def reserves(P, upto=None):
    """the pair's state from its events in (block, logIndex) order, to `upto` included: (ETH reserve, token reserve, the first Burn's key):
    the last Sync is exact after every mint, swap and burn; before any, the Mint's amounts (pending: msg.value and amountTokenDesired)"""
    r0, r1, pull = None, None, None
    for k in sorted(P["ev"]):
        if upto is not None and k > upto:
            break
        e = P["ev"][k]
        if e["k"] == "sync":
            r0, r1 = e["r0"], e["r1"]
        elif e["k"] == "burn" and pull is None:
            pull = k
    if r0 is None:
        return P["r_eth0"], P["r_tok0"], pull
    return (r0, r1, pull) if P["weth_is0"] else (r1, r0, pull)


def sides(P, e):
    """a Swap's (ETH in, tokens out, tokens in, ETH out)"""
    if P["weth_is0"]:
        return e["a0in"], e["a1out"], e["a1in"], e["a0out"]
    return e["a1in"], e["a0out"], e["a0in"], e["a1out"]


def who_of(P, txh, to, sender=None):
    """who traded: `ours` (our relay, or our own hash), `fleet` (the sender, or the recipient, in the roster), `probe`, `creator`, `outsider`.
    The sender is the Flashblocks copy's (or a read's) when known; else the Swap's `to` stands for it (an aggregator's buy: the aggregator)"""
    if txh in state["our_hashes"] or (S.RELAY and to == S.RELAY):
        return "ours"
    sender = sender or state["tx_from"].get(txh)
    actor = sender or to
    if actor in state["roster"] or to in state["roster"]:
        return "fleet"
    if actor in S.PROBE:
        return "probe"
    if P["creator"] and actor == P["creator"]:
        return "creator"
    if S.WALLET and actor == S.WALLET:
        return "ours"
    return "outsider"


def order(lg):
    try:
        return int(lg["blockNumber"], 16), int(lg["logIndex"], 16)
    except Exception:
        return -1, -1


followed = lambda: [P for P in pairs.values() if P["status"] != "skip"]
young = lambda: [P for P in followed() if state["head"] is not None and state["head"] - P["N"] < YOUNG_BLOCKS]
open_positions = lambda: [p for p in positions.values() if not p["closed"]]


# ---------------------------------------------------------------- the creation (pending in a Flashblock, or the factory's PairCreated)
def shape_why(sender, nonce, token):
    """the creator's shape: nonce BASE_V2_CREATOR_NONCE, the token created at its nonce 0"""
    if nonce != S.CREATOR_NONCE:
        return "creator nonce"
    if not sender or create_address(sender) != token:
        return "create address"
    return None


def creation_rec(P):
    g = lambda x: round(x / 1e9, 6) if x is not None else None
    return {"block": P["N"], "tx": P["creation_tx"], "creator": P["creator"], "nonce": P["nonce"], "token": P["token"], "pair": P["pair"], "weth_is0": P["weth_is0"],
            "value_eth": P["value"] / 1e18, "tier": P["tier"], "cls": P["cls"], "r_eth_wei": P["r_eth0"], "r_tok": P["r_tok0"], "supply_share": P["supply_share"],
            "tx_type": P["tx_type"], "prio_gwei": g(P["prio"]), "max_fee_gwei": g(P["max_fee"]), "gas": P["gas"], "via": P["via"], "seen_ms": P.get("seen_ms")}


seen_ms_of = lambda P, ts: round(1000 * (P["seen_wall"] - ts), 1) if ts else None      # from the block's timestamp (negative: seen before the block sealed)


def skip_pair(P, why, **fields):
    """a pair of the line refused: the `skip` line with the measured value; it stays followed (watched) for its outsider_buy and pull lines"""
    if P["status"] in ("fired", "traded", "watched"):
        return
    P["status"] = "watched"
    log({"ev": "skip", "pair": P["pair"], "token": P["token"], "block": P["N"], "tier": P["tier"], "why": why, "head": state["head"], **fields})


def announce(P):
    """the creation's class: one `creation` line; watched: a `skip` with the reason; tradable: the guard thread"""
    P["tier"], P["cls"], why = tier_of(P["value"])
    state["creations"] += 1; state[P["cls"]] += 1; P["announced"] = True
    log({"ev": "creation", **creation_rec(P)})
    if why:
        P["status"] = "arming"; skip_pair(P, why, value_eth=P["value"] / 1e18)
    else:
        P["status"] = "arming"; spawn(prepare, P)


def on_flash_create(s, raw, tx, N, at):
    """a pending router call with the create selector: the creator recovered, its nonce and the token's CREATE address checked, the pair's
    address by CREATE2; the Mint's reserves are msg.value and amountTokenDesired (a fresh pair takes both whole)"""
    d = tx["data"]
    if len(d) < 4 + 32 * 6 or tx["value"] <= 0:
        return
    token = "0x" + d[16:36].hex(); amount_tok = int.from_bytes(d[36:68], "big"); h = "0x" + keccak(raw).hex()
    sender = tx_from(h, s)
    flash_txs[h] = {"to": tx["to"], "from": sender, "sel": S.CREATE_SELECTOR, "data": d, "value": tx["value"], "nonce": tx["nonce"], "type": tx["type"], "prio": tx["prio"],
                    "max_fee": tx["max_fee"], "gas": tx["gas"], "src": "flash"}
    while len(flash_txs) > 256:
        flash_txs.popitem(last=False)
    pair = pair_address(token)
    if pair in pairs:
        return
    P = new_pair(pair, token, S.WETH < token, sender, N, "flash")
    P.update(creation_tx=h, nonce=tx["nonce"], value=tx["value"], r_eth0=tx["value"], r_tok0=amount_tok, tx_type=tx["type"], prio=tx["prio"], max_fee=tx["max_fee"],
             gas=tx["gas"], ts=state["flash_ts"].get(N))
    P["seen_ms"] = seen_ms_of(P, P["ts"]); P["flash_at"] = at
    why = shape_why(sender, tx["nonce"], token)
    if why:
        log({"ev": "skip", "pair": pair, "token": token, "block": N, "tier": None, "why": why, "value_eth": tx["value"] / 1e18, "nonce": tx["nonce"], "creator": sender,
             "via": "flash", "pending": True})
        return
    pairs[pair] = P
    announce(P)


def on_pair_created(lg, B):
    """PairCreated on the factory with WETH on either side: a pair seen pending is sealed; a new one has its creation transaction read"""
    t0, t1 = topic_addr(lg["topics"][1]), topic_addr(lg["topics"][2]); pair = A(lg["data"], 0); h = lg["transactionHash"].lower()
    if S.WETH not in (t0, t1):
        return
    token = t1 if t0 == S.WETH else t0
    ts = int(lg.get("blockTimestamp") or "0x0", 16) or (state["head_ts"] if state["head"] == B else None)
    P = pairs.get(pair)
    if P is not None:
        if not P["sealed"]:
            P.update(N=B, sealed=True, creation_tx=h, ts=P["ts"] or ts, kick=True)
        return
    P = new_pair(pair, token, t0 == S.WETH, None, B, "logs"); P.update(creation_tx=h, ts=ts); P["seen_ms"] = seen_ms_of(P, ts)
    pairs[pair] = P
    for x in sorted(orphans.pop(pair, []), key=order):
        apply(P, x)
    spawn(read_creation, P)


def read_creation(P):
    """thread: the creation transaction (its Flashblocks copy, else eth_getTransactionByHash) for the shape, and its receipt for the Mint"""
    h = P["creation_tx"]; t = flash_txs.get(h); why = None; r_eth = r_tok = 0
    try:
        rc_box = {}
        if t is None:
            def get_receipt():
                for _ in range(3):
                    rc_box["rc"] = read("eth_getTransactionReceipt", [h])
                    if rc_box["rc"]:
                        return
                    time.sleep(0.3)
            t_rc = threading.Thread(target=get_receipt, daemon=True); t_rc.start()        # beside the transaction's read: one round trip, not two
            r = None
            for _ in range(3):
                r = read("eth_getTransactionByHash", [h])
                if r:
                    break
                time.sleep(0.3)
            if not r:
                raise RuntimeError("the creation transaction is not known to the node")
            inp = r.get("input") or "0x"; n = lambda k, d="0x0": int(r.get(k) or d, 16)
            t = {"to": (r.get("to") or "").lower(), "from": (r.get("from") or "").lower(), "sel": inp[2:10].lower(), "data": bytes.fromhex(inp[2:]), "value": n("value"),
                 "nonce": n("nonce"), "type": n("type"), "prio": int(r.get("maxPriorityFeePerGas") or r.get("gasPrice") or "0x0", 16),
                 "max_fee": int(r.get("maxFeePerGas") or r.get("gasPrice") or "0x0", 16), "gas": n("gas"), "src": "rpc"}
            remember_sender(h, t["from"])
        if t["to"] != S.ROUTER:
            why = "not the router"
        elif t["sel"] != S.CREATE_SELECTOR:
            why = "selector"
        else:
            why = shape_why(t["from"], t["nonce"], P["token"])
        r_eth, r_tok = t["value"], int.from_bytes(t["data"][36:68], "big") if len(t["data"]) >= 68 else 0
        if why is None and t["src"] == "rpc":                                   # the receipt: the Mint in the same transaction, its amounts the reserves
            t_rc.join(READ_TIMEOUT_S * 6 + 1); rc = rc_box.get("rc")
            mint = next((l for l in (rc or {}).get("logs") or [] if (l.get("address") or "").lower() == P["pair"] and (l.get("topics") or [""])[0].lower() == T_MINT), None)
            if mint is not None:
                a0, a1 = W(mint["data"], 0), W(mint["data"], 1); r_eth, r_tok = (a0, a1) if P["weth_is0"] else (a1, a0)
            else:
                alarm("the creation's receipt shows no Mint on the pair" if rc else "the creation's receipt was not read", quiet_key="receipt", every_s=60, pair=P["pair"])
                why = why or ("selector" if rc else None)
    except Exception as e:
        alarm(f"a creation was not read: {scrub(e, 120)}", quiet_key="creation", every_s=60, pair=P["pair"], tx=h)
        with lock:
            pairs.pop(P["pair"], None) if pairs.get(P["pair"]) is P else None
        return
    with lock:
        if pairs.get(P["pair"]) is not P:
            return
        P.update(creator=t["from"], nonce=t["nonce"], value=t["value"], r_eth0=r_eth, r_tok0=r_tok, tx_type=t["type"], prio=t["prio"], max_fee=t["max_fee"], gas=t["gas"])
        if why:
            log({"ev": "skip", "pair": P["pair"], "token": P["token"], "block": P["N"], "tier": None, "why": why, "value_eth": t["value"] / 1e18, "nonce": t["nonce"],
                 "creator": t["from"], "to": t["to"], "selector": t["sel"], "via": "logs"})
            pairs.pop(P["pair"], None); return
        announce(P)


# ---------------------------------------------------------------- the guard (the pending window's checks, the arm's read, the exit test)
stake_for = lambda P: min(S.STAKE_ETH_WEI, S.STAKE_CAP_WEI, P["r_eth0"] * S.SHARE_CAP_PPM // 10 ** 6)


def pending_checks(P):
    """eth_getCode(token)'s size in BASE_V2_TOKEN_CODE_SIZES; totalSupply() so that the pool's token side is >= BASE_V2_MIN_SUPPLY_IN_POOL of
    it (on BASE_V2_ARCHIVE_URL, then BASE_V2_READ_ALT_URL): (why, the measured values)"""
    code = guard_read("eth_getCode", [P["token"], "latest"]); size = (len(code) - 2) // 2 if isinstance(code, str) else 0
    with lock:
        P["code_size"] = size
    if S.TOKEN_CODE_SIZES and size not in S.TOKEN_CODE_SIZES:
        return "code size", {"code_size": size}
    sup = int(guard_read("eth_call", [{"to": P["token"], "data": "0x" + SEL_TOTAL_SUPPLY}, "latest"]) or "0x0", 16)
    share = P["r_tok0"] * 10 ** 6 // sup if sup else 0
    with lock:
        P["supply"] = sup; P["supply_share"] = round(share / 1e6, 6)
    if share < S.MIN_SUPPLY_PPM:
        return "supply share", {"supply_share": round(share / 1e6, 6), "code_size": size}
    return None, {"code_size": size, "supply_share": round(share / 1e6, 6)}


def wait_sealed(P):
    """block N sealed (the PairCreated seen, or the head at N); False once the pair is no longer arming or its creation never sealed"""
    while True:
        with lock:
            if P["status"] != "arming" or pairs.get(P["pair"]) is not P:
                return False
            head = state["head"]
            if P["sealed"] or (head is not None and head >= P["N"]):
                return True
        time.sleep(0.01)


def backfill(P):
    """the pair's logs from N to the head by eth_getLogs (the arm's read: the creation block's own swaps; a watched pair's first blocks)"""
    with lock:
        a = P["N"]; b = max(state["head"] or a, a); P["backfilled"] = "running"
    err = None
    for attempt in range(4):
        try:
            ls = read("eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(b), "address": P["pair"], "topics": [PAIR_TOPICS]}], timeout=SLOW_TIMEOUT_S)
            if not isinstance(ls, list):
                raise ValueError(f"eth_getLogs gave {type(ls).__name__}")
            break
        except Exception as e:
            err = e; time.sleep(0.2 * (attempt + 1))
    else:
        alarm(f"the pair's logs at its creation block were not read ({scrub(err, 100)})", quiet_key="backfill", every_s=60, pair=P["pair"])
        with lock:
            P["backfilled"] = "failed"
        return False
    with lock:
        for lg in sorted(ls, key=order):
            on_log(lg)
        P["backfilled"] = b
    return True


def outsider_before_fire(P):
    """the buys seen before our fire with their senders resolved (the Flashblocks copy, else one read each): the probe's and the creator's
    pass, anyone else's is an outsider before our fire"""
    with lock:
        buys = [dict(b) for b in P["buys"]]; first = P["first_outsider"]
    if first is not None and any(b["who"] == "outsider" for b in buys) is False and not buys:
        return first                                                           # seen pending only
    for b in buys:
        sender = read_sender(b["tx"]) if state["tx_from"].get(b["tx"]) is None else state["tx_from"][b["tx"]]
        with lock:
            who = who_of(P, b["tx"], b["to"], sender)
            for x in P["buys"]:
                if x["tx"] == b["tx"]:
                    x["who"] = who
            if who == "outsider":
                return b["B"]
            if who == "fleet" and P["fleet_first"] is None:
                P["fleet_first"] = b["B"]
    with lock:
        P["first_outsider"] = None if not any(b["who"] == "outsider" for b in P["buys"]) else P["first_outsider"]
        P["last_outsider"] = max([b["B"] for b in P["buys"] if b["who"] == "outsider"], default=None)
    return None


def exit_test(P, stake, tag, urls, ready=None):
    """the V2RoundTrip harness by eth_call with the state override at `tag` on every url at once (an endpoint without the block yet is asked
    again every 100 ms; the first verdict counts), as deploy/base_v2_sim.py: the tokens bought must equal the constant-product expectation
    on the reserves the call ran on (else buy_tax), the ETH back >= BASE_V2_EXIT_MIN of the quote (else taxed); a reverted sell is a honeypot
    (the buy alone works), a pair nobody could read is unreadable. `ready` (an Event) holds the verdict until the arm's read of block N is in"""
    t0 = mono()
    args = aword(S.ROUTER) + aword(S.WETH) + aword(P["token"]) + word(stake)
    ov = {HARNESS_AT: {"code": HARNESS_CODE, "balance": hex(stake * 2)}}
    call = lambda do_sell: [{"from": CALLER, "to": HARNESS_AT, "data": "0x" + SEL_ROUND_TRIP + args + word(1 if do_sell else 0), "gas": HARNESS_GAS}, tag, ov]
    q = queue.Queue()

    def ask(u):
        t_end = mono() + GUARD_WAIT_S; last = "no answer"
        while mono() < t_end:
            try:
                d = http_json(u, {"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": call(True)}, GUARD_TIMEOUT_S)
            except Exception as e:
                last = f"{type(e).__name__}: {e}"; time.sleep(GUARD_RETRY_S); continue
            if isinstance(d.get("result"), str) and len(d["result"]) >= 2 + 64 * 3:
                q.put((u, "ok", d["result"])); return
            err = d.get("error") or {}; last = json.dumps(err)
            if "revert" in last.lower() or err.get("code") == 3:
                q.put((u, "revert", last)); return
            time.sleep(GUARD_RETRY_S)                                          # the block is not there yet (or a rate limit): asked again
        q.put((u, "none", last))

    for u in urls:
        threading.Thread(target=ask, args=(u,), daemon=True).start()
    got = None; nones = []
    for _ in urls:
        try:
            u, kind, r = q.get(timeout=GUARD_WAIT_S + GUARD_TIMEOUT_S + 1)
        except queue.Empty:
            break
        if kind == "none":
            nones.append((u, r)); continue
        got = (u, kind, r); break
    if ready is not None:
        ready.wait(GUARD_WAIT_S + GUARD_TIMEOUT_S)
    with lock:
        r_eth, r_tok, _ = reserves(P) if S.BACKRUN else reserves(P, (P["N"], END))   # the state the call ran on: the end of block N (the probe's swap in it)
    expect = cp_out(stake, r_eth, r_tok)
    out = {"tokens": None, "expect_tokens": expect, "eth_back_wei": None, "quote_wei": None, "ratio": None, "verdict": "unreadable", "ms": None,
           "src": host(got[0]) if got else None, "error": None}
    if got is None:
        out.update(error=scrub(nones[0][1] if nones else "no answer", 120), ms=round(1000 * (mono() - t0), 1)); return out
    u, kind, r = got
    if kind == "revert":                                                       # a buy-only probe tells a honeypot (the buy works, the sell reverts) from an unreadable pair
        try:
            d = http_json(u, {"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": call(False)}, GUARD_TIMEOUT_S)
        except Exception as e:
            d = {"error": {"message": f"{type(e).__name__}: {e}"}}
        bought = isinstance(d.get("result"), str) and len(d["result"]) >= 66
        out.update(verdict="honeypot" if bought else "unreadable", tokens=W(d["result"], 0) if bought else None, error=scrub(r, 120), ms=round(1000 * (mono() - t0), 1))
        return out
    tokens, eth_back, quote = W(r, 0), W(r, 1), W(r, 2)
    exact = tokens == expect or (S.BACKRUN and expect and abs(tokens - expect) * 1000 <= expect)   # the pending tag: the creation block's probe may sit ahead of us
    out.update(tokens=tokens, eth_back_wei=eth_back, quote_wei=quote, ratio=round(eth_back / quote, 6) if quote else 0.0, ms=round(1000 * (mono() - t0), 1),
               verdict="buy_tax" if not exact else "taxed" if not quote or eth_back * 10 ** 6 < quote * S.EXIT_MIN_PPM else "ok")
    return out


def prepare(P):
    """thread, a tradable pair: the pending window's checks (the code size, the supply: before N seals when the creation was seen pending),
    block N sealed, then at once the arm's read (the creation block's swaps) and the exit test's calls at block N (the `pending` tag with the
    back-run); the verdict once both are in; then the fire. Nothing retries a failed guard"""
    try:
        checks = {}; stake = stake_for(P)

        def run_checks():
            try:
                checks.update(zip(("why", "meas"), pending_checks(P)))
            except Exception as e:                                             # a read that failed: the skip names it (scrubbed), the thread ends quietly
                checks.update(why="guard", meas={"verdict": "unreadable", "error": scrub(f"{type(e).__name__}: {e}", 120)})
        t_checks = threading.Thread(target=run_checks, daemon=True); t_checks.start()
        if P["via"] == "flash":
            t_checks.join()                                                    # the pending window: refused before N seals (nothing else to do yet)
            with lock:
                if P["status"] != "arming":
                    return
                if checks.get("why"):
                    return skip_pair(P, checks["why"], **checks["meas"])
        if S.BACKRUN:
            tag, urls = "pending", [S.PENDING_URL]
        else:
            if not wait_sealed(P):
                return
            tag, urls = hex(P["N"]), [S.ARCHIVE_URL] + ([S.READ_ALT_URL] if S.READ_ALT_URL else [])
        with lock:
            if P["status"] != "arming":
                return
        ready = threading.Event(); box = {}
        t_exit = threading.Thread(target=lambda: box.update(v=exit_test(P, stake, tag, urls, ready)), daemon=True); t_exit.start()
        if not S.BACKRUN:
            backfill(P)
            at = outsider_before_fire(P)
        ready.set(); t_checks.join(GUARD_WAIT_S + GUARD_TIMEOUT_S)
        if "why" not in checks:
            checks.update(why="guard", meas={"error": "the code size and supply checks did not answer"})
        why, meas = checks["why"], checks["meas"]
        with lock:
            if P["status"] != "arming":
                return
            if why:
                return skip_pair(P, why, **meas)
            if not S.BACKRUN and at is not None:
                return skip_pair(P, "outsider before our fire", block=at)
            if reserves(P)[2] is not None or P["pull_pending"] is not None:
                return skip_pair(P, "pulled before our fire")
            r_eth, r_tok, _ = reserves(P)
            log({"ev": "arm", "pair": P["pair"], "token": P["token"], "block": P["N"], "tier": P["tier"], "r_eth_wei": r_eth, "r_tok": r_tok, "followed": len(pairs)})
        t_exit.join(GUARD_WAIT_S + 2 * GUARD_TIMEOUT_S + 2)
        v = box.get("v") or {"tokens": None, "expect_tokens": None, "eth_back_wei": None, "quote_wei": None, "ratio": None, "verdict": "unreadable", "ms": None, "src": None,
                             "error": "the exit test did not answer"}
        with lock:
            P["guard"] = v; state["guard_ms_last"] = v["ms"]
            log({"ev": "guard", "pair": P["pair"], "token": P["token"], "block": P["N"], "stake_wei": stake, **v, **meas})
            if P["status"] != "arming":
                return
            if v["verdict"] != "ok":
                return skip_pair(P, "guard", verdict=v["verdict"], ratio=v["ratio"], error=v["error"])
            P["status"] = "armed"; try_fire(P)
    except Exception as e:
        alarm(f"the guard failed: {type(e).__name__}: {scrub(e, 120)}", pair=P["pair"], trace=traceback.format_exc()[-400:])
        with lock:
            if P["status"] == "arming":
                skip_pair(P, "guard", verdict="unreadable", error=scrub(e, 120))


# ---------------------------------------------------------------- the confirmed feed's logs
def on_head(n, ts, base_fee, src):
    if src == "ws":
        state["ws_last"] = mono()
        if state["ws_subs"] >= 2 and state["ws_from"] is None:
            state["ws_from"] = n                                                   # the first head this connection covers: the gap to it is read
        ws_covers(n)
    if state["head"] is None or n > state["head"]:
        state.update({"head": n, "head_ts": ts, "base_fee": base_fee or state["base_fee"], "head_src": src})
        if src == "ws" and ts:
            lag = round(now() - ts, 3); state["lag_s"] = lag; state["lag_max_s"] = max(lag, state["lag_max_s"] or lag)
        for P in pairs.values():
            if P["ts"] is None and P["N"] == n and ts:
                P["ts"] = ts


def ws_covers(n):
    """a head or a log of block n on a connection whose gap is filled: every log of n - 1 came before it"""
    if state["ws_from"] is not None and state["logs_to"] is not None and state["logs_to"] >= state["ws_from"]:
        state["logs_to"] = max(state["logs_to"], n - 1)


def on_ws_log(lg):
    state["ws_last"] = state["ws_log_at"] = mono()
    if order(lg)[0] >= 0:
        ws_covers(order(lg)[0])
    on_log(lg)


def on_log(lg):
    """one log of the confirmed feed (the websocket or eth_getLogs): the factory's PairCreated, or a followed pair's Mint, Burn, Swap, Sync;
    deduped by (blockHash, logIndex); removed: its effect dropped"""
    try:
        key = (lg["blockHash"].lower(), int(lg["logIndex"], 16)); B = int(lg["blockNumber"], 16); t0 = lg["topics"][0].lower(); addr = (lg.get("address") or "").lower()
    except Exception as e:
        alarm(f"a log was not understood: {type(e).__name__}: {scrub(e, 80)}", quiet_key="badlog", every_s=60); return
    if lg.get("removed"):
        if seen.pop(key, None) is not None:
            unapply(lg, B, key[1], t0, addr)
        return
    if key in seen:
        state["dups"] += 1; return
    seen[key] = B
    try:
        if addr == S.FACTORY:
            if t0 == T_PC:
                on_pair_created(lg, B)
        elif t0 in PAIR_TOPICS:
            P = pairs.get(addr)
            if P is not None:
                apply(P, lg)
            elif state["head"] is None or B >= state["head"] - 64:
                orphans.setdefault(addr, collections.deque(maxlen=64)).append(lg)   # its PairCreated may come behind it (a gap fill)
    except Exception as e:
        alarm(f"a log was not understood: {type(e).__name__}: {scrub(e, 80)}", quiet_key="badlog", every_s=60, block=B, trace=traceback.format_exc()[-300:])


def unapply(lg, B, li, t0, addr):
    """a removed log (a reorg): its event out of the pair's (the state is folded again); an untraded pair's PairCreated drops the pair"""
    state["reorgs"] += 1
    alarm(f"a log was removed (a reorg at block {B}): its effect is dropped", quiet_key="reorg", address=addr, kind=t0[:10])
    if addr == S.FACTORY and t0 == T_PC:
        pair = A(lg["data"], 0); P = pairs.get(pair)
        if P is not None and pair not in positions and P["trade"] is None:
            pairs.pop(pair, None)
        return
    P = pairs.get(addr)
    if P is not None and (P["ev"].get((B, li)) or {}).get("bh") == lg["blockHash"].lower():
        P["ev"].pop((B, li)); P["kick"] = True


def apply(P, lg):
    d = lg["data"]; B, li = order(lg); txh = lg["transactionHash"].lower(); bh = lg["blockHash"].lower(); t0 = lg["topics"][0].lower()
    if t0 == T_SYNC:
        e = {"k": "sync", "r0": W(d, 0), "r1": W(d, 1), "tx": txh, "bh": bh}
    elif t0 == T_MINT:
        e = {"k": "mint", "a0": W(d, 0), "a1": W(d, 1), "tx": txh, "bh": bh}
        if P["r_eth0"] == 0:
            P["r_eth0"], P["r_tok0"] = (e["a0"], e["a1"]) if P["weth_is0"] else (e["a1"], e["a0"])
    elif t0 == T_BURN:
        e = {"k": "burn", "a0": W(d, 0), "a1": W(d, 1), "to": topic_addr(lg["topics"][2]), "tx": txh, "bh": bh}
    elif t0 == T_SWAP:
        e = {"k": "swap", "a0in": W(d, 0), "a1in": W(d, 1), "a0out": W(d, 2), "a1out": W(d, 3), "sender": topic_addr(lg["topics"][1]), "to": topic_addr(lg["topics"][2]), "tx": txh, "bh": bh}
    else:
        return
    P["ev"][(B, li)] = e; P["kick"] = True
    if e["k"] == "swap":
        on_swap(P, B, li, e)
    elif e["k"] == "burn":
        on_pull(P, B, "logs", tx=txh, eth_out=e["a0"] if P["weth_is0"] else e["a1"], at=(B, li))


def buy_behind(pos, B, li):
    """our buy is in ahead of a confirmed swap at (B, li): dry, its block is before B; live, its Swap (or its Flashblock) is before"""
    if pos["dry"]:
        return pos["D"] < B
    if pos["buy_at"] is not None:
        return pos["buy_at"] < (B, li)
    if pos["buy_block"] is not None:
        return pos["buy_block"] < B
    return pos.get("buy_seen") is not None and pos["buy_seen"][0] <= B


def on_swap(P, B, li, e):
    """a confirmed Swap on a followed pair: our own (the buy's or the sell's inclusion); a buy (the fleet's: its first block; the probe's,
    the creator's, an outsider's: the `outsider_buy` line and, on our pair, the instant sell; before our fire, an outsider skips the pair);
    a sell (the dump rule for the tier; the fleet's first sell on our pair: the exit)"""
    eth_in, tok_out, tok_in, eth_out = sides(P, e); pos = positions.get(P["pair"]); who = who_of(P, e["tx"], e["to"])
    if who == "ours":
        if pos is not None and not pos["dry"]:
            if eth_in > 0 and pos["buy_at"] is None and (pos["buy_hash"] is None or e["tx"] == pos["buy_hash"]):
                pos.update(buy_at=(B, li), buy_block=B, buy_index=li, eth_in=eth_in, tokens=pos["tokens"] or tok_out)
            elif tok_in > 0 and e["tx"] == pos.get("sell_hash"):
                pos.update(sell_at=(B, li), sell_block=B)
        return
    if eth_in > 0:
        P["last_buy"] = B; b = {"B": B, "li": li, "tx": e["tx"], "to": e["to"], "eth": eth_in, "who": who}; P["buys"].append(b)
        if who == "fleet":
            P["fleet_first"] = B if P["fleet_first"] is None else P["fleet_first"]; return
        action = "none"
        if who == "outsider":
            P["last_outsider"] = B; P["first_outsider"] = B if P["first_outsider"] is None else P["first_outsider"]
            if P["status"] == "armed":                                         # (pending or arming: the arm's read decides once the senders are known)
                skip_pair(P, "outsider before our fire", block=B, tx=e["tx"]); action = "skip"
            elif pos is not None and not pos["closed"] and not pos["sell_sent"] and pos["trigger"] is None and eth_in >= S.OUTSIDER_MIN_WEI and buy_behind(pos, B, li):
                pos["trigger"] = {"exit": "outsider", "block": B, "via": "logs", "price_block": B + 1, "reason": f"an outsider's buy ({eth_in / 1e18:.6f} ETH) confirmed at {B}, behind ours"}
                action = "sell"
        if e["tx"] not in P["logged_txs"]:
            P["logged_txs"].add(e["tx"])
            rec = {"ev": "outsider_buy", "pair": P["pair"], "tier": P["tier"], "block": B, "pending": False, "tx": e["tx"], "sender": state["tx_from"].get(e["tx"]), "to": e["to"],
                   "value_eth": eth_in / 1e18, "via": "logs", "ours": pos is not None, "action": action, "who": who}
            if rec["sender"] is None:
                spawn(log_resolved, P, rec, b)                                  # the sender read: a Swap's `to` is the recipient (the probe's is not the probe)
            else:
                log(rec)
    elif tok_in > 0:
        r_eth_after = reserves(P, (B, li))[0]; before = r_eth_after + eth_out
        if before > 0 and eth_out * 10 ** 6 >= before * S.PULL_SHARE_PPM:
            tier_end(P["tier"], f"a sell took {eth_out / before:.0%} of the ETH reserve on {P['pair']} at +{B - P['N']} (BASE_V2_PULL_SHARE)")
        if pos is not None and not pos["closed"] and not pos["sell_sent"] and pos["trigger"] is None and buy_behind(pos, B, li):
            if who == "fleet":
                pos["trigger"] = {"exit": "fleet_sell", "block": B, "via": "logs", "price_block": B + 1, "reason": f"the fleet's first sell ({eth_out / 1e18:.6f} ETH out) at {B}"}
            elif state["tx_from"].get(e["tx"]) is None:
                spawn(resolve_fleet_sell, P, pos, e, B, li, eth_out)           # a roster wallet's sell through the router shows the router as `to`


def log_resolved(P, rec, b):
    sender = read_sender(b["tx"])
    with lock:
        who = who_of(P, b["tx"], b["to"], sender); rec.update(sender=sender, who=who); b["who"] = who
        if who == "fleet":
            P["fleet_first"] = b["B"] if P["fleet_first"] is None else P["fleet_first"]; return
        if who != "outsider" and rec["action"] == "skip" and P["status"] == "watched":
            rec["action"] = "skip"                                             # (the skip stands: the fire's window is gone)
    log(rec)


def resolve_fleet_sell(P, pos, e, B, li, eth_out):
    sender = read_sender(e["tx"])
    with lock:
        if sender in state["roster"] and not pos["closed"] and not pos["sell_sent"] and pos["trigger"] is None:
            pos["trigger"] = {"exit": "fleet_sell", "block": B, "via": "logs", "price_block": B + 1, "reason": f"the fleet's first sell ({eth_out / 1e18:.6f} ETH out) at {B}"}
            end_burst()


def our_buy_block(P, pos):
    if P["trade"] is not None:
        return P["trade"]["buy_block"]
    return (pos["D"] if pos["dry"] else pos["buy_block"]) if pos is not None else None


def sell_landed(pos, B):
    return pos.get("sell_at") is not None or (pos["dry"] and pos.get("X") is not None and B > pos["X"])


def on_pull(P, B, via, pending=False, tx=None, eth_out=None, at=None):
    """a pull (a Burn on the pair, or the creator's pull call seen pending): the `pull` line; before our fire the pair is skipped; the tier's
    rules (section 7); a traded pair's halt rule. An open position's own outcome is decided by check_position and the settlement"""
    pos = positions.get(P["pair"]); ours = pos is not None or P["trade"] is not None
    before = "fire" if P["status"] in ("pending", "arming", "armed") else "sell" if pos is not None and not pos["closed"] and not sell_landed(pos, B) else "after"
    since_c = B - P["N"]; slb = (B - P["last_buy"]) if P["last_buy"] is not None else None; so = (B - P["last_outsider"]) if P["last_outsider"] is not None else None
    trig = [x for x in (P["last_outsider"], our_buy_block(P, pos)) if x is not None]
    reaction = bool(trig) and 0 <= B - max(trig) <= S.REACT_BLOCKS
    if not P["pull_logged"] or (P["pull_logged"] == "pending" and not pending):
        log({"ev": "pull", "pair": P["pair"], "tier": P["tier"], "block": B, "pending": pending, "tx": tx, "eth_out_wei": eth_out, "since_creation": since_c, "since_last_buy": slb,
             "since_outsider": so, "reaction": reaction, "before": before, "ours": ours, "via": via})
        P["pull_logged"] = "pending" if pending else True
    if pending:
        P["pull_pending"] = B
    else:
        P["ended"] = True
    if before == "fire":
        skip_pair(P, "pulled before our fire", block=B, pending=pending)
    if pending:
        return
    if since_c < S.SCHEDULE_MIN:
        tier_end(P["tier"], f"a Burn at +{since_c} on {P['pair']}, earlier than BASE_V2_SCHEDULE_MIN {S.SCHEDULE_MIN}")
    if so is not None and 0 <= so <= S.REACT_BLOCKS:
        tier_end(P["tier"], f"a Burn at +{since_c} on {P['pair']}, {so} blocks after an outsider's buy (BASE_V2_REACT_BLOCKS {S.REACT_BLOCKS}): a reaction")
    if P["trade"] is not None:
        react_check(P, B, at)


def react_check(P, B, at):
    """a Burn on a pair we traded, seen after the settlement: before our sell (the trade booked was -100%), or within REACT_BLOCKS after our
    buy, with no outsider's buy between ours and it: we were the trigger, the line halts"""
    t = P["trade"]
    if P["halt_checked"] or t["buy_block"] is None or t["exit"] in ("buy_reverted", "unsent"):
        return
    P["halt_checked"] = True
    between = any(b["who"] == "outsider" and b["B"] >= t["buy_block"] and (at is None or (b["B"], b["li"]) < at) for b in P["buys"])
    if between:
        return
    if t["exit"] != "pulled" and t.get("sell_at") is not None and at is not None and at < t["sell_at"]:
        halt(f"pulled: a Burn at block {B} before our sell at {t['sell_at'][0]} was seen after the settlement: the trade was -100%", P["tier"], P["pair"])
    elif B - t["buy_block"] <= S.REACT_BLOCKS:
        halt(f"reaction: the Burn landed {B - t['buy_block']} blocks after our buy at {t['buy_block']} with no outsider before it (BASE_V2_REACT_BLOCKS "
             f"{S.REACT_BLOCKS}): the tier reacts to us", P["tier"], P["pair"])


# ---------------------------------------------------------------- the Flashblocks feed
def flash_watch():
    """the hex strings that make a pending transaction worth decoding: the create selector, the followed pairs' tokens"""
    return {S.CREATE_SELECTOR} | {P["token"][2:] for P in pairs.values()}


def on_flash(m):
    """one Flashblocks message: brotli JSON; the pending block's number, timestamp and base fee, then its new raw transactions"""
    try:
        if isinstance(m, (bytes, bytearray)):
            import brotli
            m = brotli.decompress(m)
        d = json.loads(m)
        md = d.get("metadata") or {}; base = d.get("base") or {}
        N = int(base["block_number"], 16) if base.get("block_number") else int(md["block_number"])
        txs = (d.get("diff") or {}).get("transactions") or []; idx = int(d.get("index") or 0)
    except Exception as e:
        state["flash_bad"] += 1
        alarm(f"a Flashblocks message was not decoded ({type(e).__name__}): dropped", quiet_key="flashmsg", every_s=600); return
    with lock:
        state.update(flash=True, flash_at=mono()); state["flash_msgs"] += 1; state["flash_total"] += 1
        if base.get("base_fee_per_gas"):
            state["flash_base_fee"] = int(base["base_fee_per_gas"], 16)
        if base.get("timestamp"):
            state["flash_ts"][N] = int(base["timestamp"], 16)
            for k in [k for k in state["flash_ts"] if k < N - 8]:
                del state["flash_ts"][k]
        if state["flash_block"] is None or N > state["flash_block"]:
            state["flash_block"] = N
        watch = flash_watch(); ours = state["ours"]
        for i, raw in enumerate(txs):
            if not isinstance(raw, str):
                continue
            s = raw.lower()
            if s in ours:
                pos, what = ours[s]
                pos.setdefault(what + "_seen", (N, idx, i))
                continue
            if any(x in s for x in watch):
                on_flash_tx(s, N, (N, idx, i))
        end_burst()


def on_flash_tx(s, N, at):
    raw = bytes.fromhex(s[2:]); tx = decode_tx(raw)
    if tx is None or not tx["to"]:
        return
    sel = tx["data"][:4].hex(); to = tx["to"]; dh = tx["data"].hex(); h = None
    if to == S.ROUTER and sel == S.CREATE_SELECTOR:
        on_flash_create(s, raw, tx, N, at); return
    for P in list(pairs.values()):
        if P["token"][2:] not in dh:
            continue
        h = h or "0x" + keccak(raw).hex()
        if to == S.ROUTER and sel == S.PULL_SELECTOR:
            if P["creator"] and tx_from(h, s) == P["creator"] and P["pull_pending"] is None and not P["ended"]:
                on_pull(P, N, "flash", pending=True, tx=h)
        elif tx["value"] > 0 and h not in P["logged_txs"]:
            sender = tx_from(h, s); who = who_of(P, h, sender or "", sender)
            if who in ("fleet", "ours"):
                continue
            pos = positions.get(P["pair"]); action = "none"
            if who == "outsider":
                P["last_outsider"] = N if P["last_outsider"] is None or N > P["last_outsider"] else P["last_outsider"]
                if P["status"] in ("pending", "arming", "armed"):
                    P["first_outsider"] = N if P["first_outsider"] is None else P["first_outsider"]
                    if P["status"] == "armed":
                        skip_pair(P, "outsider before our fire", block=N, pending=True, tx=h)
                    action = "skip"
                elif pos is not None and not pos["closed"] and not pos["sell_sent"] and pos["trigger"] is None and bought_before(pos, N, at):
                    pos["trigger"] = {"exit": "outsider", "block": N, "via": "flash", "price_block": N, "reason": f"an outsider's buy ({tx['value'] / 1e18:.6f} ETH) seen pending at {N}, behind ours"}
                    action = "sell"
            P["logged_txs"].add(h)
            log({"ev": "outsider_buy", "pair": P["pair"], "tier": P["tier"], "block": N, "pending": True, "tx": h, "sender": sender, "to": to, "value_eth": tx["value"] / 1e18,
                 "via": "flash", "ours": pos is not None, "action": action, "who": who})


def bought_before(pos, N, at):
    """our buy is in ahead of a pending transaction at `at` (block, flashblock index, position): dry, its block is before N"""
    if pos["dry"]:
        return pos["D"] < N
    seen_at = pos.get("buy_seen")
    return (pos["buy_block"] is not None and pos["buy_block"] < N) or (seen_at is not None and seen_at < at)


# ---------------------------------------------------------------- the trade
def end_burst():
    """after a batch of feed messages (under the lock): the armed pairs' fire, the late and the expired pairs, the watched pairs' backfill,
    every open position's triggers, deadline and pull"""
    roll_day()
    head = state["head"]
    for P in list(pairs.values()):
        kicked, P["kick"] = P["kick"], False
        if P["status"] == "armed" and kicked:
            try_fire(P)
        if head is None:
            continue
        if P["status"] in ("pending", "arming", "armed"):
            if not P["sealed"] and head >= P["N"] + SEAL_GRACE:
                alarm("a creation seen pending never sealed: dropped", quiet_key="unsealed", every_s=60, pair=P["pair"], block=P["N"]); pairs.pop(P["pair"], None); continue
            if P["sealed"] and P["status"] != "pending" and head >= P["N"] + S.LAND_MAX:
                skip_pair(P, "late", block=P["N"])
        if P["status"] == "watched" and P["sealed"] and P["backfilled"] is None:
            P["backfilled"] = "running"; spawn(backfill, P)
        if (P["ended"] or head > P["N"] + S.WATCH_BLOCKS) and P["pair"] not in positions and P["status"] not in ("pending", "arming", "armed"):
            pairs.pop(P["pair"], None)
    for pos in list(positions.values()):
        check_position(pos)


def try_fire(P):
    """the fire's refusals (each a `skip`), then the fire"""
    if P["status"] != "armed":
        return
    head = state["head"]; N = P["N"]; roll_day()
    if not S.DRY and not state["halted"] and os.path.exists(S.HALT_FILE):         # the owner's file, read again before every live fire
        state["halted"] = read_halt_file()
    stake = stake_for(P); open_ = open_positions(); open_stakes = sum(p["stake"] for p in open_); relay = state["relay_wei"] or 0
    checks = (
        (reserves(P)[2] is None and P["pull_pending"] is None, "pulled before our fire", {}),
        (P["first_outsider"] is None, "outsider before our fire", {"block": P["first_outsider"]}),
        (head is None or head < N + S.LAND_MAX, "late", {"head": head}),
        (len(open_) < S.MAX_POSITIONS, "positions", {"positions": [p["pair"] for p in open_]}),
        (not state["halted"], "halted", {"reason": state["halted"]}),
        (not state["stopped"], "stopped", {"pnl_today_eth": pnl_eth(), "trades_today": state["trades_today"]}),
        (state["tiers_ended"].get(P["tier"]) != state["day"], "tier ended", {}),
        (state["trades_today"] < S.MAX_PER_DAY, "day cap", {"trades_today": state["trades_today"]}),
        (S.DRY or relay >= stake + S.MARGIN_WEI + open_stakes, "relay balance", {"relay_eth": relay / 1e18, "needed_eth": (stake + S.MARGIN_WEI + open_stakes) / 1e18}))
    for ok, why, extra in checks:
        if not ok:
            skip_pair(P, why, **extra); return
    fire(P, stake)


def fire(P, stake):
    expect = cp_out(stake, P["r_eth0"], P["r_tok0"]); min_out = expect * (10 ** 6 - S.BUY_SLIP_PPM) // 10 ** 6
    head = state["head"]; aim = (head if head is not None else P["N"]) + 1
    prio = S.PRIO_WEI
    if S.BACKRUN:
        prio = max(S.PRIO_WEI, (P["prio"] or 0) + 10 ** 6)                      # above the creation's priority: the same block, behind it
        aim = P["N"] if head is None or head < P["N"] else aim
    pos = {"pair": P["pair"], "token": P["token"], "weth_is0": P["weth_is0"], "N": P["N"], "tier": P["tier"], "dry": S.DRY, "stake": stake, "expect": expect, "min_out": min_out,
           "via": P["via"], "aim": aim, "D": aim, "fired_at": mono(), "creation_ts": P["ts"], "prio": prio, "nonce": None, "buy_hash": None, "buy_nonce": None, "buy_at": None,
           "buy_block": None, "buy_index": None, "tokens": None, "eth_in": None, "buy_status": None, "sell_sent": False, "sell_hash": None, "sell_nonce": None, "sell_at": None,
           "sell_block": None, "exit": None, "trigger": None, "sell_reason": None, "sell_via": None, "sell_min_out": None, "resent": False, "no_sell": False, "closed": False,
           "scanned": None, "X": None, "peak": 0.0, "restart": False, "sell_done": False, "sell_refused": False, "sell_receipt": False}
    positions[P["pair"]] = pos; state["trades_today"] += 1; P["status"] = "fired"
    ready_ms = round(1000 * (mono() - P["seen_at"]), 1); state["ready_ms_last"] = ready_ms
    rec = {"pair": P["pair"], "token": P["token"], "tier": P["tier"], "creation": P["N"], "head": head, "aim": aim, "stake_wei": stake, "min_out": min_out, "expect_tokens": expect,
           "nonce": None if S.DRY else state["nonce"], "prio_gwei": prio / 1e9, "max_fee_gwei": min(2 * base_fee() + prio, max(S.MAX_FEE_WEI, prio)) / 1e9, "via": P["via"],
           "ready_ms": ready_ms, "positions": len(positions)}
    if state["trades_today"] >= S.MAX_PER_DAY:
        stop_day(f"BASE_V2_MAX_PER_DAY {S.MAX_PER_DAY} buys")
    if S.DRY:
        log({"ev": "would_fire", "dry": True, **rec}); return
    log({"ev": "fire", "dry": False, **rec})
    save_positions()
    orders.put(("buy", pos, None))


def value_at(pos, r_eth, r_tok):
    """the ETH our tokens get at these reserves; the dry run's buy (not in the recorded reserves) put into them first"""
    tokens = pos["tokens"] if pos["tokens"] is not None else pos["min_out"]
    if pos["dry"]:
        r_eth += pos["stake"]; r_tok -= tokens
    return cp_out(tokens, r_tok, r_eth) if tokens > 0 and r_tok > 0 and r_eth > 0 else 0


def scan_syncs(pos, P):
    """the reserves after every Sync behind our buy, each once: the position's value against the stake (the peak kept); the take-profit"""
    after = (pos["D"], END) if pos["dry"] else pos["buy_at"]
    if after is None or pos["tokens"] is None:
        return None
    start = max(after, pos["scanned"] or after)
    for k in sorted(x for x in P["ev"] if x > start):
        e = P["ev"][k]; pos["scanned"] = k
        if e["k"] != "sync":
            continue
        r_eth, r_tok = (e["r0"], e["r1"]) if P["weth_is0"] else (e["r1"], e["r0"])
        value = value_at(pos, r_eth, r_tok); pos["peak"] = max(pos["peak"], value / pos["stake"] - 1)
        if value * 10 ** 6 >= pos["stake"] * (10 ** 6 + S.TP_PPM):
            return {"exit": "take_profit", "block": k[0], "via": "logs", "price_block": k[0] + 1, "value": value,
                    "reason": f"the reserves at {k[0]} value the position at {value / pos['stake'] - 1:+.2%} (BASE_V2_TAKE_PROFIT)"}
    return None


def hard_exit(pos):
    """the hard block: N + BASE_V2_SELL_SEND_BLOCK reached by the head (or passed by the pending block); the wall clock at the creation's
    timestamp + BASE_V2_SELL_FALLBACK_S when no head came"""
    N = pos["N"]; head = state["head"]
    for via, n in (("head", head), ("flash", state["flash_block"] - 1 if state["flash"] and state["flash_block"] else None)):
        if n is not None and n >= N + S.SELL_SEND_BLOCK:
            return {"exit": "hard", "block": n, "via": via, "price_block": n + 1, "reason": f"the hard block: N + {S.SELL_SEND_BLOCK} reached ({via} {n})"}
    ts = pos.get("creation_ts")
    if ts and now() >= ts + S.SELL_FALLBACK_S:
        b = head if head is not None else N
        return {"exit": "hard", "block": b, "via": "clock", "price_block": b + 1, "reason": f"the wall clock: the creation's timestamp + {S.SELL_FALLBACK_S} s, no head at N + {S.SELL_SEND_BLOCK}"}
    return None


def check_position(pos):
    P = pairs.get(pos["pair"])
    if pos["closed"]:
        return
    if pos["dry"]:
        return check_dry(pos, P)
    if pos["sell_sent"]:
        return maybe_resend(pos)
    if pos["no_sell"] or pos["buy_status"] in ("reverted", "lost") or (pos["buy_block"] is None and pos.get("buy_seen") is None):
        return                                                                 # the sell goes only once our buy is in (its Swap, receipt or Flashblock)
    pull = reserves(P)[2] if P is not None else None; pending = P["pull_pending"] if P is not None else None
    if (pull is not None and (pos["buy_at"] is None or pull > pos["buy_at"])) or pending is not None:
        blk = pull[0] if pull is not None else pending
        trig = {"exit": "pulled", "block": blk, "via": "logs" if pull is not None else "flash", "price_block": blk, "reason": f"the pair was pulled at {blk}, behind our buy: sold at minOut 0"}
    else:
        trig = pos["trigger"] or (scan_syncs(pos, P) if P is not None else None) or hard_exit(pos)
    if trig:
        do_sell(pos, trig)


def maybe_resend(pos):
    """a hard sell unseen (no Flashblock, no Swap, no receipt) by N + BASE_V2_SELL_RESEND_BLOCK: sent again at the same nonce, twice the priority"""
    head = state["head"]
    if pos["exit"] != "hard" or pos["resent"] or not pos.get("sell_done") or pos.get("sell_refused") or pos["sell_hash"] is None:
        return
    if pos.get("sell_seen") or pos["sell_at"] is not None or pos.get("sell_receipt"):
        return
    if head is not None and head >= pos["N"] + S.SELL_RESEND_BLOCK:
        pos["resent"] = True
        orders.put(("resend", pos, None))


def do_sell(pos, trig):
    P = pairs.get(pos["pair"])
    pos.update(sell_sent=True, exit=trig["exit"], sell_reason=trig["reason"], sell_via=trig["via"], sell_block_seen=max(state["head"] or 0, state["flash_block"] or 0))
    if pos["dry"]:
        pos["X"] = trig["price_block"]
        log({"ev": "sell_sent", "dry": True, "pair": pos["pair"], "hash": None, "nonce": None, "block_seen": pos["sell_block_seen"], "reason": trig["exit"], "why": trig["reason"],
             "min_out": None, "via": trig["via"], "deadline": None, "prio_gwei": None, "priced_at_block": pos["X"]}); return
    min_out = 0
    if trig["exit"] in ("take_profit", "fleet_sell") and P is not None:
        r_eth, r_tok, _ = reserves(P); min_out = value_at(pos, r_eth, r_tok) * (10 ** 6 - S.SELL_SLIP_PPM) // 10 ** 6
    pos["sell_min_out"] = min_out
    orders.put(("sell", pos, (min_out, int(now()) + S.SELL_DEADLINE_S, trig)))


def check_dry(pos, P):
    """the dry run: the buy priced once its block is complete, the triggers, the sell priced once the block behind its trigger is complete"""
    lt = state["logs_to"]
    if P is None:
        return close_dry(pos, None, None, "buy_reverted", "the pair's record was dropped")
    if pos["tokens"] is None:
        if lt is None or lt < pos["D"]:
            return
        r_eth, r_tok, pull = reserves(P, (pos["D"], END))
        if pull is not None:
            return close_dry(pos, P, None, "buy_reverted", "the pair was pulled before our buy's block ended")
        tokens = cp_out(pos["stake"], r_eth, r_tok)
        if tokens < pos["min_out"]:
            return close_dry(pos, P, None, "buy_reverted", f"{tokens} tokens at our block, under the buy's minOut {pos['min_out']}")
        pos.update(tokens=tokens, eth_in=pos["stake"], buy_block=pos["D"], buy_index=None)
    if not pos["sell_sent"]:
        pull = reserves(P)[2]
        trig = pos["trigger"] or scan_syncs(pos, P)
        if (pull is not None and (trig is None or pull[0] <= trig["block"])) or P["pull_pending"] is not None:
            return close_dry(pos, P, 0, "pulled", "the pull came before our sell")
        trig = trig or hard_exit(pos)
        if trig:
            do_sell(pos, trig)
    if pos["sell_sent"] and lt is not None and lt >= pos["X"]:
        r_eth, r_tok, pull = reserves(P, (pos["X"], END))
        if pull is not None:
            return close_dry(pos, P, 0, "pulled", "the pull came before our sell")
        close_dry(pos, P, value_at(pos, r_eth, r_tok), pos["exit"], pos["sell_reason"])


def close_dry(pos, P, eth_out, exit_, why):
    gas = gas_est_wei(); stake = pos["stake"]
    if exit_ == "buy_reverted":
        eth_in, eth_out, gas_used, l1 = 0, 0, gas // 2, L1_FEE_EST_WEI // 2
    else:
        eth_in, gas_used, l1 = stake, gas, L1_FEE_EST_WEI
    pull = reserves(P)[2] if P is not None else None
    net = eth_out - eth_in - gas_used
    out = {"buy_block": pos["D"] if exit_ != "buy_reverted" else None, "buy_index": None, "sell_block": pos["X"], "eth_in_wei": eth_in, "tokens": pos["tokens"], "eth_out_wei": eth_out,
           "gas_wei": gas_used, "l1_fee_wei": l1, "net_wei": net, "ret": round(net / stake, 6), "usd": round(net / 1e18 * S.ETH_USD, 4), "exit": exit_, "why": why,
           "pulled_at": pull[0] if pull else None, "buy_hash": None, "sell_hash": None}
    finish_trade(pos, P, out, pull, (pos["X"], END) if pos["X"] is not None else None)


def finish_trade(pos, P, out, pull, sell_at):
    """the close, live or dry: the trade's record on the pair, the halts (pulled or a reaction with no outsider before it; the live loss
    streak; a late live buy), one `trade_done`, the day's stop"""
    pos["closed"] = True; exit_ = out["exit"]; buy_block = out["buy_block"]
    buys = P["buys"] if P is not None else []
    behind = [b for b in buys if buy_block is not None and b["B"] >= buy_block]
    out.update(outsider_at=next((b["B"] for b in behind if b["who"] == "outsider"), None), fleet_first_buy=P["fleet_first"] if P is not None else None,
               fleet_eth=round(sum(b["eth"] for b in behind if b["who"] == "fleet") / 1e18, 6), peak_ret=round(pos["peak"], 6))
    late = not pos["dry"] and buy_block is not None and exit_ != "buy_reverted" and buy_block > pos["N"] + S.LAND_MAX
    if not pos["dry"] and exit_ != "buy_reverted":
        state["loss_streak"] = state["loss_streak"] + 1 if out["net_wei"] < 0 else 0
    if late:
        state["late_count"] += 1
    out["late"] = late; out["loss_streak"] = state["loss_streak"]
    if P is not None:
        P["status"] = "traded"; P["trade"] = {"buy_block": buy_block, "sell_block": out["sell_block"], "sell_at": sell_at, "exit": exit_}
    trade_done(pos, out)
    outsider_between = any(b["who"] == "outsider" and (pull is None or (b["B"], b["li"]) < pull) for b in behind)
    if P is not None and pull is not None and buy_block is not None and exit_ != "buy_reverted" and not outsider_between:
        P["halt_checked"] = True
        if exit_ == "pulled":
            halt(f"pulled: the Burn at block {pull[0]} came at or before our sell (our buy at {buy_block}) with no outsider before it: -100%", pos["tier"], pos["pair"])
        elif pull[0] - buy_block <= S.REACT_BLOCKS:
            halt(f"reaction: the Burn landed {pull[0] - buy_block} blocks after our buy at {buy_block} with no outsider before it (BASE_V2_REACT_BLOCKS {S.REACT_BLOCKS}): "
                 f"the tier reacts to us", pos["tier"], pos["pair"])
    if S.LOSS_STREAK_HALT and not pos["dry"] and state["loss_streak"] >= S.LOSS_STREAK_HALT and not state["halted"]:
        halt(f"{state['loss_streak']} live losses in a row (last {out['ret']:+.1%}, {exit_}): BASE_V2_LOSS_STREAK_HALT", pos["tier"], pos["pair"])
    if S.LATE_HALT and state["late_count"] >= S.LATE_HALT and not state["halted"]:
        halt(f"{state['late_count']} live buys mined past N + BASE_V2_LAND_MAX {S.LAND_MAX} (the last at +{buy_block - pos['N']}): BASE_V2_LATE_HALT", pos["tier"], pos["pair"])


def trade_done(pos, out):
    state["trades_done"] += 1
    state["ours"] = {k: v for k, v in state["ours"].items() if v[0] is not pos}; state["our_hashes"] = {k: v for k, v in state["our_hashes"].items() if v[0] is not pos}
    positions.pop(pos["pair"], None)
    save_positions()
    roll_day(); state["pnl_today_wei"] += out["net_wei"]
    log({"ev": "trade_done", "pair": pos["pair"], "token": pos["token"], "tier": pos["tier"], "creation": pos["N"], **out, "stake_wei": pos["stake"], "min_out": pos["min_out"],
         "expect_tokens": pos["expect"], "via": pos["via"], "aim": pos["aim"], "dry": pos["dry"], "live": not pos["dry"], "trades_today": state["trades_today"], "pnl_today_eth": pnl_eth()})
    if S.DAILY_STOP_WEI and state["pnl_today_wei"] <= -S.DAILY_STOP_WEI:
        stop_day(f"the day's net P&L {pnl_eth()} ETH at -BASE_V2_DAILY_STOP_ETH {S.DAILY_STOP_WEI / 1e18:g}")


# ---------------------------------------------------------------- the trader (the only thread that holds the nonce and signs)
def trader():
    while True:
        kind, pos, arg = orders.get()
        try:
            if kind == "buy":
                send_buy(pos)
            elif kind == "sell":
                send_sell(pos, *arg)
            else:
                send_resend(pos)
        except Exception as e:
            try:
                alarm(f"the trader failed on a {kind}: {type(e).__name__}: {scrub(e, 120)}", trace=traceback.format_exc()[-400:])
                with lock:
                    if kind == "buy":
                        close_unsent(pos, "the buy could not be sent")
                    elif kind == "sell":
                        pos.update(sell_refused=True, sell_done=True)           # the settlement goes on: a re-send, else "sold none"
            except Exception:
                pass


def chain_nonce():
    try:
        return int(read("eth_getTransactionCount", [S.WALLET, "pending"], tries=2), 16)
    except Exception as e:
        alarm(f"the nonce was not read: {scrub(e, 100)}", quiet_key="nonce", every_s=60); return None


def send_signed(pos, what, build, nonce=None, bump=False):
    """sign at the wallet's nonce (or the one given: a replacement) and send; "nonce too low" everywhere: the nonce read again and signed once more"""
    with lock:
        nonce = state["nonce"] if nonce is None else nonce
    for attempt in (0, 1):
        tx = build(nonce); raw, h = sign(tx)
        with lock:
            pos[what + "_hash"] = h; pos[what + "_nonce"] = nonce; pos[what + "_prio"] = tx["maxPriorityFeePerGas"]; pos[what + "_max_fee"] = tx["maxFeePerGas"]
            if what == "sell":
                pos.setdefault("sell_hashes", []).append(h)
            state["ours"][raw] = (pos, what); state["our_hashes"][h] = (pos, what); save_positions()
        kind, replies = post_all(raw)
        if kind != "nonce_low" or attempt or bump:
            break
        n = chain_nonce()
        if n is None or n <= nonce:
            break
        nonce = n
    n = chain_nonce() if kind == "unknown" and not bump else None               # no answer: the chain's count decides (a nonce gap would hold every later send)
    with lock:
        if kind != "rejected" and not bump:
            state["nonce"] = max(state["nonce"] or 0, nonce + 1) if n is None else max(n, nonce if kind == "unknown" else nonce + 1)
    return h, nonce, kind, replies


block_seen = lambda: max(state["head"] or 0, state["flash_block"] or 0)


def send_buy(pos):
    dl = int(now()) + S.BUY_DEADLINE_S
    h, nonce, kind, replies = send_signed(pos, "buy", lambda n: tx_dict(buy_data(pos["token"], pos["stake"], pos["min_out"], dl), S.BUY_GAS, n, pos["prio"]))
    pos["nonce"] = nonce
    log({"ev": "buy_sent", "pair": pos["pair"], "hash": h, "nonce": nonce, "block_seen": block_seen(), "reason": "fire", "min_out": pos["min_out"], "via": "first", "deadline": dl,
         "prio_gwei": pos["prio"] / 1e9, "kind": kind, "replies": replies, "ms_since_fire": round(1000 * (mono() - pos["fired_at"]), 1)})
    if kind == "rejected":
        with lock:
            close_unsent(pos, "the buy was refused by every endpoint")
        return
    spawn(settle_live, pos)


def close_unsent(pos, why):
    alarm(f"{why}: no trade", pair=pos["pair"])
    pos["closed"] = True
    positions.pop(pos["pair"], None); state["trades_today"] = max(0, state["trades_today"] - 1)
    P = pairs.get(pos["pair"])
    if P is not None:
        P["status"] = "traded"; P["trade"] = {"buy_block": None, "sell_block": None, "sell_at": None, "exit": "unsent"}
    save_positions()


def send_sell(pos, min_out, deadline_ts, trig):
    if trig.get("renonce"):                                                    # a re-send: the chain's count (a sell that never landed frees its nonce)
        n = chain_nonce()
        with lock:
            state["nonce"] = n if n is not None else state["nonce"]
    h, nonce, kind, replies = send_signed(pos, "sell", lambda n: tx_dict(sell_data(pos["token"], min_out, deadline_ts), S.SELL_GAS, n))
    log({"ev": "sell_sent", "dry": False, "pair": pos["pair"], "hash": h, "nonce": nonce, "block_seen": pos.get("sell_block_seen"), "reason": trig["exit"], "why": trig["reason"],
         "min_out": min_out, "via": trig.get("send_via", "first"), "deadline": deadline_ts, "prio_gwei": S.PRIO_WEI / 1e9, "kind": kind, "replies": replies})
    if kind == "rejected":
        alarm("the sell was refused by every endpoint", pair=pos["pair"], replies=replies)
    with lock:
        pos.update(sell_refused=kind == "rejected", sell_done=True)            # the final hash is in: the settlement waits on it


def send_resend(pos):
    """the hard sell again at the same nonce with twice the priority (its max fee bumped past the first's): a replacement"""
    nonce = pos["sell_nonce"]; prio = 2 * (pos.get("sell_prio") or S.PRIO_WEI); dl = int(now()) + S.SELL_DEADLINE_S
    h, nonce, kind, replies = send_signed(pos, "sell", lambda n: tx_dict(sell_data(pos["token"], 0, dl), S.SELL_GAS, n, prio, (pos.get("sell_max_fee") or 0) * 11 // 10 + 1),
                                          nonce=nonce, bump=True)
    log({"ev": "sell_sent", "dry": False, "pair": pos["pair"], "hash": h, "nonce": nonce, "block_seen": block_seen(), "reason": pos["exit"], "why": "unseen by N + BASE_V2_SELL_RESEND_BLOCK",
         "min_out": 0, "via": "resend", "deadline": dl, "prio_gwei": prio / 1e9, "kind": kind, "replies": replies})


# ---------------------------------------------------------------- settlement (live)
def wait_receipt(hashes, timeout_s, stop=lambda: False):
    """the first receipt among `hashes` (a replacement's or the original's), None within timeout_s"""
    hashes = [hashes] if isinstance(hashes, str) else list(hashes); t0 = mono()
    while mono() - t0 < timeout_s and not stop():
        for h in hashes:
            try:
                r = read("eth_getTransactionReceipt", [h])
                if r:
                    return r
            except Exception:
                pass
        time.sleep(RECEIPT_POLL_S)
    return None


def gas_of(rec):
    """(gasUsed x effectiveGasPrice + l1Fee, l1Fee) of a receipt, in wei"""
    g = int(rec.get("gasUsed") or "0x0", 16) * int(rec.get("effectiveGasPrice") or "0x0", 16); l1 = int(rec.get("l1Fee") or "0x0", 16)
    return g + l1, l1


def our_swap(rec, pos, kind):
    """our Swap on the pair in a receipt: a buy's (ETH in, tokens out, block, logIndex), a sell's (ETH out, tokens in, block, logIndex); else None"""
    for l in rec.get("logs") or []:
        t = l.get("topics") or []
        if (l.get("address") or "").lower() == pos["pair"] and len(t) >= 3 and t[0].lower() == T_SWAP:
            d = l["data"]; e = {"a0in": W(d, 0), "a1in": W(d, 1), "a0out": W(d, 2), "a1out": W(d, 3)}
            eth_in, tok_out, tok_in, eth_out = sides(pos, e); B, li = int(rec["blockNumber"], 16), int(l["logIndex"], 16)
            if kind == "buy" and eth_in > 0:
                return eth_in, tok_out, B, li
            if kind == "sell" and tok_in > 0:
                return eth_out, tok_in, B, li
    return None


def tokens_in(rec, pos):
    """the tokens of our buy: the token's Transfer(s) to the relay (a fee-on-transfer token pays out less than the Swap says)"""
    return sum(int(l["data"], 16) for l in rec.get("logs") or [] if (l.get("address") or "").lower() == pos["token"] and len(l.get("topics") or []) >= 3
               and l["topics"][0].lower() == T_TRANSFER and l["topics"][2][-40:].lower() == S.RELAY[2:])


def relay_tokens(pos):
    """the relay's balance of the token (None: not read)"""
    try:
        return int(read("eth_call", [{"to": pos["token"], "data": "0x" + SEL_BALANCE_OF + aword(S.RELAY)}, "latest"], tries=2), 16)
    except Exception as e:
        alarm(f"the relay's token balance was not read: {scrub(e, 100)}", pair=pos["pair"]); return None


def chain_pull(pos, to_block):
    """the first Burn on our pair from our buy's block to to_block, by eth_getLogs (the settlement's own read: after a restart or a gap the
    feed's events are not all there); None: none, or the read failed (an alarm)"""
    a = pos["buy_block"] or pos["N"]; err = None
    for attempt in range(4):                                                   # off the trade path: a rate limit is waited out
        try:
            ls = read("eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(max(a, to_block)), "address": pos["pair"], "topics": [T_BURN]}], timeout=SLOW_TIMEOUT_S, tries=1)
            pulls = sorted(order(l) for l in ls if l["topics"][0].lower() == T_BURN)
            return pulls[0] if pulls else None
        except Exception as e:
            err = e; time.sleep(2.0 * (attempt + 1))
    alarm(f"the pull check was not read in 4 tries ({scrub(err, 100)}): the feed's events decide", pair=pos["pair"]); return None


def wait_sell(pos):
    """the sell's final hash (the trader's), or no sell (the buy did not fill); a sell the feeds never decided goes on the clock"""
    t0 = mono()
    while True:
        with lock:
            if pos["no_sell"] or pos.get("sell_done"):
                return not pos["no_sell"]
            if not pos["sell_sent"] and mono() - t0 > BLOCK_S * S.HARD_BLOCK + 120:
                do_sell(pos, {"exit": "hard", "block": state["head"] or 0, "via": "clock", "price_block": None, "reason": "the hard block by the clock: no block came"})
        time.sleep(RECEIPT_POLL_S)


def settle_live(pos):
    try:
        _settle_live(pos)
    except Exception as e:
        alarm(f"settle failed: {type(e).__name__}: {scrub(e, 120)}", pair=pos["pair"], trace=traceback.format_exc()[-500:])
        with lock:
            pos["closed"] = True; positions.pop(pos["pair"], None); save_positions()


def _settle_live(pos):
    rb = wait_receipt(pos["buy_hash"], S.BUY_DEADLINE_S + RECEIPT_GRACE_S)
    if rb is None and (pos["buy_at"] is not None or pos.get("buy_seen")):         # in (its Swap, its Flashblock): never "lost"; asked again
        alarm("our buy is in (its Swap or its Flashblock) but its receipt is not read: still asking", pair=pos["pair"], buy_hash=pos["buy_hash"])
        rb = wait_receipt(pos["buy_hash"], BLOCK_S * S.HARD_BLOCK + RECEIPT_GRACE_S)
    held = relay_tokens(pos) if rb is None and not pos["sell_sent"] else None
    with lock:
        if rb is None and (pos["sell_sent"] or pos["buy_at"] is not None or pos.get("buy_seen") or held):
            pos["buy_status"] = "unread"; pos["tokens"] = pos["tokens"] or held; pos["eth_in"] = pos["eth_in"] or pos["stake"]
            alarm("our buy's receipt was not read but the buy is in: " + ("its sell went" if pos["sell_sent"] else f"the relay holds {held} tokens: sold at minOut 0"),
                  pair=pos["pair"], buy_hash=pos["buy_hash"])
            if not pos["sell_sent"]:
                do_sell(pos, {"exit": "hard", "block": state["head"] or 0, "via": "balance", "send_via": "balance", "price_block": None, "reason": "our buy's receipt was not read: sold at minOut 0"})
        elif rb is None:
            pos["buy_status"] = "lost"
        elif rb.get("status") != "0x1":
            pos["buy_status"] = "reverted"
        else:
            sw = our_swap(rb, pos, "buy"); pos["buy_status"] = "ok"; pos["buy_block"] = int(rb["blockNumber"], 16)
            tokens = tokens_in(rb, pos) or (sw[1] if sw else 0)
            pos.update(tokens=tokens, eth_in=sw[0] if sw else pos["stake"], buy_at=pos["buy_at"] or ((sw[2], sw[3]) if sw else (pos["buy_block"], 0)), buy_index=pos["buy_index"] if pos["buy_index"] is not None else (sw[3] if sw else None))
            if tokens == 0:
                pos["no_tokens"] = True
            if pos.get("restart") and not pos["sell_sent"] and tokens:
                do_sell(pos, {"exit": "hard", "block": state["head"] or 0, "via": "start", "send_via": "first", "price_block": None, "reason": "restart: an open position taken back at the start, sold at once"})
        if (pos["buy_status"] not in ("ok", "unread") or pos.get("no_tokens")) and not pos["sell_sent"]:
            pos["no_sell"] = True
        save_positions()
    sells = []                                                                 # every sell's receipt (a reverted one's gas counts)
    for attempt in range(SELL_RETRIES + 1):
        if not wait_sell(pos):
            break
        rs = wait_receipt(pos.get("sell_hashes") or [], S.SELL_DEADLINE_S + RECEIPT_GRACE_S) if pos.get("sell_hashes") and not pos.get("sell_refused") else None
        if rs:
            with lock:
                pos["sell_receipt"] = True
            sells.append(rs)
        if (rs and rs.get("status") == "0x1" and our_swap(rs, pos, "sell")) or attempt == SELL_RETRIES or pos["buy_status"] not in ("ok", "unread"):
            break
        if chain_pull(pos, int(rs["blockNumber"], 16) if rs else state["head"] or 0) is not None:
            break                                                              # pulled: nothing to sell; settled "pulled"
        why = "was refused" if pos.get("sell_refused") else "reverted" if rs else "has no receipt"
        alarm(f"our sell {why}: sent again at minOut 0 ({attempt + 1} of {SELL_RETRIES})", pair=pos["pair"], hash=pos["sell_hash"])
        with lock:
            pos.update(sell_done=False, sell_refused=False, sell_hashes=[], sell_receipt=False)
            orders.put(("sell", pos, (0, int(now()) + S.SELL_DEADLINE_S, {"exit": pos["exit"], "via": "retry", "send_via": "retry", "renonce": True, "block": state["head"] or 0,
                                                                          "reason": f"re-send {attempt + 1}: the sell {why}"})))
    finish_live(pos, rb, sells)


def finish_live(pos, rb, sells):
    n = chain_nonce()                                                          # every transaction is final: the chain's count, read before the slot frees
    gas = l1 = eth_in = eth_out = 0; tokens = pos["tokens"]; sell_block = None; sell_at = None; rs = sells[-1] if sells else None
    for rec in [rb] + sells:
        if rec:
            g, l = gas_of(rec); gas += g; l1 += l
    if rb and rb.get("status") == "0x1":
        sw = our_swap(rb, pos, "buy"); tokens = tokens_in(rb, pos) or (sw[1] if sw else 0); eth_in = sw[0] if sw else pos["stake"]
    elif pos["buy_status"] == "unread":
        eth_in = pos["eth_in"] or pos["stake"]
    if rs:
        sell_block = int(rs["blockNumber"], 16); sw = our_swap(rs, pos, "sell") if rs.get("status") == "0x1" else None
        if sw:
            eth_out = sw[0]; sell_at = (sw[2], sw[3])
    on_chain = chain_pull(pos, sell_block or state["head"] or 0) if pos["buy_status"] in ("ok", "unread") else None
    with lock:
        P = pairs.get(pos["pair"]); after = pos["buy_at"] or (0, 0)
        pull = min([x for x in ((reserves(P)[2] if P is not None else None), on_chain) if x is not None and x > after], default=None)
        exit_ = pos["exit"]; halt_why = None; why = pos.get("sell_reason")
        if pos["buy_status"] in ("reverted", "lost"):
            exit_ = "buy_reverted"; why = "our buy reverted" if pos["buy_status"] == "reverted" else "no receipt for our buy: it never landed"
        elif pull is not None and (sell_at is None or pull < sell_at):
            exit_ = "pulled"
        elif pos.get("no_tokens"):
            halt_why = "sold none: our buy filled with no tokens (the token's Transfer to the relay is 0): the path is broken"
        elif sell_at is None or eth_out <= 0:
            state["sold_none"] += 1
            halt_why = (f"sold none: the buy filled and the sell got nothing ({'no sell' if not rs else 'reverted' if rs.get('status') != '0x1' else 'no ETH'}, "
                        f"{len(sells)} sell(s) mined): the sell path is broken")
        base_ = eth_in or pos["stake"]; net = eth_out - eth_in - gas
        if n is not None:
            state["nonce"] = n if pos["buy_status"] == "lost" else max(n, state["nonce"] or 0)
        out = {"buy_block": pos["buy_block"], "buy_index": pos["buy_index"], "sell_block": sell_block, "eth_in_wei": eth_in, "tokens": tokens, "eth_out_wei": eth_out, "gas_wei": gas,
               "l1_fee_wei": l1, "net_wei": net, "ret": round(net / base_, 6), "usd": round(net / 1e18 * S.ETH_USD, 4), "exit": exit_, "why": why, "pulled_at": pull[0] if pull else None,
               "buy_hash": pos["buy_hash"], "sell_hash": pos["sell_hash"], "nonce": pos["nonce"]}
        finish_trade(pos, P, out, pull, sell_at)
        if halt_why and not state["halted"]:
            halt(halt_why, pos["tier"], pos["pair"])
        if state["relay_wei"] is not None:
            state["relay_wei"] += eth_out - eth_in


# ---------------------------------------------------------------- positions file
POS_KEYS = ("pair", "token", "weth_is0", "N", "tier", "stake", "expect", "min_out", "via", "aim", "D", "creation_ts", "prio", "nonce", "buy_hash", "buy_nonce", "buy_block",
            "tokens", "sell_sent", "sell_hash", "sell_hashes", "sell_nonce", "sell_prio", "sell_max_fee", "exit", "sell_min_out")


def save_positions():
    if S.DRY:
        return
    data = {"positions": {p["pair"]: {k: p.get(k) for k in POS_KEYS} for p in positions.values() if not p["closed"]}, "t": round(now(), 3)}
    try:
        with open(S.POSITIONS_FILE + ".tmp", "w") as f:
            json.dump(data, f)
        os.replace(S.POSITIONS_FILE + ".tmp", S.POSITIONS_FILE)
    except Exception as e:
        alarm(f"the positions file was not written: {str(e)[:100]}", quiet_key="posfile", every_s=60)


def load_positions():
    """the open positions of base_v2_positions.json ({"positions": {pair: {...}}})"""
    try:
        got = list(((json.load(open(S.POSITIONS_FILE)) or {}).get("positions") or {}).values())
    except FileNotFoundError:
        return []
    except Exception as e:
        alarm(f"the positions file {S.POSITIONS_FILE} was not read ({str(e)[:80]}): check it by hand"); return []
    return [p for p in got if isinstance(p, dict) and p.get("pair")]


def take_back(saved):
    """a live position left open by the last run: its buy's receipt, then the sell's (already sent) or a sell at once (minOut 0)"""
    pos = {"dry": False, "buy_at": None, "buy_index": None, "buy_status": None, "sell_at": None, "sell_block": None, "trigger": None, "no_sell": False, "closed": False, "scanned": None,
           "X": None, "peak": 0.0, "fired_at": mono(), "eth_in": None, "restart": True, "resent": True, "sell_done": False, "sell_refused": False, "sell_receipt": False,
           "sell_reason": None, "sell_via": None, **{k: saved.get(k) for k in POS_KEYS}, "buy_block": None, "tokens": None, "sell_block_seen": state["head"]}
    pos["sell_sent"] = pos["sell_done"] = bool(pos["sell_sent"] and pos["sell_hash"])   # decided but never signed: sold now
    pos["sell_hashes"] = pos.get("sell_hashes") or ([pos["sell_hash"]] if pos["sell_hash"] else [])
    positions[pos["pair"]] = pos
    if pos["buy_hash"]:
        state["our_hashes"][pos["buy_hash"]] = (pos, "buy")
    for h in pos["sell_hashes"]:
        state["our_hashes"][h] = (pos, "sell")
    log({"ev": "alarm", "what": "an open position from the last run is taken back: " + ("its sell's receipt is awaited" if pos["sell_hash"] else "sold at once"),
         "pair": pos["pair"], "buy_hash": pos["buy_hash"], "sell_hash": pos["sell_hash"]})
    spawn(settle_live, pos)


# ---------------------------------------------------------------- the start
def endpoint_chain(url):
    """eth_chainId; a send-only endpoint (the sequencer: "rpc method is not allowed") must answer a malformed transaction with -32602"""
    d = http_json(url, {"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []}, 5)
    if "result" in d:
        return int(d["result"], 16)
    if (d.get("error") or {}).get("code") == -32601:
        d2 = http_json(url, {"jsonrpc": "2.0", "id": 1, "method": "eth_sendRawTransaction", "params": ["0x02"]}, 5)
        if (d2.get("error") or {}).get("code") == -32602:
            return "send-only"
    raise RuntimeError(f"eth_chainId: {scrub(json.dumps(d.get('error')), 120)}")


def start_checks():
    """the RPC's chain (waiting up to START_WAIT_S for it), the alternate's, the archive's (and the pending endpoint's with the back-run), the
    head; live: live_checks"""
    wait, waited = 1.0, 0.0
    while True:
        try:
            chain = endpoint_chain(S.RPC_URL); break
        except Exception as e:
            if waited >= START_WAIT_S:
                raise SystemExit(f"BASE_V2_RPC_URL did not answer for {waited:.0f} s: {scrub(e, 120)}")
            alarm(f"BASE_V2_RPC_URL did not answer at the start ({scrub(e, 120)}): trying again in {wait:.0f} s", quiet_key="start", every_s=60)
            time.sleep(wait); waited += wait; wait = min(30.0, wait * 2)
    need(chain == CHAIN_ID, f"BASE_V2_RPC_URL is chain {chain}, not {CHAIN_ID}")
    chains = {host(S.RPC_URL): chain}
    others = [("BASE_V2_READ_ALT_URL", S.READ_ALT_URL), ("BASE_V2_ARCHIVE_URL", S.ARCHIVE_URL)] + ([("BASE_V2_PENDING_URL", S.PENDING_URL)] if S.BACKRUN else [])
    for name, u in others:
        if not u:
            continue
        try:
            chains[host(u)] = endpoint_chain(u)
        except Exception as e:
            if not S.DRY:
                raise SystemExit(f"{name} did not answer eth_chainId: {scrub(e, 120)}")
            alarm(f"{name} did not answer at the start: {scrub(e, 120)}")
        need(chains.get(host(u), CHAIN_ID) == CHAIN_ID, f"{name} is chain {chains.get(host(u))}, not {CHAIN_ID}")
    info = {"chains": chains, "head": int(read("eth_blockNumber", [], timeout=SLOW_TIMEOUT_S, tries=3), 16)}
    if not S.DRY:
        info.update(live_checks(chains))
    return info


def live_checks(chains):
    """the wallet, its key (locked while the engine runs), the relay (owner, router, weth), the send endpoints, the stake, the roster, the
    balances, the nonce, the guard's self-test"""
    global SIGNER, KEY_LOCK
    from eth_account import Account
    need(S.WALLET, "BASE_V2_WALLET is not set: a live start needs the wallet (deploy/base_wallet.py)")
    need(S.RELAY, "BASE_V2_RELAY is not set: a live start needs the relay (deploy/base_v2_relay_deploy.py)")
    need(S.STAKE_ETH_WEI <= S.STAKE_CAP_WEI, f"BASE_V2_STAKE_ETH {S.STAKE_ETH_WEI / 1e18:g} is over BASE_V2_STAKE_CAP_ETH {S.STAKE_CAP_WEI / 1e18:g}")
    need(load_roster(at_start=True), f"BASE_V2_ROSTER_FILE {S.ROSTER_FILE} is not readable: a live start needs the roster (deploy/base_v2_roster.py)")
    try:
        f = open(S.KEY_FILE)
        key = f.read().strip()
        acct = Account.from_key(key if key.startswith("0x") else "0x" + key); del key
    except Exception as e:
        raise SystemExit(f"BASE_V2_KEY_FILE {S.KEY_FILE} does not hold a key ({type(e).__name__})")
    try:                                                                       # held while the engine runs: deploy/base_wallet.py and base_ops.py
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)                         # test it with flock before they sign (one owner of the nonce)
    except OSError:
        f.close(); raise SystemExit(f"BASE_V2_KEY_FILE {S.KEY_FILE} is locked by another process (the Base engine live, or base_ops signing): not started")
    try:
        _live_reads(acct, chains)
        self_test()
    except BaseException:
        f.close(); raise                                                       # a refused start lets the lock go
    KEY_LOCK = f; SIGNER = acct
    return {"wallet": S.WALLET, "relay": S.RELAY, "relay_eth": state["relay_wei"] / 1e18, "wallet_eth": (state["wallet_wei"] or 0) / 1e18, "nonce": state["nonce"]}


def _live_reads(acct, chains):
    need(acct.address.lower() == S.WALLET, "the key in BASE_V2_KEY_FILE is not BASE_V2_WALLET's")
    for u in S.SEND_URLS:
        try:
            chains[host(u)] = c = endpoint_chain(u)
        except Exception as e:
            raise SystemExit(f"BASE_V2_SEND_URLS {host(u)} did not answer: {scrub(e, 120)}")
        need(c in (CHAIN_ID, "send-only"), f"BASE_V2_SEND_URLS {host(u)} is chain {c}, not {CHAIN_ID}")
    need(len(read("eth_getCode", [S.RELAY, "latest"], tries=3)) > 2, "BASE_V2_RELAY has no code: not a deployed FlipRelayV2")
    for sel, want, name in ((SEL_OWNER, S.WALLET, "owner() is {}, not BASE_V2_WALLET"), (SEL_ROUTER, S.ROUTER, "router() is {}, not BASE_V2_ROUTER"), (SEL_WETH, S.WETH, "weth() is {}, not BASE_V2_WETH")):
        got = "0x" + read("eth_call", [{"to": S.RELAY, "data": "0x" + sel}, "latest"], tries=3)[-40:].lower()
        need(got == want, "the relay's " + name.format(got))
    state["relay_wei"] = int(read("eth_getBalance", [S.RELAY, "latest"], tries=3), 16)
    state["wallet_wei"] = int(read("eth_getBalance", [S.WALLET, "latest"], tries=3), 16)
    if state["relay_wei"] < S.STAKE_WEI_MAX() + S.MARGIN_WEI:
        alarm(f"the relay holds {state['relay_wei'] / 1e18:.6f} ETH, under the stake + margin ({(S.STAKE_WEI_MAX() + S.MARGIN_WEI) / 1e18:g}): no buy until it is funded")
    state["nonce"] = int(read("eth_getTransactionCount", [S.WALLET, "pending"], tries=3), 16)


S.STAKE_WEI_MAX = lambda: min(S.STAKE_ETH_WEI, S.STAKE_CAP_WEI)


def newest_line_pair(back):
    """deploy/base_v2_sim.py's pick: the newest pair of the line (PairCreated with WETH, a Mint >= 1 ETH, the creator at BASE_V2_CREATOR_NONCE)
    in the last `back` blocks on BASE_V2_ARCHIVE_URL: {pair, token, weth_is0, bn, burn} or None"""
    urls = [S.ARCHIVE_URL]; head = int(read_from(urls, "eth_blockNumber", [], timeout=SLOW_TIMEOUT_S, tries=2), 16); w32 = "0x" + aword(S.WETH); found = []
    for a in range(max(0, head - back), head + 1, 5000):
        for pos in (1, 2):
            topics = [T_PC, w32, None] if pos == 1 else [T_PC, None, w32]
            ls = read_from(urls, "eth_getLogs", [{"address": S.FACTORY, "topics": topics, "fromBlock": hex(a), "toBlock": hex(min(a + 4999, head))}], timeout=SLOW_TIMEOUT_S, tries=2)
            found += [(int(l["blockNumber"], 16), l) for l in (ls if isinstance(ls, list) else [])]
    for bn, l in sorted(found, key=lambda x: -x[0]):
        pair = A(l["data"], 0); weth_is0 = topic_addr(l["topics"][1]) == S.WETH; token = topic_addr(l["topics"][2 if weth_is0 else 1])
        ms = read_from(urls, "eth_getLogs", [{"address": pair, "topics": [T_MINT], "fromBlock": hex(bn), "toBlock": hex(bn + 5)}], timeout=SLOW_TIMEOUT_S, tries=2)
        if not ms:
            continue
        eth = W(ms[0]["data"], 0) if weth_is0 else W(ms[0]["data"], 1)
        if eth < 10 ** 18:
            continue
        tx = read_from(urls, "eth_getTransactionByHash", [l["transactionHash"]], timeout=SLOW_TIMEOUT_S, tries=2) or {}
        if int(tx.get("nonce") or "0x0", 16) != S.CREATOR_NONCE or (tx.get("to") or "").lower() != S.ROUTER:
            continue
        bs = read_from(urls, "eth_getLogs", [{"address": pair, "topics": [T_BURN], "fromBlock": hex(bn), "toBlock": hex(head)}], timeout=SLOW_TIMEOUT_S, tries=2)
        return {"pair": pair, "token": token, "weth_is0": weth_is0, "bn": bn, "burn": int(bs[0]["blockNumber"], 16) if bs else None}
    return None


def self_test():
    """the guard's self-test at a live start: the exit test on the newest pair of the line (at +30 when it was pulled already) must answer
    SELLABLE (verdict ok) on BASE_V2_ARCHIVE_URL"""
    try:
        p = newest_line_pair(3000) or newest_line_pair(30000)
        need(p is not None, "the guard's self-test found no pair of the line in the last 30,000 blocks on BASE_V2_ARCHIVE_URL")
        tag = hex(p["bn"] + 30) if p["burn"] else hex(int(read_from([S.ARCHIVE_URL], "eth_blockNumber", [], timeout=SLOW_TIMEOUT_S, tries=2), 16))
        r = read_from([S.ARCHIVE_URL], "eth_call", [{"to": p["pair"], "data": "0x0902f1ac"}, tag], timeout=SLOW_TIMEOUT_S, tries=2)
        r0, r1 = W(r, 0), W(r, 1); r_eth, r_tok = (r0, r1) if p["weth_is0"] else (r1, r0)
        P = new_pair(p["pair"], p["token"], p["weth_is0"], None, 0, "logs"); P.update(r_eth0=r_eth, r_tok0=r_tok)
        P["ev"][(0, 0)] = {"k": "sync", "r0": r0, "r1": r1, "tx": None, "bh": None}
        v = exit_test(P, stake_for(P), tag, [S.ARCHIVE_URL])
    except SystemExit:
        raise
    except Exception as e:
        raise SystemExit(f"the guard's self-test failed: {scrub(e, 160)}")
    log({"ev": "guard", "self_test": True, "pair": p["pair"], "token": p["token"], "block": tag, "stake_wei": stake_for(P), **v})
    need(v["verdict"] == "ok", f"the guard's self-test on {p['pair']} at {tag} answered {v['verdict']} (ratio {v['ratio']}, {v['error']}), not SELLABLE: the exit test is not trusted")


def restore_today():
    """today's fires, P&L, late buys and tier stops from the log (and its .1), so the cap and the stops hold across a restart; the live loss
    streak (reset when the owner removed the halt file it wrote)"""
    roll_day(); d = state["day"]; streak = 0; streak_halted = False; late = 0; tiers = {}; stopped = None
    for path in (S.LOG_PATH + ".1", S.LOG_PATH):
        for line in (open(path).read().splitlines() if os.path.exists(path) else []):
            try:
                e = json.loads(line); ev = e.get("ev")
            except ValueError:
                continue
            if ev == "trade_done" and e.get("live"):
                streak = e.get("loss_streak") if e.get("loss_streak") is not None else streak
            elif ev == "halt" and "LOSS_STREAK" in str(e.get("reason")):
                streak_halted = True
            if datetime.datetime.fromtimestamp(e.get("t", 0), datetime.timezone.utc).strftime("%Y-%m-%d") != d:
                continue
            state["trades_today"] += ev == ("would_fire" if S.DRY else "fire")
            if ev == "trade_done" and bool(e.get("dry")) == S.DRY:
                state["pnl_today_wei"] += int(e.get("net_wei") or 0); late += bool(e.get("late")) and bool(e.get("live"))
            elif ev == "stop" and e.get("what") == "tier" and e.get("tier"):
                tiers[e["tier"]] = d
            elif ev == "stop" and e.get("what") == "day":
                stopped = d
    state["loss_streak"] = 0 if streak_halted and S.LOSS_STREAK_HALT and streak >= S.LOSS_STREAK_HALT and not os.path.exists(S.HALT_FILE) else streak
    state["late_count"] = late; state["tiers_ended"] = tiers
    state["stopped"] = stopped or (d if (S.DAILY_STOP_WEI and state["pnl_today_wei"] <= -S.DAILY_STOP_WEI) or state["trades_today"] >= S.MAX_PER_DAY else None)


def start():
    need(not os.path.basename(S.LOG_PATH).startswith(("HALTED", "engine.jsonl", "flip_engine", "bnb", "base.jsonl")),
         f"BASE_V2_LOG_PATH {S.LOG_PATH} names a halt file or another engine's log: the V2 line logs to its own file (base_v2.jsonl)")
    info = start_checks()
    restore_today()
    if S.DRY:
        load_roster(at_start=True)
    halted_file = read_halt_file() if os.path.exists(S.HALT_FILE) else None
    state["halted"] = None if S.DRY else halted_file                          # dry: the file is the live line's, not the dry run's
    saved = load_positions()
    state["logs_to"] = info["head"] - START_BACK - 2                           # a creation of the last blocks is read back (a restart mid-launch)
    shown = {k: (sorted(v) if isinstance(v, set) else host(v) if k.endswith("_URL") and v else v) for k, v in vars(S).items() if k != "KEY_FILE" and not callable(v)}
    shown["SEND_URLS"] = [host(u) for u in S.SEND_URLS]
    log({"ev": "start", "release": RELEASE, "dry": S.DRY, "head": info["head"], "wallet": S.WALLET or None, "relay": S.RELAY or None, "roster_n": len(state["roster"]),
         "roster_built": state["roster_built"], "positions": [p["pair"] for p in saved], "settings": shown, **{k: v for k, v in info.items() if k not in ("head", "wallet", "relay")},
         "halted": state["halted"], "halt_file": halted_file, "trades_today": state["trades_today"], "pnl_today_eth": pnl_eth(), "loss_streak": state["loss_streak"],
         "tiers_ended": sorted(state["tiers_ended"])})
    if saved and not S.DRY:
        for p in saved:
            take_back(p)
    elif saved:
        alarm(f"BASE_V2_DRY_RUN=1 with {len(saved)} live position(s) open in {S.POSITIONS_FILE}: not sold; start live (with HALTED.base_v2 in place to stop new buys) until they are")
    return info


# ---------------------------------------------------------------- the feeds' loops
spawn = lambda fn, *a: threading.Thread(target=fn, args=a, daemon=True).start()
ws_ssl = lambda url: ssl.create_default_context() if url.startswith("wss") else None
ws_healthy = lambda: bool(state["ws"]) and mono() - state["ws_last"] < S.WS_SILENT_S


def on_ws_message(raw, subs, pend):
    d = json.loads(raw)
    if d.get("id") is not None:
        rid = d["id"]
        if rid in (1, 2):
            if "error" in d:
                raise RuntimeError(f"eth_subscribe refused: {scrub(json.dumps(d['error']), 120)}")
            if "result" not in d:                                                  # publicnode's drop notice: {"id":2,"method":"eth_subscription","params":{"error":...}}
                raise RuntimeError(f"the server dropped subscription {rid}: reconnecting ({scrub(raw, 100)})")
            subs[d["result"]] = "heads" if rid == 1 else "factory"
            with lock:
                state["ws_subs"] = sum(1 for v in subs.values() if v in ("heads", "factory")); state["ws"] = state["ws_subs"] >= 2; state["ws_last"] = mono()
            return
        req = pend.pop(rid, None)
        if req is None:
            return
        kind, pair = req
        with lock:
            P = pairs.get(pair)
            if kind == "sub" and isinstance(d.get("result"), str):
                subs[d["result"]] = pair
                if P is not None:
                    P["sub"] = d["result"]
            elif kind == "sub":
                if P is not None:
                    P["sub_fail_at"] = mono()
                alarm(f"a pair's logs subscription was refused ({scrub(json.dumps(d.get('error')), 100)}): asked again in 5 s", quiet_key="pairsub", every_s=60, pair=pair)
        return
    if d.get("method") != "eth_subscription":
        return
    prm = d["params"]; kind = subs.get(prm.get("subscription")); r = prm.get("result")
    with lock:
        if kind == "heads":
            on_head(int(r["number"], 16), int(r.get("timestamp") or "0x0", 16), int(r.get("baseFeePerGas") or "0x0", 16), "ws")
        elif kind is not None:
            for lg in (r if isinstance(r, list) else [r]):
                on_ws_log(lg)


def ws_down(e):
    with lock:
        was = state["ws"]
        state.update(ws=False, ws_subs=0, ws_from=None)
        for P in pairs.values():
            P["sub"] = None
    alarm(f"the websocket is down ({type(e).__name__}: {scrub(e, 100)}): eth_getLogs over BASE_V2_RPC_URL until it is back", quiet_key="ws", was_up=was)


async def keep_connected(url, session, down):
    """a websocket that reconnects for ever: a pause doubling from 0.5 s to 30 s, back to 0.5 s after a connection that lasted a minute"""
    import websockets
    backoff = 0.5
    while True:
        t0 = mono()
        try:
            async with websockets.connect(url, ssl=ws_ssl(url), open_timeout=10, max_size=2 ** 24, ping_interval=20, ping_timeout=10) as ws:
                await session(ws)
        except Exception as e:
            down(e)
        backoff = 0.5 if mono() - t0 > 60 else backoff
        await asyncio.sleep(backoff); backoff = min(30.0, backoff * 2)


async def confirmed_session(ws):
    await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_subscribe", "params": ["newHeads"]}))
    await ws.send(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "eth_subscribe", "params": ["logs", {"address": S.FACTORY, "topics": [[T_PC]]}]}))
    subs = {}; pend = {}; last = [mono()]; nid = [10]
    with lock:
        state["ws_log_at"] = mono()                                                # the logs watchdog's clock starts with the connection

    async def reader():
        """one plain await per message, never cancelled while frames flow (base_engine's lesson: the websockets assembler asserts when a
        cancelled recv() meets a frame that just arrived); the actions run after every message"""
        while True:
            raw = await ws.recv()
            last[0] = mono()
            try:
                on_ws_message(raw, subs, pend)
            except RuntimeError:
                raise
            except Exception as e:
                alarm(f"a websocket message was not understood: {type(e).__name__}: {scrub(e, 80)}", quiet_key="wsmsg", every_s=60)
            with lock:
                end_burst()

    async def subscriber():
        """one logs subscription per followed pair, added as pairs come and dropped as they go (a send on the open socket beside the reader)"""
        while True:
            await asyncio.sleep(0.1)
            with lock:
                want = {P["pair"] for P in pairs.values()}
                have = {v for v in subs.values() if v not in ("heads", "factory")}; asked = {p for k, p in pend.values() if k == "sub"}
                to_add = [p for p in want - have - asked if pairs[p].get("sub_fail_at") is None or mono() - pairs[p]["sub_fail_at"] > 5]
                to_drop = [(sid, p) for sid, p in list(subs.items()) if p not in ("heads", "factory") and p not in want]
            for p in to_add:
                nid[0] += 1; pend[nid[0]] = ("sub", p)
                await ws.send(json.dumps({"jsonrpc": "2.0", "id": nid[0], "method": "eth_subscribe", "params": ["logs", {"address": p, "topics": [PAIR_TOPICS]}]}))
            for sid, p in to_drop:
                subs.pop(sid, None); nid[0] += 1; pend[nid[0]] = ("unsub", p)
                await ws.send(json.dumps({"jsonrpc": "2.0", "id": nid[0], "method": "eth_unsubscribe", "params": [sid]}))

    async def watchdog():
        """silent for WS_SILENT_S, or heads flowing with no log of a young pair for LOGS_SILENT_S (a reconnected publicnode socket once
        delivered heads and not one log for 33 minutes): the session ends, the reconnection and the gap fill follow"""
        while True:
            await asyncio.sleep(0.25)
            if mono() - last[0] > S.WS_SILENT_S:
                raise asyncio.TimeoutError(f"silent for {S.WS_SILENT_S:g} s")
            with lock:
                stale = bool(young()) and mono() - state.get("ws_log_at", 0.0) > LOGS_SILENT_S
            if stale:
                raise asyncio.TimeoutError(f"heads but no log of a followed pair for {LOGS_SILENT_S:g} s: the logs subscriptions are dead")

    tasks = [asyncio.ensure_future(reader()), asyncio.ensure_future(subscriber()), asyncio.ensure_future(watchdog())]
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        for t in done:
            t.result()                                                         # raises the first exception: the reconnection
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def flash_session(ws):
    while True:
        on_flash(await asyncio.wait_for(ws.recv(), timeout=FLASH_SILENT_S))     # silent for 10 s: reconnected


def flash_down(e):
    with lock:
        state["flash"] = False; state["flash_reconnects"] += 1
    alarm(f"Flashblocks is down ({type(e).__name__}: {scrub(e, 100)}): reconnecting; the confirmed feed trades alone", quiet_key="flash")


confirmed_loop = lambda: keep_connected(S.WS_URL, confirmed_session, ws_down)
flash_loop = lambda: keep_connected(S.FLASH_URL, flash_session, flash_down)


def poll_step():
    """the poller's pass: with the websocket down or silent, the head and the logs (the factory and the followed pairs) one block behind it
    over BASE_V2_RPC_URL; with a gap after a reconnection, the logs to the connection's first head. Never skips: a range is read whole or again"""
    with lock:
        healthy = ws_healthy(); ws_from = state["ws_from"]; lt = state["logs_to"]
    gap = healthy and ws_from is not None and lt is not None and lt < ws_from
    if healthy and not gap:
        return False
    hd = read("eth_getBlockByNumber", ["latest", False], timeout=SLOW_TIMEOUT_S)
    h = int(hd["number"], 16)
    with lock:
        if not healthy:
            if state["head_src"] != "poll" and mono() - state["started_at"] > 15:     # (the websocket's first connection: not an alarm)
                alarm("no websocket: the head and the logs from BASE_V2_RPC_URL", quiet_key="poll")
            on_head(h, int(hd.get("timestamp") or "0x0", 16), int(hd.get("baseFeePerGas") or "0x0", 16), "poll")
        lt = state["logs_to"] if state["logs_to"] is not None else h - START_BACK - 2
        addresses = [S.FACTORY] + [P["pair"] for P in pairs.values()]
    target = min(ws_from, h) if gap else h - POLL_LAG
    if target <= lt:
        return False
    b = min(target, lt + MAX_RANGE)
    logs = read("eth_getLogs", [{"fromBlock": hex(lt + 1), "toBlock": hex(b), "address": addresses, "topics": [[T_PC] + PAIR_TOPICS]}], timeout=SLOW_TIMEOUT_S)
    if not isinstance(logs, list):
        raise ValueError(f"eth_getLogs gave {type(logs).__name__}")
    with lock:
        for lg in sorted(logs, key=order):
            on_log(lg)
        state["logs_to"] = max(state["logs_to"] if state["logs_to"] is not None else b, b); state["filled"] += b - lt
        end_burst()
    return True


def poller():
    fails = 0
    while True:
        try:
            busy = poll_step(); fails = 0
        except Exception as e:
            fails += 1; busy = False
            alarm(f"the poller failed ({type(e).__name__}: {scrub(e, 120)}): trying again", quiet_key="poller", every_s=60, tries=fails)
            time.sleep(min(10.0, 0.5 * 2 ** min(fails, 5)))
        if not busy:
            time.sleep(POLL_S)


def flow():
    log({"ev": "flow", "head": state["head"], "head_ts": state["head_ts"], "lag_s": state["lag_s"], "lag_max_s": state["lag_max_s"], "ws": ws_healthy(), "flash": state["flash"],
         "head_src": state["head_src"], "logs_to": state["logs_to"], "flash_block": state["flash_block"], "flash_msgs_min": state["flash_msgs"], "flash_total": state["flash_total"],
         "flash_reconnects": state["flash_reconnects"], "flash_bad": state["flash_bad"], "dups": state["dups"], "reorgs": state["reorgs"], "filled": state["filled"],
         "creations": state["creations"], "tradable": state["tradable"], "watched": state["watched"], "followed": len(pairs), "positions": [p["pair"] for p in open_positions()],
         "trades_today": state["trades_today"], "pnl_today_eth": pnl_eth(), "trades_done": state["trades_done"], "halted": state["halted"], "stopped": state["stopped"],
         "tiers_ended": sorted(k for k, v in state["tiers_ended"].items() if v == state["day"]),
         "relay_eth": state["relay_wei"] / 1e18 if state["relay_wei"] is not None else None, "wallet_eth": state["wallet_wei"] / 1e18 if state["wallet_wei"] is not None else None,
         "roster_n": len(state["roster"]), "ready_ms_last": state["ready_ms_last"], "guard_ms_last": state["guard_ms_last"]})
    state["flow_at"] = mono(); state["lag_max_s"] = None; state["flash_msgs"] = 0


def tick():
    """every second (under the lock): the Flashblocks health, the roster's mtime, the pruning, the flow line"""
    t = mono()
    if state["flash"] and t - state["flash_at"] > FLASH_SILENT_S:
        state["flash"] = False
    if t - state["roster_at"] > 5:
        state["roster_at"] = t; load_roster()
    head = state["head"]
    if head is not None and t - state.get("pruned_at", 0.0) > 30:
        state["pruned_at"] = t
        for k in [k for k, b in seen.items() if b < head - 300]:
            del seen[k]
        for a in [k for k, q in orphans.items() if not q or int(q[-1]["blockNumber"], 16) < head - 64]:
            del orphans[a]
    end_burst()
    if t - state["flow_at"] >= FLOW_S:
        flow()


async def ticker():
    while True:
        await asyncio.sleep(1.0)
        try:
            with lock:
                tick()
        except Exception as e:                                                 # one bad pass must not end the process mid-trade
            alarm(f"the ticker failed: {type(e).__name__}: {scrub(e, 120)}", quiet_key="tick", every_s=60, trace=traceback.format_exc()[-400:])


def stop(*_):
    """SIGTERM: a last line and out (the open live positions stay in base_v2_positions.json for the next start); run by the loop, between its
    callbacks, so no lock of the main thread is held"""
    log({"ev": "stop", "what": "process", "day": state["day"], "tier": None, "reason": "SIGTERM", "pnl_today_eth": pnl_eth(), "trades_today": state["trades_today"],
         "positions": [p["pair"] for p in open_positions()]}); os._exit(0)


async def run_feeds():
    asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, stop)
    tasks = [confirmed_loop(), ticker()] + ([flash_loop()] if S.FLASH_URL else [])
    await asyncio.gather(*tasks)


def main(argv):
    start()
    if not S.DRY:
        for fn in (trader, upkeep):
            spawn(fn)
    spawn(poller)
    try:
        asyncio.run(run_feeds())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main(sys.argv[1:])
