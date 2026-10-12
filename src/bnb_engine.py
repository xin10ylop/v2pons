#!/usr/bin/env python3
"""bnb_engine: a DRY RUN of one launch line on BNB Chain (research/session_oct12/bnb/REPORT_BNB.md, the survivor 0xc9b7cc61).

The line: PancakeSwap V2 (factory 0xca143ce3, router 0x10ed43c7, WBNB, 25 bps, 0.45 s blocks). The launcher contract 0xc9b7cc61 (a call
with selector 50b6f139, 196 bytes of calldata, msg.value = the pool's BNB) creates a pair and adds its liquidity in the same transaction,
about 177 times a day, with pools of 1, 2.5, 10, 15 and 25 BNB. A crowd of ~136 accounts then buys through the router
(7ff36ab5 swapExactETHForTokens, minOut 0.9999 of the price before each buy, so a buy of ours ahead of them does not revert theirs);
the creator never buys and drains each pool by selling into it on a schedule by size (+997 at the earliest; no Burn was ever seen).
The rule: buy $15 at L+40..58 (BNB_BUY_AT, 50), sell at L+260 (BNB_SELL_AT), skip the 15-BNB pools.

With BNB_LIVE=0 (the default) this program signs nothing and sends nothing: it has no key, no wallet and no transaction code of its own.
It reads the chain and logs what the rule would have done. BNB_LIVE=1 loads src/bnb_live.py (the live path: its own wallet's key from
BNB_KEY_FILE, the pre-buy check, the router calls, the nonce, the halts, the positions file); every `if LIVE:` hook below is a no-op
without it. A websocket newHeads subscription (BNB_WS_URL; eth_blockNumber over BNB_RPC_URL while it is down) gives the head;
for every block (BNB_LAG_BLOCKS behind the head) one eth_getLogs over the factory and every pair being watched returns PairCreated, Sync,
Mint, Burn and Swap. A WBNB PairCreated has its creating transaction read (eth_getTransactionByHash): the launcher and the selector make
it a launch of the line. The pair's own logs give its size (the first Mint's WBNB), the reserves (every Sync), the crowd (each buy's
transaction is read while it can matter: the router, 7ff36ab5, tx.from == the Swap's recipient) and the dump (a sell or a Burn taking
>= BNB_DUMP_SHARE of the WBNB reserve). At the start of block L+BUY_AT the stake (BNB_STAKE_USD at the on-chain WBNB/USDT price) is
priced on the reserves then (would_fire); from there every swap, mint and burn is replayed on a copy of the pool with our buy in it
(exact input, the PancakeSwap formula), and at the start of block L+SELL_AT our tokens are sold on that copy (trade_done, dry: true,
dry_ret net of gas). A dump before that is dry_ret -1.0. The gate before live money (a dump before +997, no crowd buy in +60..+260, a
negative median over the first 10 trades) is logged as alarms ("gate: ..."); nothing halts.

Settings from the environment (/etc/flip/bnb.env on the box). Log: JSONL, one event per line with "ev" and "t", BNB_LOG_PATH.
    python3 src/bnb_engine.py                       # live, from the head
    BNB_LOG_PATH=/tmp/r.jsonl python3 src/bnb_engine.py --replay FROM TO    # past blocks (an archive RPC beyond ~10,000 blocks back)
"""
import os, sys, json, time, asyncio, threading, traceback, statistics, signal, urllib.request, urllib.parse

RELEASE = "bnb-0.2"


def env(k, d=""):
    v = os.environ.get(k)
    return d if v is None or v.strip() == "" else v.split(" #", 1)[0].strip()


def _setting(name, default, lo, hi, integer=False):
    """a number setting within [lo, hi]; anything else stops the start with its name (as the main engine's settings do)"""
    raw = env(name, default)
    try:
        v = int(raw) if integer else float(raw)
    except ValueError:
        raise SystemExit(f"{name} must be a {'whole number' if integer else 'number'}, not {raw!r}")
    if v != v or not lo <= v <= hi:
        raise SystemExit(f"{name} {raw!r} is not in {lo}..{hi}")
    return v


def _sizes(name, default):
    try:
        return sorted({float(x) for x in env(name, default).split(",") if x.strip()})
    except ValueError:
        raise SystemExit(f"{name} must be a comma list of pool sizes in BNB, not {env(name, default)!r}")


WS_URL = env("BNB_WS_URL", "wss://bsc-rpc.publicnode.com"); RPC_URL = env("BNB_RPC_URL", "https://bsc-rpc.publicnode.com")
LOG_PATH = env("BNB_LOG_PATH", "/var/log/flip/bnb.jsonl")                                # --replay refuses this default (the service's log)
LAUNCHER = env("BNB_LAUNCHER", "0xc9b7cc619200418649f9e3fc718e45028dfe9c47").lower(); SELECTOR = env("BNB_SELECTOR", "50b6f139").lower().replace("0x", "")
CALLDATA_LEN = _setting("BNB_CALLDATA_LEN", "196", 0, 100000, True)                       # 0: any length
LIVE_ON = env("BNB_LIVE", "0")
if LIVE_ON not in ("0", "1"):
    raise SystemExit(f"BNB_LIVE must be 0 or 1, not {LIVE_ON!r}")
