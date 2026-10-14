#!/usr/bin/env python3
"""base_engine: the front on the 2.433 operator's Uniswap v4 launches on Base (docs/BASE.md, the design; research/session_oct14/base2433).

The line on Base (its five launches of Oct 14, 2026): a fresh launch wallet calls a launcher contract made for the launch (c3e0ff3d, 260 B,
code hash prefix 225f9af97d88) that emits the PoolManager's Initialize at block L: currency0 ETH, currency1 the token (1,526 B, code hash
63ad5291...63bb, the address ending 777), fee 5000, tick spacing 100, a hook made for the launch with address flags 0x80 (beforeSwap). At
L+3 (once L+2) the launch wallet calls the hook (2346bb56, 2.133329 ETH; the 0.133 ETH pools were tests): two ModifyLiquidity, full range,
46141758126452008872416 + 1. The operator's bot buys from L+8 (0x987d5db8, 27f7e6ee, the token in the calldata, 0.15-0.27 ETH, minOut 0.95
of its quote), its 35 wallets sell through the Universal Router from L+12, and the launch wallet pulls (f2f230a8 to the hook) on a ~4.1
minute timer (+126, +128; the 09:42 test pool at +30). The Swap event's sender is the Universal Router for every swap, the bot's included.

ARM on an Initialize of the line's fingerprint (currency0 0, BASE_FEE, BASE_TICK_SPACING, the hook's low 14 address bits BASE_HOOK_FLAGS;
the launch transaction's selector and calldata length from its Flashblocks copy, else eth_getTransactionByHash; the token's code hash in
BASE_TOKEN_CODEHASHES; the launcher's code hash prefix): one `launch` line for every v4 Initialize on Base, armed or skip and why (no read
for a pool that fails the event's own fields). FIRE on the first positive ModifyLiquidity of an armed pool, or earlier on its add seen
pending in a Flashblock (to the hook, BASE_ADD_SELECTOR, from the launch wallet): FlipRelay.buy(key, stake, minOut, deadline), the stake
min(BASE_STAKE_ETH, BASE_STAKE_CAP_ETH), minOut = v4math.buy_out_int at the pool's state x (1 - BASE_BUY_SLIP) (a pending add's liquidity
is value x sqrtPriceX96 / 2^96, a full-range position at the launch price: the chain's to the unit on the 09:42 pool), a type-2
transaction at the wallet's nonce to every BASE_SEND_URLS at once. Refused (a `skip` line): the pool's ETH under BASE_MIN_POOL_ETH (the
pending add's value, or the confirmed add's liquidity at the pool's price), a pull seen, the head past the add's block + BASE_FIRE_MAX, a
position open, halted (BASE_HALT_FILE is read again before every live fire), stopped for the day, BASE_MAX_PER_DAY fires today, the relay
under the stake + BASE_RELAY_MARGIN_ETH. An armed pool with no add by L + BASE_ADD_MAX_BLOCKS expires. SELL (FlipRelay.sell(key, minOut,
deadline), everything the relay holds) on the first of: the bot's buy seen pending (to BASE_BOT_ROUTERS with the token, in a Flashblock
after the one holding our buy: one sequenced ahead of ours is no exit) or confirmed behind ours (that transaction, or a Swap sender in
BASE_BOT_SENDERS, off by default) (`exit: bot`); a confirmed buy behind ours at whose price our tokens are worth the stake x (1 +
BASE_TAKE_PROFIT) + the round trip's estimated gas (`take_profit`); our buy's block + BASE_HOLD_BLOCKS reached by the head or a Flashblock
(`deadline`, minOut 0). A live sell goes only once our buy is in (its Swap, receipt or Flashblock); its minOut is the ETH out at the tracked
price (our buy in it) x (1 - BASE_SELL_SLIP). THE PULL (a negative ModifyLiquidity; a pending f2f230a8 only logs): before our fire the pool
is skipped; after our buy and at or before our sell the trade is -100% (`pulled`, no sell sent if none was) and the line halts; a pull
within BASE_NEAR_MISS_BLOCKS of our buy halts even behind our sell; a sell that sold nothing on a pool not pulled halts ("sold none");
BASE_NONBOT_HALT live trades in a row under BASE_NONBOT_MIN_RET halt (the decoy rule). A halt writes HALTED.base (beside the log; held across
restarts until the owner removes it), stops new buys and still sells what is open. SETTLE from the receipts: the tokens and ETH in from our
buy's Swap (or the token's Transfer to the relay), the ETH out from our sell's, the gas of each = gasUsed x effectiveGasPrice + l1Fee; a
reverted (or never mined) buy is a gas-only loss (`buy_reverted`, no sell sent); one `trade_done`; BASE_DAILY_STOP_USD of losses in a UTC
day stops new buys (`stop`). One position at a time, in base_positions.json ({"positions": {pool: ...}}) beside the log, taken back at a
start: a sell already sent has its receipt waited for, else it is sold at once (minOut 0).

THE DRY RUN (BASE_DRY_RUN=1, the default): everything but sign and send; no key is read. A dry buy lands at the end of the block after the
fire's head (the add's block for a Flashblocks fire, the next for a confirmed one), behind that block's recorded swaps: buy_out_int there
(under its minOut: `buy_reverted`). The sell rules run on the recorded swaps behind it; the dry sell is priced at the end of the block its
trigger was seen in, our buy put into the recorded price (1/sqrtP adds: exact for one range), by v4math.sell_out_int. Gas: DRY_GAS_UNITS x
(the base fee + the priority) + L1_FEE_EST_WEI. A dry halt is held in memory. `would_fire`, `sell_sent`, `trade_done` carry dry: true.

THE FEEDS. Confirmed, required: one websocket (BASE_WS_URL), eth_subscribe newHeads (the clock) and the PoolManager's logs (Initialize,
ModifyLiquidity, Swap), deduped by (blockHash, logIndex); removed: true drops a log's effect (an alarm); a pool's state is folded from its
events in (block, logIndex) order, so a log late or twice changes nothing. A block's logs are complete once a head or log of a later block
came on a connection that covered it. Down or silent for BASE_WS_SILENT_S: the poller reads eth_getBlockByNumber("latest") and eth_getLogs
over BASE_RPC_URL (a block behind its head); a reconnection's first head M has every block from the last complete one to M read by
eth_getLogs: no block is skipped (a failed range is read again). Flashblocks, optional (BASE_FLASH_URL; 0 = off): brotli JSON, a message
that fails to decode is dropped (an alarm); the raw transactions touching an armed pool's hook, a bot router (while a pool is armed or
held) or carrying the launch selector are decoded (types 0, 1, 2, 4; 0x7e deposits skipped), their sender recovered; ours are known by
their bytes. Silent for 10 s: reconnected (flow: flash false). Every fire and sell it advances has its confirmed twin, each done once.
Sends: BASE_SEND_URLS at once over warm connections (with a User-Agent: the sequencer's Cloudflare refuses Python's); the first "ok" or
"already known" counts; "nonce too low" everywhere re-reads the nonce and signs once more. Reads: BASE_RPC_URL (3 s on the trade path),
BASE_READ_ALT_URL once when it fails. Threads: the asyncio loop (both websockets, the 1 s ticker); the poller, the arm reads, the trader (the
only one that holds the nonce and signs), each settlement; the feeds never wait on an RPC; one lock guards the state.

SETTINGS from the environment (/etc/flip/base.env; docs/BASE.md section 5): each checked at the start, a wrong one stops it by name; ETH and
gwei amounts become exact integer wei (decimal text, never a float). A live start (BASE_DRY_RUN=0) needs BASE_WALLET, its key in
BASE_KEY_FILE (flock'ed while the engine runs: base_wallet.py and base_ops.py test the lock before they sign), BASE_RELAY with owner() the
wallet and pm() the PoolManager, the stake within the cap, chain 8453 on every endpoint (the sequencer answers no eth_chainId: a send-only
endpoint must answer a malformed transaction with -32602). A relay under the stake + margin is an alarm, and no buy until it is funded.

LOG: JSONL (BASE_LOG_PATH), "ev" and "t": start, flow (every 60 s), launch, add, fire / would_fire, buy_sent, sell_sent, bot_buy, pull,
trade_done, halt, stop, alarm (one a key every 10 min at most), skip.
    python3 src/base_engine.py                                   # from the environment (dry unless BASE_DRY_RUN=0)
    BASE_LOG_PATH=/tmp/base.jsonl python3 src/base_engine.py     # a dry run anywhere
"""
import os, sys, json, time, ssl, socket, queue, types, fcntl, asyncio, decimal, datetime, threading, traceback, signal, collections
import urllib.request, urllib.parse, urllib.error, http.client
import rlp
from eth_utils import keccak, to_checksum_address
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v4math

RELEASE = "base-0.1"
CHAIN_ID = 8453
Q96 = v4math.Q96
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_TRANSFER = "0x" + keccak(text="Transfer(address,address,uint256)").hex()
SEL_BUY, SEL_SELL, SEL_OWNER, SEL_PM = "5ed06f60", "137f1fdd", "8da5cb5b", "8970cdff"      # contracts/FlipRelay.json
ZERO = "0x" + "00" * 20
UA = "Mozilla/5.0 Chrome/128"                                                   # mainnet-sequencer.base.org's Cloudflare refuses Python's own (error 1010)
DRY_GAS_UNITS = 320_000                  # the round trip's gas used, estimated (the bot's buys used 150-167k through the Universal Router; FlipRelay is direct)
L1_FEE_EST_WEI = 4_200_000_000           # two L1 data fees (the bot's 356 B buys paid 2.09e9 wei each on Oct 14)
READ_TIMEOUT_S = 3.0; SEND_TIMEOUT_S = 4.0; SLOW_TIMEOUT_S = 10.0
RECEIPT_POLL_S = 0.25; POLL_S = 0.5; POLL_LAG = 1; MAX_RANGE = 20; DRAIN_S = 0.003; FLASH_SILENT_S = 10.0; FLOW_S = 60.0
WATCH_BLOCKS = 200                       # a traded pool is watched to L + 200 for its pull (the real pools: +126, +128)
START_WAIT_S = 300; DEFAULT_LOG = "/var/log/flip/base.jsonl"
END = 1 << 62                            # a logIndex after every real one: (block, END) is the end of a block


# ---------------------------------------------------------------- settings
def env(k, d=""):
    v = os.environ.get(k)
    return d if v is None or v.strip() == "" else v.split(" #", 1)[0].strip()


