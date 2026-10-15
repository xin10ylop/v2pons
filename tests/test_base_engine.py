"""The Base engine (src/base_engine.py) against the 2.433 operator's 09:42 UTC test pool on Base (launch block L = 52590807,
tests/data/base_launch.json, built by research/session_oct14/base2433/b13_fixture.py from Tenderly): its Initialize, the add at +3 (two
ModifyLiquidity), the bot's buys and the wallets' sells from +8, the pull at +30, the block headers, the launch, add, bot-buy and pull
transactions with their receipts (l1Fee included) and the token's code. The RPC (every read and send), both websockets (the confirmed
feed's messages and the Flashblocks stream's brotli frames) and the signing key are stubbed; nothing reaches a network. Each case prints
"ok <name>"; the count at the end. Plain script: python3 tests/test_base_engine.py"""
import os, sys, json, copy, time, tempfile, threading, asyncio, types
import brotli, rlp
from eth_account import Account
from eth_utils import keccak
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); TMP = tempfile.mkdtemp(prefix="base_engine_test_"); LOG = os.path.join(TMP, "base.jsonl")
BASE_ENV = {"BASE_LOG_PATH": LOG, "BASE_RPC_URL": "https://rpc.example.org/v1/k3y-rpc-secret", "BASE_READ_ALT_URL": "https://alt.example.org/",
            "BASE_WS_URL": "wss://ws.example.org/ws/k3y-ws-secret", "BASE_FLASH_URL": "wss://flash.example.org/ws",
            "BASE_SEND_URLS": "https://seq.example.org,https://send2.example.org", "BASE_KEY_FILE": os.path.join(TMP, "missing.key"),
            "BASE_FIRE_DELAY_BLOCKS": "0"}                                     # the cases below fire at once unless they set it
for k in [k for k in os.environ if k.startswith("BASE_")]:
    os.environ.pop(k)
os.environ.update(BASE_ENV)
sys.path.insert(0, os.path.join(ROOT, "src"))
import base_engine as E
import v4math
REAL_HTTP = E.http_json
E.RECEIPT_POLL_S = 0.005; E.POLL_S = 0.005

FX = json.load(open(os.path.join(ROOT, "tests", "data", "base_launch.json")))
L = FX["launch_block"]; PID = FX["pool"]; TOKEN = FX["key"]["currency1"]; HOOK = FX["key"]["hooks"]; ROLES = FX["roles"]
UR = "0x6ff5693b99212da76ad316178a184ab56d299b43"; BOT = "0x987d5db84d105c1f49391af409cc34c6050fb1d0"
LAUNCH_TX = FX["txs"][ROLES["launch"][0]]; ADD_TX = FX["txs"][ROLES["add"][0]]; BOT1_TX = FX["txs"][ROLES["bot_buys"][0]]; PULL_TX = FX["txs"][ROLES["pull"][0]]
LAUNCHER = LAUNCH_TX["to"].lower(); FAKE_LAUNCHER_CODE = "0x6080604052" + "00" * 40
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16); sgn = E.sgn; word = E.word
blk = lambda lg: int(lg["blockNumber"], 16)
Q96 = 1 << 96; FEE = 5000
SP0 = W(FX["init_log"]["data"], 3); TICK0 = sgn(W(FX["init_log"]["data"], 4))
LIQ = sum(sgn(W(l["data"], 2)) for l in FX["pool_logs"] if l["topics"][0] == E.T_ML and sgn(W(l["data"], 2)) > 0)
HEAD = {int(h["number"], 16): h for h in FX["headers"]}
KEY = Account.create(); RELAY = "0x" + "f1" * 20
TESTS = []


def test(fn):
    TESTS.append(fn); return fn


# ---------------------------------------------------------------- the exact PoolManager arithmetic (to make the chain's side of our own swaps)
def exact_buy(sp, liq, eth_in, fee=FEE):
    x = eth_in * (10 ** 6 - fee) // 10 ** 6; num = liq << 96; den = num + x * sp; sn = (num * sp + den - 1) // den
    return liq * (sp - sn) // Q96, sn