LIVE_ON = LIVE_ON == "1"                                                                  # 1: src/bnb_live.py trades every BNB_PROBE_EVERY-th launch
STAKE_USD = _setting("BNB_STAKE_USD", "5" if LIVE_ON else "15", 0.01, 10000)              # live: the $5 probe unless set
BUY_AT = _setting("BNB_BUY_AT", "50", 1, 5000, True); SELL_AT = _setting("BNB_SELL_AT", "260", BUY_AT + 1, 20000, True)
SKIP_POOL_BNB = _sizes("BNB_SKIP_POOL_BNB", "15"); POOL_SIZES = _sizes("BNB_POOL_SIZES", "1,2.5,10,15,25")   # a size outside POOL_SIZES: skipped, an alarm
BNB_USD = _setting("BNB_USD", "750", 1, 1e6)                                              # the fallback until the pair is read
USD_PAIR = env("BNB_USD_PAIR", "0x16b9a82891338f9ba80e2d6970fdda79d1eb0dae").lower()     # PancakeSwap V2 USDT/WBNB, read every PRICE_EVERY blocks
PRICE_EVERY = 133                                                                       # blocks, about a minute
GAS_UNITS = _setting("BNB_GAS_UNITS", "370000", 0, 5_000_000, True); GAS_GWEI = _setting("BNB_GAS_GWEI", "0.1", 0, 100)   # approve + buy + sell (verify: ~370k)
DUMP_SHARE = _setting("BNB_DUMP_SHARE", "0.5", 0.01, 1.0)
WATCH_TO = _setting("BNB_WATCH_TO", "8000", SELL_AT, 100000, True)                        # blocks after L a pool is watched for its dump (25 BNB: ~+6,800)
LAG_BLOCKS = _setting("BNB_LAG_BLOCKS", "2", 0, 50, True)                                 # read blocks this far behind the head (a node that just announced a block may not serve its logs yet)
MAX_RANGE = _setting("BNB_MAX_RANGE", "50", 1, 5000, True); MAX_BEHIND = _setting("BNB_MAX_BEHIND", "2000", 10, 100000, True)
RETRY_S = 0.5; RETRY_MAX_S = 10.0                                                      # a range that fails is tried again (doubling pause, capped), never skipped
TX_NULL_TRIES = 6; TX_NULL_PAUSE_S = 0.3                                                # a creating transaction the node does not have yet (null)
START_WAIT_S = 300; WS_STABLE_S = 60                                                    # the start waits this long for the RPC; a connection this old resets the back-off
DEFAULT_LOG = "/var/log/flip/bnb.jsonl"
GATE_DUMP_BEFORE = _setting("BNB_GATE_DUMP_BEFORE", "997", 0, 100000, True); GATE_CROWD_FROM = _setting("BNB_GATE_CROWD_FROM", "60", 0, 100000, True)
GATE_PROBES = _setting("BNB_GATE_PROBES", "10", 1, 1000, True)
FLOW_S = _setting("BNB_FLOW_S", "60", 1, 3600)
CHAIN_ID = 56
FACTORY = "0xca143ce32fe78f1f7019d7d551a6402fc5350c73"; ROUTER = "0x10ed43c718714eb63d5aa57b78b54704e256024e"
WBNB = "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"; CROWD_SELECTOR = "7ff36ab5"
T_PC = "0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9"             # PairCreated(address,address,address,uint256)
T_SYNC = "0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1"           # Sync(uint112,uint112)
T_MINT = "0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f"           # Mint(address,uint256,uint256)
T_BURN = "0xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496"           # Burn(address,uint256,uint256,address)
T_SWAP = "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"           # Swap(address,uint256,uint256,uint256,uint256,address)
PAIR_TOPICS = [T_SYNC, T_MINT, T_BURN, T_SWAP]

state = {"head": None, "head_ts": None, "head_at": 0.0, "head_src": None, "polled_at": 0.0, "poll_wait": 0.5, "done_to": None, "ws": False, "stop": False,
         "launches": 0, "launches_flow": 0, "pairs_wbnb": 0, "pairs_unread": 0, "blocks_flow": 0, "flow_at": time.monotonic(), "trades": [], "median_alarmed": False,
         "price": None, "price_block": None, "fails": 0, "usdt_is_token0": True, "alarms_quiet": {}}
pools = {}                                                                              # pair -> its record (many at once: the pools overlap)
LIVE = None                                                                             # the live path (bnb_live.Live) when BNB_LIVE=1, else None
_log_lock = threading.RLock()


def log(ev):
    ev["t"] = round(time.time(), 3)
    line = json.dumps(ev, separators=(",", ":"))
    with _log_lock:
        with open(LOG_PATH, "a") as f:
            f.write(line + "\n")


def alarm(what, quiet_key=None, every_s=600, **kw):
    """an alarm line; with quiet_key, at most one per every_s seconds for that key (a dead endpoint must not fill the log)"""
    if quiet_key is not None:
        now = time.monotonic(); last = state["alarms_quiet"].get(quiet_key)
        if last is not None and now - last < every_s:
            return
        state["alarms_quiet"][quiet_key] = now
    log({"ev": "alarm", "what": what, **kw})


def host(url):
    """only an endpoint's host is ever logged: a provider's URL may carry its key in the path or the query"""
    try:
        return urllib.parse.urlparse(url).hostname or "?"
    except ValueError:
        return "?"