def _setting(name, default, lo, hi, integer=False):
    """a number within [lo, hi]; anything else stops the start naming it (bnb_engine's rule)"""
    raw = env(name, default)
    try:
        v = int(raw, 0) if integer else float(raw)
    except ValueError:
        raise SystemExit(f"{name} must be a {'whole number' if integer else 'number'}, not {raw!r}")
    if v != v or not lo <= v <= hi:
        raise SystemExit(f"{name} {raw!r} is not in {lo}..{hi}")
    return v


def _exact(name, default, lo, hi, scale):
    """a decimal setting as an exact integer of 1/scale units (ETH -> wei: 10**18; gwei -> wei: 10**9; a fraction -> ppm: 10**6), never via a float"""
    raw = env(name, default)
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


def _hexlist(name, default, n):
    out = []
    for x in [x.strip().lower() for x in env(name, default).split(",") if x.strip()]:
        v = x[2:] if x.startswith("0x") else x
        if len(v) != n or any(c not in "0123456789abcdef" for c in v):
            raise SystemExit(f"{name} must be a comma list of {n}-digit hex values, not {env(name, default)!r}")
        out.append("0x" + v)
    return out


def _url(name, default, schemes, v=None):
    v = env(name, default) if v is None else v
    if urllib.parse.urlparse(v).scheme not in schemes or not urllib.parse.urlparse(v).hostname:
        raise SystemExit(f"{name} must be a {'/'.join(schemes)} URL, not {host(v)!r}")
    return v


def settings():
    s = types.SimpleNamespace()
    dry = env("BASE_DRY_RUN", "1")
    if dry not in ("0", "1"):
        raise SystemExit(f"BASE_DRY_RUN must be 0 or 1, not {dry!r}")
    s.DRY = dry == "1"
    s.LOG_PATH = env("BASE_LOG_PATH", DEFAULT_LOG); here = os.path.dirname(os.path.abspath(s.LOG_PATH))
    s.WS_URL = _url("BASE_WS_URL", "wss://base-rpc.publicnode.com", ("wss", "ws"))
    s.RPC_URL = _url("BASE_RPC_URL", "https://base-rpc.publicnode.com", ("https", "http"))      # mainnet.base.org answers eth_getLogs with 429
    s.READ_ALT_URL = "" if env("BASE_READ_ALT_URL") == "0" else _url("BASE_READ_ALT_URL", "https://mainnet.base.org", ("https", "http"))   # 0: none
    s.SEND_URLS = [_url("BASE_SEND_URLS", "", ("https", "http"), x.strip()) for x in env("BASE_SEND_URLS", "https://mainnet-sequencer.base.org,https://mainnet.base.org").split(",") if x.strip()]
    if not s.SEND_URLS:
        raise SystemExit("BASE_SEND_URLS is empty")
    flash = env("BASE_FLASH_URL", "wss://mainnet.flashblocks.base.org/ws")
    s.FLASH_URL = None if flash == "0" else _url("BASE_FLASH_URL", flash, ("wss", "ws"))
    s.WALLET = _addr("BASE_WALLET", "", empty_ok=True); s.RELAY = _addr("BASE_RELAY", "", empty_ok=True)
    s.KEY_FILE = env("BASE_KEY_FILE", "/etc/flip/base.key"); s.PM = _addr("BASE_POOL_MANAGER", "0x498581ff718922c3f8e6a244956af099b2652b2b")
    s.HALT_FILE = env("BASE_HALT_FILE", os.path.join(here, "HALTED.base")); s.POSITIONS_FILE = os.path.join(here, "base_positions.json")
    s.WS_SILENT_S = _setting("BASE_WS_SILENT_S", "10", 1, 600)
    s.LAUNCH_SELECTOR = _hex("BASE_LAUNCH_SELECTOR", "c3e0ff3d", 8); s.LAUNCH_CALLDATA_LEN = _setting("BASE_LAUNCH_CALLDATA_LEN", "260", 0, 100000, True)
    s.LAUNCHER_PREFIX = _hex("BASE_LAUNCHER_CODEHASH_PREFIX", "225f9af97d88", empty_ok=True)
    s.TOKEN_CODEHASHES = set(_hexlist("BASE_TOKEN_CODEHASHES", "0x63ad5291cdef5d82cddf8e5d8d4c48bd6ad1de2394616ab66a6c6c6cceae63bb", 64))
    if not s.TOKEN_CODEHASHES:
        raise SystemExit("BASE_TOKEN_CODEHASHES is empty")
    s.FEE = _setting("BASE_FEE", "5000", 0, 999_999, True); s.TICK_SPACING = _setting("BASE_TICK_SPACING", "100", 1, 32767, True)
    s.HOOK_FLAGS = _setting("BASE_HOOK_FLAGS", "0x80", -1, 0x3fff, True)
    s.ADD_SELECTOR = _hex("BASE_ADD_SELECTOR", "2346bb56", 8); s.PULL_SELECTOR = _hex("BASE_PULL_SELECTOR", "f2f230a8", 8)
    s.BOT_ROUTERS = set(_hexlist("BASE_BOT_ROUTERS", "0x987d5db84d105c1f49391af409cc34c6050fb1d0", 40))
    s.BOT_SENDERS = set(_hexlist("BASE_BOT_SENDERS", "", 40))
    s.MIN_POOL_WEI = _exact("BASE_MIN_POOL_ETH", "1.0", 0, 1_000_000, 10 ** 18); s.ADD_MAX_BLOCKS = _setting("BASE_ADD_MAX_BLOCKS", "10", 1, 1000, True)
    s.STAKE_ETH_WEI = _exact("BASE_STAKE_ETH", "0.002", "0.000001", 10, 10 ** 18); s.STAKE_CAP_WEI = _exact("BASE_STAKE_CAP_ETH", "0.005", "0.000001", 10, 10 ** 18)
    s.STAKE_WEI = min(s.STAKE_ETH_WEI, s.STAKE_CAP_WEI)
    s.BUY_SLIP_PPM = _exact("BASE_BUY_SLIP", "0.03", "0.0001", "0.5", 10 ** 6); s.BUY_DEADLINE_S = _setting("BASE_BUY_DEADLINE_S", "20", 2, 600, True)
    s.FIRE_MAX = _setting("BASE_FIRE_MAX", "2", 0, 50, True); s.HOLD_BLOCKS = _setting("BASE_HOLD_BLOCKS", "6", 1, 500, True)
    s.TP_PPM = _exact("BASE_TAKE_PROFIT", "0.01", "-0.5", 100, 10 ** 6); s.SELL_SLIP_PPM = _exact("BASE_SELL_SLIP", "0.05", 0, "0.99", 10 ** 6)
    s.SELL_DEADLINE_S = _setting("BASE_SELL_DEADLINE_S", "30", 2, 600, True); s.NEAR_MISS_BLOCKS = _setting("BASE_NEAR_MISS_BLOCKS", "3", 0, 1000, True)
    s.NONBOT_HALT = _setting("BASE_NONBOT_HALT", "5", 0, 10000, True); s.NONBOT_MIN_RET = _setting("BASE_NONBOT_MIN_RET", "0.02", -1, 100)
    s.MAX_PER_DAY = _setting("BASE_MAX_PER_DAY", "400", 0, 100000, True); s.DAILY_STOP_USD = _setting("BASE_DAILY_STOP_USD", "10", 0, 1e6)
    s.ETH_USD = _setting("BASE_ETH_USD", "2570", 1, 1e6)
    s.PRIO_WEI = _exact("BASE_PRIO_GWEI", "0.05", 0, 100, 10 ** 9); s.MAX_FEE_WEI = _exact("BASE_MAX_FEE_GWEI", "0.5", "0.000001", 1000, 10 ** 9)
    if s.MAX_FEE_WEI < s.PRIO_WEI:
        raise SystemExit(f"BASE_MAX_FEE_GWEI is under BASE_PRIO_GWEI: no transaction could pay its priority")
    s.BUY_GAS = _setting("BASE_BUY_GAS", "400000", 50_000, 5_000_000, True); s.SELL_GAS = _setting("BASE_SELL_GAS", "400000", 50_000, 5_000_000, True)
    s.MARGIN_WEI = _exact("BASE_RELAY_MARGIN_ETH", "0.0005", 0, 10, 10 ** 18)
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
state, pools, orphans, seen, flash_txs = {}, {}, {}, {}, collections.OrderedDict()
orders = queue.Queue(); SIGNER = None; SENDERS = {}; KEY_LOCK = None


def reset():
    """the engine's state at a start (the tests call it between cases)"""
    for d in (state, pools, orphans, seen, flash_txs):
        d.clear()
    state.update({"head": None, "head_ts": None, "base_fee": 0, "head_src": None, "lag_s": None, "lag_max_s": None, "logs_to": None, "started_at": mono(),
                  "ws": False, "ws_subs": 0, "ws_last": 0.0, "ws_from": None, "flash": False, "flash_at": 0.0, "flash_block": None, "flash_base_fee": 0,
                  "flash_msgs": 0, "flash_total": 0, "flash_reconnects": 0, "flash_bad": 0, "launches": 0, "position": None, "nonce": None, "relay_wei": None,
                  "halted": None, "stopped": None,
                  "day": None, "trades_today": 0, "pnl_today_usd": 0.0, "nonbot_streak": 0, "dry_streak": 0, "trades_done": 0, "dups": 0, "reorgs": 0,
                  "filled": 0, "ours": {}, "alarms_quiet": {}, "flow_at": mono()})


reset()


# ---------------------------------------------------------------- log, alarm, halt
def log(ev):
    ev["t"] = round(now(), 3)
    line = json.dumps(ev, separators=(",", ":"), default=str)
    with _log_lock:
        with open(S.LOG_PATH, "a") as f:
            f.write(line + "\n")


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
    for u in [S.WS_URL, S.RPC_URL, S.READ_ALT_URL, S.FLASH_URL or ""] + S.SEND_URLS:
        if u:
            s = s.replace(u, host(u))
            x = urllib.parse.urlparse(u)
            for part, mark in ((x.query, "<query>"), (x.path if len(x.path) > 1 else "", "/<path>")):
                if part:
                    s = s.replace(part, mark)
    return s[:n]


def halt(reason):
    """live: HALTED.base written (a halt holds across restarts until the owner removes the file); dry: in memory. No new buy after it;
    what is open is still sold"""
    state["halted"] = reason; path = None if S.DRY else S.HALT_FILE
    try:
        path and open(path, "w").write(reason + "\n")
    except Exception as e:
        alarm(f"the halt file {path} could not be written ({str(e)[:80]}): the halt holds in memory until a restart")
    log({"ev": "halt", "reason": reason, "dry": S.DRY, "file": path})


today = lambda: datetime.datetime.fromtimestamp(now(), datetime.timezone.utc).strftime("%Y-%m-%d")


