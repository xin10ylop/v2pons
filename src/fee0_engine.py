#!/usr/bin/env python3
"""fee0_engine: the fee-0 launch family on Robinhood Chain (research/hunt_oct26/REPORT_FEE0.md), a process of its own.

The line: a launcher contract, deployed fresh for every launch by a fresh wallet (one code, keccak LAUNCHER_CODE_HASH), is called with
selector LAUNCH_SELECTOR and ~5 ETH; it creates a token, opens a Uniswap v4 pool (ETH / token, fee 0, tick spacing 60, no hook, one
launch price FAM_SQRT_P) and buys it with the ETH in the same transaction. Minutes later (launch + 180..2100 blocks, median ~400) a crowd of
~660 recurring wallets buys it through the Universal Router; their buys push the price up for a while, then they sell out. No liquidity was
ever pulled (Oct 12 - Nov 17), a buy and a sell through the relay round-trip at 0.00% (fee 0), the token sells freely.

The trade: buy right behind the first crowd buy of TRIG_ETH or more (after the launch block), sell at +TAKE_PROFIT, or at -STOP_LOSS, or
HOLD_BLOCKS after our buy, or at once on a pull. Replayed on the chain (research/hunt_oct26/exitlag.py), +8% / -5% / 2000 blocks: Oct 19-26
+4.2% a trade on 216 (mean), Nov 14-17 +4.6% on 25; it holds with our buy and sell landing up to ~20 blocks late, so the chain is read
by polling the RPC's logs (no feed): every PoolManager Initialize, Swap and ModifyLiquidity, exact prices, sells included.

Every pool is checked before any buy: the launch transaction's target must carry the launcher code, and a buy and a sell of the stake
through the relay are run on the live pool by eth_call (state overrides: the relay's code and a harness, contracts/RoundTripHarness.json)
and must come back within CHECK_MAX_LOSS; the check is repeated every CHECK_EVERY blocks while the pool waits, and a buy needs one
younger than CHECK_MAX_AGE blocks. A pool that fails is never traded.

DRY_RUN=1 (default) does everything but sign and send: its buy lands LAND_BLOCKS after the block it was decided on, at the pool's real
price then, its sell the same, and it logs the paper result. Live (DRY_RUN=0) needs WALLET, PRIVATE_KEY and RELAY (a FlipRelay owned by
WALLET: deploy/relay_deploy.py); use a wallet and relay of their own, not flip_engine's (each process keeps its own nonces). One position
at a time; MAX_TRADES_PER_DAY; DAILY_STOP_USD; STAKE_ETH at most STAKE_CAP_ETH (0.3: the most the line's pools take without our own buy
eating the take-profit, research/hunt_oct26/REPORT_NOV16B.md). A sell that fails twice, or one that comes back under SANE_MIN of what the
pool's price said, writes HALT_FILE: no live buy until it is removed.

Replay (REPLAY_FROM=<block> [REPLAY_TO=<block>]): runs the same code dry over past blocks (no exit test: there is no past state), to
check its decisions against the research replays.

Settings from the environment; log: JSONL, one event per line, LOG_PATH."""
import os, sys, json, time, math, threading, http.client, urllib.parse, urllib.request, datetime, traceback, concurrent.futures
from eth_utils import keccak, to_checksum_address
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v4math

RELEASE = "0.1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def env(k, d=""):
    v = os.environ.get(k)
    return d if v is None or v.strip() == "" else v.split(" #", 1)[0].strip()


RPC_URL = env("RPC_URL", "https://rpc.mainnet.chain.robinhood.com"); SEQ_URL = env("SEQ_URL", "https://sequencer.mainnet.chain.robinhood.com")
CHAIN_ID = 4663; PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
DRY_RUN = env("DRY_RUN", "1") != "0"
WALLET = env("WALLET", "").lower(); RELAY = env("RELAY", "").lower()
LOG_PATH = env("LOG_PATH", "fee0_engine.jsonl"); HALT_FILE = env("HALT_FILE", os.path.join(os.path.dirname(os.path.abspath(LOG_PATH)), "FEE0_HALTED"))
LAUNCHER_CODE_HASH = env("LAUNCHER_CODE_HASH", "f554b29bdabadc9ff0388b9e48d16c9f7039e2b0d61ced2d09f4b813193dceb4").lower().replace("0x", "")
LAUNCH_SELECTOR = env("LAUNCH_SELECTOR", "d27d1e00").lower().replace("0x", "")
FAM_FEE = int(env("FAM_FEE", "0")); FAM_TICK_SPACING = int(env("FAM_TICK_SPACING", "60"))
FAM_SQRT_P = int(env("FAM_SQRT_P", "2505036234966386302045715536678303"))            # 0: any launch price
STAKE_CAP_ETH = 0.3
STAKE_ETH = float(env("STAKE_ETH", "0.002")); STAKE_WEI = int(STAKE_ETH * 1e18); ETH_USD = float(env("ETH_USD", "3000"))
TRIG_ETH = float(env("TRIG_ETH", "0.02")); TRIG_WEI = int(TRIG_ETH * 1e18)
TRIGGER_MAX_BLOCKS = int(env("TRIGGER_MAX_BLOCKS", "2500"))                          # the crowd's first buy came at launch + 179..2113 (Nov 14-17)
TAKE_PROFIT = float(env("TAKE_PROFIT", "0.08")); STOP_LOSS = float(env("STOP_LOSS", "0.05")); HOLD_BLOCKS = int(env("HOLD_BLOCKS", "2000"))
BUY_SLIP = float(env("BUY_SLIP", "0.05")); BUY_DEADLINE_S = int(env("BUY_DEADLINE_S", "4"))
LAND_BLOCKS = int(env("LAND_BLOCKS", "4"))                                           # dry: our transaction lands this many blocks after the block it was decided on
MAX_TRADES_PER_DAY = int(env("MAX_TRADES_PER_DAY", "40")); DAILY_STOP_USD = float(env("DAILY_STOP_USD", "10"))
CHECK_EVERY = int(env("CHECK_EVERY", "300")); CHECK_MAX_AGE = int(env("CHECK_MAX_AGE", "600")); CHECK_MAX_LOSS = float(env("CHECK_MAX_LOSS", "0.02"))
SANE_MIN = float(env("SANE_MIN", "0.5"))
GAS_LIMIT = int(env("GAS_LIMIT", "350000")); GAS_HEADROOM = float(env("GAS_HEADROOM", "3")); DRY_GAS_WEI = int(float(env("DRY_GAS_ETH", "0.000006")) * 1e18)
POLL_S = float(env("POLL_S", "0.1")); STATUS_EVERY_S = float(env("STATUS_EVERY_S", "600")); OVERLAP = int(env("OVERLAP", "3"))
REPLAY_FROM = int(env("REPLAY_FROM", "0")); REPLAY_TO = int(env("REPLAY_TO", "0")); MAX_POSITIONS = int(env("MAX_POSITIONS", "1"))
if REPLAY_FROM:
    DRY_RUN = True
