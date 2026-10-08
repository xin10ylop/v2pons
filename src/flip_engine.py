#!/usr/bin/env python3
"""flip_engine: the crowd-following flip on one operator's Uniswap v4 launches on Robinhood Chain (research report 24.54).

The operator (launcher contract LAUNCHERS) creates a pool paired with native ETH and, two to six seconds later, buys it with its
own wallets for minutes before its deployer removes the liquidity. Its deployer also removes the liquidity 1.0-1.9 s after an
outside buy of a few dollars. The flip buys right after the operator's FIRST real-size buy, holds HOLD_BLOCKS (0.7 s) while the
operator's next buys land behind us, and sells before its reaction. On paper (Oct 5-8, sub-1% fee pools): +3.6% a trade at a 4-block
hold, +6.3% at 7, 83-94% of trades positive; nobody has tried it live, and the test is whether our buy changes the operator's
reaction. DRY_RUN=1 (default) does everything but sign and send; src/score.py prices every decision from the chain afterwards.

Reads the public sequencer feed (one message per ~100 ms block; sequenceNumber = block number), decodes every signed transaction,
and acts on two kinds: a call to a launcher (the pool's key and liquidity come from the launch receipt, fetched at once), and the
first transaction carrying the new token's address with value >= MIN_TRIGGER_ETH (the operator's first buy). Then: the buy to the
FlipRelay at the reserved nonce, the sell at the next nonce when the feed shows our buy's block + HOLD_BLOCKS - SELL_LEAD_BLOCKS
(or by the wall-clock fallback), the receipts, the P&L. One position at a time; a daily cap and a daily stop.

Settings come from the environment (/etc/flip/engine.env on the box). Log: JSONL, one event per line, LOG_PATH.
"""
import os, sys, json, time, base64, threading, asyncio, socket, ssl, http.client, urllib.request, urllib.parse, datetime, traceback
import rlp
from eth_utils import keccak, to_checksum_address
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v4math

RELEASE = "0.1"


def env(k, d=""):
    v = os.environ.get(k)
    return d if v is None or v.strip() == "" else v.split(" #", 1)[0].strip()


FEED_URL = env("FEED_URL", "wss://feed.mainnet.chain.robinhood.com"); FEED_COMPRESSION = env("FEED_COMPRESSION", "deflate") or None
SEQ_URL = env("SEQ_URL", "https://sequencer.mainnet.chain.robinhood.com"); RPC_URL = env("RPC_URL", "https://rpc.mainnet.chain.robinhood.com")
LOG_PATH = env("LOG_PATH", "flip_engine.jsonl"); DRY_RUN = env("DRY_RUN", "1") != "0"; CHAIN_ID = 4663
LAUNCHERS = {a.strip().lower().replace("0x", "") for a in env("LAUNCHERS", "0x3194e32622c5d860a0572c74edda99dcfd8fc827").split(",") if a.strip()}
POOL_MANAGER = env("POOL_MANAGER", "0x8366a39cc670b4001a1121b8f6a443a643e40951").lower()
RELAY = env("RELAY", "").lower(); WALLET = env("WALLET", "").lower()
STAKE_ETH = float(env("STAKE_ETH", "0.0012")); STAKE_WEI = int(STAKE_ETH * 1e18); ETH_USD = float(env("ETH_USD", "2570"))
MIN_TRIGGER_ETH = float(env("MIN_TRIGGER_ETH", "0.0002")); MIN_TRIGGER_WEI = int(MIN_TRIGGER_ETH * 1e18)
FEE_MIN_PPM = int(env("FEE_MIN_PPM", "0")); FEE_MAX_PPM = int(env("FEE_MAX_PPM", "9999"))         # the sub-1% tier: the flip's edge is the operator's own flow minus two fees
MIN_LIQUIDITY = float(env("MIN_LIQUIDITY", "1e21")); TRIGGER_MAX_BLOCKS = int(env("TRIGGER_MAX_BLOCKS", "150"))
BUY_SLIP = float(env("BUY_SLIP", "0.10")); BUY_DEADLINE_S = int(env("BUY_DEADLINE_S", "3"))
HOLD_BLOCKS = int(env("HOLD_BLOCKS", "7")); SELL_LEAD_BLOCKS = int(env("SELL_LEAD_BLOCKS", "2")); SELL_FALLBACK_S = float(env("SELL_FALLBACK_S", "1.2"))
BUY_GAS = int(env("BUY_GAS", "350000")); SELL_GAS = int(env("SELL_GAS", "350000")); GAS_HEADROOM = float(env("GAS_HEADROOM", "3")); SELL_GAS_HEADROOM = float(env("SELL_GAS_HEADROOM", "6"))
MAX_TRADES_PER_DAY = int(env("MAX_TRADES_PER_DAY", "10")); DAILY_STOP_USD = float(env("DAILY_STOP_USD", "15"))
STALE_S = float(env("STALE_S", "2.5")); RECEIPT_TIMEOUT_S = float(env("RECEIPT_TIMEOUT_S", "25"))
POSITION_MANAGER = env("POSITION_MANAGER", "0x58daec3116aae6d93017baaea7749052e8a04fa7").lower().replace("0x", "")