def read_halt_file():
    try:
        return (open(S.HALT_FILE).read().strip() or "HALTED.base")[:200]
    except OSError as e:
        return f"HALTED.base ({e.strerror})"


def roll_day():
    d = today()
    if state["day"] != d:
        state.update({"day": d, "trades_today": 0, "pnl_today_usd": 0.0, "stopped": None})


# ---------------------------------------------------------------- reads and sends
def http_json(url, payload, timeout):
    """one JSON-RPC POST (urllib: the environment's proxy and CA); an HTTP error's body is read, as the sequencer answers 400/403 in JSON"""
    req = urllib.request.Request(url, json.dumps(payload).encode(), {"Content-Type": "application/json", "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read()
    try:
        return json.loads(body)
    except ValueError:
        raise RuntimeError(f"HTTP {e.code}: {body[:80]!r}")


def read(method, params, timeout=READ_TIMEOUT_S, tries=1):
    """a read: BASE_RPC_URL, then BASE_READ_ALT_URL once when it fails (3 s each on the trade path); a JSON null is a result"""
    last = None
    for k in range(tries):
        for u in [S.RPC_URL] + ([S.READ_ALT_URL] if S.READ_ALT_URL else []):
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
    """thread (live): an idle send connection gets a cheap request every 15 s (a send never pays the TLS handshake); the relay's balance every
    60 s while no position is open (a deposit lifts the fire's refusal)"""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []}); t_bal = mono()
    for u in S.SEND_URLS:
        SENDERS.setdefault(u, Sender(u))
    while True:
        time.sleep(5)
        for snd in list(SENDERS.values()):
            if mono() - snd.last > 15:
                snd.post(body)
        if mono() - t_bal > 60 and state["position"] is None:
            t_bal = mono()
            try:
                b = int(read("eth_getBalance", [S.RELAY, "latest"]), 16)
                with lock:
                    state["relay_wei"] = b if state["position"] is None else state["relay_wei"]
            except Exception as e:
                alarm(f"the relay's balance was not read: {scrub(e, 100)}", quiet_key="balance")


def reply_kind(reply):
    """an eth_sendRawTransaction reply: "ok", "known" (the node has it), "nonce_low", "rejected", "unknown" (no answer: it may be in)"""
    err = reply.get("error") or {}; msg = str(err.get("message", "")).lower()
    return ("ok" if "result" in reply else "unknown" if "code" not in err else "nonce_low" if "nonce too low" in msg else
            "known" if any(x in msg for x in ("already known", "already exists", "known transaction", "already imported")) else "rejected")


def post_all(raw_hex):
    """the signed transaction to every BASE_SEND_URLS at once; the first "ok"/"known" wins; else nonce_low, unknown, rejected in that order"""
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


# ---------------------------------------------------------------- words, transactions
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
A = lambda d, i: "0x" + d[2 + 64 * i + 24: 2 + 64 * (i + 1)].lower()
sgn = lambda x: x - (1 << 256) if x >= (1 << 255) else x
word = lambda x: "%064x" % (x % (1 << 256))                                      # an int (negative: two's complement)
aword = lambda a: "%064x" % int(a, 16)


key_words = lambda k: aword(k["c0"]) + aword(k["c1"]) + word(k["fee"]) + word(k["ts"]) + aword(k["hooks"])      # the PoolKey, 5 words
buy_data = lambda k, amount, min_out, deadline: "0x" + SEL_BUY + key_words(k) + word(amount) + word(min_out) + word(deadline)
sell_data = lambda k, min_out, deadline: "0x" + SEL_SELL + key_words(k) + word(min_out) + word(deadline)
net_of_fee = lambda x, fee: x - (x * fee + 999_999) // 1_000_000                          # v4math.buy_out_int's own fee step
base_fee = lambda: max(state["base_fee"] or 0, state["flash_base_fee"] or 0)             # the head's or the pending block's, the higher
gas_est_wei = lambda: DRY_GAS_UNITS * (base_fee() + S.PRIO_WEI) + L1_FEE_EST_WEI


def tx_dict(data, gas, nonce):
    """a type-2 transaction to the relay: priority BASE_PRIO_GWEI, max fee 2 x the base fee (the head's or the pending block's, the higher)
    + the priority, at most BASE_MAX_FEE_GWEI; all integers"""
    return {"type": 2, "chainId": CHAIN_ID, "nonce": nonce, "to": to_checksum_address(S.RELAY), "value": 0, "data": data, "gas": gas,
            "maxFeePerGas": min(2 * base_fee() + S.PRIO_WEI, S.MAX_FEE_WEI), "maxPriorityFeePerGas": S.PRIO_WEI}


def sign(tx):
    raw = bytes(SIGNER.sign_transaction(tx).raw_transaction)
    return "0x" + raw.hex(), "0x" + keccak(raw).hex()


def sqrt_after_buy_int(sp, liq, x_net):
    """the price after a buy of x_net wei (after the fee): buy_out_int's own new-price step, which v4math exposes only in float"""
    if liq <= 0 or x_net <= 0:
        return sp
    den = liq + (x_net * sp) // Q96
    return (liq * sp + den - 1) // den


# ---------------------------------------------------------------- the raw transactions of a Flashblock
def decode_tx(raw):
    """{type, to, value, data, nonce, prio, max_fee} of a raw signed transaction: legacy (rlp [nonce, gasPrice, gas, to, value, data, v, r,
    s]), 0x01 ([chainId, nonce, gasPrice, gas, to, value, data, accessList, ...]), 0x02 and 0x04 ([chainId, nonce, maxPriorityFeePerGas,
    maxFeePerGas, gas, to, value, data, accessList, ...]); None for a deposit (0x7e), anything else or a malformed one"""
    try:
        t = raw[0]
        if t >= 0xc0 or t == 1:                                                    # legacy, 2930: one gas price
            f = rlp.decode(raw) if t >= 0xc0 else rlp.decode(raw[1:])[1:]; nonce, gp, _gas, to, value, data = f[:6]; prio = mx = gp
        elif t in (2, 4):
            _c, nonce, prio, mx, _gas, to, value, data = rlp.decode(raw[1:])[:8]
        else:
            return None
        n = lambda b: int.from_bytes(b, "big")
        return {"type": t, "to": "0x" + to.hex() if to else None, "value": n(value), "data": bytes(data), "nonce": n(nonce), "prio": n(prio), "max_fee": n(mx)}
    except Exception:
        return None


def tx_sender(raw_hex):
    from eth_account import Account
    try:
        return Account.recover_transaction(raw_hex).lower()
    except Exception:
        return None


# ---------------------------------------------------------------- the pools
def new_pool(pid, key, lg, B, sp0, tick0):
    return {"pid": pid, "key": key, "token": key["c1"], "hook": key["hooks"], "L": B, "launch_tx": lg["transactionHash"], "sp0": sp0, "tick0": tick0,
            "ev": {}, "status": "arming", "launch_from": None, "add_pending": None, "add_conf": None, "add_logged": False, "kick": False,
            "pull_logged": False, "bot_txs": set(), "bot_logged": set(), "trade": None}


def fold(p, upto=None):
    """the pool's state from its events in (block, logIndex) order, to `upto` included: the price and tick (the last Swap's own record,
    else the Initialize's), the active liquidity (the adds covering the tick, v4math.active_liquidity, before any swap; the last Swap's
    record, moved by later ModifyLiquidity covering the tick, after), the first pull"""
    sp, tick, liq, ranges, pull = p["sp0"], p["tick0"], None, [], None
    for k in sorted(p["ev"]):
        if upto is not None and k > upto:
            break
        e = p["ev"][k]
        if e["k"] == "ml":
            if e["d"] < 0 and pull is None:
                pull = k
            if liq is None:
                ranges.append((e["lo"], e["hi"], e["d"]))
            elif e["lo"] <= tick < e["hi"]:
                liq += e["d"]
        else:
            sp, tick, liq = e["sp"], e["tick"], e["liq"]
    if liq is None:
        liq = v4math.active_liquidity(tick, ranges) + sum(d for lo, hi, d in ranges if d < 0 and lo < tick <= hi)
    return {"sp": sp, "tick": tick, "liq": max(liq, 0), "pull": pull}


def pool_state(p):
    """fold(p), with the liquidity of an add seen only pending (Flashblocks) until its ModifyLiquidity is confirmed"""
    st = fold(p)
    if st["liq"] == 0 and p["add_pending"] is not None and p["add_conf"] is None:
        st["liq"] = p["add_pending"]["liq_pred"]
    return st


sqrt_at = lambda tick: int(1.0001 ** (tick / 2) * Q96)                               # float: a pool's size for a threshold and a log, never a transaction field


def eth_of(liq, sp, lo, hi):
    """the ETH (currency0) a position of `liq` in [lo, hi] holds at the price sp"""
    sa, sb = sqrt_at(lo), sqrt_at(hi); s = min(max(sp, sa), sb)
    return liq * Q96 * (sb - s) // (s * sb) if 0 < s < sb else 0


def cheap_skip(key):
    """the fingerprint's checks on the Initialize's own fields (no read)"""
    flags = int(key["hooks"], 16) & 0x3fff
    return ("currency0 is not ETH" if key["c0"] != ZERO else f"fee {key['fee']}, not {S.FEE}" if key["fee"] != S.FEE else
            f"tick spacing {key['ts']}, not {S.TICK_SPACING}" if key["ts"] != S.TICK_SPACING else
            "a hook (BASE_HOOK_FLAGS 0: no hook)" if S.HOOK_FLAGS == 0 and key["hooks"] != ZERO else
            f"hook flags 0x{flags:x}, not 0x{S.HOOK_FLAGS:x}" if S.HOOK_FLAGS > 0 and (key["hooks"] == ZERO or flags != S.HOOK_FLAGS) else None)


launch_rec = lambda p: {"block": p["L"], "pool": p["pid"], "token": p["token"], "hook": p["hook"], "fee": p["key"]["fee"], "ts": p["key"]["ts"]}
code_hash = lambda code: "0x" + keccak(bytes.fromhex(code[2:] if code.startswith("0x") else code)).hex()


def on_init(lg, B):
    d = lg["data"]; pid = lg["topics"][1].lower()
    key = {"c0": "0x" + lg["topics"][2][-40:].lower(), "c1": "0x" + lg["topics"][3][-40:].lower(), "fee": W(d, 0), "ts": sgn(W(d, 1)), "hooks": A(d, 2)}
    p = new_pool(pid, key, lg, B, W(d, 3), sgn(W(d, 4)))
    state["launches"] += 1
    why = cheap_skip(key)
    if why is None and state["head"] is not None and state["head"] - B > S.ADD_MAX_BLOCKS:
        why = f"launched {state['head'] - B} blocks ago (past BASE_ADD_MAX_BLOCKS)"
    if why is not None or pid in pools:
        if why:
            log({"ev": "launch", **launch_rec(p), "launcher": None, "selector": None, "calldata_len": None, "token_code": None, "armed": False, "skip": why})
        return
    pools[pid] = p
    for x in sorted(orphans.pop(pid, []), key=order):
        apply(p, x)
    spawn(arm, p)