def exact_sell(sp, liq, t_in, fee=FEE):
    x = t_in * (10 ** 6 - fee) // 10 ** 6; sn = sp + (x << 96) // liq
    return ((liq << 96) * (sn - sp) // sn) // sp, sn


# ---------------------------------------------------------------- the stubbed chain
def header(n):
    if n in HEAD:
        return HEAD[n]
    last = max(HEAD); h = HEAD[last]
    return {"number": hex(n), "hash": "0x" + keccak(text=f"block{n}").hex(), "timestamp": hex(int(h["timestamp"], 16) + 2 * (n - last)), "baseFeePerGas": h["baseFeePerGas"]}


def mklog(kind, B, li, words_, sender=UR, tx=None, pid=PID):
    t0 = {"ml": E.T_ML, "swap": E.T_SWAP}[kind]
    return {"address": E.S.PM, "topics": [t0, pid, "0x" + "0" * 24 + sender[2:]], "data": "0x" + "".join(word(x) for x in words_), "blockNumber": hex(B),
            "blockHash": header(B)["hash"], "logIndex": hex(li), "transactionHash": tx or "0x" + keccak(text=f"tx{B}.{li}.{kind}").hex(), "transactionIndex": "0x1", "removed": False}


def swap_log(B, li, a0, a1, sp, liq=LIQ, sender=UR, tx=None):
    return mklog("swap", B, li, [a0, a1, sp, liq, 0, FEE], sender, tx)


class Chain:
    def __init__(self, logs=None, txs=None):
        self.logs = copy.deepcopy([FX["init_log"]] + FX["pool_logs"] if logs is None else logs)
        self.txs = copy.deepcopy(FX["txs"] if txs is None else txs); self.receipts = {}; self.head = L + 40; self.calls = []; self.ranges = []
        self.code = {TOKEN: FX["token_code"], LAUNCHER: FAKE_LAUNCHER_CODE, RELAY: "0x6001"}; self.chain_ids = {}; self.owner = None; self.pm = E.S.PM
        self.balance = 10 ** 18; self.nonce = 7; self.sent = []; self.fail = set(); self.auto = None; self.replies = []; self.tokens = 0

    def http(self, url, payload, timeout):
        m, prm = payload["method"], payload["params"]; self.calls.append((E.host(url), m))
        if (E.host(url), m) in self.fail or m in self.fail:
            raise RuntimeError(f"stub: {url} is down")
        if m == "eth_chainId":
            c = self.chain_ids.get(E.host(url), 8453)
            return {"error": {"code": -32601, "message": "rpc method is not allowed"}} if c == "send-only" else {"result": hex(c)}
        if m == "eth_sendRawTransaction":
            return {"error": {"code": -32602, "message": "typed transaction too short"}}
        if m == "eth_blockNumber":
            return {"result": hex(self.head)}
        if m == "eth_getBlockByNumber":
            return {"result": header(self.head)}
        if m == "eth_getLogs":
            f = prm[0]; a, b = int(f["fromBlock"], 16), int(f["toBlock"], 16); self.ranges.append((a, b))
            return {"result": [copy.deepcopy(l) for l in self.logs if a <= blk(l) <= b]}
        if m == "eth_getTransactionByHash":
            return {"result": copy.deepcopy(self.txs.get(prm[0]))}
        if m == "eth_getTransactionReceipt":
            if prm[0] not in self.receipts and self.auto and prm[0] in {"0x" + keccak(bytes.fromhex(r[2:])).hex() for _, r in self.sent}:
                r = self.auto(prm[0])
                if r:
                    self.receipts[prm[0]] = r
            return {"result": copy.deepcopy(self.receipts.get(prm[0]))}
        if m == "eth_getCode":
            return {"result": self.code.get(prm[0].lower(), "0x")}
        if m == "eth_getBalance":
            return {"result": hex(self.balance)}
        if m == "eth_getTransactionCount":
            return {"result": hex(self.nonce)}
        if m == "eth_call":
            sel = prm[0]["data"][2:10]
            if sel == "70a08231":
                return {"result": "0x" + word(self.tokens)}
            return {"result": "0x" + "0" * 24 + ((self.owner or E.S.WALLET)[2:] if sel == E.SEL_OWNER else self.pm[2:])}
        raise RuntimeError(m)

    def post(self, url, body):
        raw = json.loads(body)["params"][0]; self.sent.append((E.host(url), raw))
        if self.replies:
            return self.replies.pop(0)
        return {"jsonrpc": "2.0", "id": 1, "result": "0x" + keccak(bytes.fromhex(raw[2:])).hex()}


def fresh(logs=None, txs=None, dry=True, **env):
    """a new engine state with these settings, a stubbed chain and an empty log; the websocket connected from block L - 1"""
    for k in [k for k in os.environ if k.startswith("BASE_")]:
        os.environ.pop(k)
    os.environ.update(BASE_ENV); os.environ["BASE_DRY_RUN"] = "1" if dry else "0"
    os.environ.update({k: str(v) for k, v in env.items()})
    E.S = E.settings(); E.S.LAUNCHER_PREFIXES = [E.code_hash(FAKE_LAUNCHER_CODE)[2:14]]   # the launcher's real code is not in the fixture (its hash is)
    E.reset(); E.SIGNER = None
    if E.KEY_LOCK:
        E.KEY_LOCK.close(); E.KEY_LOCK = None
    for f in (LOG, E.S.HALT_FILE, E.S.POSITIONS_FILE):
        if os.path.exists(f):
            os.remove(f)
    open(LOG, "w").close()
    c = Chain(logs, txs); E.http_json = c.http; E.post_one = c.post
    if not dry:
        E.S.WALLET = KEY.address.lower(); E.S.RELAY = RELAY; E.SIGNER = KEY; E.state.update(nonce=7, relay_wei=10 ** 18)
    E.state["logs_to"] = L - 1                                                  # complete to L - 1: the websocket covers from its first head
    c.subs = {}
    E.on_ws_message(json.dumps({"jsonrpc": "2.0", "id": 1, "result": "0xh"}), c.subs)
    E.on_ws_message(json.dumps({"jsonrpc": "2.0", "id": 2, "result": "0xl"}), c.subs)
    return c


def by_block(logs):
    out = {}
    for l in logs:
        out.setdefault(blk(l), []).append(l)
    return out


def feed(c, a, b, logs=None, skip_heads=()):
    """the websocket from block a to b: each block's logs, then its head, one burst each"""
    bb = by_block(c.logs if logs is None else logs)
    for n in range(a, b + 1):
        for lg in bb.get(n, []):
            E.on_ws_message(json.dumps({"jsonrpc": "2.0", "method": "eth_subscription", "params": {"subscription": "0xl", "result": lg}}), c.subs)
        if n not in skip_heads:
            h = header(n)
            E.on_ws_message(json.dumps({"jsonrpc": "2.0", "method": "eth_subscription", "params": {"subscription": "0xh", "result": {
                "number": h["number"], "timestamp": h["timestamp"], "baseFeePerGas": h["baseFeePerGas"]}}}), c.subs)
        with E.lock:
            E.end_burst()


def events(ev=None, **match):
    out = []
    for line in open(LOG):
        e = json.loads(line)
        if (ev is None or e["ev"] == ev) and all(e.get(k) == v for k, v in match.items()):
            out.append(e)
    return out


def wait_ev(ev, n=1, timeout=5.0, **match):
    t0 = time.time()
    while time.time() - t0 < timeout:
        got = events(ev, **match)
        if len(got) >= n:
            return got
        time.sleep(0.005)
    raise AssertionError(f"no {n} x {ev} {match} in {timeout} s; log tail: {open(LOG).read()[-1500:]}")


def launch_armed(c):
    """block L (the Initialize), the arm's reads, then L+1, L+2"""
    feed(c, L - 1, L); wait_ev("launch"); feed(c, L + 1, L + 2)
    return events("launch")[0]


def raw_of(t):
    """a transaction of the fixture as its raw signed bytes, re-encoded (type 2)"""
    i = lambda x: int(x, 16); b = lambda x: bytes.fromhex(x[2:]) if x and x != "0x" else b""
    f = [i(t["chainId"]), i(t["nonce"]), i(t["maxPriorityFeePerGas"]), i(t["maxFeePerGas"]), i(t["gas"]), b(t["to"]), i(t["value"]), b(t["input"]), [],
         i(t["yParity"]), i(t["r"]), i(t["s"])]
    return "0x02" + rlp.encode(f).hex()


def flash(n, txs, index=1, base_fee=None):
    msg = {"payload_id": "0x01", "index": index, "diff": {"transactions": txs}, "metadata": {"block_number": n}}
    if index == 0:
        msg["base"] = {"block_number": hex(n), "timestamp": header(n)["timestamp"], "base_fee_per_gas": base_fee or header(n)["baseFeePerGas"]}
    E.on_flash(brotli.compress(json.dumps(msg).encode()))


def first_bot_swap():
    return [l for l in FX["pool_logs"] if l["topics"][0] == E.T_SWAP][0]


def expected_dry(sell_sp, sell_liq=LIQ, stake=None, buy_sp=SP0):
    """the dry trade by v4math alone: the buy at buy_sp, the sell at sell_sp with our buy put in (1/sqrtP adds)"""
    stake = stake or E.S.STAKE_WEI
    tokens = v4math.buy_out_int(buy_sp, LIQ, stake, FEE)
    net = stake - (stake * FEE + 999_999) // 1_000_000
    sp = int(v4math.sqrt_after_buy(sell_sp, sell_liq, net))
    out = v4math.sell_out_int(sp, sell_liq, tokens, FEE)
    return tokens, out


# ---------------------------------------------------------------- the cases
@test
def fixture_shape():
    assert os.path.getsize(os.path.join(ROOT, "tests", "data", "base_launch.json")) < 400_000 and "_about" in FX
    assert FX["code_hashes"]["token"] in E.S.TOKEN_CODEHASHES and FX["code_hashes"]["launcher"][2:].startswith("225f9af97d88")
    assert E.code_hash(FX["token_code"]) == FX["code_hashes"]["token"] and FX["code_sizes"]["token"] == 1526
    assert int(HOOK, 16) & 0x3fff == 0x80 and FX["key"]["fee"] == 5000 and FX["key"]["tickSpacing"] == 100
    for h, t in FX["txs"].items():
        assert "0x" + keccak(bytes.fromhex(raw_of(t)[2:])).hex() == h, h
    kinds = [(blk(l) - L, "ml" if l["topics"][0] == E.T_ML else "swap") for l in FX["pool_logs"]]
    assert kinds[:3] == [(3, "ml"), (3, "ml"), (8, "swap")] and kinds[-1] == (30, "ml") and LIQ == 46141758126452008872417
    assert all(int(r.get("l1Fee", "0x0"), 16) > 0 for r in FX["receipts"].values())


@test
def v4math_against_the_chain():
    """buy_out_int at the Initialize price and the add's liquidity against every recorded bot buy before any sell: a few thousand raw
    units LOW (v4math's denominator floors x * sqrtP / 2^96 where the PoolManager rounds the whole quotient), relative error < 1e-18"""
    sp = SP0; n = 0
    for l in FX["pool_logs"]:
        if l["topics"][0] != E.T_SWAP:
            continue
        a0, a1, sp_after = sgn(W(l["data"], 0)), sgn(W(l["data"], 1)), W(l["data"], 2)
        if a0 < 0:
            got = v4math.buy_out_int(sp, LIQ, -a0, FEE)
            assert got <= a1 and (a1 - got) / a1 < 1e-18, (blk(l) - L, got, a1)
            assert exact_buy(sp, LIQ, -a0) == (a1, sp_after)                     # the test's own exact arithmetic: to the unit
            n += 1
        sp = sp_after
    first = first_bot_swap(); a1 = sgn(W(first["data"], 1))
    assert a1 - v4math.buy_out_int(SP0, LIQ, 15 * 10 ** 16, FEE) == 4495 and n == 11


@test
def settings_bounds():
    bad = {"BASE_STAKE_ETH": "abc", "BASE_BUY_SLIP": "0.9", "BASE_DRY_RUN": "2", "BASE_HOOK_FLAGS": "0x10000", "BASE_TOKEN_CODEHASHES": "0x1234",
           "BASE_RELAY": "0x12", "BASE_PRIO_GWEI": "2", "BASE_STAKE_CAP_ETH": "0.0000000000000000001", "BASE_SEND_URLS": "ftp://x.org", "BASE_FIRE_MAX": "x"}
    for k, v in bad.items():
        os.environ.update(BASE_ENV); os.environ[k] = v
        try:
            E.settings()
        except SystemExit as e:
            assert k in str(e) or ("BASE_PRIO_GWEI" in str(e) and k == "BASE_PRIO_GWEI"), (k, str(e))
        else:
            raise AssertionError(f"{k}={v} was accepted")
        os.environ.pop(k)
    s = E.settings()
    assert s.STAKE_WEI == 2 * 10 ** 15 and s.PRIO_WEI == 10 ** 7 and s.MAX_FEE_WEI == 5 * 10 ** 8 and s.BUY_SLIP_PPM == 30_000 and s.BOT_SENDERS == set()
    assert isinstance(s.STAKE_WEI, int) and isinstance(s.MIN_POOL_WEI, int) and s.HOOK_FLAGS == 0x80


@test
def arm_on_the_fixture():
    c = fresh(); e = launch_armed(c)
    assert e["armed"] and e["skip"] is None and e["selector"] == "c3e0ff3d" and e["calldata_len"] == 260 and e["launcher"] == LAUNCHER, e
    assert e["token_code"] == FX["code_hashes"]["token"][:14] and e["fee"] == 5000 and e["ts"] == 100 and e["hook"] == HOOK and e["tx_src"] == "rpc"
    assert E.pools[PID]["status"] == "armed" and E.pools[PID]["sp0"] == SP0 and E.pools[PID]["launch_from"] == LAUNCH_TX["from"]


@test
def arm_skips():
    def init_with(fee=5000, ts=100, hook=HOOK, c0="0" * 40):
        lg = copy.deepcopy(FX["init_log"]); d = lg["data"][2:]
        lg["data"] = "0x" + word(fee) + word(ts) + "0" * 24 + hook[2:] + d[192:]; lg["topics"][2] = "0x" + "0" * 24 + c0
        return lg
    cheap = [(init_with(fee=3000), "fee 3000"), (init_with(ts=60), "tick spacing 60"), (init_with(hook="0x" + "1c" * 18 + "c040"), "hook flags 0x40,"),
             (init_with(c0="ab" * 20), "currency0 is not ETH"), (init_with(hook="0x" + "00" * 20), "hook flags 0x0")]
    for lg, why in cheap:
        c = fresh(logs=[lg]); feed(c, L, L)
        e = events("launch")[0]
        assert not e["armed"] and why in e["skip"] and not any(m.startswith("eth_get") for _, m in c.calls), (why, e, c.calls)
    txs = copy.deepcopy(FX["txs"]); t = txs[LAUNCH_TX["hash"]]
    for change, why in [(lambda t: t.update(input="0xdeadbeef" + t["input"][10:]), "launch selector deadbeef"),
                        (lambda t: t.update(input=t["input"] + "00" * 32), "launch calldata 292 B")]:
        tx2 = copy.deepcopy(txs); change(tx2[LAUNCH_TX["hash"]])
        c = fresh(txs=tx2); feed(c, L, L); e = wait_ev("launch")[0]
        assert not e["armed"] and why in e["skip"], e
    c = fresh(); c.code[TOKEN] = "0x6001"; feed(c, L, L); e = wait_ev("launch")[0]
    assert not e["armed"] and "token code" in e["skip"] and PID not in E.pools, e
    c = fresh(); c.code[LAUNCHER] = "0x6002"; feed(c, L, L); e = wait_ev("launch")[0]
    assert not e["armed"] and "launcher code" in e["skip"], e
    c = fresh(BASE_LAUNCH_SELECTOR="c3e0ff3d"); tx2 = copy.deepcopy(FX["txs"]); tx2[LAUNCH_TX["hash"]]["input"] += "00" * 32; c.txs = tx2
    feed(c, L, L); assert wait_ev("launch")[0]["armed"]                       # a bare selector: any length


@test
def arm_on_the_second_launch_call():
    """the operator's launch call from 19:42 UTC Oct 14: selector 99dfa5c4 to a fresh launcher of code 53959585f666..., the calldata's length
    varying with the launch (868-1348 B: a list of addresses at its end); the same token code, add (2346bb56 at L+3) and pull (f2f230a8)"""
    def with_launch(sel, extra=0, prefixes=None):
        txs = copy.deepcopy(FX["txs"]); t = txs[LAUNCH_TX["hash"]]; t["input"] = "0x" + sel + t["input"][10:] + "00" * extra
        c = fresh(txs=txs)
        if prefixes is not None:
            E.S.LAUNCHER_PREFIXES = prefixes
        feed(c, L, L); return wait_ev("launch")[0]
    fake = E.code_hash(FAKE_LAUNCHER_CODE)[2:14]
    for extra in (0, 32, 1088):                                                  # 260, 292 and 1348 B: any length for the new call
        e = with_launch("99dfa5c4", extra); assert e["armed"] and e["selector"] == "99dfa5c4" and e["calldata_len"] == 260 + extra, e
        assert E.pools[PID]["status"] == "armed" and E.pools[PID]["launch_from"] == LAUNCH_TX["from"]
    e = with_launch("c3e0ff3d", 32); assert not e["armed"] and "launch calldata 292 B, not 260" in e["skip"], e        # the first call keeps its length
    e = with_launch("deadbeef"); assert not e["armed"] and e["skip"] == "launch selector deadbeef, not c3e0ff3d or 99dfa5c4", e
    e = with_launch("99dfa5c4", 32, ["deadbeefdead", fake]); assert e["armed"], e                                     # any of the prefixes
    e = with_launch("99dfa5c4", 32, ["deadbeefdead"]); assert not e["armed"] and "launcher code" in e["skip"] and "deadbeefdead" in e["skip"], e
    e = with_launch("99dfa5c4", 32, []); assert e["armed"], e                                                           # empty: any launcher
    assert "99dfa5c4" in E.flash_watch() and "c3e0ff3d" in E.flash_watch()
    os.environ.update(BASE_ENV); os.environ.pop("BASE_LAUNCH_SELECTOR", None); os.environ.pop("BASE_LAUNCHER_CODEHASH_PREFIX", None)
    s = E.settings(); assert s.LAUNCHES == {"c3e0ff3d": 260, "99dfa5c4": 0} and s.LAUNCHER_PREFIXES == ["225f9af97d88", "53959585f666", "aee87105d146"], vars(s)
    os.environ["BASE_LAUNCH_SELECTOR"] = "0xC3E0FF3D/260, 99dfa5c4/1156"; os.environ["BASE_LAUNCHER_CODEHASH_PREFIX"] = "0xAB12, 53959585f666"
    s = E.settings(); assert s.LAUNCHES == {"c3e0ff3d": 260, "99dfa5c4": 1156} and s.LAUNCHER_PREFIXES == ["ab12", "53959585f666"], vars(s)
    for k, v in [("BASE_LAUNCH_SELECTOR", "c3e0ff3d/x"), ("BASE_LAUNCH_SELECTOR", "c3e0ff3"), ("BASE_LAUNCH_SELECTOR", ","), ("BASE_LAUNCH_SELECTOR", "c3e0ff3d/2600000"),
                 ("BASE_LAUNCH_CALLDATA_LEN", "260"), ("BASE_LAUNCHER_CODEHASH_PREFIX", "zz"), ("BASE_LAUNCHER_CODEHASH_PREFIX", "ab" * 33)]:
        os.environ.update(BASE_ENV); os.environ.pop("BASE_LAUNCH_SELECTOR", None); os.environ.pop("BASE_LAUNCHER_CODEHASH_PREFIX", None); os.environ[k] = v
        try:
            E.settings()
        except SystemExit as e:
            assert k in str(e), (k, str(e))
        else:
            raise AssertionError(f"{k}={v} was accepted")
        os.environ.pop(k)


@test
def fire_on_the_add_confirmed():
    c = fresh(); launch_armed(c); feed(c, L + 3, L + 3)
    add = events("add")[0]; f = events("would_fire")[0]
    assert add["block"] == L + 3 and add["liquidity"] == LIQ and not add["pending"] and abs(add["eth"] - 2.133328) < 1e-5, add
    expected = v4math.buy_out_int(SP0, LIQ, E.S.STAKE_WEI, FEE)
    assert f["min_out"] == expected * (10 ** 6 - 30_000) // 10 ** 6 and f["expected"] == expected and f["via"] == "logs" and f["add_block"] == L + 3, f
    assert f["head"] == L + 3 and f["stake_wei"] == 2 * 10 ** 15 and f["nonce"] is None and f["buy_block"] == L + 4 and f["dry"]
    assert isinstance(f["min_out"], int) and len(events("would_fire")) == 1


@test
def dry_trade_against_the_fixture():
    """the dry buy at +4 (the block after the fire's head +3), sold into the bot's +8 buy (take-profit: the bot is not named by the Swap's
    sender): the return by v4math within 1e-9"""
    c = fresh(); launch_armed(c); feed(c, L + 3, L + 9)
    t = events("trade_done")
    assert len(t) == 1, t
    t = t[0]; s8 = first_bot_swap()
    tokens, out = expected_dry(W(s8["data"], 2))
    gas = E.DRY_GAS_UNITS * (int(header(L + 9)["baseFeePerGas"], 16) + E.S.PRIO_WEI) + E.L1_FEE_EST_WEI
    ret = (out - E.S.STAKE_WEI - gas) / E.S.STAKE_WEI
    assert t["exit"] == "take_profit" and t["buy_block"] == L + 4 and t["sell_block"] == L + 8 and t["tokens"] == tokens and t["dry"] and not t["live"], t
    assert abs(t["ret"] - ret) < 1e-6 and abs((t["eth_out_wei"] - E.S.STAKE_WEI - t["gas_wei"]) / E.S.STAKE_WEI - ret) < 1e-9 and t["gas_wei"] == gas, (t, ret)
    assert abs(t["eth_out_wei"] - out) <= 1 and 0.12 < ret < 0.14 and t["pulled_at"] is None            # +13.3% gross, about +13.1% after gas at 0.01 gwei
    s = events("sell_sent")[0]
    assert s["dry"] and s["exit"] == "take_profit" and s["priced_at_block"] == L + 8 and s["block_seen"] == L + 8


@test
def small_pool_skipped():
    logs = copy.deepcopy([FX["init_log"]] + FX["pool_logs"])
    for l in logs:
        if l["topics"][0] == E.T_ML and sgn(W(l["data"], 2)) > 1:
            d = l["data"]; l["data"] = d[:2 + 128] + word(sgn(W(d, 2)) // 16) + d[2 + 192:]   # 0.1333 ETH, as the 09:32 test pool
    c = fresh(logs=logs); launch_armed(c); feed(c, L + 3, L + 9)
    s = events("skip")
    assert len(s) == 1 and "under BASE_MIN_POOL_ETH" in s[0]["why"] and not events("would_fire") and PID not in E.pools, s


@test
def late_add_refused():
    c = fresh(); launch_armed(c)
    feed(c, L + 3, L + 6, logs=[])                                            # the heads to +6 came, the add's logs not (a slow node)
    bb = by_block(c.logs)
    for lg in bb[L + 3]:
        E.on_ws_message(json.dumps({"jsonrpc": "2.0", "method": "eth_subscription", "params": {"subscription": "0xl", "result": lg}}), c.subs)
    with E.lock:
        E.end_burst()
    s = events("skip")
    assert len(s) == 1 and s[0]["why"].startswith("late: head") and not events("would_fire"), s


@test
def pull_before_the_fire():
    pull = copy.deepcopy([l for l in FX["pool_logs"] if l["topics"][0] == E.T_ML and sgn(W(l["data"], 2)) < 0][0])
    pull["blockNumber"] = hex(L + 2); pull["blockHash"] = header(L + 2)["hash"]
    c = fresh(logs=[FX["init_log"], pull] + FX["pool_logs"]); launch_armed(c); feed(c, L + 3, L + 5)
    p = events("pull")[0]; s = events("skip")
    assert p["before"] == "fire" and p["block"] == L + 2 and s[0]["why"] == "pulled before our fire" and not events("would_fire"), (p, s)


@test
def sell_on_the_bot_confirmed_by_sender():
    c = fresh(BASE_BOT_SENDERS=UR); launch_armed(c); feed(c, L + 3, L + 9)
    t = events("trade_done")[0]; b = events("bot_buy")
    assert t["exit"] == "bot" and t["sell_block"] == L + 8 and b[0]["block"] == L + 8 and b[0]["value"] == 15 * 10 ** 16 and b[0]["via"] == "logs", (t, b)
    tokens, out = expected_dry(W(first_bot_swap()["data"], 2))
    assert abs(t["eth_out_wei"] - out) <= 1


@test
def take_profit_needs_a_paying_buy():
    """a small buy behind ours does not pay the take-profit; the bot's +8 buy does"""
    tiny = swap_log(L + 6, 5, -10 ** 13, 0, exact_buy(SP0, LIQ, 10 ** 13)[1])
    s8 = first_bot_swap(); _, sp8 = exact_buy(exact_buy(SP0, LIQ, 10 ** 13)[1], LIQ, 15 * 10 ** 16)
    s8 = copy.deepcopy(s8); s8["data"] = s8["data"][:2 + 128] + word(sp8) + s8["data"][2 + 192:]
    c = fresh(logs=[FX["init_log"]] + FX["pool_logs"][:2] + [tiny, s8]); launch_armed(c); feed(c, L + 3, L + 7)
    assert not events("sell_sent")
    feed(c, L + 8, L + 9)
    t = events("trade_done")[0]
    assert t["exit"] == "take_profit" and t["sell_block"] == L + 8, t
    _, out = expected_dry(sp8)
    assert abs(t["eth_out_wei"] - out) <= 1


@test
def deadline_sell():
    c = fresh(logs=[FX["init_log"]] + FX["pool_logs"][:2]); launch_armed(c); feed(c, L + 3, L + 11)
    t = events("trade_done")[0]
    assert t["exit"] == "deadline" and t["buy_block"] == L + 4 and t["sell_block"] == L + 10, t
    _, out = expected_dry(SP0)
    assert abs(t["eth_out_wei"] - out) <= 1 and -0.02 < t["ret_gross"] < -0.009    # the two 0.5% fees


@test
def pulled_first_halts():
    pull = copy.deepcopy(FX["pool_logs"][-1]); pull["blockNumber"] = hex(L + 6); pull["blockHash"] = header(L + 6)["hash"]
    c = fresh(logs=[FX["init_log"]] + FX["pool_logs"][:2] + [pull] + FX["pool_logs"][2:-1]); launch_armed(c); feed(c, L + 3, L + 10)
    t = events("trade_done")[0]; h = events("halt"); p = events("pull")[0]
    assert t["exit"] == "pulled" and t["eth_out_wei"] == 0 and t["ret"] < -1.0 and t["pulled_at"] == L + 6, t
    assert len(h) == 1 and h[0]["reason"].startswith("pulled") and h[0]["dry"] and h[0]["file"] is None and p["before"] == "sell", (h, p)
    assert not os.path.exists(E.S.HALT_FILE) and E.state["halted"]
    c2 = copy.deepcopy(FX["init_log"]); c2["topics"][1] = "0x" + "77" * 32                # a later launch of the line: refused while halted
    c2["blockNumber"] = hex(L + 20); c2["blockHash"] = header(L + 20)["hash"]; c2["logIndex"] = "0x0"
    ml = [copy.deepcopy(l) for l in FX["pool_logs"][:2]]
    for l in ml:
        l["topics"][1] = c2["topics"][1]; l["blockNumber"] = hex(L + 23); l["blockHash"] = header(L + 23)["hash"]
    feed(c, L + 11, L + 20, logs=[c2]); wait_ev("launch", 2); feed(c, L + 21, L + 23, logs=ml)
    assert events("skip")[-1]["why"].startswith("halted: pulled")


@test
def near_miss_halts():
    """our sell at +5 (a paying buy there), the pull at +6: two blocks after our buy at +4, behind our sell"""
    buy5 = copy.deepcopy(first_bot_swap()); buy5["blockNumber"] = hex(L + 5); buy5["blockHash"] = header(L + 5)["hash"]
    pull = copy.deepcopy(FX["pool_logs"][-1]); pull["blockNumber"] = hex(L + 6); pull["blockHash"] = header(L + 6)["hash"]
    c = fresh(logs=[FX["init_log"]] + FX["pool_logs"][:2] + [buy5, pull]); launch_armed(c); feed(c, L + 3, L + 8)
    t = events("trade_done")[0]; h = events("halt"); p = events("pull")[0]
    assert t["exit"] == "take_profit" and t["sell_block"] == L + 5 and p["before"] == "after" and p["after_buy"] == 2, (t, p)
    assert len(h) == 1 and h[0]["reason"].startswith("near miss"), h


@test
def daily_cap_and_stop():
    def second_launch(at):
        pid2 = "0x" + "66" * 32; out = []
        for l in [FX["init_log"]] + FX["pool_logs"][:2]:
            l = copy.deepcopy(l); l["topics"][1] = pid2; n = blk(l) - L + at; l["blockNumber"] = hex(n); l["blockHash"] = header(n)["hash"]; out.append(l)
        return out
    logs = [FX["init_log"]] + FX["pool_logs"][:2] + second_launch(L + 20)
    c = fresh(logs=logs, BASE_MAX_PER_DAY="1"); launch_armed(c); feed(c, L + 3, L + 20); wait_ev("launch", 2); feed(c, L + 21, L + 24)
    assert len(events("would_fire")) == 1 and events("skip")[-1]["why"].startswith("daily cap"), events("skip")
    c = fresh(logs=logs, BASE_DAILY_STOP_USD="0.01"); launch_armed(c); feed(c, L + 3, L + 20); wait_ev("launch", 2); feed(c, L + 21, L + 24)   # a deadline loss of ~$0.06
    st = events("stop")
    assert len(st) == 1 and st[0]["losses"] > 0.01 and events("trade_done")[0]["usd"] < 0 and events("skip")[-1]["why"].startswith("stopped"), (st, events("skip"))


@test
def flash_decoder():
    for t in FX["txs"].values():
        raw = raw_of(t); d = E.decode_tx(bytes.fromhex(raw[2:]))
        assert d["to"] == t["to"].lower() and d["value"] == int(t["value"], 16) and d["data"].hex() == t["input"][2:] and d["nonce"] == int(t["nonce"], 16)
        assert d["prio"] == int(t["maxPriorityFeePerGas"], 16) and d["max_fee"] == int(t["maxFeePerGas"], 16) and E.tx_sender(raw) == t["from"].lower()
    k = Account.create()
    for extra in ({"gasPrice": 10 ** 7}, {"gasPrice": 10 ** 7, "accessList": [], "chainId": 8453}, {"type": 2, "maxFeePerGas": 9, "maxPriorityFeePerGas": 1, "chainId": 8453}):
        raw = "0x" + bytes(k.sign_transaction({"nonce": 3, "to": E.to_checksum_address(BOT), "value": 5, "data": "0x27f7e6ee", "gas": 50000, **extra}).raw_transaction).hex()
        d = E.decode_tx(bytes.fromhex(raw[2:]))
        assert d["to"] == BOT and d["value"] == 5 and d["data"] == bytes.fromhex("27f7e6ee") and d["nonce"] == 3 and E.tx_sender(raw) == k.address.lower(), (extra, d)
    assert E.decode_tx(bytes.fromhex("7e" + "c0")) is None and E.decode_tx(b"\x02\xff") is None
    c = fresh(); E.on_flash(b"not brotli at all"); E.on_flash(brotli.compress(b"{not json"))
    a = events("alarm")
    assert len(a) == 1 and "dropped" in a[0]["what"] and E.state["flash_bad"] == 2, a                # one alarm a key every 10 min


@test
def flash_fires_and_sells_earlier_once():
    c = fresh()
    flash(L, [raw_of(LAUNCH_TX)], index=3)                                    # the launch pending: its copy serves the arm (no eth_getTransactionByHash)
    e = launch_armed(c)
    assert e["armed"] and e["tx_src"] == "flash" and ("rpc.example.org", "eth_getTransactionByHash") not in c.calls, (e, c.calls)
    flash(L + 3, [], index=0)
    flash(L + 3, ["0x7e" + "00" * 10, raw_of(ADD_TX)], index=2)               # the add pending, with a deposit before it
    f = events("would_fire")
    assert len(f) == 1 and f[0]["via"] == "flash" and f[0]["head"] == L + 2 and f[0]["buy_block"] == L + 3 and f[0]["liquidity"] == LIQ, f
    assert events("add")[0]["pending"] and f[0]["min_out"] == v4math.buy_out_int(SP0, LIQ, E.S.STAKE_WEI, FEE) * 97 // 100
    feed(c, L + 3, L + 7)
    assert len(events("would_fire")) == 1 and not events("add", pending=False)[0]["pending"]
    flash(L + 8, [raw_of(BOT1_TX)], index=4)                                   # the bot's buy pending: the sell goes now
    s = events("sell_sent")
    assert len(s) == 1 and s[0]["via"] == "flash" and s[0]["exit"] == "bot" and s[0]["block_seen"] == L + 8, s
    assert events("bot_buy")[0]["pending"] and events("bot_buy")[0]["from"] == BOT1_TX["from"].lower()
    feed(c, L + 8, L + 10)
    t = events("trade_done")
    assert len(t) == 1 and len(events("sell_sent")) == 1 and t[0]["exit"] == "bot" and t[0]["via"] == "flash", t
    tokens, out = expected_dry(W(first_bot_swap()["data"], 2))
    assert t[0]["tokens"] == tokens and abs(t[0]["eth_out_wei"] - out) <= 1 and t[0]["buy_block"] == L + 3


@test
def flash_bot_buy_ahead_of_ours_is_no_exit():
    c = fresh(); launch_armed(c); feed(c, L + 3, L + 3)                        # the dry buy lands at the end of +4
    flash(L + 4, [raw_of(BOT1_TX)], index=5)                                   # a bot buy in our own block: ahead of ours
    assert not events("sell_sent") and events("bot_buy")


@test
def websocket_drop_gap_filled():
    c = fresh(); launch_armed(c)
    E.ws_down(ConnectionError("dropped"))                                     # down after +2; it comes back at +5
    assert events("alarm")[-1]["what"].startswith("the websocket is down")
    c.subs = {}
    E.on_ws_message(json.dumps({"jsonrpc": "2.0", "id": 1, "result": "0xh"}), c.subs); E.on_ws_message(json.dumps({"jsonrpc": "2.0", "id": 2, "result": "0xl"}), c.subs)
    feed(c, L + 5, L + 5, logs=[])
    assert E.state["ws_from"] == L + 5 and E.state["logs_to"] < L + 3
    c.head = L + 5
    while E.poll_step():
        pass
    assert c.ranges and c.ranges[0][0] == L + 2 and all(b + 1 == a for (_, b), (a, _) in zip(c.ranges, c.ranges[1:])) and c.ranges[-1][1] == L + 5, c.ranges
    f = events("would_fire")
    assert len(f) == 1 and f[0]["add_block"] == L + 3 and f[0]["head"] == L + 5 and E.state["logs_to"] == L + 5, f
    dups = E.state["dups"]; feed(c, L + 5, L + 9)                            # the websocket's own copies of +5: deduped
    assert len(events("trade_done")) == 1 and events("trade_done")[0]["buy_block"] == L + 6 and E.state["dups"] == dups


@test
def silent_websocket_polls():
    c = fresh(); launch_armed(c)
    E.state["ws_last"] = E.mono() - 60                                         # silent for a minute
    c.head = L + 4
    while E.poll_step():
        pass
    assert E.state["head"] == L + 4 and E.state["head_src"] == "poll" and E.state["logs_to"] == L + 3 and c.ranges[-1][1] == L + 3, (E.state["head"], c.ranges)
    f = events("would_fire")
    assert len(f) == 1 and f[0]["via"] == "logs" and f[0]["head"] == L + 4, f


@test
def duplicate_and_removed_logs():
    tiny = swap_log(L + 6, 5, -10 ** 16, 10 ** 24, SP0 // 2)                   # a fake price move at +6, later removed by a reorg
    c = fresh(logs=[FX["init_log"]] + FX["pool_logs"][:2]); launch_armed(c); feed(c, L + 3, L + 5)
    feed(c, L + 6, L + 6, logs=[tiny, tiny])
    assert E.state["dups"] == 1 and E.fold(E.pools[PID])["sp"] == SP0 // 2
    gone = dict(tiny, removed=True)
    E.on_ws_message(json.dumps({"jsonrpc": "2.0", "method": "eth_subscription", "params": {"subscription": "0xl", "result": gone}}), c.subs)
    assert E.fold(E.pools[PID])["sp"] == SP0 and E.state["reorgs"] == 1 and "reorg" in events("alarm")[-1]["what"]


# ---------------------------------------------------------------- live (the key, the relay and the sends stubbed)
def live_receipt(h, B, logs, ok=True, gas=150_000, egp=55_000_000, l1=2_090_000_000):
    return {"transactionHash": h, "blockNumber": hex(B), "status": "0x1" if ok else "0x0", "gasUsed": hex(gas), "effectiveGasPrice": hex(egp), "l1Fee": hex(l1),
            "logs": logs, "transactionIndex": "0x2"}


def sent_hash(c, i):
    return "0x" + keccak(bytes.fromhex(c.sent[i][1][2:])).hex()


def live_trade(c, sell_ok=True, buy_ok=True, bot_eth=15 * 10 ** 16, sell_tokens_back=None):
    """fire live on the fixture, mine our buy at +4, the bot's buy at +8 behind it, our sell at +9; returns the chain's amounts"""
    launch_armed(c); feed(c, L + 3, L + 3)
    wait_ev("buy_sent"); hb = sent_hash(c, 0)
    stake = E.S.STAKE_WEI; tokens, sp1 = exact_buy(SP0, LIQ, stake)
    if buy_ok:
        mine = swap_log(L + 4, 7, -stake, tokens, sp1, sender=RELAY, tx=hb)
        c.receipts[hb] = live_receipt(hb, L + 4, [mine]); c.logs.append(mine)
    else:
        c.receipts[hb] = live_receipt(hb, L + 4, [], ok=False)
    bot_out, sp2 = exact_buy(sp1 if buy_ok else SP0, LIQ, bot_eth)
    bot = swap_log(L + 8, 3, -bot_eth, bot_out, sp2, tx=BOT1_TX["hash"])
    c.logs = [l for l in c.logs if not (l["topics"][0] == E.T_SWAP and blk(l) > L + 4 and l["topics"][2][-40:] != RELAY[2:])] + [bot]
    feed(c, L + 4, L + 8)
    out = {"tokens": tokens, "hb": hb, "sp2": sp2}
    if not buy_ok:
        return out
    wait_ev("sell_sent"); hs = sent_hash(c, len(c.sent) - 1)
    eth_out, sp3 = exact_sell(sp2, LIQ, tokens)
    sw = swap_log(L + 9, 2, eth_out, -tokens, sp3, sender=RELAY, tx=hs)
    c.receipts[hs] = live_receipt(hs, L + 9, [sw] if sell_ok else [], ok=sell_ok, gas=120_000, l1=1_500_000_000); c.logs.append(sw)
    feed(c, L + 9, L + 10)
    out.update(hs=hs, eth_out=eth_out)
    return out


threading.Thread(target=E.trader, daemon=True).start()


@test
def live_trade_settles_with_l1_fee():
    c = fresh(dry=False); x = live_trade(c)
    t = wait_ev("trade_done")[0]; f = events("fire")[0]; b = events("buy_sent")[0]; s = events("sell_sent")[0]
    gas = 150_000 * 55_000_000 + 2_090_000_000 + 120_000 * 55_000_000 + 1_500_000_000
    assert t["live"] and not t["dry"] and t["exit"] == "take_profit" and t["eth_in_wei"] == E.S.STAKE_WEI and t["tokens"] == x["tokens"], t
    assert t["eth_out_wei"] == x["eth_out"] and t["gas_wei"] == gas and t["l1_fee_wei"] == 2_090_000_000 + 1_500_000_000 and t["buy_block"] == L + 4 and t["sell_block"] == L + 9
    assert abs(t["ret"] - (x["eth_out"] - E.S.STAKE_WEI - gas) / E.S.STAKE_WEI) < 1e-6 and t["nonbot_streak"] == 0
    assert f["nonce"] == 7 and b["nonce"] == 7 and s["nonce"] == 8 and b["kind"] == "ok" and len(c.sent) == 4 and {h for h, _ in c.sent} == {"seq.example.org", "send2.example.org"}
    tx = E.decode_tx(bytes.fromhex(c.sent[0][1][2:])); d = tx["data"].hex()
    assert d[:8] == "5ed06f60" and int(d[8 + 64 * 5: 8 + 64 * 6], 16) == E.S.STAKE_WEI and int(d[8 + 64 * 6: 8 + 64 * 7], 16) == f["min_out"] and tx["to"] == RELAY
    assert tx["prio"] == E.S.PRIO_WEI == 10 ** 7 and tx["max_fee"] == 2 * 5_000_000 + E.S.PRIO_WEI and E.tx_sender(c.sent[0][1]) == KEY.address.lower()
    sd = E.decode_tx(bytes.fromhex(c.sent[-1][1][2:]))["data"].hex()
    want = E.v4math.sell_out_int(x["sp2"], LIQ, x["tokens"], FEE) * 95 // 100
    assert sd[:8] == "137f1fdd" and int(sd[8 + 64 * 5: 8 + 64 * 6], 16) == want and E.state["position"] is None, (sd, want)
    assert json.load(open(E.S.POSITIONS_FILE))["positions"] == {}


@test
def live_buy_reverted_sends_no_sell():
    c = fresh(dry=False); live_trade(c, buy_ok=False)
    t = wait_ev("trade_done")[0]
    assert t["exit"] == "buy_reverted" and t["eth_in_wei"] == 0 and t["gas_wei"] == 150_000 * 55_000_000 + 2_090_000_000 and t["usd"] < 0, t
    assert not events("sell_sent") and len(c.sent) == 2 and not events("halt")


@test
def live_sold_none_halts():
    """the sell reverts on a pool not pulled: sent again twice at minOut 0 (each after the last one's receipt), all revert: "sold none", the halt"""
    c = fresh(dry=False); c.auto = lambda h: None if h == sent_hash(c, 0) else live_receipt(h, L + 10, [], ok=False, gas=120_000, l1=1_500_000_000)
    live_trade(c, sell_ok=False)
    t = wait_ev("trade_done")[0]; h = wait_ev("halt"); s = events("sell_sent")
    assert t["exit"] == "take_profit" and t["eth_out_wei"] == 0 and h[0]["reason"].startswith("sold none") and not h[0]["dry"], (t, h)
    assert len(s) == 3 and [x["min_out"] for x in s[1:]] == [0, 0] and [x["via"] for x in s[1:]] == ["retry", "retry"], s
    assert t["gas_wei"] == 150_000 * 55_000_000 + 2_090_000_000 + 3 * (120_000 * 55_000_000 + 1_500_000_000), t     # the three sells' gas
    assert open(E.S.HALT_FILE).read().startswith("sold none") and len([a for a in events("alarm") if "sent again" in a["what"]]) == 2


@test
def live_decoy_streak_halts():
    c = fresh(dry=False, BASE_NONBOT_HALT="3")
    for i in range(3):
        pos = {"pid": PID, "token": TOKEN, "key": {}, "dry": False, "stake": E.S.STAKE_WEI, "expected": 1, "min_out": 1, "via": "logs", "add_block": L + 3,
               "buy_status": "ok", "buy_block": L + 4, "buy_at": (L + 4, 1), "tokens": 10, "exit": "deadline", "nonce": 7 + 2 * i, "buy_hash": "0x1", "sell_hash": "0x2", "closed": False}
        E.state["position"] = pos
        rb = live_receipt("0x1", L + 4, [swap_log(L + 4, 1, -E.S.STAKE_WEI, 10, SP0, sender=RELAY)])
        rs = live_receipt("0x2", L + 9, [swap_log(L + 9, 1, E.S.STAKE_WEI * 101 // 100, -10, SP0, sender=RELAY)])
        E.finish_live(pos, rb, [rs])
    t = events("trade_done"); h = events("halt")
    assert [x["nonbot_streak"] for x in t] == [1, 2, 3] and len(h) == 1 and "BASE_NONBOT_HALT" in h[0]["reason"], (t, h)


@test
def live_pull_first():
    """the pull lands between our buy (+4) and the bot's buy: the sell still goes at minOut 0 (a partial pull would strand tokens), -100%, the halt"""
    c = fresh(dry=False); launch_armed(c); feed(c, L + 3, L + 3)
    wait_ev("buy_sent"); hb = sent_hash(c, 0); stake = E.S.STAKE_WEI; tokens, sp1 = exact_buy(SP0, LIQ, stake)
    mine = swap_log(L + 4, 7, -stake, tokens, sp1, sender=RELAY, tx=hb); c.receipts[hb] = live_receipt(hb, L + 4, [mine])
    pull = copy.deepcopy(FX["pool_logs"][-1]); pull["blockNumber"] = hex(L + 6); pull["blockHash"] = header(L + 6)["hash"]
    c.logs = [FX["init_log"]] + FX["pool_logs"][:2] + [mine, pull]
    c.auto = lambda h: None if h == hb else live_receipt(h, L + 7, [swap_log(L + 7, 1, 3, -tokens, SP0, liq=1, sender=RELAY, tx=h)])   # 3 wei: the 1-unit position
    feed(c, L + 4, L + 12)
    t = wait_ev("trade_done")[0]; h = wait_ev("halt"); s = events("sell_sent")
    assert t["exit"] == "pulled" and t["pulled_at"] == L + 6 and t["eth_out_wei"] == 3 and t["ret"] < -0.99 and len(s) == 1, (t, s)
    assert s[0]["exit"] == "pulled" and s[0]["min_out"] == 0 and h[0]["reason"].startswith("pulled") and os.path.exists(E.S.HALT_FILE)


@test
def live_flash_sell_behind_our_buy():
    """live with Flashblocks: the add pending fires, our buy is seen in the next Flashblock, the bot's buy pending behind it sells at once
    (minOut from the price with our buy in); the confirmed logs later send nothing twice"""
    c = fresh(dry=False); flash(L, [raw_of(LAUNCH_TX)]); launch_armed(c)
    flash(L + 3, [raw_of(ADD_TX)], index=2)
    b = wait_ev("buy_sent")[0]; hb = sent_hash(c, 0); my_raw = c.sent[0][1]
    assert events("fire")[0]["via"] == "flash" and b["nonce"] == 7
    flash(L + 3, [my_raw], index=3)                                            # our buy in the same block, behind the add
    stake = E.S.STAKE_WEI; tokens, sp1 = exact_buy(SP0, LIQ, stake)
    flash(L + 8, [raw_of(BOT1_TX)], index=1)
    s = wait_ev("sell_sent")[0]
    want = E.v4math.sell_out_int(E.sqrt_after_buy_int(SP0, LIQ, E.net_of_fee(stake, FEE)), LIQ, E.state["position"]["min_out"], FEE) * 95 // 100
    assert s["exit"] == "bot" and s["via"] == "flash" and s["nonce"] == 8 and s["min_out"] == want, (s, want)
    mine = swap_log(L + 3, 9, -stake, tokens, sp1, sender=RELAY, tx=hb); c.receipts[hb] = live_receipt(hb, L + 3, [mine])
    bot_out, sp2 = exact_buy(sp1, LIQ, 15 * 10 ** 16); bot = swap_log(L + 8, 3, -15 * 10 ** 16, bot_out, sp2, tx=BOT1_TX["hash"])
    hs = sent_hash(c, len(c.sent) - 1); eth_out, sp3 = exact_sell(sp2, LIQ, tokens)
    sell = swap_log(L + 8, 4, eth_out, -tokens, sp3, sender=RELAY, tx=hs); c.receipts[hs] = live_receipt(hs, L + 8, [sell])
    c.logs = [FX["init_log"]] + FX["pool_logs"][:2] + [mine, bot, sell]
    feed(c, L + 3, L + 10)
    t = wait_ev("trade_done")[0]
    assert t["exit"] == "bot" and t["eth_out_wei"] == eth_out and t["buy_block"] == L + 3 and t["sell_block"] == L + 8 and len(c.sent) == 4, (t, len(c.sent))
    assert len(events("sell_sent")) == 1 and len(events("fire")) == 1 and t["ret"] > 0.1


@test
def live_halt_file_read_before_the_fire():
    c = fresh(dry=False); launch_armed(c)
    open(E.S.HALT_FILE, "w").write("owner: stop\n")
    feed(c, L + 3, L + 4)
    s = events("skip")
    assert s and s[0]["why"] == "halted: owner: stop" and not events("fire") and not c.sent, s


@test
def live_restart_pull_and_zero_sell():
    """a restart (no pool in memory) whose sell lands after a pull at +6 and gets 0 ETH: the settlement's own eth_getLogs finds the pull:
    "pulled", the halt; the same without a pull: a sell of 0 ETH is "sold none", the halt"""
    for pulled in (True, False):
        c = fresh(dry=False); stake = E.S.STAKE_WEI; tokens, sp1 = exact_buy(SP0, LIQ, stake)
        saved = {"pid": PID, "key": {"c0": E.ZERO, "c1": TOKEN, "fee": FEE, "ts": 100, "hooks": HOOK}, "token": TOKEN, "L": L, "stake": stake, "expected": tokens,
                 "min_out": tokens * 97 // 100, "via": "logs", "add_block": L + 3, "fire_head": L + 3, "D": L + 4, "nonce": 7, "buy_hash": "0x" + "b1" * 32,
                 "buy_block": None, "tokens": None, "sell_sent": False, "sell_hash": None}
        json.dump({"positions": {PID: saved}}, open(E.S.POSITIONS_FILE, "w"))
        c.receipts[saved["buy_hash"]] = live_receipt(saved["buy_hash"], L + 4, [swap_log(L + 4, 7, -stake, tokens, sp1, sender=RELAY)])
        pull = copy.deepcopy(FX["pool_logs"][-1]); pull["blockNumber"] = hex(L + 6); pull["blockHash"] = header(L + 6)["hash"]
        c.logs = [pull] if pulled else []; c.head = L + 40
        c.auto = lambda h: live_receipt(h, L + 40, [swap_log(L + 40, 1, 0, -tokens, SP0, liq=1, sender=RELAY, tx=h)])
        os.environ.update({"BASE_KEY_FILE": os.path.join(TMP, "k.key"), "BASE_WALLET": KEY.address, "BASE_RELAY": RELAY}); open(os.path.join(TMP, "k.key"), "w").write(KEY.key.hex())
        E.S = E.settings(); E.start()
        t = wait_ev("trade_done")[0]; h = wait_ev("halt")
        assert t["exit"] == ("pulled" if pulled else "deadline") and t["eth_out_wei"] == 0 and t["pulled_at"] == (L + 6 if pulled else None), t
        assert h[0]["reason"].startswith("pulled" if pulled else "sold none") and len(events("sell_sent")) == 1, h


@test
def live_pull_seen_after_settlement():
    """a pull at +8, before our sell at +9, that the feed shows only after the trade was settled: the line halts ("pulled"), not a near miss"""
    c = fresh(dry=False); live_trade(c)
    t = wait_ev("trade_done")[0]
    assert t["exit"] == "take_profit" and not events("halt")
    pull = copy.deepcopy(FX["pool_logs"][-1]); pull["blockNumber"] = hex(L + 8); pull["blockHash"] = header(L + 8)["hash"]; pull["logIndex"] = "0x9"
    E.on_ws_message(json.dumps({"jsonrpc": "2.0", "method": "eth_subscription", "params": {"subscription": "0xl", "result": pull}}), c.subs)   # a late log
    h = events("halt")
    assert len(h) == 1 and h[0]["reason"].startswith("pulled: a pull at block") and "after the settlement" in h[0]["reason"], h


@test
def live_sell_resent_after_a_revert():
    """the first sell reverts on a pool not pulled: sent again at minOut 0 at the chain's nonce; the second lands: settled from it, the first's gas counted"""
    c = fresh(dry=False); c.nonce = 9; x = {}
    def auto(h):
        if h == sent_hash(c, 0):
            return None                                                        # our buy: its receipt below
        if h == sent_hash(c, 2):
            return live_receipt(h, L + 10, [], ok=False, gas=60_000, l1=10 ** 9)   # the first sell reverts
        return live_receipt(h, L + 11, [swap_log(L + 11, 1, x["out"], -x["tokens"], SP0, sender=RELAY, tx=h)], gas=110_000, l1=10 ** 9)
    c.auto = auto
    launch_armed(c); feed(c, L + 3, L + 3); wait_ev("buy_sent"); hb = sent_hash(c, 0)
    stake = E.S.STAKE_WEI; tokens, sp1 = exact_buy(SP0, LIQ, stake); x.update(tokens=tokens, out=E.v4math.sell_out_int(sp1, LIQ, tokens, FEE))
    mine = swap_log(L + 4, 7, -stake, tokens, sp1, sender=RELAY, tx=hb); c.receipts[hb] = live_receipt(hb, L + 4, [mine]); c.logs = [FX["init_log"]] + FX["pool_logs"][:2] + [mine]
    feed(c, L + 4, L + 10)
    t = wait_ev("trade_done")[0]; s = events("sell_sent")
    assert len(s) == 2 and s[1]["min_out"] == 0 and s[1]["nonce"] == 9 and s[1]["via"] == "retry" and t["eth_out_wei"] == x["out"] and t["exit"] == "deadline", (s, t)
    assert t["gas_wei"] == 150_000 * 55_000_000 + 2_090_000_000 + 60_000 * 55_000_000 + 10 ** 9 + 110_000 * 55_000_000 + 10 ** 9 and not events("halt"), t


@test
def live_buy_receipt_unread():
    """our buy's receipt never comes: with its Swap logged it is not "lost": the sell goes and the trade settles from it; with no sign of it at
    all but the relay holding tokens, a sell at minOut 0 and an alarm; with neither, buy_reverted (as before)"""
    c = fresh(dry=False); E.S.BUY_DEADLINE_S = 0; old = E.RECEIPT_GRACE_S, E.BLOCK_S; E.RECEIPT_GRACE_S = 0.05; E.BLOCK_S = 0
    try:
        launch_armed(c); feed(c, L + 3, L + 3); wait_ev("buy_sent"); hb = sent_hash(c, 0)
        stake = E.S.STAKE_WEI; tokens, sp1 = exact_buy(SP0, LIQ, stake)
        mine = swap_log(L + 4, 7, -stake, tokens, sp1, sender=RELAY, tx=hb); c.logs = [FX["init_log"]] + FX["pool_logs"][:2] + [mine]
        out = E.v4math.sell_out_int(sp1, LIQ, tokens, FEE)
        c.auto = lambda h: None if h == hb else live_receipt(h, L + 11, [swap_log(L + 11, 1, out, -tokens, SP0, sender=RELAY, tx=h)])
        feed(c, L + 4, L + 10)
        t = wait_ev("trade_done")[0]
        assert t["exit"] == "deadline" and t["eth_in_wei"] == stake and t["eth_out_wei"] == out and t["tokens"] == tokens, t
        assert any("still asking" in a["what"] for a in events("alarm")) and not events("halt")
        c = fresh(dry=False); E.S.BUY_DEADLINE_S = 0; c.tokens = 12345
        c.auto = lambda h: None if h == sent_hash(c, 0) else live_receipt(h, L + 30, [swap_log(L + 30, 1, 77, -12345, SP0, sender=RELAY, tx=h)])
        launch_armed(c); feed(c, L + 3, L + 3)
        t = wait_ev("trade_done")[0]; s = events("sell_sent")
        assert s[0]["min_out"] == 0 and s[0]["via"] == "balance" and t["tokens"] == 12345 and t["eth_out_wei"] == 77, (s, t)
        assert any("receipt was not read" in a["what"] for a in events("alarm"))
        c = fresh(dry=False); E.S.BUY_DEADLINE_S = 0; launch_armed(c); feed(c, L + 3, L + 3)
        t = wait_ev("trade_done")[0]
        assert t["exit"] == "buy_reverted" and "never landed" in t["why"] and not events("sell_sent"), t
    finally:
        E.RECEIPT_GRACE_S, E.BLOCK_S = old


@test
def live_nonce_low_resigned_sell():
    """the sell answered "nonce too low" everywhere: signed again at the chain's nonce; the settlement waits on that final hash"""
    c = fresh(dry=False); launch_armed(c); feed(c, L + 3, L + 3); wait_ev("buy_sent"); hb = sent_hash(c, 0)
    stake = E.S.STAKE_WEI; tokens, sp1 = exact_buy(SP0, LIQ, stake); out = E.v4math.sell_out_int(sp1, LIQ, tokens, FEE)
    mine = swap_log(L + 4, 7, -stake, tokens, sp1, sender=RELAY, tx=hb); c.receipts[hb] = live_receipt(hb, L + 4, [mine]); c.logs = [FX["init_log"]] + FX["pool_logs"][:2] + [mine]
    low = {"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "nonce too low"}}
    c.replies = [low, low]; c.nonce = 9
    c.auto = lambda h: None if h == hb else live_receipt(h, L + 11, [swap_log(L + 11, 1, out, -tokens, SP0, sender=RELAY, tx=h)])
    feed(c, L + 4, L + 10)
    t = wait_ev("trade_done")[0]; s = events("sell_sent")
    assert len(s) == 1 and s[0]["nonce"] == 9 and s[0]["kind"] == "ok" and t["sell_hash"] == s[0]["hash"] and t["eth_out_wei"] == out and not events("halt"), (s, t)
    raws = {r for _, r in c.sent}                                                  # the buy, the sell at 8 (refused everywhere), the sell at 9
    assert len(raws) == 3 and s[0]["hash"] in {"0x" + keccak(bytes.fromhex(r[2:])).hex() for r in raws}


@test
def live_trader_exception_sell():
    """the signer fails on the first sell: the settlement goes on (a re-send at minOut 0), the trade settles; and log() never raises"""
    c = fresh(dry=False); calls = {"n": 0}
    class Flaky:
        def sign_transaction(self, tx):
            calls["n"] += 1
            if calls["n"] == 2:
                raise ValueError("hsm busy")
            return KEY.sign_transaction(tx)
    E.SIGNER = Flaky(); launch_armed(c); feed(c, L + 3, L + 3); wait_ev("buy_sent"); hb = sent_hash(c, 0)
    stake = E.S.STAKE_WEI; tokens, sp1 = exact_buy(SP0, LIQ, stake); out = E.v4math.sell_out_int(sp1, LIQ, tokens, FEE)
    mine = swap_log(L + 4, 7, -stake, tokens, sp1, sender=RELAY, tx=hb); c.receipts[hb] = live_receipt(hb, L + 4, [mine]); c.logs = [FX["init_log"]] + FX["pool_logs"][:2] + [mine]
    c.auto = lambda h: None if h == hb else live_receipt(h, L + 11, [swap_log(L + 11, 1, out, -tokens, SP0, sender=RELAY, tx=h)])
    feed(c, L + 4, L + 10)
    t = wait_ev("trade_done")[0]
    assert t["eth_out_wei"] == out and any(a["what"].startswith("the trader failed on a sell") for a in events("alarm")) and len(events("sell_sent")) == 1, t
    import contextlib, io
    good = E.S.LOG_PATH; E.S.LOG_PATH = TMP; err = io.StringIO()                # a directory: the write fails, log() does not raise
    try:
        with contextlib.redirect_stderr(err):
            E.log({"ev": "x"}); E.alarm("y")
    finally:
        E.S.LOG_PATH = good
    assert err.getvalue().count("the log line was not written") == 1, err.getvalue()          # stderr, once a kind


@test
def pending_bot_call_must_be_a_buy():
    """only a call of BASE_BOT_SELECTORS with value is the bot's buy: its value-0 funding call (4977dff6) carrying the token is not"""
    c = fresh(); launch_armed(c); feed(c, L + 3, L + 5)
    k = Account.create(); data = "0x4977dff6" + word(0x40) + "0" * 24 + TOKEN[2:]
    for sel, value in (("4977dff6", 0), ("4977dff6", 10 ** 17), ("27f7e6ee", 0)):
        tx = {"type": 2, "chainId": 8453, "nonce": 1, "to": E.to_checksum_address(BOT), "value": value, "data": "0x" + sel + data[10:], "gas": 500000,
              "maxFeePerGas": 10 ** 7, "maxPriorityFeePerGas": 10 ** 6}
        flash(L + 8, ["0x" + bytes(k.sign_transaction(tx).raw_transaction).hex()])
    assert not events("bot_buy") and not events("sell_sent") and E.S.BOT_SELECTORS == {"27f7e6ee"}
    flash(L + 8, [raw_of(BOT1_TX)])
    assert len(events("bot_buy")) == 1 and events("sell_sent")[0]["exit"] == "bot"


@test
def pending_add_and_pull_from_the_launch_wallet_only():
    """a pending add seen while the arm is reading is held, then fires once the launch wallet is known; a stranger's add or pull does nothing"""
    c = fresh(); slow = c.http
    def http(url, payload, timeout):
        if payload["method"] == "eth_getCode":
            time.sleep(0.2)
        return slow(url, payload, timeout)
    E.http_json = http
    feed(c, L - 1, L); feed(c, L + 1, L + 2)
    flash(L + 3, [raw_of(ADD_TX)], index=2)                                    # while arming
    assert E.pools[PID]["status"] == "arming" and not events("would_fire") and E.pools[PID]["add_held"]
    wait_ev("would_fire")
    assert events("would_fire")[0]["via"] == "flash" and events("add")[0]["pending"]
    c = fresh(); launch_armed(c); k = Account.create()
    for sel in (E.S.ADD_SELECTOR, E.S.PULL_SELECTOR):
        tx = {"type": 2, "chainId": 8453, "nonce": 1, "to": E.to_checksum_address(HOOK), "value": 3 * 10 ** 18, "data": "0x" + sel + "00" * 32, "gas": 500000,
              "maxFeePerGas": 10 ** 7, "maxPriorityFeePerGas": 10 ** 6}
        flash(L + 3, ["0x" + bytes(k.sign_transaction(tx).raw_transaction).hex()])
    assert not events("would_fire") and not events("pull") and E.pools[PID]["status"] == "armed" and any("another wallet" in a["what"] for a in events("alarm"))


@test
def http_error_without_json():
    import urllib.error, io
    real = E.urllib.request.urlopen
    def boom(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 502, "Bad Gateway", {}, io.BytesIO(b"<html>bad gateway</html>"))
    E.urllib.request.urlopen = boom
    try:
        try:
            REAL_HTTP("https://x.example.org", {"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []}, 1)
        except RuntimeError as e:
            assert str(e).startswith("HTTP 502"), str(e)
        else:
            raise AssertionError("no error")
    finally:
        E.urllib.request.urlopen = real


@test
def ticker_survives_an_exception():
    c = fresh(); real = E.tick; n = {"k": 0}
    def bad():
        n["k"] += 1; raise KeyError("boom")
    E.tick = bad
    try:
        asyncio.run(asyncio.wait_for(E.ticker(), 2.3))
    except (asyncio.TimeoutError, TimeoutError):
        pass
    finally:
        E.tick = real
    a = [x for x in events("alarm") if x["what"].startswith("the ticker failed")]
    assert n["k"] >= 2 and len(a) == 1 and "KeyError" in a[0]["trace"], (n, a)


@test
def fire_delayed_to_the_add_plus_n():
    """BASE_FIRE_DELAY_BLOCKS 3: the add at +3, the buy aimed at +6: would_fire at head +5 (not before), the dry buy at the end of +6, sold into
    the bot's +8 buy by v4math; a Flashblocks add waits the same way; a head already past +6 when the add is known is late"""
    c = fresh(BASE_FIRE_DELAY_BLOCKS="3"); launch_armed(c); feed(c, L + 3, L + 4)
    assert not events("would_fire") and E.pools[PID]["status"] == "armed"
    feed(c, L + 5, L + 5)
    f = events("would_fire")
    assert len(f) == 1 and f[0]["head"] == L + 5 and f[0]["buy_block"] == L + 6 and f[0]["via"] == "logs", f
    feed(c, L + 6, L + 9)
    t = events("trade_done")[0]; tokens, out = expected_dry(W(first_bot_swap()["data"], 2))
    gas = E.DRY_GAS_UNITS * (int(header(L + 9)["baseFeePerGas"], 16) + E.S.PRIO_WEI) + E.L1_FEE_EST_WEI
    assert t["buy_block"] == L + 6 and t["sell_block"] == L + 8 and t["tokens"] == tokens and abs(t["eth_out_wei"] - out) <= 1, t
    assert abs((t["eth_out_wei"] - E.S.STAKE_WEI - t["gas_wei"]) / E.S.STAKE_WEI - (out - E.S.STAKE_WEI - gas) / E.S.STAKE_WEI) < 1e-9
    c = fresh(BASE_FIRE_DELAY_BLOCKS="3"); flash(L, [raw_of(LAUNCH_TX)]); launch_armed(c); flash(L + 3, [raw_of(ADD_TX)], index=2)
    feed(c, L + 3, L + 4)
    assert not events("would_fire")
    feed(c, L + 5, L + 5)
    f = events("would_fire")
    assert len(f) == 1 and f[0]["via"] == "flash" and f[0]["head"] == L + 5 and f[0]["buy_block"] == L + 6, f
    c = fresh(BASE_FIRE_DELAY_BLOCKS="3"); launch_armed(c); feed(c, L + 3, L + 7, logs=[])           # the heads to +7, the add's logs late
    for lg in by_block(c.logs)[L + 3]:
        E.on_ws_message(json.dumps({"jsonrpc": "2.0", "method": "eth_subscription", "params": {"subscription": "0xl", "result": lg}}), c.subs)
    with E.lock:
        E.end_burst()
    s = events("skip")
    assert len(s) == 1 and s[0]["why"].startswith("late: head") and "BASE_FIRE_DELAY_BLOCKS 3" in s[0]["why"] and not events("would_fire"), s
    for bad in ("6", "-1", "x"):
        os.environ.update(BASE_ENV); os.environ["BASE_FIRE_DELAY_BLOCKS"] = bad
        try:
            E.settings(); raise AssertionError(bad)
        except SystemExit as e:
            assert "BASE_FIRE_DELAY_BLOCKS" in str(e)
    os.environ.update(BASE_ENV)
    assert E.settings().FIRE_DELAY == 0 and (os.environ.pop("BASE_FIRE_DELAY_BLOCKS") and E.settings().FIRE_DELAY == 3)
    os.environ.update(BASE_ENV)


@test
def near_miss_after_our_sell():
    """the fixture's trade (sold into the bot's +8 buy seen pending: exit bot), then the pull two blocks after our sell: a halt; four after: none"""
    for gap, halts in ((2, True), (4, False)):
        c = fresh(); flash(L, [raw_of(LAUNCH_TX)]); launch_armed(c); flash(L + 3, [raw_of(ADD_TX)], index=2); feed(c, L + 3, L + 7)
        flash(L + 8, [raw_of(BOT1_TX)], index=4); feed(c, L + 8, L + 9)
        t = events("trade_done")
        assert len(t) == 1 and t[0]["exit"] == "bot" and t[0]["ret"] > 0 and t[0]["sell_block"] == L + 8 and not events("halt"), t
        pull = copy.deepcopy(FX["pool_logs"][-1]); pull["blockNumber"] = hex(L + 8 + gap); pull["blockHash"] = header(L + 8 + gap)["hash"]
        feed(c, L + 10, L + 8 + gap, logs=[pull])
        h = events("halt")
        assert (len(h) == 1 and h[0]["reason"] == f"near miss: the pull landed {gap} blocks after our sell (BASE_NEAR_MISS_SELL_BLOCKS 3): the operator is reacting") \
            if halts else not h, (gap, h)
    assert E.settings().NEAR_MISS_SELL_BLOCKS == 3
    c = fresh(dry=False)                                                       # live: the pull one block after our sell, on the chain at the settlement
    pull = copy.deepcopy(FX["pool_logs"][-1]); pull["blockNumber"] = hex(L + 10); pull["blockHash"] = header(L + 10)["hash"]
    c.logs = c.logs + [pull]; live_trade(c)
    t = wait_ev("trade_done")[0]; h = wait_ev("halt")
    assert t["exit"] == "take_profit" and t["sell_block"] == L + 9 and len(h) == 1 and "1 blocks after our sell" in h[0]["reason"], (t, h)


@test
def live_start_refusals():
    def start_with(c_setup=None, **env):
        c = fresh(dry=False, **env); E.SIGNER = None
        open(os.path.join(TMP, "k.key"), "w").write(KEY.key.hex())
        os.environ.update({"BASE_KEY_FILE": os.path.join(TMP, "k.key"), "BASE_WALLET": KEY.address, "BASE_RELAY": RELAY, **{k: str(v) for k, v in env.items()}})
        E.S = E.settings()
        if c_setup:
            c_setup(c)
        return c
    cases = [({"BASE_WALLET": ""}, None, "BASE_WALLET is not set"), ({"BASE_RELAY": ""}, None, "BASE_RELAY is not set"),
             ({"BASE_KEY_FILE": os.path.join(TMP, "none.key")}, None, "does not hold a key"),
             ({"BASE_WALLET": "0x" + "ab" * 20}, None, "not BASE_WALLET's"), ({"BASE_STAKE_ETH": "0.01"}, None, "over BASE_STAKE_CAP_ETH"),
             ({}, lambda c: setattr(c, "owner", "0x" + "cd" * 20), "owner()"), ({}, lambda c: setattr(c, "pm", "0x" + "ef" * 20), "pm()"),
             ({}, lambda c: c.chain_ids.update({"send2.example.org": 1}), "chain 1"), ({}, lambda c: c.chain_ids.update({"alt.example.org": 10}), "chain 10"),
             ({}, lambda c: c.code.pop(RELAY), "no code")]
    for env, setup, why in cases:
        c = start_with(setup, **env)
        if "BASE_KEY_FILE" in env or "BASE_WALLET" in env or "BASE_RELAY" in env:
            os.environ.update(env); E.S = E.settings()
        try:
            E.start()
        except SystemExit as e:
            assert why in str(e), (why, str(e))
        else:
            raise AssertionError(f"started with {env} ({why})")
    import fcntl
    c = start_with(); held = open(os.path.join(TMP, "k.key")); fcntl.flock(held, fcntl.LOCK_EX)    # base_ops signing: the engine does not start
    try:
        E.start(); raise AssertionError("started with the key file locked")
    except SystemExit as e:
        assert "locked by another process" in str(e), str(e)
    held.close()
    c = start_with(lambda c: (setattr(c, "balance", 10 ** 14), c.chain_ids.update({"seq.example.org": "send-only"})))
    info = E.start()
    assert info["chains"]["seq.example.org"] == "send-only" and E.SIGNER is not None and E.state["nonce"] == 7 and E.KEY_LOCK is not None
    probe = open(os.path.join(TMP, "k.key"))
    try:
        fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB); raise AssertionError("the running engine does not hold the key file's lock")
    except BlockingIOError:
        pass
    probe.close()
    assert "under the stake + margin" in events("alarm")[0]["what"] and events("start")[0]["dry"] is False
    assert KEY.key.hex()[2:] not in open(LOG).read() and "k3y-rpc-secret" not in open(LOG).read()
    E.state["position"] = None


@test
def dry_start_reads_no_key():
    c = fresh(); E.SIGNER = None
    info = E.start()
    st = events("start")[0]
    assert st["dry"] and E.SIGNER is None and info["head"] == c.head and not any(m == "eth_getTransactionCount" for _, m in c.calls)
    assert st["settings"]["RPC_URL"] == "rpc.example.org" and "KEY_FILE" not in st["settings"] and E.state["logs_to"] == c.head - 12


@test
def restart_with_an_open_position():
    c = fresh(dry=False); stake = E.S.STAKE_WEI; tokens, sp1 = exact_buy(SP0, LIQ, stake)
    key = {"c0": E.ZERO, "c1": TOKEN, "fee": FEE, "ts": 100, "hooks": HOOK}
    saved = {"pid": PID, "key": key, "token": TOKEN, "L": L, "stake": stake, "expected": tokens, "min_out": tokens * 97 // 100, "via": "logs", "add_block": L + 3,
             "fire_head": L + 3, "D": L + 4, "nonce": 7, "buy_hash": "0x" + "b1" * 32, "buy_block": None, "tokens": None, "sell_sent": False, "sell_hash": None}
    json.dump({"positions": {PID: saved}}, open(E.S.POSITIONS_FILE, "w"))
    c.receipts[saved["buy_hash"]] = live_receipt(saved["buy_hash"], L + 4, [swap_log(L + 4, 7, -stake, tokens, sp1, sender=RELAY)])
    open(os.path.join(TMP, "k.key"), "w").write(KEY.key.hex())
    os.environ.update({"BASE_KEY_FILE": os.path.join(TMP, "k.key"), "BASE_WALLET": KEY.address, "BASE_RELAY": RELAY}); E.S = E.settings()
    E.start()
    s = wait_ev("sell_sent")[0]
    assert s["exit"] == "deadline" and s["reason"].startswith("restart") and s["min_out"] == 0 and s["nonce"] == 7 and len(c.sent) == 2, (s, c.sent)  # the stub's chain nonce: 7
    hs = sent_hash(c, 1); eth_out, _ = exact_sell(sp1, LIQ, tokens)
    c.receipts[hs] = live_receipt(hs, L + 30, [swap_log(L + 30, 1, eth_out, -tokens, SP0, sender=RELAY)])
    t = wait_ev("trade_done")[0]
    assert t["exit"] == "deadline" and t["eth_out_wei"] == eth_out and t["tokens"] == tokens and json.load(open(E.S.POSITIONS_FILE))["positions"] == {}, t
    # a sell already sent: its receipt is waited for, nothing new is sent
    c2 = fresh(dry=False); saved.update(sell_sent=True, sell_hash="0x" + "5e" * 32)
    json.dump({"positions": {PID: saved}}, open(E.S.POSITIONS_FILE, "w"))
    c2.receipts[saved["buy_hash"]] = c.receipts[saved["buy_hash"]]
    c2.receipts[saved["sell_hash"]] = live_receipt(saved["sell_hash"], L + 30, [swap_log(L + 30, 1, eth_out, -tokens, SP0, sender=RELAY)])
    os.environ.update({"BASE_KEY_FILE": os.path.join(TMP, "k.key"), "BASE_WALLET": KEY.address, "BASE_RELAY": RELAY}); E.S = E.settings()
    E.start()
    t = wait_ev("trade_done")[0]
    assert t["eth_out_wei"] == eth_out and not c2.sent and not events("sell_sent"), (t, c2.sent)


@test
def confirmed_loop_reconnects():
    """the asyncio reader with a stubbed websockets module: a connection that drops after its messages, the next one silent: both end in
    a reconnection (ws_down), the burst's actions run after its messages"""
    msgs = [json.dumps({"jsonrpc": "2.0", "id": 1, "result": "0xh"}), json.dumps({"jsonrpc": "2.0", "id": 2, "result": "0xl"})]
    h = header(L - 1)
    msgs.append(json.dumps({"jsonrpc": "2.0", "method": "eth_subscription", "params": {"subscription": "0xh", "result": {"number": h["number"], "timestamp": h["timestamp"], "baseFeePerGas": h["baseFeePerGas"]}}}))
    msgs.append(json.dumps({"jsonrpc": "2.0", "method": "eth_subscription", "params": {"subscription": "0xl", "result": FX["init_log"]}}))
    conns = []

    class Conn:
        def __init__(self, data):
            self.data = list(data); self.sent = []
        async def __aenter__(self):
            conns.append(self); return self
        async def __aexit__(self, *a):
            return False
        async def send(self, m):
            self.sent.append(json.loads(m))
        async def recv(self):
            if self.data:
                return self.data.pop(0)
            if len(conns) == 1:
                raise ConnectionError("closed")
            await asyncio.sleep(3600)
    fake = types.ModuleType("websockets"); plan = [msgs, []]
    fake.connect = lambda *a, **k: Conn(plan.pop(0) if plan else [])
    c = fresh(); E.state.update(ws=False, ws_subs=0); sys.modules["websockets"] = fake; E.S.WS_SILENT_S = 0.2
    try:
        asyncio.run(asyncio.wait_for(E.confirmed_loop(), 1.5))
    except (asyncio.TimeoutError, TimeoutError):
        pass
    finally:
        sys.modules.pop("websockets", None)
    assert len(conns) >= 2 and conns[0].sent[1]["params"][1]["topics"] == [[E.T_INIT, E.T_ML, E.T_SWAP]] and conns[0].sent[1]["params"][1]["address"] == E.S.PM
    assert wait_ev("launch")[0]["armed"] and len([a for a in events("alarm") if a["what"].startswith("the websocket is down")]) == 1   # quiet: one a key


@test
def flash_silent_stream_reconnects():
    """a Flashblocks stream that goes silent: flash false (the ticker, and the reader's timeout), a reconnection, then messages again"""
    conns = []
    msg = lambda n: brotli.compress(json.dumps({"index": 1, "diff": {"transactions": []}, "metadata": {"block_number": n}}).encode())

    class Conn:
        def __init__(self, data):
            self.data = list(data)
        async def __aenter__(self):
            conns.append(self); return self
        async def __aexit__(self, *a):
            return False
        async def recv(self):
            if self.data:
                return self.data.pop(0)
            await asyncio.sleep(3600)                                          # silent
    plan = [[msg(L), msg(L + 1)], [msg(L + 2), msg(L + 3), msg(L + 4)]]
    fake = types.ModuleType("websockets"); fake.connect = lambda *a, **k: Conn(plan.pop(0) if plan else [])
    c = fresh(); sys.modules["websockets"] = fake; old = E.FLASH_SILENT_S; E.FLASH_SILENT_S = 0.3; seen = []

    async def watch():
        while True:
            await asyncio.sleep(0.02)
            with E.lock:
                E.tick(); seen.append((E.state["flash"], E.state["flash_total"], E.state["flash_reconnects"]))
    async def both():
        await asyncio.gather(E.flash_loop(), watch())
    try:
        asyncio.run(asyncio.wait_for(both(), 1.6))
    except (asyncio.TimeoutError, TimeoutError):
        pass
    finally:
        sys.modules.pop("websockets", None); E.FLASH_SILENT_S = old
    assert len(conns) >= 2 and E.state["flash_total"] == 5 and E.state["flash_block"] == L + 4 and E.state["flash_reconnects"] >= 1, (len(conns), E.state["flash_total"])
    i_false = next(i for i, x in enumerate(seen) if x[1] == 2 and not x[0])               # silent after its 2 messages: flash false
    assert any(x[0] and x[1] == 5 for x in seen[i_false:]), seen                         # then back, with the second connection's messages
    assert any(a["what"].startswith("Flashblocks is down") for a in events("alarm"))


@test
def scrubbed_and_bounded_log():
    c = fresh(BASE_READ_ALT_URL="0"); c.fail.add("eth_getCode"); feed(c, L, L)
    e = wait_ev("launch")[0]
    assert not e["armed"] and e["skip"].startswith("not read") and "k3y" not in open(LOG).read() and "rpc.example.org" in e["skip"], e


if __name__ == "__main__":
    t0 = time.time(); n = 0
    only = sys.argv[1:]
    for fn in TESTS:
        if only and fn.__name__ not in only:
            continue
        fn(); n += 1
        print("ok", fn.__name__, flush=True)
    print(f"{n} tests passed in {time.time() - t0:.1f} s")