T_INIT = keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP = keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
SEL_BUY = "5ed06f60"; SEL_SELL = "137f1fdd"; SEL_OWNER = "8da5cb5b"; SEL_PM = "8970cdff"
mono = time.monotonic
W = lambda d, i: int(d[2 + 64*i: 2 + 64*(i+1)], 16)
sgn = lambda x: x - (1 << 256) if x >= (1 << 255) else x
word = lambda x: ("%064x" % (x % (1 << 256))) if isinstance(x, int) else x.lower().replace("0x", "").zfill(64)
h0x = lambda s: s if s.startswith("0x") else "0x" + s

_log_lock = threading.Lock()
def log(ev):
    ev["t"] = round(time.time(), 3)
    line = json.dumps(ev, separators=(",", ":"))
    with _log_lock:
        with open(LOG_PATH, "a") as f:
            f.write(line + "\n")


# ---------------------------------------------------------------- RPC and the sequencer
def rpc(method, params, tries=4, timeout=10):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(RPC_URL, json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(), {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"})
            d = json.load(urllib.request.urlopen(req, timeout=timeout))
            if "result" in d:
                return d["result"]
            last = d.get("error")
            if isinstance(last, dict) and last.get("code") != 429:
                raise RuntimeError(json.dumps(last)[:300])
        except RuntimeError:
            raise
        except Exception as e:
            last = str(e)
        time.sleep(0.2 * (i + 1))
    raise RuntimeError(f"{method}: {last}")


class Sender:
    """warm HTTPS connections to the sequencer (one per slot), TCP_NODELAY, a keepalive every 5 s; post() returns the parsed reply"""
    def __init__(self, url, slots=2):
        u = urllib.parse.urlparse(url); self.host = u.hostname; self.port = u.port or 443; self.path = u.path or "/"
        self.conns = [None] * slots; self.locks = [threading.Lock() for _ in range(slots)]; self.last = [0.0] * slots
        threading.Thread(target=self._keepalive, daemon=True).start()

    def _open(self, i):
        c = http.client.HTTPSConnection(self.host, self.port, timeout=4, context=ssl.create_default_context()); c.connect()
        c.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1); self.conns[i] = c; return c

    def post(self, i, body, retry=True):
        with self.locks[i]:
            try:
                c = self.conns[i] or self._open(i)
                c.request("POST", self.path, body, {"Content-Type": "application/json", "Connection": "keep-alive"})
                r = c.getresponse(); data = r.read(); self.last[i] = mono()
                return json.loads(data)
            except Exception as e:
                try:
                    if self.conns[i]: self.conns[i].close()
                except Exception:
                    pass
                self.conns[i] = None
                if retry:
                    return self._retry(i, body)
                return {"error": {"message": f"send failed: {e}"}}

    def _retry(self, i, body):
        try:
            c = self._open(i); c.request("POST", self.path, body, {"Content-Type": "application/json", "Connection": "keep-alive"})
            r = c.getresponse(); data = r.read(); self.last[i] = mono(); return json.loads(data)
        except Exception as e:
            self.conns[i] = None; return {"error": {"message": f"send failed twice: {e}"}}

    def _keepalive(self):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []})
        while True:
            time.sleep(1.0)
            for i in range(len(self.conns)):
                if mono() - self.last[i] > 5.0 and self.locks[i].acquire(blocking=False):
                    try:
                        c = self.conns[i] or self._open(i)
                        c.request("POST", self.path, body, {"Content-Type": "application/json", "Connection": "keep-alive"}); c.getresponse().read(); self.last[i] = mono()
                    except Exception:
                        self.conns[i] = None
                    finally:
                        self.locks[i].release()