def read_launch_tx(h):
    """the launch transaction from its Flashblocks copy, else eth_getTransactionByHash (a node that does not have it yet: three tries)"""
    if h in flash_txs:
        return dict(flash_txs[h], src="flash")
    for i in range(3):
        t = read("eth_getTransactionByHash", [h])
        if t:
            inp = t.get("input") or "0x"
            return {"to": (t.get("to") or "").lower(), "from": (t.get("from") or "").lower(), "sel": inp[2:10].lower(), "len": (len(inp) - 2) // 2, "src": "rpc"}
        time.sleep(0.3)
    raise RuntimeError("the launch transaction is not known to the node")


def arm(p):
    """thread: the launch transaction, the token's code hash, the launcher's; then `launch` (armed or skip) and, armed, any add already seen"""
    rec = {"launcher": None, "selector": None, "calldata_len": None, "token_code": None}; why = None; tx = {}
    try:
        tx = read_launch_tx(p["launch_tx"]); rec.update(launcher=tx["to"], selector=tx["sel"], calldata_len=tx["len"], tx_src=tx["src"])
        if tx["sel"] != S.LAUNCH_SELECTOR:
            why = f"launch selector {tx['sel']}, not {S.LAUNCH_SELECTOR}"
        elif S.LAUNCH_CALLDATA_LEN and tx["len"] != S.LAUNCH_CALLDATA_LEN:
            why = f"launch calldata {tx['len']} B, not {S.LAUNCH_CALLDATA_LEN}"
        else:
            th = code_hash(read("eth_getCode", [p["token"], "latest"])); rec["token_code"] = th[:14]
            if th not in S.TOKEN_CODEHASHES:
                why = f"token code {th[:14]} is not in BASE_TOKEN_CODEHASHES"
            elif S.LAUNCHER_PREFIX:
                lh = code_hash(read("eth_getCode", [tx["to"], "latest"])); rec["launcher_code"] = lh[:14]
                if not lh[2:].startswith(S.LAUNCHER_PREFIX):
                    why = f"launcher code {lh[:14]}, not {S.LAUNCHER_PREFIX}"
    except Exception as e:
        why = f"not read: {scrub(e, 120)}"
        alarm(f"a launch was not read: {why}", quiet_key="arm", every_s=60, pool=p["pid"])
    with lock:
        if pools.get(p["pid"]) is not p:
            return                                                                 # removed meanwhile (a reorg)
        p.update(launch_from=tx.get("from"), status="skip" if why else "armed", kick=not why)
        why and pools.pop(p["pid"], None)
        log({"ev": "launch", **launch_rec(p), **rec, "armed": not why, "skip": why})
        why or end_burst()


def order(lg):
    try:
        return int(lg["blockNumber"], 16), int(lg["logIndex"], 16)
    except Exception:
        return -1, -1


# ---------------------------------------------------------------- the confirmed feed
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


def ws_covers(n):
    """a head or a log of block n on a connection whose gap is filled: every log of n - 1 came before it"""
    if state["ws_from"] is not None and state["logs_to"] is not None and state["logs_to"] >= state["ws_from"]:
        state["logs_to"] = max(state["logs_to"], n - 1)


def on_ws_log(lg):
    state["ws_last"] = mono()
    if order(lg)[0] >= 0:
        ws_covers(order(lg)[0])
    on_log(lg)


def on_log(lg):
    """one PoolManager log of the confirmed feed (the websocket or eth_getLogs): deduped by (blockHash, logIndex); removed: its effect dropped"""
    try:
        key = (lg["blockHash"].lower(), int(lg["logIndex"], 16)); B = int(lg["blockNumber"], 16); t0 = lg["topics"][0].lower()
    except Exception as e:
        alarm(f"a log was not understood: {type(e).__name__}: {scrub(e, 80)}", quiet_key="badlog", every_s=60); return
    if lg.get("removed"):
        if seen.pop(key, None) is not None:
            unapply(lg, B, key[1], t0)
        return
    if key in seen:
        state["dups"] += 1; return
    seen[key] = B
    try:
        if t0 == T_INIT:
            on_init(lg, B)
        elif t0 in (T_ML, T_SWAP):
            pid = lg["topics"][1].lower(); p = pools.get(pid)
            if p is not None:
                apply(p, lg)
            elif state["head"] is None or B >= state["head"] - 64:
                orphans.setdefault(pid, collections.deque(maxlen=32)).append(lg)   # a gap fill may bring its Initialize later
    except Exception as e:
        alarm(f"a log was not understood: {type(e).__name__}: {scrub(e, 80)}", quiet_key="badlog", every_s=60, block=B, trace=traceback.format_exc()[-300:])


def unapply(lg, B, li, t0):
    """a removed log (a reorg): its event out of the pool's (the state is folded again), an unfired pool's Initialize drops the pool"""
    state["reorgs"] += 1; pid = lg["topics"][1].lower(); p = pools.get(pid)
    alarm(f"a log was removed (a reorg at block {B}): its effect is dropped", quiet_key="reorg", pool=pid, kind=t0[:10])
    if p is not None and t0 == T_INIT and p["status"] in ("arming", "armed") and p["L"] == B:
        pools.pop(pid, None)
    elif p is not None and (p["ev"].get((B, li)) or {}).get("bh") == lg["blockHash"].lower():
        e = p["ev"].pop((B, li)); p["kick"] = True
        if p["add_conf"] and p["add_conf"]["tx"] == e["tx"] and p["status"] in ("arming", "armed"):
            p["add_conf"] = None; p["add_logged"] = False


def apply(p, lg):
    d = lg["data"]; B, li = order(lg); txh = lg["transactionHash"].lower(); sender = "0x" + lg["topics"][2][-40:].lower(); bh = lg["blockHash"].lower()
    if lg["topics"][0].lower() == T_ML:
        e = {"k": "ml", "lo": sgn(W(d, 0)), "hi": sgn(W(d, 1)), "d": sgn(W(d, 2)), "tx": txh, "bh": bh, "sender": sender}
        p["ev"][(B, li)] = e
        if e["d"] > 0 and p["add_conf"] is None:
            p["add_conf"] = {"block": B, "tx": txh, "via": "logs", "seen_at": mono()}
        if e["d"] < 0:
            on_pull(p, B, "logs")
    else:
        e = {"k": "swap", "a0": sgn(W(d, 0)), "a1": sgn(W(d, 1)), "sp": W(d, 2), "liq": W(d, 3), "tick": sgn(W(d, 4)), "tx": txh, "bh": bh, "sender": sender}
        p["ev"][(B, li)] = e
        if e["a0"] < 0 and (txh in p["bot_txs"] or sender in S.BOT_SENDERS) and txh not in p["bot_logged"] and p["status"] != "arming":
            p["bot_logged"].add(txh)
            log({"ev": "bot_buy", "pool": p["pid"], "block": B, "pending": False, "value": -e["a0"], "via": "logs", "tx": txh})
        pos = state["position"]
        if pos is not None and pos["pid"] == p["pid"] and not pos["dry"] and S.RELAY and sender == S.RELAY:
            if e["a0"] < 0 and pos["buy_at"] is None:
                pos.update(buy_at=(B, li), buy_block=B, tokens=e["a1"], eth_in=-e["a0"])
            elif e["a0"] > 0:
                pos["sell_at"] = (B, li)
    p["kick"] = True


def on_pull(p, B, via, pending=False):
    """a pull (a negative ModifyLiquidity, or its call seen pending): the `pull` line; before our fire the pool is skipped; a traded pool's
    near miss. The trade's own outcome is decided from the pool's events (check_position) and the receipts (finish_live)"""
    pos = state["position"]; ours = pos is not None and pos["pid"] == p["pid"]
    if p["status"] in ("arming", "armed"):
        before = "fire"
    elif ours and not (pos.get("sell_at") or (pos["dry"] and pos.get("X") is not None and B > pos["X"])):
        before = "sell"
    else:
        before = "after"
    bought = p["trade"]["buy_block"] if p["trade"] else ((pos["D"] if pos["dry"] else pos["buy_block"]) if ours else None)
    if not p["pull_logged"] or (p["pull_logged"] == "pending" and not pending):
        log({"ev": "pull", "pool": p["pid"], "block": B, "before": before, "pending": pending, "via": via, "after_buy": B - bought if bought else None})
        p["pull_logged"] = "pending" if pending else True
    if before == "fire":
        p["status"] = "skip"; pools.pop(p["pid"], None)
        log({"ev": "skip", "pool": p["pid"], "why": "pulled before our fire", "block": B})
    elif not pending and p["trade"] and not ours:
        near_miss(p, B)


def near_miss(p, B):
    t = p["trade"]
    if t.get("near_checked") or t["buy_block"] is None:
        return
    t["near_checked"] = True
    if t["exit"] != "pulled" and B - t["buy_block"] <= S.NEAR_MISS_BLOCKS:
        halt(f"near miss: the pull landed {B - t['buy_block']} blocks after our buy (BASE_NEAR_MISS_BLOCKS {S.NEAR_MISS_BLOCKS}), our sell at "
             f"{t['sell_block']}: the reaction is too fast to keep trading")


# ---------------------------------------------------------------- the Flashblocks feed
def flash_watch():
    """the hex strings that make a pending transaction worth decoding: the launch selector, the pools' hooks, the bot's routers (a pool held)"""
    live = [p for p in pools.values() if p["status"] in ("arming", "armed", "fired", "traded")]
    return {S.LAUNCH_SELECTOR} | {p["hook"][2:] for p in live} | ({r[2:] for r in S.BOT_ROUTERS} if any(p["status"] != "arming" for p in live) else set())


def on_flash(m):
    """one Flashblocks message: brotli JSON; the pending block's number and base fee, then its new raw transactions"""
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
    sel = tx["data"][:4].hex(); to = tx["to"]; h = None
    if sel == S.LAUNCH_SELECTOR:
        h = "0x" + keccak(raw).hex()
        flash_txs[h] = {"to": to, "from": tx_sender(s), "sel": sel, "len": len(tx["data"])}
        while len(flash_txs) > 256:
            flash_txs.popitem(last=False)
    for p in list(pools.values()):
        if to == p["hook"] and sel == S.ADD_SELECTOR and p["status"] in ("arming", "armed") and p["add_pending"] is None and p["add_conf"] is None:
            frm = tx_sender(s)
            if p["launch_from"] and frm != p["launch_from"]:
                alarm("a pending add to an armed hook from another wallet than the launch's: not the add", quiet_key="addfrom", pool=p["pid"], sender=frm); continue
            h = h or "0x" + keccak(raw).hex()
            liq = tx["value"] * p["sp0"] // Q96                                         # a full-range position at the launch price: amount0 = L x 2^96 / sqrtP
            p["add_pending"] = {"block": N, "tx": h, "via": "flash", "value": tx["value"], "liq_pred": liq, "from": frm, "seen_at": mono()}
            log({"ev": "add", "pool": p["pid"], "block": N, "eth": tx["value"] / 1e18, "eth_wei": tx["value"], "liquidity": liq, "pending": True, "via": "flash", "tx": h, "from": frm})
            p["kick"] = True
        elif to == p["hook"] and sel == S.PULL_SELECTOR and p["status"] != "skip":
            on_pull(p, N, "flash", pending=True)
        elif to in S.BOT_ROUTERS and p["status"] in ("armed", "fired", "traded") and p["token"][2:] in tx["data"].hex():
            h = h or "0x" + keccak(raw).hex()
            if h in p["bot_txs"]:
                continue
            p["bot_txs"].add(h); p["bot_logged"].add(h)
            log({"ev": "bot_buy", "pool": p["pid"], "block": N, "pending": True, "value": tx["value"], "via": "flash", "tx": h, "from": tx_sender(s)})
            pos = state["position"]
            if pos is not None and pos["pid"] == p["pid"] and not pos["sell_sent"] and pos["trigger"] is None and bought_before(pos, N, at):
                pos["trigger"] = {"exit": "bot", "block": N, "via": "flash", "reason": f"the bot's buy seen pending ({tx['value'] / 1e18:.4f} ETH), behind ours"}


def bought_before(pos, N, at):
    """our buy is in ahead of a pending transaction at `at` (block, flashblock index, position): dry, its block is before N"""
    if pos["dry"]:
        return pos["D"] < N
    seen_at = pos.get("buy_seen")
    return (pos["buy_block"] is not None and pos["buy_block"] < N) or (seen_at is not None and seen_at < at)


# ---------------------------------------------------------------- the trade
def end_burst():
    """after a batch of feed messages (under the lock): expiries, the fire, the open position's dry pricing, triggers, deadline and pull"""
    roll_day()
    head = state["head"]
    for p in list(pools.values()):
        if p["kick"]:
            p["kick"] = False
            if p["add_conf"] and not p["add_logged"] and p["status"] != "arming":
                st, eth = add_info(p); p["add_logged"] = True; p["add_conf"]["eth"] = eth
                log({"ev": "add", "pool": p["pid"], "block": p["add_conf"]["block"], "eth": eth / 1e18, "eth_wei": eth, "liquidity": st["liq"], "pending": False,
                     "via": "logs", "tx": p["add_conf"]["tx"], "fired": p["status"] != "armed"})
            if p["status"] == "armed":
                try_fire(p)
        if head is not None and p["status"] in ("arming", "armed") and p["add_pending"] is None and p["add_conf"] is None and head > p["L"] + S.ADD_MAX_BLOCKS:
            log({"ev": "skip", "pool": p["pid"], "why": f"no add by +{S.ADD_MAX_BLOCKS}", "head": head}); pools.pop(p["pid"], None)
        elif head is not None and p["status"] == "traded" and head > p["L"] + WATCH_BLOCKS and (state["position"] or {}).get("pid") != p["pid"]:
            pools.pop(p["pid"], None)
    pos = state["position"]
    if pos is not None:
        check_position(pos)


def add_info(p):
    """the confirmed add: its block, the liquidity of the pool's state then, the ETH its ModifyLiquidity events put in at the price"""
    a = p["add_conf"]; st = fold(p, (a["block"], END)); eth = 0
    for k, e in p["ev"].items():
        if e["k"] == "ml" and e["tx"] == a["tx"] and e["d"] > 0:
            eth += eth_of(e["d"], st["sp"], e["lo"], e["hi"])
    return st, eth


def try_fire(p):
    add = p["add_pending"] or p["add_conf"]
    if add is None:
        return
    eth = add["value"] if add["via"] == "flash" else add.get("eth", 0); head = state["head"]; roll_day()
    if not S.DRY and not state["halted"] and os.path.exists(S.HALT_FILE):         # the owner's file, read again before every live fire
        state["halted"] = read_halt_file()
    why = next((w for ok, w in (
        (eth >= S.MIN_POOL_WEI, lambda: f"the pool's {eth / 1e18:.4f} ETH is under BASE_MIN_POOL_ETH"),
        (fold(p)["pull"] is None, lambda: "pulled before our fire"),
        (head is None or head <= add["block"] + S.FIRE_MAX, lambda: f"late: head {head}, the add at {add['block']} (BASE_FIRE_MAX {S.FIRE_MAX})"),
        (state["position"] is None, lambda: "a position is open"),
        (not state["halted"], lambda: "halted: " + state["halted"]),
        (not state["stopped"], lambda: "stopped for the day (BASE_DAILY_STOP_USD)"),
        (state["trades_today"] < S.MAX_PER_DAY, lambda: f"daily cap: {state['trades_today']} today (BASE_MAX_PER_DAY)"),
        (S.DRY or (state["relay_wei"] or 0) >= S.STAKE_WEI + S.MARGIN_WEI,
         lambda: f"the relay holds {(state['relay_wei'] or 0) / 1e18:.6f} ETH, under the stake + BASE_RELAY_MARGIN_ETH")) if not ok), None)
    if why:
        why = why()
        p["status"] = "skip"; pools.pop(p["pid"], None)
        log({"ev": "skip", "pool": p["pid"], "why": why, "head": head, "add_block": add["block"]}); return
    fire(p, add)


def fire(p, add):
    st = pool_state(p); fee = p["key"]["fee"]; via = add["via"]; liq = st["liq"]       # a pending add: the predicted liquidity; the confirmed one fixes the state
    stake = S.STAKE_WEI
    expected = v4math.buy_out_int(st["sp"], liq, stake, fee)
    min_out = expected * (10 ** 6 - S.BUY_SLIP_PPM) // 10 ** 6
    head = state["head"] or add["block"]
    pos = {"pid": p["pid"], "key": p["key"], "token": p["token"], "L": p["L"], "dry": S.DRY, "stake": stake, "expected": expected, "min_out": min_out,
           "via": via, "add_block": add["block"], "fire_head": head, "nonce": None,
           "D": max(head, add["block"]) + 1 if via == "logs" else max(head + 1, add["block"]), "buy_hash": None, "buy_at": None,   # D: the dry buy's block
           "buy_block": None, "tokens": None, "eth_in": None, "buy_status": None, "sell_sent": False, "sell_hash": None, "sell_at": None, "exit": None,
           "trigger": None, "no_sell": False, "closed": False, "scanned": None, "X": None, "fired_at": mono(), "sp_fire": st["sp"], "liq_fire": liq}
    state["position"] = pos; state["trades_today"] += 1; p["status"] = "fired"
    rec = {"pool": p["pid"], "token": p["token"], "add_block": add["block"], "head": head, "stake_wei": stake, "min_out": min_out, "expected": expected,
           "nonce": None if S.DRY else state["nonce"], "via": via, "sqrt_price": st["sp"], "liquidity": liq, "react_ms": round(1000 * (mono() - add["seen_at"]), 1)}
    if S.DRY:
        log({"ev": "would_fire", "dry": True, **rec, "buy_block": pos["D"]}); return
    log({"ev": "fire", "dry": False, **rec})
    orders.put(("buy", pos, None))


def check_position(pos):
    p = pools.get(pos["pid"])
    if pos["closed"] or pos["dry"]:
        return None if pos["closed"] else check_dry(pos, p)
    pull = fold(p)["pull"] if p is not None else None
    if pull is not None and not pos["sell_sent"] and not pos["no_sell"] and (pos["buy_at"] is None or pull > pos["buy_at"]):
        pos["no_sell"] = True; pos["exit"] = "pulled"                             # the pool is empty: no sell; the settlement closes it (-100%, a halt)
    if pos["sell_sent"] or pos["no_sell"] or pos["buy_status"] in ("reverted", "lost") or (pos["buy_block"] is None and pos.get("buy_seen") is None):
        return
    trig = pos["trigger"] or (scan_swaps(pos, p) if p is not None else None) or deadline(pos)
    if trig:
        do_sell(pos, trig)


def scan_swaps(pos, p):
    """the confirmed swaps behind our buy, in order, each once: a bot buy (its transaction seen pending to a bot router, or its sender in
    BASE_BOT_SENDERS) or a buy whose price pays the take-profit"""
    after = (pos["D"], END) if pos["dry"] else pos["buy_at"]
    if after is None or pos["tokens"] is None:
        return None
    start = max(after, pos["scanned"] or after)
    for k in sorted(x for x in p["ev"] if x > start):
        e = p["ev"][k]; pos["scanned"] = k
        if e["k"] != "swap" or e["a0"] >= 0:
            continue
        if e["tx"] in p["bot_txs"] or e["sender"] in S.BOT_SENDERS:
            return {"exit": "bot", "block": k[0], "via": "logs", "reason": f"the bot's buy confirmed ({-e['a0'] / 1e18:.4f} ETH) behind ours"}
        value = sell_value(pos, p, e["sp"], e["liq"])
        if value * 10 ** 6 >= pos["stake"] * (10 ** 6 + S.TP_PPM) + gas_est_wei() * 10 ** 6:
            return {"exit": "take_profit", "block": k[0], "via": "logs", "reason": f"a buy behind ours ({-e['a0'] / 1e18:.4f} ETH): the sell prices at "
                    f"{(value - pos['stake']) / pos['stake']:+.2%} before gas"}
    return None


def sell_value(pos, p, sp, liq, ours_in=None):
    """the ETH our tokens get at the price sp (the dry run's buy, or a live buy the logs have not shown yet, put into it)"""
    fee = p["key"]["fee"] if p else pos["key"]["fee"]
    if ours_in is None:
        ours_in = not pos["dry"] and pos["buy_at"] is not None
    if not ours_in:
        sp = sqrt_after_buy_int(sp, liq, net_of_fee(pos["stake"], fee))
    tokens = pos["tokens"] if pos["tokens"] is not None else pos["min_out"]
    return v4math.sell_out_int(sp, liq, tokens, fee) if liq > 0 and tokens > 0 else 0


def deadline(pos):
    b = (pos["D"] if pos["dry"] else pos["buy_block"] if pos["buy_block"] is not None else pos["buy_seen"][0]) + S.HOLD_BLOCKS
    for via, n in (("head", state["head"]), ("flash", state["flash_block"] if state["flash"] else None)):
        if n is not None and n >= b:
            return {"exit": "deadline", "block": n, "via": via, "reason": f"the deadline: our buy's block + {S.HOLD_BLOCKS} ({via})"}
    return None


def do_sell(pos, trig):
    p = pools.get(pos["pid"])
    pos.update(sell_sent=True, exit=trig["exit"], sell_reason=trig["reason"], sell_via=trig["via"], sell_block_seen=max(state["head"] or 0, state["flash_block"] or 0))
    if pos["dry"]:
        pos["X"] = trig["block"]
        log({"ev": "sell_sent", "dry": True, "pool": pos["pid"], "hash": None, "nonce": None, "block_seen": pos["sell_block_seen"], "reason": trig["reason"],
             "exit": trig["exit"], "via": trig["via"], "priced_at_block": pos["X"]}); return
    min_out = 0
    if trig["exit"] != "deadline" and p is not None:
        st = pool_state(p); min_out = sell_value(pos, p, st["sp"], st["liq"]) * (10 ** 6 - S.SELL_SLIP_PPM) // 10 ** 6
    orders.put(("sell", pos, (min_out, int(now()) + S.SELL_DEADLINE_S, trig)))


def check_dry(pos, p):
    """the dry run: the buy priced once its block is complete, the triggers, the sell priced once the trigger's block is complete"""
    lt = state["logs_to"]
    if p is None:
        return close_dry(pos, None, None, "buy_reverted", "the pool's record was dropped")
    if pos["tokens"] is None:
        if lt is None or lt < pos["D"]:
            return
        st = fold(p, (pos["D"], END))
        if st["pull"] is not None:
            return close_dry(pos, p, None, "buy_reverted", "the pool was pulled before our buy's block ended")
        tokens = v4math.buy_out_int(st["sp"], st["liq"], pos["stake"], p["key"]["fee"])
        if tokens < pos["min_out"]:
            return close_dry(pos, p, None, "buy_reverted", f"{tokens} tokens at our block, under the buy's minOut {pos['min_out']}")
        pos.update(tokens=tokens, eth_in=pos["stake"], buy_block=pos["D"])
    if not pos["sell_sent"]:
        pull = fold(p)["pull"]
        trig = pos["trigger"] or scan_swaps(pos, p)
        if pull is not None and (trig is None or pull[0] <= trig["block"]):
            return close_dry(pos, p, 0, "pulled", "the pull came before our sell")
        trig = trig or deadline(pos)
        if trig:
            do_sell(pos, trig)
    if pos["sell_sent"] and lt is not None and lt >= pos["X"]:
        st = fold(p, (pos["X"], END))
        if st["pull"] is not None:
            return close_dry(pos, p, 0, "pulled", "the pull came before our sell")
        close_dry(pos, p, sell_value(pos, p, st["sp"], st["liq"]), pos["exit"], pos["sell_reason"])


def close_dry(pos, p, eth_out, exit_, why):
    pos["closed"] = True; gas = gas_est_wei(); stake = pos["stake"]
    if exit_ == "buy_reverted":
        eth_in, eth_out, gas_used = 0, 0, gas // 2
    else:
        eth_in, gas_used = stake, gas
    pull = fold(p)["pull"] if p is not None else None
    net = eth_out - eth_in - gas_used
    ret = net / stake
    streak = None
    if exit_ != "buy_reverted":
        state["dry_streak"] = 0 if ret >= S.NONBOT_MIN_RET else state["dry_streak"] + 1; streak = state["dry_streak"]
    trade_done(pos, {"buy_block": pos["D"], "sell_block": pos["X"], "eth_in_wei": eth_in, "tokens": pos["tokens"], "eth_out_wei": eth_out, "gas_wei": gas_used,
                     "l1_fee_wei": L1_FEE_EST_WEI if gas_used == gas else L1_FEE_EST_WEI // 2, "ret": round(ret, 6), "ret_gross": round((eth_out - eth_in) / stake, 6),
                     "usd": round(net / 1e18 * S.ETH_USD, 4), "exit": exit_, "why": why, "pulled_at": pull[0] if pull else None, "nonbot_streak": streak})
    if exit_ == "pulled":
        halt(f"pulled: the pull at block {pull[0] if pull else '?'} came at or before our sell (our buy at {pos['D']}): -100%")
    if p is not None:
        p["status"] = "traded"
        p["trade"] = {"buy_block": pos["D"] if exit_ != "buy_reverted" else None, "sell_block": pos["X"], "exit": exit_}
        if pull is not None and exit_ != "pulled" and p["trade"]["buy_block"] is not None:
            near_miss(p, pull[0])


def trade_done(pos, out):
    state["trades_done"] += 1; state["ours"] = {k: v for k, v in state["ours"].items() if v[0] is not pos}
    if state["position"] is pos:
        state["position"] = None
    save_positions()
    log({"ev": "trade_done", "pool": pos["pid"], "token": pos["token"], **out, "stake_wei": pos["stake"], "expected": pos["expected"], "min_out": pos["min_out"],
         "via": pos["via"], "add_block": pos["add_block"], "dry": pos["dry"], "live": not pos["dry"]})
    roll_day(); state["pnl_today_usd"] += out["usd"]
    if S.DAILY_STOP_USD and state["pnl_today_usd"] <= -S.DAILY_STOP_USD and not state["stopped"]:
        state["stopped"] = state["day"]
        log({"ev": "stop", "day": state["day"], "losses": round(-state["pnl_today_usd"], 4), "dry": pos["dry"]})


# ---------------------------------------------------------------- the trader (the only thread that holds the nonce and signs)
def trader():
    while True:
        kind, pos, arg = orders.get()
        try:
            (send_buy(pos) if kind == "buy" else send_sell(pos, *arg))
        except Exception as e:
            alarm(f"the trader failed on a {kind}: {type(e).__name__}: {scrub(e, 120)}", trace=traceback.format_exc()[-400:])
            if kind == "buy":
                with lock:
                    close_unsent(pos, "the buy could not be sent")


def chain_nonce():
    try:
        return int(read("eth_getTransactionCount", [S.WALLET, "pending"], tries=2), 16)
    except Exception as e:
        alarm(f"the nonce was not read: {scrub(e, 100)}", quiet_key="nonce", every_s=60); return None


def send_signed(pos, what, build):
    """sign at the wallet's nonce and send; "nonce too low" everywhere: the nonce read again and signed once more"""
    with lock:
        nonce = state["nonce"]
    for attempt in (0, 1):
        raw, h = sign(build(nonce))
        with lock:
            pos[what + "_hash"] = h; pos[what + "_nonce"] = nonce; state["ours"][raw] = (pos, what); save_positions()
        kind, replies = post_all(raw)
        if kind != "nonce_low" or attempt:
            break
        n = chain_nonce()
        if n is None or n <= nonce:
            break
        nonce = n
    with lock:
        if kind != "rejected":
            state["nonce"] = nonce + 1
    return h, nonce, kind, replies


def send_buy(pos):
    h, nonce, kind, replies = send_signed(pos, "buy", lambda n: tx_dict(buy_data(pos["key"], pos["stake"], pos["min_out"], int(now()) + S.BUY_DEADLINE_S), S.BUY_GAS, n))
    pos["nonce"] = nonce
    log({"ev": "buy_sent", "pool": pos["pid"], "hash": h, "nonce": nonce, "block_seen": max(state["head"] or 0, state["flash_block"] or 0), "reason": f"the add ({pos['via']})",
         "kind": kind, "replies": replies, "ms_since_fire": round(1000 * (mono() - pos["fired_at"]), 1)})
    if kind == "rejected":
        with lock:
            close_unsent(pos, "the buy was refused by every endpoint")
        return
    spawn(settle_live, pos)


def close_unsent(pos, why):
    alarm(f"{why}: no trade", pool=pos["pid"])
    pos["closed"] = True
    if state["position"] is pos:
        state["position"] = None; state["trades_today"] = max(0, state["trades_today"] - 1)
    p = pools.get(pos["pid"])
    if p is not None:
        p["status"] = "traded"; p["trade"] = {"buy_block": None, "sell_block": None, "exit": "unsent"}
    save_positions()


def send_sell(pos, min_out, deadline_ts, trig):
    h, nonce, kind, replies = send_signed(pos, "sell", lambda n: tx_dict(sell_data(pos["key"], min_out, deadline_ts), S.SELL_GAS, n))
    log({"ev": "sell_sent", "dry": False, "pool": pos["pid"], "hash": h, "nonce": nonce, "block_seen": pos["sell_block_seen"], "reason": trig["reason"],
         "exit": trig["exit"], "via": trig["via"], "min_out": min_out, "kind": kind, "replies": replies})
    if kind == "rejected":
        with lock:
            pos["sell_refused"] = True
        alarm("the sell was refused by every endpoint", pool=pos["pid"], replies=replies)


# ---------------------------------------------------------------- settlement (live)
def wait_receipt(h, timeout_s, stop=lambda: False):
    t0 = mono()
    while mono() - t0 < timeout_s and not stop():
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


def our_swap(rec, pos):
    """our Swap in a receipt: (amount0, amount1, block, logIndex), else None"""
    for l in rec.get("logs") or []:
        t = l.get("topics") or []
        if (l.get("address") or "").lower() == S.PM and len(t) >= 3 and t[0].lower() == T_SWAP and t[1].lower() == pos["pid"] and t[2][-40:].lower() == S.RELAY[2:]:
            return sgn(W(l["data"], 0)), sgn(W(l["data"], 1)), int(rec["blockNumber"], 16), int(l["logIndex"], 16)
    return None


def tokens_in(rec, pos):
    """the tokens of our buy from the token's Transfer to the relay (when no Swap of ours is in the receipt)"""
    return sum(int(l["data"], 16) for l in rec.get("logs") or [] if (l.get("address") or "").lower() == pos["token"] and len(l.get("topics") or []) >= 3
               and l["topics"][0].lower() == T_TRANSFER and l["topics"][2][-40:].lower() == S.RELAY[2:])


def settle_live(pos):
    try:
        _settle_live(pos)
    except Exception as e:
        alarm(f"settle failed: {type(e).__name__}: {scrub(e, 120)}", pool=pos["pid"], trace=traceback.format_exc()[-500:])
        with lock:
            pos["closed"] = True
            if state["position"] is pos:
                state["position"] = None
            save_positions()


def _settle_live(pos):
    rb = wait_receipt(pos["buy_hash"], S.BUY_DEADLINE_S + 60)
    with lock:
        if rb is None:
            pos["buy_status"] = "lost"
        elif rb.get("status") != "0x1":
            pos["buy_status"] = "reverted"
        else:
            sw = our_swap(rb, pos); pos["buy_status"] = "ok"; pos["buy_ok_at"] = mono()
            if pos["buy_at"] is None:                                              # the logs did not show our Swap (yet): the receipt's
                pos["buy_block"] = int(rb["blockNumber"], 16)
                if sw:
                    pos.update(buy_at=(sw[2], sw[3]), tokens=sw[1], eth_in=-sw[0])
                else:
                    pos.update(buy_at=(pos["buy_block"], 0), tokens=tokens_in(rb, pos), eth_in=pos["stake"])
            if pos.get("restart") and not pos["sell_sent"]:
                do_sell(pos, {"exit": "deadline", "block": state["head"] or 0, "via": "start", "reason": "restart: an open position taken back at the start, sold at once"})
        if pos["buy_status"] != "ok" and not pos["sell_sent"]:
            pos["no_sell"] = True
        save_positions()
    t0 = mono()
    while True:                                                                    # the sell's decision (the feeds), or no sell (a pull)
        with lock:
            if pos["no_sell"] or pos.get("sell_refused") or (pos["sell_sent"] and pos["sell_hash"]):
                break
        if mono() - t0 > 2.0 * S.HOLD_BLOCKS + 120:
            with lock:
                if not pos["sell_sent"]:
                    do_sell(pos, {"exit": "deadline", "block": state["head"] or 0, "via": "clock", "reason": "the deadline by the clock: no block came"})
            t0 = mono()
        time.sleep(RECEIPT_POLL_S)
    rs = wait_receipt(pos["sell_hash"], S.SELL_DEADLINE_S + 60) if pos["sell_hash"] and not pos.get("sell_refused") else None
    finish_live(pos, rb, rs)


def finish_live(pos, rb, rs):
    n = chain_nonce()                                                          # both transactions are final: the chain's count, read before the slot frees
    gas = l1 = eth_in = eth_out = 0; tokens = pos["tokens"]; sell_block = None; sell_at = None
    for rec in (rb, rs):
        if rec:
            g, l = gas_of(rec); gas += g; l1 += l
    if rb and rb.get("status") == "0x1":
        sw = our_swap(rb, pos)
        eth_in, tokens = (-sw[0], sw[1]) if sw else (pos["stake"], tokens_in(rb, pos))
    if rs:
        sell_block = int(rs["blockNumber"], 16); sw = our_swap(rs, pos) if rs.get("status") == "0x1" else None
        if sw:
            eth_out = sw[0]; sell_at = (sw[2], sw[3])
    with lock:
        p = pools.get(pos["pid"]); pull = fold(p)["pull"] if p is not None else None
        exit_ = pos["exit"]; halt_why = None
        if pos["buy_status"] in ("reverted", "lost"):
            exit_ = "buy_reverted"; pos["sell_reason"] = "our buy reverted" if pos["buy_status"] == "reverted" else "no receipt for our buy: it never landed"
        elif pull is not None and (sell_at is None or pull < sell_at):
            exit_ = "pulled"
            halt_why = f"pulled: the pull at block {pull[0]} came at or before our sell (our buy at {pos['buy_block']}): -100%"
        elif sell_at is None:
            halt_why = f"sold none: the buy filled and the sell sold nothing ({'no sell' if not rs else 'reverted' if rs.get('status') != '0x1' else 'no Swap'}): the sell path is broken"
        base = eth_in or pos["stake"]; net = eth_out - eth_in - gas; ret = net / base
        streak = state["nonbot_streak"]
        if exit_ != "buy_reverted":
            streak = state["nonbot_streak"] = 0 if ret >= S.NONBOT_MIN_RET else state["nonbot_streak"] + 1
        pos["closed"] = True
        if n is not None:
            state["nonce"] = n if pos["buy_status"] == "lost" else max(n, state["nonce"] or 0)
        trade_done(pos, {"buy_block": pos["buy_block"], "sell_block": sell_block, "eth_in_wei": eth_in, "tokens": tokens, "eth_out_wei": eth_out, "gas_wei": gas,
                         "l1_fee_wei": l1, "ret": round(ret, 6), "ret_gross": round((eth_out - eth_in) / base, 6), "usd": round(net / 1e18 * S.ETH_USD, 4), "exit": exit_,
                         "why": pos.get("sell_reason"), "pulled_at": pull[0] if pull else None, "nonbot_streak": streak, "buy_hash": pos["buy_hash"],
                         "sell_hash": pos["sell_hash"], "nonce": pos["nonce"]})
        if halt_why:
            halt(halt_why)
        if S.NONBOT_HALT and exit_ != "buy_reverted" and streak >= S.NONBOT_HALT and not halt_why:
            halt(f"{streak} live trades in a row under {S.NONBOT_MIN_RET:+.0%} (last {ret:+.1%}, {exit_}): decoys or a changed schedule (BASE_NONBOT_HALT)")
        if p is not None:
            p["status"] = "traded"; p["trade"] = {"buy_block": pos["buy_block"], "sell_block": sell_block, "exit": exit_}
            if pull is not None and exit_ not in ("pulled", "buy_reverted"):
                near_miss(p, pull[0])
        if state["relay_wei"] is not None:
            state["relay_wei"] += eth_out - eth_in


# ---------------------------------------------------------------- positions file
POS_KEYS = ("pid", "key", "token", "L", "stake", "expected", "min_out", "via", "add_block", "fire_head", "D", "nonce", "buy_hash", "buy_nonce", "buy_block", "tokens",
            "sell_sent", "sell_hash", "sell_nonce", "exit")


def save_positions():
    if S.DRY:
        return
    pos = state["position"]
    data = {"positions": {pos["pid"]: {k: pos.get(k) for k in POS_KEYS}} if pos is not None and not pos["closed"] else {}, "t": round(now(), 3)}
    try:
        with open(S.POSITIONS_FILE + ".tmp", "w") as f:
            json.dump(data, f)
        os.replace(S.POSITIONS_FILE + ".tmp", S.POSITIONS_FILE)
    except Exception as e:
        alarm(f"the positions file was not written: {str(e)[:100]}", quiet_key="posfile", every_s=60)


def load_position():
    """the open position of base_positions.json ({"positions": {pool: {...}}}; one at a time: a second is an alarm)"""
    try:
        got = list(((json.load(open(S.POSITIONS_FILE)) or {}).get("positions") or {}).values())
    except FileNotFoundError:
        return None
    except Exception as e:
        alarm(f"the positions file {S.POSITIONS_FILE} was not read ({str(e)[:80]}): check it by hand"); return None
    if len(got) > 1:
        alarm(f"{len(got)} positions in {S.POSITIONS_FILE}: the first is taken back, the others need the owner (deploy/base_ops.py sweep)")
    return got[0] if got else None


def take_back(saved):
    """a live position left open by the last run: its buy's receipt, then the sell's (already sent) or a sell at once (minOut 0)"""
    pos = {"dry": False, "buy_at": None, "buy_status": None, "sell_at": None, "trigger": None, "no_sell": False, "closed": False, "scanned": None, "X": None,
           "fired_at": mono(), "eth_in": None, "restart": True, **{k: saved.get(k) for k in POS_KEYS}, "buy_block": None, "tokens": None, "sell_block_seen": state["head"]}
    pos["sell_sent"] = bool(pos["sell_sent"] and pos["sell_hash"])                # decided but never signed: sold now
    state["position"] = pos
    log({"ev": "alarm", "what": "an open position from the last run is taken back: " + ("its sell's receipt is awaited" if pos["sell_hash"] else "sold at once"),
         "pool": pos["pid"], "buy_hash": pos["buy_hash"], "sell_hash": pos["sell_hash"]})
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
    """the RPC's chain (waiting up to START_WAIT_S for it), the alternate's, the head; live: live_checks"""
    wait, waited = 1.0, 0.0
    while True:
        try:
            chain = endpoint_chain(S.RPC_URL); break
        except Exception as e:
            if waited >= START_WAIT_S:
                raise SystemExit(f"BASE_RPC_URL did not answer for {waited:.0f} s: {scrub(e, 120)}")
            alarm(f"BASE_RPC_URL did not answer at the start ({scrub(e, 120)}): trying again in {wait:.0f} s", quiet_key="start", every_s=60)
            time.sleep(wait); waited += wait; wait = min(30.0, wait * 2)
    need(chain == CHAIN_ID, f"BASE_RPC_URL is chain {chain}, not {CHAIN_ID}")
    chains = {host(S.RPC_URL): chain}
    if S.READ_ALT_URL:
        try:
            chains[host(S.READ_ALT_URL)] = endpoint_chain(S.READ_ALT_URL)
        except Exception as e:
            if not S.DRY:
                raise SystemExit(f"BASE_READ_ALT_URL did not answer eth_chainId: {scrub(e, 120)}")
            alarm(f"BASE_READ_ALT_URL did not answer at the start: {scrub(e, 120)}")
        need(chains.get(host(S.READ_ALT_URL), CHAIN_ID) == CHAIN_ID, f"BASE_READ_ALT_URL is chain {chains.get(host(S.READ_ALT_URL))}, not {CHAIN_ID}")
    info = {"chains": chains, "head": int(read("eth_blockNumber", [], timeout=SLOW_TIMEOUT_S, tries=3), 16)}
    if not S.DRY:
        info.update(live_checks(chains))
    return info


def need(ok, why):
    if not ok:
        raise SystemExit(why)


def live_checks(chains):
    """the wallet, its key (locked while the engine runs), the relay (owner, pm), the send endpoints, the stake, the balance, the nonce"""
    global SIGNER, KEY_LOCK
    from eth_account import Account
    need(S.WALLET, "BASE_WALLET is not set: a live start needs the wallet (deploy/base_wallet.py)")
    need(S.RELAY, "BASE_RELAY is not set: a live start needs the relay (deploy/base_relay_deploy.py)")
    need(S.STAKE_ETH_WEI <= S.STAKE_CAP_WEI, f"BASE_STAKE_ETH {S.STAKE_ETH_WEI / 1e18:g} is over BASE_STAKE_CAP_ETH {S.STAKE_CAP_WEI / 1e18:g}")
    try:
        f = open(S.KEY_FILE)
        key = f.read().strip()
        acct = Account.from_key(key if key.startswith("0x") else "0x" + key); del key
    except Exception as e:
        raise SystemExit(f"BASE_KEY_FILE {S.KEY_FILE} does not hold a key ({type(e).__name__})")
    try:                                                                       # held while the engine runs: deploy/base_wallet.py and base_ops.py
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)                         # test it with flock before they sign (one owner of the nonce)
    except OSError:
        f.close(); raise SystemExit(f"BASE_KEY_FILE {S.KEY_FILE} is locked by another process (another engine, or base_ops signing): not started")
    try:
        _live_reads(acct, chains)
    except BaseException:
        f.close(); raise                                                       # a refused start lets the lock go
    KEY_LOCK = f; SIGNER = acct
    return {"wallet": S.WALLET, "relay": S.RELAY, "relay_eth": state["relay_wei"] / 1e18, "nonce": state["nonce"]}