if not DRY_RUN:
    MAX_POSITIONS = 1                                                                 # live: one position (the wallet's nonces are one line)

T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
SEL_BUY = "5ed06f60"; SEL_SELL = "137f1fdd"; SEL_OWNER = "8da5cb5b"; SEL_PM = "8970cdff"
SEL_RUN = keccak(text="run(address,(address,address,uint24,int24,address),uint256,uint256)")[:4].hex()
RELAY_AT = "0x" + "f1" * 20; HARNESS_AT = "0x" + "a1" * 20; ZERO = "0" * 40
word = lambda x: ("%064x" % (x % (1 << 256))) if isinstance(x, int) else x.lower().replace("0x", "").zfill(64)
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
sgn = lambda x: x - (1 << 256) if x >= (1 << 255) else x
lock = threading.Lock()


def log(ev):
    ev = {"t": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z", **ev}
    line = json.dumps(ev, default=str)
    with lock:
        with open(LOG_PATH, "a") as f:
            f.write(line + "\n")
    if ev.get("ev") in ("start", "armed", "check", "trigger", "would_fire", "fire", "landed", "exit", "settled", "skip", "alarm", "halt", "status", "replay_done"):
        print(line, flush=True)


def rpc(method, params, url=None, tries=4, timeout=10):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url or RPC_URL, json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                                         {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/128.0"})
            d = json.load(urllib.request.urlopen(req, timeout=timeout))
            if "result" in d:
                return d["result"]
            last = d.get("error")
            if not (isinstance(last, dict) and last.get("code") in (429, -32005)):
                raise RuntimeError(f"{method}: {json.dumps(last)[:300]}")
        except RuntimeError:
            raise
        except Exception as e:
            last = str(e)[:200]
        time.sleep(0.2 * (i + 1))
    raise RuntimeError(f"{method}: {last}")


def rpc_batch(calls, url=None, timeout=6):
    """several calls in one HTTP request: their results in order (an error in any raises)"""
    body = json.dumps([{"jsonrpc": "2.0", "id": i, "method": m, "params": p} for i, (m, p) in enumerate(calls)]).encode()
    req = urllib.request.Request(url or RPC_URL, body, {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/128.0"})
    d = json.load(urllib.request.urlopen(req, timeout=timeout))
    if not isinstance(d, list):
        raise RuntimeError(f"batch: {json.dumps(d)[:200]}")
    by = {x.get("id"): x for x in d}
    out = []
    for i, (m, _) in enumerate(calls):
        x = by.get(i) or {}
        if "result" not in x:
            raise RuntimeError(f"{m}: {json.dumps(x.get('error'))[:200]}")
        out.append(x["result"])
    return out


def relay_runtime(owner):
    """FlipRelay's runtime code with its immutables (pm, owner) filled in: the exit test's relay"""
    art = json.load(open(os.path.join(ROOT, "contracts", "FlipRelay.json"))); code = bytearray.fromhex(art["deployedBytecode"][2:])
    ids = sorted(art["immutableReferences"], key=int)
    assert len(ids) == 2, art["immutableReferences"]
    for ast_id, val in zip(ids, (PM, owner)):
        for r in art["immutableReferences"][ast_id]:
            code[r["start"]:r["start"] + r["length"]] = bytes(12) + bytes.fromhex(val[2:])
    return "0x" + code.hex()


HARNESS = json.load(open(os.path.join(ROOT, "contracts", "RoundTripHarness.json")))["deployedBytecode"]
RELAY_SIM = relay_runtime(HARNESS_AT)


def key_words(p):
    return word(0) + word(p["token"]) + word(p["fee"]) + word(p["tick_spacing"]) + word(0)


def exit_test(p, amount):
    """a buy of `amount` and a sell of everything through the relay on the pool as it is now, by eth_call: (ok, detail)"""
    data = "0x" + SEL_RUN + word(RELAY_AT) + key_words(p) + word(amount) + word(0)
    ov = {RELAY_AT: {"code": RELAY_SIM, "balance": hex(amount * 2)}, HARNESS_AT: {"code": HARNESS}}
    try:
        r = rpc("eth_call", [{"from": "0x" + "c0" * 20, "to": HARNESS_AT, "data": data, "gas": hex(3_000_000)}, "latest", ov], tries=2, timeout=8)
    except RuntimeError as e:
        msg = str(e)
        if "execution reverted" in msg or "revert" in msg:
            return False, "the round trip reverted: " + msg[:160]
        return None, "no answer: " + msg[:160]                                     # the RPC, not the token: ask again
    tokens, held, back, _ = (W(r, i) for i in range(4))
    if tokens == 0 or held == 0:
        return False, "the buy got no tokens"
    loss = (amount - back) / amount
    return (loss <= CHECK_MAX_LOSS), f"round trip {-loss:+.2%} (tokens {tokens})"


def launcher_ok(tx_hash):
    """the launch transaction calls LAUNCH_SELECTOR on a contract carrying the launcher code: (ok, detail)"""
    try:
        t = rpc("eth_getTransactionByHash", [tx_hash])
        to = (t.get("to") or "").lower(); sel = t["input"][2:10]
        c = rpc("eth_getCode", [to, "latest"])
        h = keccak(bytes.fromhex(c[2:])).hex() if len(c) > 2 else "none"
    except Exception as e:
        return None, "no answer: " + str(e)[:120]
    if sel != LAUNCH_SELECTOR:
        return False, f"launch selector {sel}"
    if h != LAUNCHER_CODE_HASH:
        return False, f"launcher code {h[:16]}"
    return True, f"launcher {to[:10]}, value {int(t['value'], 16) / 1e18:g} ETH, from {t['from'][:10]}"


class Sender:
    """eth_sendRawTransaction on a kept-open connection to the sequencer, the RPC as the second way"""
    def __init__(self, url):
        self.u = urllib.parse.urlparse(url); self.c = None

    def send(self, raw):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_sendRawTransaction", "params": ["0x" + raw.hex()]})
        for attempt in range(2):
            try:
                if self.c is None:
                    self.c = http.client.HTTPSConnection(self.u.hostname, self.u.port or 443, timeout=4)
                self.c.request("POST", self.u.path or "/", body, {"Content-Type": "application/json"})
                d = json.loads(self.c.getresponse().read())
                if "result" in d:
                    return True, d["result"]
                err = json.dumps(d.get("error"))[:200]
                if "already" in err or "known" in err:
                    return True, err
                return False, err
            except Exception as e:
                self.c = None; last = str(e)[:200]
        try:
            return True, rpc("eth_sendRawTransaction", ["0x" + raw.hex()], tries=1, timeout=4)
        except Exception as e:
            return False, f"{last}; rpc: {str(e)[:200]}"


class Engine:
    def __init__(self):
        self.pools = {}; self.pos = {}; self.day = None; self.trades = 0; self.pnl_usd = 0.0; self.seen_txs = set()
        self.head = 0; self.signer = None; self.sender = None; self.nonce = None; self.gas_price = None; self.halted = os.path.exists(HALT_FILE)
        self.workers = concurrent.futures.ThreadPoolExecutor(max_workers=4); self.results = []; self.last_status = time.time(); self.limited = 0

    # ------------------------------------------------------------------ the day
    def roll_day(self):
        d = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        if d != self.day:
            self.day, self.trades, self.pnl_usd = d, 0, 0.0

    # ------------------------------------------------------------------ pools
    def on_init(self, l):
        d = l["data"]; pid = l["topics"][1]
        if l["topics"][2][-40:] != ZERO or W(d, 0) != FAM_FEE or sgn(W(d, 1)) != FAM_TICK_SPACING or d[2 + 128 + 24: 2 + 192] != ZERO:
            return
        if FAM_SQRT_P and W(d, 3) != FAM_SQRT_P:
            return
        bn = int(l["blockNumber"], 16)
        p = {"pid": pid, "bn": bn, "token": "0x" + l["topics"][3][-40:], "fee": FAM_FEE, "tick_spacing": FAM_TICK_SPACING, "sp": W(d, 3), "liq": 0, "adds": [],
             "tick0": sgn(W(d, 4)), "status": "armed", "tx": l["transactionHash"], "launcher": None, "launcher_detail": None, "check": None, "check_at": None,
             "check_detail": None, "checking": False, "swaps": 0}
        self.pools[pid] = p
        log({"ev": "armed", "pid": pid, "block": bn, "token": p["token"], "tx": p["tx"]})
        self.workers.submit(self.check_launcher, p)

    def check_launcher(self, p):
        ok, det = launcher_ok(p["tx"])
        if ok is None:                                                               # no answer: once more
            time.sleep(1); ok, det = launcher_ok(p["tx"])
        p["launcher"], p["launcher_detail"] = ok, det
        log({"ev": "check", "what": "launcher", "pid": p["pid"], "ok": ok, "detail": det})
        if not ok and p["status"] == "armed":
            p["status"] = "refused"

    def check_exit(self, p, at):
        try:
            ok, det = exit_test(p, self.stake())
            p["check"], p["check_detail"] = ok, det
            if ok is not None:
                p["check_at"] = at
            log({"ev": "check", "what": "exit", "pid": p["pid"], "ok": ok, "detail": det, "block": at})
            if ok is False:
                p["status"] = "refused"
        finally:
            p["checking"] = False

    def stake(self):
        return min(STAKE_WEI, int(STAKE_CAP_ETH * 1e18))

    def on_ml(self, l):
        p = self.pools.get(l["topics"][1])
        if p is None:
            return
        d = l["data"]; lo, hi, dl = sgn(W(d, 0)), sgn(W(d, 1)), sgn(W(d, 2)); bn = int(l["blockNumber"], 16)
        if bn == p["bn"] and dl > 0:
            p["adds"].append((lo, hi, dl))
            if p["swaps"] == 0:
                p["liq"] = v4math.active_liquidity(p["tick0"], p["adds"])                   # before the first swap only: every Swap carries the pool's liquidity
        if dl < 0 and bn > p["bn"]:
            p["pulled"] = bn
            log({"ev": "alarm", "what": "liquidity pulled", "pid": p["pid"], "block": bn, "delta": dl, "open": p["pid"] in self.pos})
            pos = self.pos.get(p["pid"])
            if pos is not None and pos["state"] == "open":
                self.exit(pos, bn, "the liquidity was pulled")

    def on_swap(self, l):
        p = self.pools.get(l["topics"][1])
        if p is None:
            return
        d = l["data"]; a0, a1 = sgn(W(d, 0)), sgn(W(d, 1)); bn = int(l["blockNumber"], 16)
        sender = "0x" + l["topics"][2][-40:]
        p["swaps"] += 1; p.setdefault("hist", []).append((bn, W(d, 2), W(d, 3)))
        if len(p["hist"]) > 4000:
            del p["hist"][:-4000]
        p["sp"], p["liq"] = W(d, 2), W(d, 3)
        pos = self.pos.get(p["pid"])
        if pos is not None and not pos["dry"] and sender == RELAY:                  # our own swap: the buy's tokens, or the sell's ETH
            if a0 < 0 and pos["state"] == "sent":
                pos.update({"state": "open", "land": bn, "tokens": a1, "paid": -a0})
                log({"ev": "landed", "side": "buy", "pid": p["pid"], "block": bn, "trig_block": pos["trig"], "late": bn - pos["trig"], "tokens": a1, "paid": -a0, "tx": l["transactionHash"]})
            elif a0 > 0 and pos["state"] == "selling":
                self.settle_live(pos, bn, a0, l["transactionHash"])
            return
        native_in = -a0
        if p["status"] == "armed" and bn > p["bn"] and native_in >= TRIG_WEI:
            p["status"] = "triggered"; p["trig"] = bn
            log({"ev": "trigger", "pid": p["pid"], "block": bn, "offset": bn - p["bn"], "eth": native_in / 1e18, "via": sender, "seen_at": self.head, "seen_late": self.head - bn})
            self.fire(p, bn, l["transactionHash"])

    # ------------------------------------------------------------------ the buy
    def fire(self, p, bn, h):
        self.roll_day()
        stake = self.stake(); live = not DRY_RUN
        why = None
        if bn - p["bn"] > TRIGGER_MAX_BLOCKS:
            why = f"trigger at launch + {bn - p['bn']}, after TRIGGER_MAX_BLOCKS"
        elif p["launcher"] is not True:
            why = f"launcher not confirmed: {p['launcher_detail']}"
        elif not REPLAY_FROM and (p["check"] is not True or p["check_at"] is None or self.head - p["check_at"] > CHECK_MAX_AGE):   # dry too: it shows what live would do
            why = f"no recent exit test: {p['check_detail']} at {p['check_at']}"
        elif live and (self.halted or os.path.exists(HALT_FILE)):
            self.halted = True; why = f"halted ({HALT_FILE})"
        elif len(self.pos) >= MAX_POSITIONS:
            why = "position open"
        elif self.trades >= MAX_TRADES_PER_DAY:
            why = "daily cap"
        elif self.pnl_usd <= -DAILY_STOP_USD:
            why = "daily stop"
        if why:
            p["status"] = "skipped"; log({"ev": "skip", "pid": p["pid"], "block": bn, "why": why}); return
        self.trades += 1; p["status"] = "fired"
        pos = {"pid": p["pid"], "trig": bn, "trig_tx": h, "decided": self.head, "stake": stake, "dry": not live, "state": "sent", "land": None, "tokens": None,
               "exit_why": None, "exit_signal": None, "exit_decided": None}
        if not live:
            pos["land"] = self.head + LAND_BLOCKS                                        # the dry buy lands LAND_BLOCKS after the block it was decided on
            pos["state"] = "landing"
            self.pos[p["pid"]] = pos
            log({"ev": "would_fire", "pid": p["pid"], "trig_block": bn, "decided_at": self.head, "land_block": pos["land"], "stake": stake / 1e18}); return
        expected = v4math.buy_out_int(p["sp"], p["liq"], stake, 0); min_out = int(expected * (1 - BUY_SLIP))
        deadline = int(time.time()) + BUY_DEADLINE_S
        tx = {"to": to_checksum_address(RELAY), "value": 0, "data": "0x" + SEL_BUY + key_words(p) + word(stake) + word(min_out) + word(deadline),
              "gas": GAS_LIMIT, "gasPrice": self.gas_price, "nonce": self.nonce, "chainId": CHAIN_ID}
        raw = bytes(self.signer.sign_transaction(tx).raw_transaction); txh = "0x" + keccak(raw).hex()
        ok, res = self.sender.send(raw)
        pos.update({"buy_tx": txh, "nonce": self.nonce, "expected": expected, "min_out": min_out, "sent_at": time.time()})
        log({"ev": "fire", "pid": p["pid"], "token": p["token"], "trig_block": bn, "decided_at": self.head, "stake": stake / 1e18, "expected": expected, "min_out": min_out, "tx": txh,
             "sent": ok, "reply": res})
        if not ok:
            self.trades -= 1; p["status"] = "skipped"; self.resync_nonce(); return
        self.nonce += 1; self.pos[p["pid"]] = pos

    # ------------------------------------------------------------------ the exit
    def ret_now(self, p, pos):
        """what selling our tokens gets now, net of the round trip's gas, as a return on the stake (a dry position is not in the pool:
        its buy is put in first)"""
        sp = p["sp"] if not pos["dry"] else int(v4math.sqrt_after_buy(p["sp"], p["liq"], pos["stake"]))
        eth = v4math.sell_out_int(sp, p["liq"], pos["tokens"], 0)
        gas = DRY_GAS_WEI if pos["dry"] else pos.get("gas_est", DRY_GAS_WEI)
        return (eth - pos["stake"] - gas) / pos["stake"]

    def state_before(self, p, blk, inclusive=False):
        """the pool's (sqrtP, liquidity) after the last swap before block blk (or in it, inclusive)"""
        best = None
        for b, sp, lq in p.get("hist", []):
            if b < blk or (inclusive and b == blk):
                best = (sp, lq)
        return best or (p["sp"], p["liq"])

    def tick(self):
        """after every poll: dry landings, every open position's take-profit / stop / cap, dry sells' landing, live timeouts"""
        for pid, pos in list(self.pos.items()):
            p = self.pools[pid]
            if pos["state"] == "landing" and self.head >= pos["land"] - 1:             # dry: the buy is in at the price before its block
                if p.get("pulled") and p["pulled"] < pos["land"]:
                    log({"ev": "skip", "pid": pid, "why": "pulled before our dry buy landed"}); del self.pos[pid]; self.trades -= 1; continue
                sp, lq = self.state_before(p, pos["land"])
                pos.update({"state": "open", "tokens": v4math.buy_out_int(sp, lq, pos["stake"], 0), "entry_sp": sp})
                log({"ev": "landed", "side": "buy", "pid": pid, "dry": True, "block": pos["land"], "trig_block": pos["trig"], "late": pos["land"] - pos["trig"], "tokens": pos["tokens"]})
            if pos["state"] == "open":
                if self.head >= pos["land"] + HOLD_BLOCKS:
                    self.exit(pos, self.head, f"the cap: our buy + {HOLD_BLOCKS} blocks"); continue
                if p.get("hist") and p["hist"][-1][0] >= pos["land"]:
                    r = self.ret_now(p, pos)
                    if r >= TAKE_PROFIT:
                        self.exit(pos, p["hist"][-1][0], f"take profit {r:+.1%}")
                    elif r <= -STOP_LOSS:
                        self.exit(pos, p["hist"][-1][0], f"stop loss {r:+.1%}")
            if pos["state"] == "selling" and pos["dry"] and self.head >= pos["sell_land"]:
                self.settle_dry(pos)
            elif pos["state"] == "sent" and not pos["dry"] and time.time() - pos["sent_at"] > BUY_DEADLINE_S + 6:
                self.workers.submit(self.buy_lost, pos); pos["state"] = "checking_buy"
            elif pos["state"] == "selling" and not pos["dry"] and time.time() - pos["sell_at"] > 8 and not pos.get("sell_checking"):
                pos["sell_checking"] = True; self.workers.submit(self.sell_lost, pos)

    def exit(self, pos, blk, why):
        if pos["state"] != "open":
            return
        pos.update({"state": "selling", "exit_why": why, "exit_signal": blk, "exit_decided": self.head})
        p = self.pools[pos["pid"]]
        if pos["dry"]:
            pos["sell_land"] = self.head + LAND_BLOCKS
            pos["model_ret"] = self.ret_now(p, pos) if not p.get("pulled") else -1.0
            log({"ev": "exit", "pid": pos["pid"], "dry": True, "why": why, "signal_block": blk, "decided_at": self.head, "sell_land": pos["sell_land"], "held": self.head - pos["land"]}); return
        pos["model_ret"] = self.ret_now(p, pos)
        self.send_sell(pos, why)

    def send_sell(self, pos, why):
        p = self.pools[pos["pid"]]
        tx = {"to": to_checksum_address(RELAY), "value": 0, "data": "0x" + SEL_SELL + key_words(p) + word(0) + word(0), "gas": GAS_LIMIT,
              "gasPrice": self.gas_price * 2, "nonce": self.nonce, "chainId": CHAIN_ID}
        raw = bytes(self.signer.sign_transaction(tx).raw_transaction); txh = "0x" + keccak(raw).hex()
        ok, res = self.sender.send(raw); self.nonce += 1
        pos.update({"sell_tx": txh, "sell_at": time.time(), "sell_tries": pos.get("sell_tries", 0) + 1})
        log({"ev": "exit", "pid": pos["pid"], "why": why, "decided_at": self.head, "held": self.head - pos["land"], "model_ret": round(pos["model_ret"], 4), "tx": txh, "sent": ok, "reply": res})
        if not ok:
            self.resync_nonce()

    def settle_dry(self, pos):
        p = self.pools[pos["pid"]]
        if p.get("pulled") and p["pulled"] <= pos["sell_land"]:
            r = -1.0
        else:
            sp, lq = self.state_before(p, pos["sell_land"], inclusive=True)
            sp2 = int(v4math.sqrt_after_buy(sp, lq, pos["stake"]))
            r = (v4math.sell_out_int(sp2, lq, pos["tokens"], 0) - pos["stake"] - DRY_GAS_WEI) / pos["stake"]
        self.book(pos, r, {"dry": True, "sell_block": pos["sell_land"]})

    def settle_live(self, pos, bn, eth_back, txh):
        pos["state"] = "settling"
        def work():
            gas = 0
            for h in (pos.get("buy_tx"), txh):
                try:
                    rc = rpc("eth_getTransactionReceipt", [h])
                    gas += int(rc["gasUsed"], 16) * int(rc.get("effectiveGasPrice", "0x0"), 16)
                except Exception:
                    pass
            r = (eth_back - pos["stake"] - gas) / pos["stake"]
            model_eth = (pos["model_ret"] * pos["stake"]) + pos["stake"]
            self.book(pos, r, {"dry": False, "sell_block": bn, "eth_back": eth_back, "gas": gas, "sell_tx": txh})
            if pos["model_ret"] > -0.9 and eth_back < SANE_MIN * model_eth:
                self.halt(f"the sell got {eth_back / 1e18:.6f} ETH, under {SANE_MIN:.0%} of the {model_eth / 1e18:.6f} the pool's price said")
        self.workers.submit(work)

    def book(self, pos, r, extra):
        usd = r * pos["stake"] / 1e18 * ETH_USD
        self.pnl_usd += usd
        self.results.append(r)
        n = len(self.results)
        log({"ev": "settled", "pid": pos["pid"], "ret": round(r, 4), "usd": round(usd, 3), "why": pos["exit_why"], "trig_block": pos["trig"], "land": pos["land"],
             "held": (pos["exit_signal"] or 0) - (pos["land"] or 0), "model_ret": round(pos.get("model_ret") or 0, 4), **extra,
             "run": {"n": n, "mean": round(sum(self.results) / n, 4), "won": sum(1 for x in self.results if x > 0), "pnl_today_usd": round(self.pnl_usd, 3)}})
        self.pos.pop(pos["pid"], None)

    # ------------------------------------------------------------------ live failures
    def buy_lost(self, pos):
        """the buy's Swap never showed: its receipt says why (reverted: no trade; none: dropped)"""
        try:
            rc = rpc("eth_getTransactionReceipt", [pos["buy_tx"]])
        except Exception as e:
            rc = None
        if rc and rc.get("status") == "0x1":                                        # it went in and our Swap was missed: read it from the receipt
            for l in rc.get("logs", []):
                if l["address"].lower() == PM and l["topics"][0] == T_SWAP and l["topics"][1] == pos["pid"]:
                    a0, a1 = sgn(W(l["data"], 0)), sgn(W(l["data"], 1))
                    pos.update({"state": "open", "land": int(rc["blockNumber"], 16), "tokens": a1, "paid": -a0})
                    log({"ev": "landed", "side": "buy", "pid": pos["pid"], "block": pos["land"], "from": "receipt", "tokens": a1}); return
        log({"ev": "skip", "pid": pos["pid"], "why": "the buy did not go in", "status": rc.get("status") if rc else None, "tx": pos["buy_tx"]})
        self.trades -= 1; self.pos.pop(pos["pid"], None); self.resync_nonce()

    def sell_lost(self, pos):
        """the sell's Swap never showed: reverted or dropped: once more, then halt"""
        try:
            rc = rpc("eth_getTransactionReceipt", [pos["sell_tx"]])
        except Exception:
            rc = None
        if rc and rc.get("status") == "0x1":
            for l in rc.get("logs", []):
                if l["address"].lower() == PM and l["topics"][0] == T_SWAP and l["topics"][1] == pos["pid"]:
                    self.settle_live(pos, int(rc["blockNumber"], 16), sgn(W(l["data"], 0)), pos["sell_tx"]); return
        self.resync_nonce()
        if pos["sell_tries"] >= 2:
            self.halt(f"the sell failed twice on {pos['pid']} (status {rc.get('status') if rc else None})"); pos["sell_checking"] = False; return
        log({"ev": "alarm", "what": "the sell did not go in: once more", "pid": pos["pid"], "status": rc.get("status") if rc else None})
        pos["sell_checking"] = False; self.send_sell(pos, pos["exit_why"] + " (again)")

    def halt(self, why):
        self.halted = True
        with open(HALT_FILE, "w") as f:
            f.write(why + "\n")
        log({"ev": "halt", "why": why, "file": HALT_FILE})

    def recover(self):
        """live start: a position a stopped or crashed run left open (a sent fire in the log with no settlement after it) is sold now if
        the relay still holds its token"""
        if not os.path.exists(LOG_PATH):
            return
        open_ = {}
        with open(LOG_PATH) as f:
            for line in f:
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                if ev.get("ev") == "fire" and ev.get("sent") and ev.get("token"):
                    open_[ev["pid"]] = ev
                elif ev.get("ev") in ("settled", "recovered") or (ev.get("ev") == "skip" and ev.get("why") == "the buy did not go in"):
                    open_.pop(ev.get("pid"), None)
        for pid, ev in open_.items():
            bal = int(rpc("eth_call", [{"to": ev["token"], "data": "0x70a08231" + word(RELAY)}, "latest"]), 16)
            if bal == 0:
                log({"ev": "recovered", "pid": pid, "what": "nothing held"}); continue
            p = {"token": ev["token"], "fee": FAM_FEE, "tick_spacing": FAM_TICK_SPACING}
            tx = {"to": to_checksum_address(RELAY), "value": 0, "data": "0x" + SEL_SELL + key_words(p) + word(0) + word(0), "gas": GAS_LIMIT,
                  "gasPrice": self.gas_price * 2, "nonce": self.nonce, "chainId": CHAIN_ID}
            raw = bytes(self.signer.sign_transaction(tx).raw_transaction); ok, res = self.sender.send(raw); self.nonce += 1
            rc = None
            for _ in range(40):
                time.sleep(0.5)
                try:
                    rc = rpc("eth_getTransactionReceipt", ["0x" + keccak(raw).hex()])
                except Exception:
                    rc = None
                if rc:
                    break
            back = 0
            for l in (rc or {}).get("logs", []):
                if l["address"].lower() == PM and l["topics"][0] == T_SWAP and l["topics"][1] == pid:
                    back = sgn(W(l["data"], 0))
            log({"ev": "recovered", "pid": pid, "what": f"sold {bal} tokens left from a stopped run", "sent": ok, "status": (rc or {}).get("status"), "eth_back": back / 1e18,
                 "stake": ev.get("stake")})
            if not rc or rc.get("status") != "0x1":
                self.halt(f"a position left open ({pid}) could not be sold at start: sell it by hand"); return
        self.resync_nonce()

    def resync_nonce(self):
        try:
            self.nonce = int(rpc("eth_getTransactionCount", [WALLET, "pending"]), 16)
        except Exception as e:
            log({"ev": "alarm", "what": "nonce read failed", "err": str(e)[:120]})

    # ------------------------------------------------------------------ the loop
    def ingest(self, logs):
        logs.sort(key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
        for l in logs:
            k = (l["transactionHash"], l["logIndex"])
            if k in self.seen_txs:
                continue
            self.seen_txs.add(k)
            t0 = l["topics"][0]
            if t0 == T_INIT:
                self.on_init(l)
            elif t0 == T_SWAP:
                self.on_swap(l)
            elif t0 == T_ML:
                self.on_ml(l)

    def maintain(self):
        """exit tests on waiting pools; pools past their window dropped"""
        for pid, p in list(self.pools.items()):
            if p["status"] == "armed" and self.head - p["bn"] > TRIGGER_MAX_BLOCKS + 10:
                p["status"] = "expired"
            if p["status"] in ("expired", "refused", "skipped") or (p["status"] == "fired" and pid not in self.pos):
                if self.head - p["bn"] > TRIGGER_MAX_BLOCKS + HOLD_BLOCKS + 200:
                    del self.pools[pid]
                continue
            if not REPLAY_FROM and p["status"] == "armed" and p["launcher"] and not p["checking"] and (p["check_at"] is None or self.head - p["check_at"] >= CHECK_EVERY) \
                    and self.head > p["bn"] + 1:
                p["checking"] = True; self.workers.submit(self.check_exit, p, self.head)
        if len(self.seen_txs) > 200000:
            self.seen_txs = set(list(self.seen_txs)[-50000:])
        if time.time() - self.last_status > STATUS_EVERY_S:
            self.last_status = time.time(); n = len(self.results)
            log({"ev": "status", "head": self.head, "pools_waiting": sum(1 for p in self.pools.values() if p["status"] == "armed"), "open": len(self.pos), "trades_today": self.trades,
                 "pnl_today_usd": round(self.pnl_usd, 3), "settled": n, "mean": round(sum(self.results) / n, 4) if n else None, "halted": self.halted,
                 "rate_limited": self.limited})

    def run_live(self):
        """one round trip a poll: the head and the PoolManager's logs since a little before the last head (OVERLAP blocks, the two
        answers may come from a node a block apart; a log seen twice counts once)"""
        cursor = int(rpc("eth_blockNumber", []), 16)
        while True:
            try:
                head_r, logs = rpc_batch([("eth_blockNumber", []), ("eth_getLogs", [{"fromBlock": hex(max(0, cursor - OVERLAP)), "toBlock": "latest", "address": PM,
                                                                                       "topics": [[T_INIT, T_SWAP, T_ML]]}])])
                head = int(head_r, 16)
                top = max([head] + [int(l["blockNumber"], 16) for l in logs or []])
                self.head = max(self.head, top); self.ingest(logs or []); cursor = max(cursor, top)
                self.tick(); self.maintain()
            except Exception as e:
                if "429" in str(e):                                                    # the RPC's rate limit: counted (status), not an alarm each time
                    self.limited += 1; time.sleep(1.0)
                else:
                    log({"ev": "alarm", "what": "loop", "err": str(e)[:200]}); time.sleep(0.5)
            time.sleep(POLL_S)

    def run_replay(self):
        """the same code over past blocks: the family's launches (Initialize), then each one's swaps and liquidity changes over its window,
        fed block by block (a block's logs are seen at that block: LAND_BLOCKS is the whole delay to our landing)"""
        to = REPLAY_TO or int(rpc("eth_blockNumber", []), 16) - TRIGGER_MAX_BLOCKS - HOLD_BLOCKS - 50
        log({"ev": "start", "replay": [REPLAY_FROM, to]})
        inits = []
        for c in range(REPLAY_FROM, to + 1, 50000):
            inits += rpc("eth_getLogs", [{"fromBlock": hex(c), "toBlock": hex(min(to, c + 49999)), "address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}], tries=8, timeout=60) or []
        fam = [l for l in inits if W(l["data"], 0) == FAM_FEE and sgn(W(l["data"], 1)) == FAM_TICK_SPACING and l["data"][2 + 128 + 24: 2 + 192] == ZERO
               and (not FAM_SQRT_P or W(l["data"], 3) == FAM_SQRT_P)]
        byb = {}
        for l in fam:
            byb.setdefault(int(l["blockNumber"], 16), []).append(l)
            bn = int(l["blockNumber"], 16); end = bn + TRIGGER_MAX_BLOCKS + HOLD_BLOCKS + 3 * LAND_BLOCKS + 20
            for c in range(bn, end + 1, 50000):
                for x in rpc("eth_getLogs", [{"fromBlock": hex(c), "toBlock": hex(min(end, c + 49999)), "address": PM, "topics": [[T_SWAP, T_ML], l["topics"][1]]}], tries=8, timeout=60) or []:
                    byb.setdefault(int(x["blockNumber"], 16), []).append(x)
        log({"ev": "status", "replay_launches": len(fam), "replay_logs": sum(len(v) for v in byb.values())})
        last = to + TRIGGER_MAX_BLOCKS + HOLD_BLOCKS + 3 * LAND_BLOCKS + 20
        blk = REPLAY_FROM
        while blk <= last:
            self.head = blk
            if blk in byb:
                self.ingest(byb[blk])
                if any(l["topics"][0] == T_INIT for l in byb[blk]):
                    self.workers.shutdown(wait=True); self.workers = concurrent.futures.ThreadPoolExecutor(max_workers=4)   # replay: the launcher check before the next block
            self.tick()
            if blk % 200 == 0:
                self.maintain()
            blk += 1
        n = len(self.results)
        log({"ev": "replay_done", "settled": n, "mean": round(sum(self.results) / n, 4) if n else None, "won": sum(1 for x in self.results if x > 0),
             "median": round(sorted(self.results)[n // 2], 4) if n else None, "worst": round(min(self.results), 4) if n else None})


def checks(e):
    """live: the key is WALLET's, the relay is WALLET's and the PoolManager's, it holds the stake; the gas price and the nonce"""
    info = {}
    if STAKE_ETH > STAKE_CAP_ETH:
        raise SystemExit(f"STAKE_ETH {STAKE_ETH} is over STAKE_CAP_ETH {STAKE_CAP_ETH}")
    if not 0 < TAKE_PROFIT < 5 or not 0 < STOP_LOSS < 1 or not 1 <= HOLD_BLOCKS <= 20000 or not 0 < TRIG_WEI:
        raise SystemExit("TAKE_PROFIT, STOP_LOSS, HOLD_BLOCKS or TRIG_ETH out of range")
    gp = int(rpc("eth_gasPrice", []), 16); e.gas_price = max(int(gp * GAS_HEADROOM), gp + 1); info["gas_price_gwei"] = e.gas_price / 1e9
    if DRY_RUN:
        return info
    from eth_account import Account
    if not (WALLET and RELAY):
        raise SystemExit("live needs WALLET, RELAY and PRIVATE_KEY")
    e.signer = Account.from_key(os.environ["PRIVATE_KEY"])
    if e.signer.address.lower() != WALLET:
        raise SystemExit(f"PRIVATE_KEY is for {e.signer.address}, WALLET is {WALLET}")
    owner = "0x" + rpc("eth_call", [{"to": RELAY, "data": "0x" + SEL_OWNER}, "latest"])[-40:]
    pm = "0x" + rpc("eth_call", [{"to": RELAY, "data": "0x" + SEL_PM}, "latest"])[-40:]
    if owner.lower() != WALLET or pm.lower() != PM:
        raise SystemExit(f"RELAY {RELAY}: owner {owner}, PoolManager {pm}: must be WALLET and {PM}")
    bal = int(rpc("eth_getBalance", [RELAY, "latest"]), 16); info["relay_eth"] = bal / 1e18
    if bal < e.stake():
        raise SystemExit(f"RELAY holds {bal / 1e18} ETH, under the stake {e.stake() / 1e18}")
    e.nonce = int(rpc("eth_getTransactionCount", [WALLET, "pending"]), 16); e.sender = Sender(SEQ_URL); info["nonce"] = e.nonce
    e.recover()
    return info


def gas_loop(e):
    while True:
        time.sleep(60)
        try:
            gp = int(rpc("eth_gasPrice", []), 16); e.gas_price = max(int(gp * GAS_HEADROOM), gp + 1)
        except Exception:
            pass


def main():
    e = Engine(); info = checks(e)
    log({"ev": "start", "release": RELEASE, "dry_run": DRY_RUN, "replay": REPLAY_FROM or None, "wallet": WALLET, "relay": RELAY, "stake_eth": e.stake() / 1e18, "trig_eth": TRIG_ETH,
         "take_profit": TAKE_PROFIT, "stop_loss": STOP_LOSS, "hold_blocks": HOLD_BLOCKS, "trigger_max_blocks": TRIGGER_MAX_BLOCKS, "land_blocks": LAND_BLOCKS,
         "fam": {"fee": FAM_FEE, "tick_spacing": FAM_TICK_SPACING, "sqrt_p": FAM_SQRT_P, "launch_selector": LAUNCH_SELECTOR, "launcher_code": LAUNCHER_CODE_HASH[:16]},
         "max_trades_per_day": MAX_TRADES_PER_DAY, "daily_stop_usd": DAILY_STOP_USD, "halted": e.halted, "halt_file": HALT_FILE, "rpc": urllib.parse.urlparse(RPC_URL).hostname, **info})
    if REPLAY_FROM:
        e.run_replay(); return
    threading.Thread(target=gas_loop, args=(e,), daemon=True).start()
    e.run_live()


if __name__ == "__main__":
    main()