SENDER = None; SIGNER = None


# ---------------------------------------------------------------- feed decoding
def decode_batch(l2msg_b64):
    """the signed transactions (raw bytes) in one L2 batch message: kind byte 3, then segments of 8-byte big-endian length + body,
    of which kind 4 bodies are signed transactions"""
    raw = base64.b64decode(l2msg_b64)
    if not raw or raw[0] != 3:
        return []
    out = []; i = 1; n = len(raw)
    while i + 8 <= n:
        ln = int.from_bytes(raw[i:i+8], "big"); i += 8; seg = raw[i:i+ln]; i += ln
        if seg and seg[0] == 4:
            out.append(seg[1:])
    return out


def parse_tx(t):
    """(to, value, data, nonce, hash) for legacy and type 1/2 transactions, else None; `to` lower-case hex without 0x"""
    try:
        if t[0] >= 0xc0:
            f = rlp.decode(t); nonce, to, value, data = f[0], f[3], f[4], f[5]
        elif t[0] == 1:
            f = rlp.decode(t[1:]); nonce, to, value, data = f[1], f[4], f[5], f[6]
        elif t[0] == 2:
            f = rlp.decode(t[1:]); nonce, to, value, data = f[1], f[5], f[6], f[7]
        else:
            return None
        return (to.hex() if to else "", int.from_bytes(value, "big"), bytes(data), int.from_bytes(nonce, "big"), keccak(t).hex())
    except Exception:
        return None


# ---------------------------------------------------------------- state
state = {"seq": 0, "ts": 0, "nonce": None, "base_fee": 20_000_000, "armed": {}, "position": None, "day": None, "trades_today": 0, "pnl_today_usd": 0.0,
         "launches": 0, "fires": 0, "blocks": 0, "stale_blocks": 0, "connected": False}
lock = threading.RLock()


def today():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def roll_day():
    d = today()
    if state["day"] != d:
        state["day"] = d; state["trades_today"] = 0; state["pnl_today_usd"] = 0.0


def pool_from_receipt(rec):
    """the pool a launch receipt initialized (ETH as currency0, no hook) with its first liquidity, or None"""
    init = None; adds = []
    for l in rec.get("logs", []):
        if l["address"].lower() != POOL_MANAGER or not l["topics"]:
            continue
        tp = l["topics"][0][2:]
        if tp == T_INIT:
            init = l
        elif tp == T_ML:
            d = l["data"]; adds.append((sgn(W(d, 0)), sgn(W(d, 1)), sgn(W(d, 2)), l["topics"][1]))
    if init is None:
        return None
    d = init["data"]; pid = init["topics"][1]
    p = {"pid": pid, "c0": init["topics"][2][-40:], "token": init["topics"][3][-40:], "fee": W(d, 0), "tick_spacing": sgn(W(d, 1)), "hooks": d[2 + 64*2 + 24: 2 + 64*3],
         "sqrt_p": W(d, 3), "tick0": sgn(W(d, 4))}
    p["liq"] = v4math.active_liquidity(p["tick0"], [(lo, hi, dl) for lo, hi, dl, ppid in adds if ppid == pid])
    p["token_bytes"] = bytes.fromhex(p["token"])
    return p


def wait_receipt(h, timeout, every=0.04):
    t0 = mono()
    while mono() - t0 < timeout:
        try:
            r = rpc("eth_getTransactionReceipt", [h0x(h)], tries=1, timeout=3)
            if r:
                return r
        except Exception:
            pass
        time.sleep(every)
    return None