def _live_reads(acct, chains):
    need(acct.address.lower() == S.WALLET, "the key in BASE_KEY_FILE is not BASE_WALLET's")
    for u in S.SEND_URLS:
        try:
            chains[host(u)] = c = endpoint_chain(u)
        except Exception as e:
            raise SystemExit(f"BASE_SEND_URLS {host(u)} did not answer: {scrub(e, 120)}")
        need(c in (CHAIN_ID, "send-only"), f"BASE_SEND_URLS {host(u)} is chain {c}, not {CHAIN_ID}")
    need(len(read("eth_getCode", [S.RELAY, "latest"], tries=3)) > 2, "BASE_RELAY has no code: not a deployed FlipRelay")
    for sel, want, name in ((SEL_OWNER, S.WALLET, "owner() is {}, not BASE_WALLET"), (SEL_PM, S.PM, "pm() is {}, not BASE_POOL_MANAGER")):
        got = "0x" + read("eth_call", [{"to": S.RELAY, "data": "0x" + sel}, "latest"], tries=3)[-40:].lower()
        need(got == want, "the relay's " + name.format(got))
    state["relay_wei"] = int(read("eth_getBalance", [S.RELAY, "latest"], tries=3), 16)
    if state["relay_wei"] < S.STAKE_WEI + S.MARGIN_WEI:
        alarm(f"the relay holds {state['relay_wei'] / 1e18:.6f} ETH, under the stake + margin ({(S.STAKE_WEI + S.MARGIN_WEI) / 1e18:g}): no buy until it is funded")
    state["nonce"] = int(read("eth_getTransactionCount", [S.WALLET, "pending"], tries=3), 16)