def scrub(text, n=200, tail=False):
    """text for the log without any endpoint's URL: the whole URL becomes its host, and its path, query and user:password@ go
    wherever they appear alone; the first n characters (the last n with tail, for a trace)"""
    s = str(text)
    for u in (WS_URL, RPC_URL):
        if u:
            s = s.replace(u, host(u))
            try:
                x = urllib.parse.urlparse(u)
            except ValueError:
                continue
            for part, mark in ((x.query, "<query>"), (x.path if len(x.path) > 1 else "", "/<path>"), (x.netloc.rpartition("@")[0], "<user>")):
                if part:
                    s = s.replace(part, mark)
    return s[-n:] if tail else s[:n]


def rpc(method, params, tries=4, timeout=10):
    """one JSON-RPC call, up to `tries` times with pauses of 0.25, 0.5, 1, 2, then 4 s between them (4 tries: 1.75 s of pauses in all;
    6 tries: 7.75 s), so that a public node's rate limit (HTTP 429) passes"""
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(RPC_URL, json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                                         {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"})
            d = json.load(urllib.request.urlopen(req, timeout=timeout))
            if "result" in d:
                return d["result"]
            last = d.get("error")
        except Exception as e:
            last = scrub(e)
        if i < tries - 1:
            time.sleep(min(4.0, 0.25 * 2 ** i))
    raise RuntimeError(f"{method}: {scrub(json.dumps(last))[:200]}")


# ---------------------------------------------------------------- PancakeSwap V2 arithmetic
def amount_out(a, r_in, r_out):
    """PancakeSwap V2 getAmountOut, 25 bps: in*9975*rOut // (rIn*10000 + in*9975), exact integers"""
    if a <= 0 or r_in <= 0 or r_out <= 0:
        return 0
    x = a * 9975
    return x * r_out // (r_in * 10000 + x)


def words(data):
    d = data[2:] if data.startswith("0x") else data
    if len(d) % 64 or not d:
        raise ValueError(f"log data of {len(d) // 2} bytes")
    return [int(d[i:i + 64], 16) for i in range(0, len(d), 64)]


def addr_topic(t):
    return "0x" + t[-40:].lower()


def bnb_usd():
    p = state["price"]
    return p[0] / p[1] if p else BNB_USD


def stake_wei():
    """BNB_STAKE_USD in wei at the pair's price, to the wei from its reserves: stake * 1e18 * r_wbnb // r_usdt"""
    p = state["price"] or (int(round(BNB_USD * 1e6)), 10 ** 6)
    return int(round(STAKE_USD * 1e6)) * p[1] * 10 ** 12 // p[0]


def read_price(tag="latest"):
    r = words(rpc("eth_call", [{"to": USD_PAIR, "data": "0x0902f1ac"}, tag]))
    usd, bnb = (r[0], r[1]) if state["usdt_is_token0"] else (r[1], r[0])
    if usd <= 0 or bnb <= 0:
        raise ValueError("empty USDT/WBNB reserves")
    return usd, bnb


def refresh_price(block, replay=False):
    if state["price_block"] is not None and block - state["price_block"] < PRICE_EVERY:
        return
    state["price_block"] = block
    try:
        state["price"] = read_price(hex(block) if replay else "latest")
    except Exception as e:
        alarm(f"the USDT/WBNB price was not read ({scrub(e)}): the stake is priced at {bnb_usd():.2f} $/BNB", quiet_key="price")


# ---------------------------------------------------------------- the pools
def new_pool(lg, tx, side, token):
    return {"pair": "0x" + lg["data"][26:66].lower(), "token": token, "side": side, "L": int(lg["blockNumber"], 16), "launch_tx": lg["transactionHash"],
            "creator": (tx.get("from") or "").lower(), "value_bnb": int(tx.get("value") or "0x0", 16) / 1e18, "size": None, "skip": None,
            "rq": 0, "rt": 0, "pend": None, "breaks": 0, "fired": False, "sold": False, "q": 0, "tok": 0, "sq": 0, "st": 0,
            "crowd": 0, "crowd_bnb": 0, "crowd_ahead": 0, "crowd_gate": 0, "first_crowd": None, "minout": None, "strangers": 0, "stranger_bnb": 0,
            "unread": 0, "sells": 0, "swaps_before": 0, "entry_swaps": 0, "dump": None, "gaps": 0, "upto": int(lg["blockNumber"], 16)}


def on_pair_created(lg):
    """a WBNB pair whose creating transaction is the launcher's call with its selector (and calldata length) -> a new pool; else None"""
    t0, t1 = addr_topic(lg["topics"][1]), addr_topic(lg["topics"][2])
    if WBNB not in (t0, t1):
        return None
    state["pairs_wbnb"] += 1
    tx, err = None, "null each time"
    for i in range(TX_NULL_TRIES):                                                    # null: the node does not have it yet
        try:
            tx = rpc("eth_getTransactionByHash", [lg["transactionHash"]], tries=6)
        except Exception as e:
            err = scrub(e); break
        if tx:
            break
        time.sleep(TX_NULL_PAUSE_S)
    if not tx:
        state["pairs_unread"] += 1
        alarm(f"a WBNB pair's creating transaction was not read ({err}): a launch may be missed", pair="0x" + lg["data"][26:66].lower(), tx=lg["transactionHash"])
        return None
    if (tx.get("to") or "").lower() != LAUNCHER:
        return None
    inp = (tx.get("input") or "")[2:]
    if inp[:8].lower() != SELECTOR or (CALLDATA_LEN and len(inp) // 2 != CALLDATA_LEN):
        return None
    side = 0 if t0 == WBNB else 1
    return new_pool(lg, tx, side, t1 if side == 0 else t0)


def by_side(p, a0, a1):
    return (a0, a1) if p["side"] == 0 else (a1, a0)


def flush(p):
    """a Sync that no Swap, Mint or Burn followed (a sync() or a transfer to the pair): the copy with our buy moves by the same amounts"""
    bq, bt, aq, at_, _tx, _b = p["pend"]; p["pend"] = None
    if p["fired"] and not p["sold"]:
        p["sq"] = max(0, p["sq"] + aq - bq); p["st"] = max(0, p["st"] + at_ - bt)


def take_pend(p, lg, dq, dt):
    """the reserves before an event, from the Sync that came just before it in the same transaction; the chain check
    (before + the event's amounts == the Sync) breaks only when a log was missed: an alarm, once per pool"""
    pe = p["pend"]
    if pe is None or pe[4] != lg["transactionHash"]:
        bq, bt, ok = p["rq"], p["rt"], False
    else:
        bq, bt, ok = pe[0], pe[1], pe[0] + dq == pe[2] and pe[1] + dt == pe[3]
        p["pend"] = None
    if not ok:
        p["breaks"] += 1
        if p["breaks"] == 1:
            alarm("a pool's reserves do not follow its own logs (a missed log?)", pair=p["pair"], block=int(lg["blockNumber"], 16), tx=lg["transactionHash"])
    return bq, bt


def launch_line(p):
    size = p["size"]
    if any(abs(size - s) < 0.005 for s in SKIP_POOL_BNB):
        p["skip"] = f"pool size {size:g} BNB is skipped (BNB_SKIP_POOL_BNB)"
    elif not any(abs(size - s) < 0.005 for s in POOL_SIZES):
        p["skip"] = f"pool size {size:g} BNB is not one of the line's (BNB_POOL_SIZES)"
        alarm(f"the launcher made a pool of {size:g} BNB, a size the research did not see: not traded", pair=p["pair"])
    state["launches"] += 1; state["launches_flow"] += 1
    log({"ev": "launch", "pair": p["pair"], "token": p["token"], "L": p["L"], "pool_bnb": round(size, 6), "value_bnb": p["value_bnb"], "creator": p["creator"],
         "launch_tx": p["launch_tx"], "wbnb_side": p["side"], "skip": p["skip"]})
    if LIVE:
        LIVE.on_launch(p)                                                               # live: the slot (live or control), the pre-buy check


def classify_buy(p, lg, off, a, bq, bt):
    """a buy before our sell: the crowd's shape (the router, 7ff36ab5, the sender's own account as the recipient) or a stranger"""
    try:
        tx = rpc("eth_getTransactionByHash", [lg["transactionHash"]])
    except Exception:
        tx = None
    inp = ((tx or {}).get("input") or "")[2:]
    if tx is None:
        p["unread"] += 1; p["strangers"] += 1; p["stranger_bnb"] += a
    elif (tx.get("to") or "").lower() == ROUTER and inp[:8] == CROWD_SELECTOR and (tx.get("from") or "").lower() == addr_topic(lg["topics"][2]):
        p["first_crowd"] = off if p["first_crowd"] is None else p["first_crowd"]
        if off < BUY_AT:
            p["crowd_ahead"] += 1
        else:
            p["crowd"] += 1; p["crowd_bnb"] += a
        if off >= GATE_CROWD_FROM:
            p["crowd_gate"] += 1
        exp = amount_out(a, bq, bt)
        if exp and len(inp) >= 72:                                                   # amountOutMin over the output at the price before the buy
            r = int(inp[8:72], 16) / exp; p["minout"] = r if p["minout"] is None else min(p["minout"], r)
    else:
        p["strangers"] += 1; p["stranger_bnb"] += a


def on_dump(p, off, share, kind, lg):
    try:
        frm = (rpc("eth_getTransactionByHash", [lg["transactionHash"]]) or {}).get("from", "").lower()
    except Exception:
        frm = None
    p["dump"] = {"off": off, "share": round(share, 4), "kind": kind, "by_creator": (frm == p["creator"]) if frm else None, "tx": lg["transactionHash"]}
    log({"ev": "dump", "pair": p["pair"], "L": p["L"], "pool_bnb": p["size"], "traded": p["fired"], **p["dump"]})
    if LIVE:
        LIVE.on_dump(p, off)                                                            # live: an open position sold at once; the gate
    if off < GATE_DUMP_BEFORE:
        alarm(f"gate: a dump at +{off}, before +{GATE_DUMP_BEFORE} ({kind}, {share:.0%} of the WBNB reserve, pool {p['size']} BNB)", pair=p["pair"])
    if p["fired"] and not p["sold"]:
        p["sold"] = True
        trade_done(p, -1.0, -1.0, 0, f"the dump at +{off} came before our sell at +{SELL_AT}", pulled=True)
    finish(p)


def on_event(p, lg):
    k = lg["topics"][0]; B = int(lg["blockNumber"], 16); off = B - p["L"]
    if k == T_SYNC:
        r0, r1 = words(lg["data"])[:2]
        if p["pend"]:
            flush(p)
        q, t = by_side(p, r0, r1)
        p["pend"] = (p["rq"], p["rt"], q, t, lg["transactionHash"], B); p["rq"], p["rt"] = q, t
    elif k == T_MINT:
        q, t = by_side(p, *words(lg["data"])[:2])
        take_pend(p, lg, q, t)
        if p["size"] is None:
            p["size"] = q / 1e18; launch_line(p)
        if p["fired"] and not p["sold"] and q > 0 and t > 0 and p["sq"] > 0 and p["st"] > 0:   # liquidity added on the copy pro rata
            tb = q * p["st"] // p["sq"]
            if tb <= t:
                p["sq"] += q; p["st"] += tb
            else:
                p["sq"] += t * p["sq"] // p["st"]; p["st"] += t
    elif k == T_BURN:
        q, t = by_side(p, *words(lg["data"])[:2])
        bq, bt = take_pend(p, lg, -q, -t)
        if p["fired"] and not p["sold"] and bq > 0 and bt > 0:
            p["sq"] -= p["sq"] * q // bq; p["st"] -= p["st"] * t // bt
        if bq > 0 and q >= DUMP_SHARE * bq and p["dump"] is None:
            on_dump(p, off, q / bq, "burn", lg)
    elif k == T_SWAP:
        w = words(lg["data"])[:4]
        q_in, t_in = by_side(p, w[0], w[1]); q_out, t_out = by_side(p, w[2], w[3])
        bq, bt = take_pend(p, lg, q_in - q_out, t_in - t_out)
        if LIVE and LIVE.ours(lg):
            return                                                                      # live: our own buy or sell, out of the dry copy and the counts
        if off < BUY_AT:
            p["swaps_before"] += 1
        elif off == BUY_AT:
            p["entry_swaps"] += 1                                                        # in our buy's block, behind it (we would be first)
        if q_in > q_out:
            a = q_in - q_out
            if off < SELL_AT and not p["skip"] and p["size"] is not None:
                classify_buy(p, lg, off, a, bq, bt)
            if p["fired"] and not p["sold"]:
                o = amount_out(a, p["sq"], p["st"]); p["sq"] += a; p["st"] -= o
        else:
            a, qo = t_in - t_out, q_out - q_in
            if off < SELL_AT:
                p["sells"] += 1
            if p["fired"] and not p["sold"]:
                o = amount_out(a, p["st"], p["sq"]); p["sq"] -= o; p["st"] += a
            if bq > 0 and qo >= DUMP_SHARE * bq and p["dump"] is None:
                on_dump(p, off, qo / bq, "sell", lg)


def advance(p, B):
    """every log of this pool before block B is in: buy at the start of L+BUY_AT, sell at the start of L+SELL_AT, stop watching at L+WATCH_TO"""
    if p["pend"] and p["pend"][5] < B:
        flush(p)
    p["upto"] = max(p["upto"], B - 1); off = B - p["L"]
    if not p["fired"] and off >= BUY_AT and p["pair"] in pools:
        if p["size"] is None and p["skip"] is None:
            p["skip"] = "no liquidity by the buy"; log({"ev": "skip", "pair": p["pair"], "L": p["L"], "why": p["skip"]})
        if not p["skip"]:
            fire(p, B)
    if p["fired"] and not p["sold"] and off >= SELL_AT:
        sell(p, B)
    if off >= WATCH_TO and p["pair"] in pools:
        finish(p)


def fire(p, B):
    """our buy, first in block L+BUY_AT: B (logged as ran_in_block) is the first block whose logs were not yet applied, L+BUY_AT when the
    pool had a log in that block, else a later one with no log of the pool in between (the same reserves)"""
    q = stake_wei(); tok = amount_out(q, p["rq"], p["rt"])
    p["fired"] = True
    if tok <= 0:
        p["sold"] = True; log({"ev": "skip", "pair": p["pair"], "L": p["L"], "why": "no tokens for the stake at +%d" % BUY_AT})
        if LIVE:
            LIVE.on_fire(p, B)                                                          # live: no buy (the position is dropped)
        return
    p["q"], p["tok"], p["sq"], p["st"] = q, tok, p["rq"] + q, p["rt"] - tok
    log({"ev": "would_fire", "dry": True, "pair": p["pair"], "L": p["L"], "at": p["L"] + BUY_AT, "off": BUY_AT, "pool_bnb": p["size"], "stake_wei": q,
         "stake_bnb": q / 1e18, "stake_usd": STAKE_USD, "bnb_usd": round(bnb_usd(), 4), "r_wbnb": p["rq"], "r_token": p["rt"], "tokens": tok,
         "swaps_before": p["swaps_before"], "crowd_ahead": p["crowd_ahead"], "ran_in_block": B})
    if LIVE:
        LIVE.on_fire(p, B)                                                              # live: the buy, minOut from these tokens


def sell(p, B):
    back = amount_out(p["tok"], p["st"], p["sq"]); gas = int(round(GAS_UNITS * GAS_GWEI * 1e9))
    p["sold"] = True
    clean = trade_done(p, (back - p["q"] - gas) / p["q"], (back - p["q"]) / p["q"], back, f"sell at +{SELL_AT}", sold_in=B)
    if p["crowd_gate"] == 0 and clean:
        alarm(f"gate: no crowd buy in +{GATE_CROWD_FROM}..+{SELL_AT} (pool {p['size']} BNB)", pair=p["pair"])
    if LIVE:
        LIVE.on_sell(p, B, back)                                                        # live: the sale; the crowd gate on a traded pool


def trade_done(p, ret, gross, back, why, pulled=False, sold_in=None):
    """the dry result; a trade with a missed log (breaks) or a gap (dropped by a jump: dry_ret null) is not clean: the gate and the
    screen's statistics leave it out"""
    clean = ret is not None and not p["breaks"] and not p["gaps"]
    log({"ev": "trade_done", "dry": True, "pair": p["pair"], "L": p["L"], "pool_bnb": p["size"], "why": why, "clean": clean, "sold_in_block": sold_in,
         "dry_ret": round(ret, 6) if ret is not None else None, "dry_ret_gross": round(gross, 6) if gross is not None else None,
         "stake_wei": p["q"], "tokens": p["tok"], "back_wei": back, "r_wbnb": p["rq"], "r_token": p["rt"], "pulled_before_sell": pulled,
         "crowd_buys": p["crowd"], "crowd_bnb": round(p["crowd_bnb"] / 1e18, 6), "crowd_ahead": p["crowd_ahead"], "crowd_gate": p["crowd_gate"],
         "first_crowd_off": p["first_crowd"], "crowd_minout": round(p["minout"], 6) if p["minout"] is not None else None,
         "strangers": p["strangers"], "stranger_bnb": round(p["stranger_bnb"] / 1e18, 6), "unread_txs": p["unread"], "sells": p["sells"],
         "entry_block_swaps": p["entry_swaps"], "dump_off": p["dump"]["off"] if p["dump"] else None, "breaks": p["breaks"], "gaps": p["gaps"],
         **(LIVE.tag(p) if LIVE else {})})
    if clean:
        gate_probe(ret)
    return clean


def gate_probe(ret):
    """the gate's last rule: a negative median over the first GATE_PROBES clean trades (of this run); later ones are not kept"""
    if len(state["trades"]) >= GATE_PROBES:
        return
    state["trades"].append(ret)
    if len(state["trades"]) == GATE_PROBES and not state["median_alarmed"]:
        m = statistics.median(state["trades"])
        if m < 0:
            state["median_alarmed"] = True
            alarm(f"gate: the median of the first {GATE_PROBES} dry trades is {m:+.2%}")


def finish(p, why=None):
    if pools.pop(p["pair"], None) is None:
        return
    if LIVE:
        LIVE.on_finish(p, why)                                                          # live: a position still open is sold at once
    if p["pend"]:
        flush(p)
    d = p["dump"] or {}
    log({"ev": "pool_done", "pair": p["pair"], "L": p["L"], "pool_bnb": p["size"], "skip": p["skip"], "traded": p["fired"] and p["q"] > 0, "dump_off": d.get("off"),
         "dump_share": d.get("share"), "dump_kind": d.get("kind"), "dump_by_creator": d.get("by_creator"), "watched_to": p["upto"] - p["L"],
         "gaps": p["gaps"], **({"why": why} if why else {})})


# ---------------------------------------------------------------- the block reader
def handle(lg, to_block):
    if lg.get("removed"):
        return
    addr = lg["address"].lower(); B = int(lg["blockNumber"], 16)
    if addr == FACTORY:
        if lg["topics"][0] == T_PC:
            p = on_pair_created(lg)
            if p:
                pools[p["pair"]] = p
                try:
                    own = rpc("eth_getLogs", [{"fromBlock": hex(B), "toBlock": hex(to_block), "address": p["pair"], "topics": [PAIR_TOPICS]}])
                    if not isinstance(own, list):
                        raise ValueError(f"eth_getLogs gave {type(own).__name__}")
                except Exception as e:
                    alarm(f"a launch's own logs were not read ({scrub(e)}): not followed", pair=p["pair"]); finish(p, "logs not read"); return
                for x in sorted(own, key=order):
                    handle_safe(x, to_block)
        return
    p = pools.get(addr)
    if p is None or B < p["L"]:
        return
    advance(p, B)
    if addr in pools:
        on_event(p, lg)


def order(x):
    try:
        return int(x["blockNumber"], 16), int(x["logIndex"], 16)
    except Exception:
        return -1, -1                                                               # malformed: first, and handle_safe reports it


def handle_safe(lg, to_block):
    try:
        handle(lg, to_block)
    except Exception as e:
        p = pools.get(str(lg.get("address", "")).lower()) if isinstance(lg, dict) else None
        if p is not None:
            p["breaks"] += 1                                                         # a log of this pool missed: its trade is not clean
        alarm(f"a log was not understood: {type(e).__name__}: {scrub(e)}", quiet_key="badlog", every_s=60, block=scrub(lg.get("blockNumber") if isinstance(lg, dict) else lg, 20),
              trace=scrub(traceback.format_exc(), 300, tail=True))


def process_range(a, b):
    logs = rpc("eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(b), "address": [FACTORY] + list(pools), "topics": [[T_PC] + PAIR_TOPICS]}])
    if not isinstance(logs, list):
        raise ValueError(f"eth_getLogs gave {type(logs).__name__}")
    for lg in sorted(logs, key=order):
        handle_safe(lg, b)
    for p in list(pools.values()):
        try:
            advance(p, b + 1)
        except Exception as e:
            alarm(f"a pool's step failed: {scrub(e)}", quiet_key="advance", every_s=60, pair=p.get("pair"))
    state["blocks_flow"] += b - a + 1; state["done_to"] = b
    if LIVE:
        LIVE.after_range(b)                                                             # live: the pools of open positions kept for a restart


def current_head():
    """the websocket's newest head; while it is quiet for 3 s, eth_blockNumber every poll_wait s (0.5 s, doubling to 30 s while the
    poll fails, back to 0.5 s on an answer)"""
    now = time.monotonic()
    if now - state["head_at"] < 3:                                                 # (head_at starts at the start: the websocket has 3 s)
        return state["head"]
    if now - state["polled_at"] >= state["poll_wait"]:
        state["polled_at"] = now
        try:
            n = int(rpc("eth_blockNumber", [], tries=1, timeout=5), 16); state["poll_wait"] = 0.5
            if state["head"] is None or n > state["head"]:
                state["head"] = n; state["head_ts"] = None
            if state["head_src"] != "poll" and time.monotonic() - state["head_at"] >= 3:   # no websocket head came in while it was asked
                state["head_src"] = "poll"; log({"ev": "feed_fallback", "head": n, "why": "no head from the websocket for 3 s: eth_blockNumber"})
        except Exception as e:
            state["poll_wait"] = min(30.0, state["poll_wait"] * 2)
            alarm(f"no head: {scrub(e)}", quiet_key="head", every_s=60, retry_s=state["poll_wait"])
    return state["head"]


def step(replay_to=None):
    """one pass of the reader: the next range of blocks up to the head (or replay_to), then the price and the flow line"""
    if replay_to is None:
        head = current_head()
        if head is None:
            return False
        target = head - LAG_BLOCKS
    else:
        target = replay_to
    if state["done_to"] is None:
        state["done_to"] = target - 1
    if target - state["done_to"] > MAX_BEHIND and replay_to is None:
        alarm(f"the reader is {target - state['done_to']} blocks behind: jumping to the head; the pools being watched are dropped")
        for p in list(pools.values()):
            if p["fired"] and not p["sold"]:
                p["sold"] = True; p["gaps"] += 1
                trade_done(p, None, None, 0, "the reader jumped past the sale: no result")
            finish(p, "the reader jumped")
        state["done_to"] = target - 1; state["fails"] = 0
    if target <= state["done_to"]:
        return False
    a = state["done_to"] + 1; b = min(target, state["done_to"] + MAX_RANGE)
    try:
        process_range(a, b); state["fails"] = 0
    except Exception as e:                                                         # never skipped: tried again until it is read (or, live, the jump)
        state["fails"] += 1; wait = min(RETRY_MAX_S, RETRY_S * 2 ** min(state["fails"] - 1, 10))
        alarm(f"blocks {a}..{b} not read ({scrub(e)}): trying again", quiet_key="range", every_s=60, tries=state["fails"], retry_s=wait)
        time.sleep(wait); return True
    refresh_price(state["done_to"], replay=replay_to is not None)
    flow()
    return True


def flow(force=False):
    now = time.monotonic()
    if not force and now - state["flow_at"] < FLOW_S:
        return
    head = state["head"]
    log({"ev": "flow", "head": head, "done_to": state["done_to"], "lag_blocks": (head - state["done_to"]) if head is not None and state["done_to"] is not None else None,
         "head_age_s": round(time.time() - state["head_ts"], 2) if state["head_ts"] else None, "feed": state["head_src"], "ws": state["ws"],
         "blocks": state["blocks_flow"], "launches": state["launches"], "launches_new": state["launches_flow"], "pairs_wbnb": state["pairs_wbnb"],
         "pairs_unread": state["pairs_unread"], "watching": len(pools), "open": sum(1 for p in pools.values() if p["fired"] and not p["sold"]), "bnb_usd": round(bnb_usd(), 4),
         **(LIVE.flow_info() if LIVE else {})})
    state["flow_at"] = now; state["blocks_flow"] = 0; state["launches_flow"] = 0


def reader():
    """the reader's thread: never stops on an error (an alarm, then on); a bug that escapes ends the process so systemd restarts it"""
    try:
        while not state["stop"]:
            try:
                busy = step()
            except Exception as e:
                alarm(f"reader: {type(e).__name__}: {scrub(e)}", quiet_key="reader", every_s=60, trace=scrub(traceback.format_exc(), 400, tail=True)); busy = False
            if not busy:
                flow(); time.sleep(0.05)                                            # a flow line even when no block comes (a stalled head shows)
    except BaseException:
        try:
            log({"ev": "alarm", "what": "the reader crashed", "trace": scrub(traceback.format_exc(), 800, tail=True)})
        finally:
            os._exit(1)


# ---------------------------------------------------------------- the websocket
def on_ws_message(raw):
    d = json.loads(raw)
    if d.get("id") == 1:
        if "error" in d:
            raise RuntimeError(f"eth_subscribe refused: {scrub(json.dumps(d['error']))}")
        return
    if d.get("method") == "eth_subscription":
        h = d["params"]["result"]; n = int(h["number"], 16)
        if state["head"] is not None and n <= state["head"]:
            return False                                                             # not newer: the websocket is not giving the head
        state["head"] = n; state["head_ts"] = int(h["timestamp"], 16) if h.get("timestamp") else None; state["head_at"] = time.monotonic()
        if state["head_src"] != "ws":
            state["head_src"] = "ws"; log({"ev": "feed_heads", "head": n})
        return True
    return False


async def feed_loop():
    import websockets
    backoff = 0.5
    while not state["stop"]:
        try:
            async with websockets.connect(WS_URL, open_timeout=10, max_size=2 ** 22, ping_interval=20, ping_timeout=10) as ws:
                await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_subscribe", "params": ["newHeads"]}))
                state["ws"] = True; log({"ev": "feed_connected", "host": host(WS_URL)}); since = time.monotonic()
                while not state["stop"]:
                    raw = await asyncio.wait_for(ws.recv(), timeout=10)
                    try:
                        if on_ws_message(raw) and time.monotonic() - since >= WS_STABLE_S:
                            backoff = 0.5                                            # reset by heads over a lasting connection only
                    except RuntimeError:
                        raise
                    except Exception as e:
                        alarm(f"a websocket message was not understood: {scrub(e)}", quiet_key="wsmsg", every_s=60)
        except Exception as e:
            log({"ev": "feed_error", "err": scrub(f"{type(e).__name__}: {e}"), "retry_s": backoff})
        state["ws"] = False
        if not state["stop"]:
            await asyncio.sleep(backoff); backoff = min(30.0, backoff * 2)


# ---------------------------------------------------------------- start
def open_positions_warning():
    """BNB_LIVE=0 with live positions left open in the positions file: nothing would sell them; an alarm (no file, nothing logged)"""
    path = env("BNB_POSITIONS_FILE", os.path.join(os.path.dirname(os.path.abspath(LOG_PATH)), "bnb_positions.json"))
    try:
        n = len(json.load(open(path)).get("positions") or {})
    except Exception:
        return
    if n:
        alarm(f"BNB_LIVE=0 with {n} live position(s) open in {path}: they are not sold; set BNB_LIVE=1 (with HALTED.bnb in place to stop new buys) until they are")


def checks():
    """the chain id (waiting for the RPC up to START_WAIT_S, a pause doubling from 1 s to 30 s: a DNS or network failure at boot is not
    an exit), the price pair's side and price, the head"""
    wait, waited = 1.0, 0.0
    while True:
        try:
            chain = int(rpc("eth_chainId", []), 16); break
        except Exception as e:
            if waited >= START_WAIT_S:
                raise SystemExit(f"BNB_RPC_URL did not answer for {waited:.0f} s: {scrub(e)}")
            alarm(f"BNB_RPC_URL did not answer at the start ({scrub(e)}): trying again in {wait:.0f} s", quiet_key="start", every_s=60)
            time.sleep(wait); waited += wait; wait = min(30.0, wait * 2)
    if chain != CHAIN_ID:
        raise SystemExit(f"BNB_RPC_URL is chain {chain}, not {CHAIN_ID}")
    try:
        state["usdt_is_token0"] = rpc("eth_call", [{"to": USD_PAIR, "data": "0x0dfe1681"}, "latest"])[-40:].lower() != WBNB[2:]
        state["price"] = read_price()
    except Exception as e:
        alarm(f"the USDT/WBNB price was not read at the start ({scrub(e)}): {BNB_USD} $/BNB (BNB_USD) until it is")
    try:
        head = int(rpc("eth_blockNumber", []), 16)
    except Exception:
        head = None
    return {"chain": chain, "head": head}


def main(argv):
    global LIVE
    replay = None
    if len(argv) >= 3 and argv[0] == "--replay":
        replay = (int(argv[1]), int(argv[2]))
        if os.path.abspath(LOG_PATH) == DEFAULT_LOG:
            raise SystemExit(f"--replay writes to BNB_LOG_PATH: set it to another file than the service's log {DEFAULT_LOG}")
        if LIVE_ON:
            raise SystemExit("--replay never trades: run it with BNB_LIVE=0")
    if LIVE_ON:                                                                         # the live module by name, so that this file holds no signing code
        LIVE = __import__("bnb_live").Live(sys.modules[__name__])                       # the key read and checked against BNB_WALLET, or a stop
    info = checks()
    if LIVE:
        info.update(LIVE.start(info["head"]))                                           # the halt file, the positions taken back, the worker
    else:
        open_positions_warning()
    log({"ev": "start", "release": RELEASE, "dry_run": LIVE is None, "mode": "replay" if replay else "live", "replay": replay, "ws": host(WS_URL), "rpc": host(RPC_URL),
         "launcher": LAUNCHER, "selector": SELECTOR, "calldata_len": CALLDATA_LEN, "stake_usd": STAKE_USD, "buy_at": BUY_AT, "sell_at": SELL_AT,
         "skip_pool_bnb": SKIP_POOL_BNB, "pool_sizes": POOL_SIZES, "bnb_usd": round(bnb_usd(), 4), "bnb_usd_src": "chain" if state["price"] else "BNB_USD",
         "usd_pair": USD_PAIR, "gas_units": GAS_UNITS, "gas_gwei": GAS_GWEI, "dump_share": DUMP_SHARE, "watch_to": WATCH_TO, "lag_blocks": LAG_BLOCKS,
         "gate": {"dump_before": GATE_DUMP_BEFORE, "crowd_from": GATE_CROWD_FROM, "probes": GATE_PROBES}, **info})
    if replay:
        state["done_to"] = replay[0] - 1; state["price_block"] = None; refresh_price(replay[0], replay=True)
        while state["done_to"] < replay[1]:
            step(replay_to=replay[1])
        flow(force=True); log({"ev": "replay_done", "to": replay[1], "watching": len(pools)}); return
    signal.signal(signal.SIGTERM, lambda s, f: (log({"ev": "stopped"}), os._exit(0)))
    state["head_at"] = time.monotonic()
    threading.Thread(target=reader, daemon=True).start()
    try:
        asyncio.run(feed_loop())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main(sys.argv[1:])