def arm_launch(tx_hash, seq, ts, seen_at):
    """thread: the launch receipt, the pool, the arming"""
    rec = wait_receipt(tx_hash, 4.0)
    if rec is None:
        log({"ev": "launch_no_receipt", "tx": tx_hash, "seq": seq}); return
    p = pool_from_receipt(rec)
    if p is None or rec.get("status") != "0x1":
        log({"ev": "launch_no_pool", "tx": tx_hash, "seq": seq, "status": rec.get("status")}); return
    p.update({"launch_seq": seq, "launch_ts": ts, "armed_at": mono(), "arm_ms": round(1000 * (mono() - seen_at), 1), "arm_seq": state["seq"], "first_buy": None, "status": "armed", "tx": tx_hash})
    eligible = p["c0"] == "0" * 40 and p["hooks"] == "0" * 40 and FEE_MIN_PPM <= p["fee"] <= FEE_MAX_PPM and p["liq"] >= MIN_LIQUIDITY
    p["eligible"] = eligible
    with lock:
        state["armed"][p["pid"]] = p; state["launches"] += 1
    log({"ev": "armed", "pid": p["pid"], "token": p["token"], "fee": p["fee"], "tick_spacing": p["tick_spacing"], "hooks": p["hooks"][-8:], "liq": p["liq"], "sqrt_p": p["sqrt_p"], "seq": seq,
         "arm_ms": p["arm_ms"], "arm_seq": p["arm_seq"], "eligible": eligible, "eth_pair": p["c0"] == "0" * 40})


def prune(seq):
    for pid in [k for k, p in state["armed"].items() if seq - p["launch_seq"] > 3000]:
        p = state["armed"].pop(pid)
        if p["first_buy"] is None:
            log({"ev": "no_first_buy", "pid": pid, "fee": p["fee"]})


# ---------------------------------------------------------------- transactions
def tx_buy(p, nonce, min_out, deadline):
    data = "0x" + SEL_BUY + word(p["c0"]) + word(p["token"]) + word(p["fee"]) + word(p["tick_spacing"]) + word(p["hooks"]) + word(STAKE_WEI) + word(min_out) + word(deadline)
    return {"to": to_checksum_address(RELAY), "value": 0, "data": data, "gas": BUY_GAS, "gasPrice": int(state["base_fee"] * GAS_HEADROOM), "nonce": nonce, "chainId": CHAIN_ID}


def tx_sell(p, nonce, min_out=0, deadline=0):
    data = "0x" + SEL_SELL + word(p["c0"]) + word(p["token"]) + word(p["fee"]) + word(p["tick_spacing"]) + word(p["hooks"]) + word(min_out) + word(deadline)
    return {"to": to_checksum_address(RELAY), "value": 0, "data": data, "gas": SELL_GAS, "gasPrice": int(state["base_fee"] * SELL_GAS_HEADROOM), "nonce": nonce, "chainId": CHAIN_ID}


def sign(tx):
    raw = bytes(SIGNER.sign_transaction(tx).raw_transaction)
    return raw, keccak(raw).hex()


def body(raw):
    return json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_sendRawTransaction", "params": ["0x" + raw.hex()]})