def restore_today():
    """today's fires and P&L from the log (and its .1), so the cap and the stop hold across a restart; the live decoy streak (reset when the
    owner removed the halt file it wrote)"""
    roll_day(); d = state["day"]; streak = 0; streak_halted = False
    for path in (S.LOG_PATH + ".1", S.LOG_PATH):
        for line in (open(path).read().splitlines() if os.path.exists(path) else []):
            try:
                e = json.loads(line); ev = e.get("ev")
            except ValueError:
                continue
            if ev == "trade_done" and e.get("live"):
                streak = e.get("nonbot_streak") if e.get("nonbot_streak") is not None else streak
            elif ev == "halt" and "BASE_NONBOT_HALT" in str(e.get("reason")):
                streak_halted = True
            if datetime.datetime.fromtimestamp(e.get("t", 0), datetime.timezone.utc).strftime("%Y-%m-%d") == d:
                state["trades_today"] += ev == ("would_fire" if S.DRY else "fire")
                state["pnl_today_usd"] += (e.get("usd") or 0.0) if ev == "trade_done" and bool(e.get("dry")) == S.DRY else 0.0
    state["nonbot_streak"] = 0 if streak_halted and S.NONBOT_HALT and streak >= S.NONBOT_HALT and not os.path.exists(S.HALT_FILE) else streak
    state["stopped"] = d if S.DAILY_STOP_USD and state["pnl_today_usd"] <= -S.DAILY_STOP_USD else None


def start():
    need(not os.path.basename(S.LOG_PATH).startswith(("HALTED", "engine.jsonl", "flip_engine", "bnb")),
         f"BASE_LOG_PATH {S.LOG_PATH} names a halt file or another engine's log: the Base line logs to its own file (base.jsonl)")
    info = start_checks()
    restore_today()
    halted_file = read_halt_file() if os.path.exists(S.HALT_FILE) else None
    state["halted"] = None if S.DRY else halted_file                          # dry: the file is the live line's, not the dry run's
    saved = load_position()
    state["logs_to"] = info["head"] - S.ADD_MAX_BLOCKS - 2                       # a launch of the last blocks is read back (a restart mid-launch)
    shown = {k: (sorted(v) if isinstance(v, set) else host(v) if k.endswith("_URL") and v else v) for k, v in vars(S).items() if k != "KEY_FILE"}
    shown["SEND_URLS"] = [host(u) for u in S.SEND_URLS]
    log({"ev": "start", "release": RELEASE, "dry": S.DRY, "head": info["head"], "settings": shown, **{k: v for k, v in info.items() if k != "head"},
         "halted": state["halted"], "halt_file": halted_file, "trades_today": state["trades_today"], "pnl_today_usd": round(state["pnl_today_usd"], 4),
         "nonbot_streak": state["nonbot_streak"], "open_position": (saved or {}).get("pid")})
    if saved and not S.DRY:
        take_back(saved)
    elif saved:
        alarm(f"BASE_DRY_RUN=1 with a live position open in {S.POSITIONS_FILE}: it is not sold; start live (with HALTED.base in place to stop new buys) until it is")
    return info