def fire(p, seq, ts, trig_value, trig_hash, seen_at):
    """the operator's first real-size buy on an armed pool is in block `seq`: buy now, sell HOLD_BLOCKS after our buy's block"""
    roll_day()
    if state["position"] is not None:
        log({"ev": "skip", "why": "position open", "pid": p["pid"], "seq": seq}); return
    if state["trades_today"] >= MAX_TRADES_PER_DAY:
        log({"ev": "skip", "why": "daily cap", "pid": p["pid"], "seq": seq, "trades_today": state["trades_today"]}); return
    if state["pnl_today_usd"] <= -DAILY_STOP_USD:
        log({"ev": "skip", "why": "daily stop", "pid": p["pid"], "seq": seq, "pnl_today_usd": round(state["pnl_today_usd"], 2)}); return
    if seq - p["launch_seq"] > TRIGGER_MAX_BLOCKS:
        log({"ev": "skip", "why": "late first buy (not the crowd)", "pid": p["pid"], "seq": seq, "offset": seq - p["launch_seq"]}); return
    if not p["eligible"]:
        log({"ev": "skip", "why": "pool not eligible", "pid": p["pid"], "fee": p["fee"], "liq": p["liq"]}); return
    fee = p["fee"]; x_trig = trig_value - (trig_value * fee + 999_999) // 1_000_000
    sp1 = int(v4math.sqrt_after_buy(p["sqrt_p"], p["liq"], x_trig))               # the pool after the trigger buy
    expected = v4math.buy_out_int(sp1, p["liq"], STAKE_WEI, fee); min_out = int(expected * (1 - BUY_SLIP))
    sp2 = int(v4math.sqrt_after_buy(sp1, p["liq"], STAKE_WEI - (STAKE_WEI * fee + 999_999) // 1_000_000))
    eth_back_flat = v4math.sell_out_int(sp2, p["liq"], expected, fee)             # what the sell gets if nobody buys behind us
    nonce = state["nonce"] if state["nonce"] is not None else 0
    deadline = ts + BUY_DEADLINE_S
    buy = tx_buy(p, nonce, min_out, deadline); sell = tx_sell(p, nonce + 1)
    pos = {"pid": p["pid"], "token": p["token"], "fee": fee, "trig_seq": seq, "trig_ts": ts, "trig_value": trig_value, "trig_hash": trig_hash, "fired_at": mono(), "nonce": nonce,
           "expected_tokens": expected, "min_out": min_out, "flat_eth_back": eth_back_flat, "buy_seq": None, "sell_sent": False, "sell_seq_sent": None, "buy_hash": None, "sell_hash": None, "dry": DRY_RUN,
           "plan_buy_seq": seq + 2, "plan_sell_seq": seq + 2 + HOLD_BLOCKS}
    state["position"] = pos; state["fires"] += 1; state["trades_today"] += 1; p["status"] = "fired"
    if DRY_RUN:
        log({"ev": "would_fire", **{k: v for k, v in pos.items() if k not in ("dry",)}, "buy_tx": buy, "sell_tx": sell, "react_ms": round(1000 * (mono() - seen_at), 1)})
        return
    t0 = mono(); raw_b, hb = sign(buy); raw_s, hs = sign(sell); pos["buy_hash"] = hb; pos["sell_hash"] = hs; pos["sell_raw"] = raw_s; t1 = mono()
    reply = SENDER.post(0, body(raw_b)); t2 = mono()
    pos["buy_reply"] = reply
    log({"ev": "fire", **{k: v for k, v in pos.items() if k not in ("sell_raw", "dry")}, "sign_ms": round(1000 * (t1 - t0), 1), "send_ms": round(1000 * (t2 - t1), 1), "react_ms": round(1000 * (t2 - seen_at), 1)})
    if "error" in reply:
        log({"ev": "buy_rejected", "pid": p["pid"], "reply": reply}); state["position"] = None; state["trades_today"] -= 1
        threading.Thread(target=refresh_nonce, daemon=True).start()
        return
    state["nonce"] = nonce + 2


def send_sell(why):
    pos = state["position"]
    if pos is None or pos["sell_sent"]:
        return
    pos["sell_sent"] = True; pos["sell_seq_sent"] = state["seq"]; pos["sell_sent_at"] = mono(); pos["sell_why"] = why
    if DRY_RUN:
        log({"ev": "would_sell", "pid": pos["pid"], "seq": state["seq"], "why": why, "buy_seq": pos["buy_seq"], "ms_since_fire": round(1000 * (mono() - pos["fired_at"]), 1)})
        threading.Thread(target=settle_dry, args=(pos,), daemon=True).start()
        return
    reply = SENDER.post(1, body(pos["sell_raw"])); pos["sell_reply"] = reply
    log({"ev": "sell_sent", "pid": pos["pid"], "seq": state["seq"], "why": why, "buy_seq": pos["buy_seq"], "hash": pos["sell_hash"], "reply": reply, "ms_since_fire": round(1000 * (mono() - pos["fired_at"]), 1)})
    threading.Thread(target=settle, args=(pos,), daemon=True).start()


def settle_dry(pos):
    time.sleep(1.0)
    with lock:
        if state["position"] is pos:
            state["position"] = None
    log({"ev": "trade_done", "dry": True, "pid": pos["pid"], "trig_seq": pos["trig_seq"], "plan_buy_seq": pos["plan_buy_seq"], "plan_sell_seq": pos["plan_sell_seq"], "sell_seq_sent": pos["sell_seq_sent"]})


def swap_of(rec, pid):
    for l in rec.get("logs", []):
        if l["address"].lower() == POOL_MANAGER and l["topics"] and l["topics"][0][2:] == T_SWAP and l["topics"][1] == pid:
            d = l["data"]; a0 = sgn(W(d, 0)); a1 = sgn(W(d, 1))
            if a0 >= (1 << 127): a0 -= 1 << 128
            if a1 >= (1 << 127): a1 -= 1 << 128
            return a0, a1
    return None


def settle(pos):
    """thread: both receipts, the pull check, the P&L; whatever happens, the position is closed and the nonce re-read"""
    try:
        _settle(pos)
    except Exception:
        log({"ev": "alarm", "what": "settle failed", "pid": pos["pid"], "trace": traceback.format_exc()[-600:]})
        with lock:
            if state["position"] is pos:
                state["position"] = None
        refresh_nonce()


def _settle(pos):
    rb = wait_receipt(pos["buy_hash"], RECEIPT_TIMEOUT_S); rs = wait_receipt(pos["sell_hash"], RECEIPT_TIMEOUT_S)
    out = {"ev": "trade_done", "dry": False, "pid": pos["pid"], "token": pos["token"], "fee": pos["fee"], "trig_seq": pos["trig_seq"], "trig_value": pos["trig_value"], "nonce": pos["nonce"],
           "expected_tokens": pos["expected_tokens"], "min_out": pos["min_out"], "buy_seq_feed": pos["buy_seq"], "sell_why": pos.get("sell_why"), "sell_seq_sent": pos["sell_seq_sent"]}
    gas_wei = 0; eth_in = 0; eth_out = 0; tokens = 0
    for name, rec in (("buy", rb), ("sell", rs)):
        if rec is None:
            out[name] = "no receipt"; continue
        bn = int(rec["blockNumber"], 16); ok = rec.get("status") == "0x1"; g = int(rec["gasUsed"], 16) * int(rec["effectiveGasPrice"], 16); gas_wei += g
        sw = swap_of(rec, pos["pid"]) if ok else None
        out[name] = {"block": bn, "status": "ok" if ok else "reverted", "gas_usd": round(g / 1e18 * ETH_USD, 4), "index": int(rec["transactionIndex"], 16)}
        if sw:
            a0, a1 = sw
            if name == "buy":
                eth_in = -a0; tokens = a1; out[name]["eth_in"] = eth_in; out[name]["tokens"] = tokens
            else:
                eth_out = a0; out[name]["eth_out"] = eth_out; out[name]["tokens_in"] = -a1
    if rb and rs and rb.get("status") == "0x1":
        b0 = int(rb["blockNumber"], 16); b1 = int(rs["blockNumber"], 16); out["hold_blocks"] = b1 - b0; out["buy_offset"] = b0 - pos["trig_seq"]
        try:
            ls = rpc("eth_getLogs", [{"fromBlock": hex(b0), "toBlock": hex(b1 + 30), "address": h0x(POOL_MANAGER), "topics": [h0x(T_ML), pos["pid"]]}])
            pulls = [int(l["blockNumber"], 16) - b0 for l in ls if sgn(W(l["data"], 2)) < 0]
            out["pull_after_buy_blocks"] = min(pulls) if pulls else None
        except Exception as e:
            out["pull_check"] = str(e)[:100]
    pnl = eth_out - eth_in - gas_wei
    out.update({"eth_in": eth_in, "eth_out": eth_out, "gas_wei": gas_wei, "pnl_eth": pnl / 1e18, "pnl_usd": round(pnl / 1e18 * ETH_USD, 3), "ret": round((eth_out - eth_in) / eth_in, 4) if eth_in else None,
                "flat_eth_back": pos["flat_eth_back"]})
    with lock:
        roll_day(); state["pnl_today_usd"] += out["pnl_usd"]
        if state["position"] is pos:
            state["position"] = None
    log(out)
    refresh_nonce()


def refresh_nonce():
    try:
        n = int(rpc("eth_getTransactionCount", [h0x(WALLET), "pending"]), 16)
        with lock:
            state["nonce"] = max(n, state["nonce"] or 0) if state["position"] is None else state["nonce"]
        log({"ev": "nonce", "chain": n, "engine": state["nonce"]})
    except Exception as e:
        log({"ev": "alarm", "what": "nonce refresh failed", "err": str(e)[:200]})


def watchdog():
    """the sell's wall-clock fallback, and the base fee"""
    while True:
        time.sleep(0.02)
        pos = state["position"]
        if pos and not pos["sell_sent"] and mono() - pos["fired_at"] > SELL_FALLBACK_S:
            with lock:
                send_sell("time fallback")
        if mono() - state.get("fee_at", 0) > 10:
            try:
                b = rpc("eth_getBlockByNumber", ["latest", False], tries=1, timeout=3); state["base_fee"] = int(b["baseFeePerGas"], 16); state["fee_at"] = mono()
            except Exception:
                pass


# ---------------------------------------------------------------- the feed
def ingest(raw):
    """one feed frame: every block in it, every transaction; the launches, the triggers, our own buy, the sell timing"""
    try:
        frame = json.loads(raw)
    except Exception:
        return
    wall = time.time()
    for m in frame.get("messages", []):
        seq = m.get("sequenceNumber"); inner = (m.get("message") or {}).get("message") or {}; hdr = inner.get("header") or {}
        if seq is None or hdr.get("kind") != 3:
            continue
        with lock:
            if seq <= state["seq"]:
                continue
            state["seq"] = seq; state["ts"] = hdr.get("timestamp", 0); state["blocks"] += 1
            stale = wall - state["ts"] > STALE_S
            if stale:
                state["stale_blocks"] += 1
            seen_at = mono(); txs = decode_batch(inner.get("l2Msg", "")); state["txs"] = state.get("txs", 0) + len(txs)
            for t in txs:
                tx = parse_tx(t)
                if tx is None:
                    continue
                to, value, data, nonce, h = tx
                pos = state["position"]
                if pos is not None and pos["buy_hash"] == h and pos["buy_seq"] is None:
                    pos["buy_seq"] = seq; log({"ev": "buy_seen", "pid": pos["pid"], "seq": seq, "offset": seq - pos["trig_seq"], "ms_since_fire": round(1000 * (mono() - pos["fired_at"]), 1)})
                    continue
                if stale:
                    continue
                if to in LAUNCHERS:
                    log({"ev": "launch", "tx": h, "seq": seq, "to": to}); threading.Thread(target=arm_launch, args=(h, seq, state["ts"], seen_at), daemon=True).start(); continue
                if value < MIN_TRIGGER_WEI or not state["armed"]:
                    continue
                for pid, p in list(state["armed"].items()):
                    if p["token_bytes"] in data and to != p["token"]:
                        if p["first_buy"] is None:
                            p["first_buy"] = seq
                            log({"ev": "first_buy", "pid": pid, "seq": seq, "offset": seq - p["launch_seq"], "value": value, "to": to, "fee": p["fee"], "eligible": p["eligible"], "ms_since_arm": round(1000 * (mono() - p["armed_at"]), 1)})
                            if p["status"] == "armed":
                                fire(p, seq, state["ts"], value, h, seen_at)
                        break
            pos = state["position"]
            if pos is not None and not pos["sell_sent"]:
                if pos["buy_seq"] is not None and seq >= pos["buy_seq"] + HOLD_BLOCKS - SELL_LEAD_BLOCKS:
                    send_sell("hold from the buy block")
                elif pos["buy_seq"] is None and seq >= pos["plan_buy_seq"] + HOLD_BLOCKS - SELL_LEAD_BLOCKS:
                    send_sell("hold from the planned buy block (buy not seen in the feed)")
            if state["blocks"] % 600 == 0:                                   # about once a minute: alive, decoding, and what it has seen
                prune(seq); log({"ev": "flow", "seq": seq, "ts": state["ts"], "lag_s": round(wall - state["ts"], 1), "blocks": state["blocks"], "txs": state["txs"], "launches": state["launches"], "fires": state["fires"], "armed": len(state["armed"]),
                                 "stale_blocks": state["stale_blocks"], "trades_today": state["trades_today"], "pnl_today_usd": round(state["pnl_today_usd"], 2)})


async def feed_loop():
    import websockets
    backoff = 0.2
    while True:
        try:
            async with websockets.connect(FEED_URL, open_timeout=10, max_size=None, ping_interval=10, ping_timeout=5, max_queue=4, compression=FEED_COMPRESSION) as ws:
                state["connected"] = True; log({"ev": "feed_connected", "url": FEED_URL}); backoff = 0.2
                while True:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    except asyncio.TimeoutError:
                        log({"ev": "feed_stall", "seq": state["seq"]}); break
                    ingest(raw)
        except Exception as e:
            log({"ev": "feed_error", "err": str(e)[:200]})
        state["connected"] = False
        await asyncio.sleep(backoff); backoff = min(5.0, backoff * 2)


# ---------------------------------------------------------------- start
def checks():
    chain = int(rpc("eth_chainId", []), 16)
    if chain != CHAIN_ID:
        raise SystemExit(f"RPC_URL is chain {chain}, not {CHAIN_ID}")
    b = rpc("eth_getBlockByNumber", ["latest", False]); state["base_fee"] = int(b["baseFeePerGas"], 16); state["fee_at"] = mono()
    info = {"chain": chain, "head": int(b["number"], 16), "base_fee_gwei": state["base_fee"] / 1e9}
    if RELAY:
        code = rpc("eth_getCode", [h0x(RELAY), "latest"]); owner = rpc("eth_call", [{"to": h0x(RELAY), "data": "0x" + SEL_OWNER}, "latest"]); pm = rpc("eth_call", [{"to": h0x(RELAY), "data": "0x" + SEL_PM}, "latest"])
        bal = int(rpc("eth_getBalance", [h0x(RELAY), "latest"]), 16)
        info.update({"relay_code_bytes": len(code) // 2 - 1, "relay_owner": "0x" + owner[-40:], "relay_pm": "0x" + pm[-40:], "relay_eth": bal / 1e18})
        if len(code) <= 2:
            raise SystemExit("RELAY has no code")
        if ("0x" + pm[-40:]).lower() != POOL_MANAGER:
            raise SystemExit(f"the relay's PoolManager is {pm[-40:]}, not {POOL_MANAGER}")
        if WALLET and ("0x" + owner[-40:]).lower() != h0x(WALLET):
            raise SystemExit(f"the relay's owner is 0x{owner[-40:]}, WALLET is {WALLET}")
        if not DRY_RUN and bal < STAKE_WEI:
            raise SystemExit(f"the relay holds {bal / 1e18:.6f} ETH, under the stake {STAKE_ETH}")
    if WALLET:
        state["nonce"] = int(rpc("eth_getTransactionCount", [h0x(WALLET), "pending"]), 16); info["wallet_nonce"] = state["nonce"]
        info["wallet_eth"] = int(rpc("eth_getBalance", [h0x(WALLET), "latest"]), 16) / 1e18
    if not DRY_RUN:
        global SIGNER, SENDER
        from eth_account import Account
        SIGNER = Account.from_key(os.environ["PRIVATE_KEY"])
        if SIGNER.address.lower() != h0x(WALLET):
            raise SystemExit(f"PRIVATE_KEY is for {SIGNER.address}, WALLET is {WALLET}")
        if not RELAY:
            raise SystemExit("RELAY is required when DRY_RUN=0")
        SENDER = Sender(SEQ_URL)
    return info


def main():
    roll_day(); info = checks()
    log({"ev": "start", "release": RELEASE, "dry_run": DRY_RUN, "launchers": sorted(LAUNCHERS), "relay": RELAY, "wallet": WALLET, "stake_eth": STAKE_ETH, "min_trigger_eth": MIN_TRIGGER_ETH,
         "fee_ppm": [FEE_MIN_PPM, FEE_MAX_PPM], "min_liquidity": MIN_LIQUIDITY, "trigger_max_blocks": TRIGGER_MAX_BLOCKS, "buy_slip": BUY_SLIP, "hold_blocks": HOLD_BLOCKS, "sell_lead_blocks": SELL_LEAD_BLOCKS,
         "sell_fallback_s": SELL_FALLBACK_S, "max_trades_per_day": MAX_TRADES_PER_DAY, "daily_stop_usd": DAILY_STOP_USD, "feed": FEED_URL, "seq": SEQ_URL, "rpc": RPC_URL, **info})
    threading.Thread(target=watchdog, daemon=True).start()
    try:
        asyncio.run(feed_loop())
    except KeyboardInterrupt:
        pass
    except Exception:
        log({"ev": "alarm", "what": "engine crashed", "trace": traceback.format_exc()[-800:]}); raise


if __name__ == "__main__":
    main()