# ---------------------------------------------------------------- the feeds' loops
spawn = lambda fn, *a: threading.Thread(target=fn, args=a, daemon=True).start()
ws_ssl = lambda url: ssl.create_default_context() if url.startswith("wss") else None
ws_healthy = lambda: bool(state["ws"]) and mono() - state["ws_last"] < S.WS_SILENT_S


def on_ws_message(raw, subs):
    d = json.loads(raw)
    if d.get("id") in (1, 2):
        if "error" in d:
            raise RuntimeError(f"eth_subscribe refused: {scrub(json.dumps(d['error']), 120)}")
        subs[d["result"]] = "heads" if d["id"] == 1 else "logs"
        with lock:
            state["ws_subs"] = len(subs); state["ws"] = len(subs) >= 2; state["ws_last"] = mono()
        return
    if d.get("method") != "eth_subscription":
        return
    prm = d["params"]; kind = subs.get(prm.get("subscription")); r = prm.get("result")
    with lock:
        if kind == "heads":
            on_head(int(r["number"], 16), int(r.get("timestamp") or "0x0", 16), int(r.get("baseFeePerGas") or "0x0", 16), "ws")
        elif kind == "logs":
            for lg in (r if isinstance(r, list) else [r]):
                on_ws_log(lg)


def ws_down(e):
    with lock:
        was = state["ws"]
        state.update(ws=False, ws_subs=0, ws_from=None)
    alarm(f"the websocket is down ({type(e).__name__}: {scrub(e, 100)}): eth_getLogs over BASE_RPC_URL until it is back", quiet_key="ws", was_up=was)


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
    await ws.send(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "eth_subscribe", "params": ["logs", {"address": S.PM, "topics": [[T_INIT, T_ML, T_SWAP]]}]}))
    subs = {}
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=S.WS_SILENT_S)          # silent: an exception, the reconnection, the gap filled
        for _ in range(500):                                                   # the burst: every message already here, then the actions
            try:
                on_ws_message(raw, subs)
            except RuntimeError:
                raise
            except Exception as e:
                alarm(f"a websocket message was not understood: {type(e).__name__}: {scrub(e, 80)}", quiet_key="wsmsg", every_s=60)
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=DRAIN_S)
            except asyncio.TimeoutError:
                break
        with lock:
            end_burst()


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
    """the poller's pass: with the websocket down or silent, the head and the logs one block behind it over BASE_RPC_URL; with a gap after
    a reconnection, the logs to the connection's first head. Never skips: a range is read whole or again"""
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
                alarm("no websocket: the head and the logs from BASE_RPC_URL", quiet_key="poll")
            on_head(h, int(hd.get("timestamp") or "0x0", 16), int(hd.get("baseFeePerGas") or "0x0", 16), "poll")
        lt = state["logs_to"] if state["logs_to"] is not None else h - S.ADD_MAX_BLOCKS - 2
    target = min(ws_from, h) if gap else h - POLL_LAG
    if target <= lt:
        return False
    b = min(target, lt + MAX_RANGE)
    logs = read("eth_getLogs", [{"fromBlock": hex(lt + 1), "toBlock": hex(b), "address": S.PM, "topics": [[T_INIT, T_ML, T_SWAP]]}], timeout=SLOW_TIMEOUT_S)
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
    pos = state["position"]
    log({"ev": "flow", "head": state["head"], "lag_s": state["lag_s"], "lag_max_s": state["lag_max_s"], "ws": ws_healthy(), "flash": state["flash"],
         "launches": state["launches"], "armed": sum(1 for p in pools.values() if p["status"] in ("arming", "armed")), "trades": state["trades_today"],
         "trades_done": state["trades_done"], "halted": state["halted"], "stopped": state["stopped"], "head_src": state["head_src"], "logs_to": state["logs_to"],
         "flash_block": state["flash_block"], "flash_msgs_min": state["flash_msgs"], "flash_total": state["flash_total"], "flash_bad": state["flash_bad"],
         "flash_reconnects": state["flash_reconnects"], "dups": state["dups"], "reorgs": state["reorgs"],
         "filled": state["filled"], "position": pos["pid"] if pos else None, "relay_eth": state["relay_wei"] / 1e18 if state["relay_wei"] is not None else None})
    state["flow_at"] = mono(); state["lag_max_s"] = None; state["flash_msgs"] = 0


def tick():
    """every second (under the lock): the Flashblocks health, the flow line, the pruning"""
    t = mono()
    if state["flash"] and t - state["flash_at"] > FLASH_SILENT_S:
        state["flash"] = False
    head = state["head"]
    if head is not None and t - state.get("pruned_at", 0.0) > 30:
        state["pruned_at"] = t
        for k in [k for k, b in seen.items() if b < head - 300]:
            del seen[k]
        for pid in [k for k, q in orphans.items() if not q or int(q[-1]["blockNumber"], 16) < head - 64]:
            del orphans[pid]
    end_burst()
    if t - state["flow_at"] >= FLOW_S:
        flow()


async def ticker():
    while True:
        await asyncio.sleep(1.0)
        with lock:
            tick()


def stop(*_):
    """SIGTERM: a last line and out (an open live position stays in base_positions.json for the next start); run by the loop, between its
    callbacks, so no lock of the main thread is held"""
    log({"ev": "stopped", "position": (state["position"] or {}).get("pid")}); os._exit(0)


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
