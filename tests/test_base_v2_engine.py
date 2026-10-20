"""The Base V2 engine (src/base_v2_engine.py, docs/BASE_V2.md) against the line's real 15 ETH pair of 12:07 UTC Oct 20 2026 (creation block
N = 52854344, tests/data/base_v2_pair.json: the creation transaction and its receipt, every pair log to +2000 blocks with the transactions
behind them, 21 block headers): the probe's buy inside the creation block, the fleet's dust at +2 and its buys from +15, the creator's
approve at +4, an outsider's 0.00075 ETH buy at +419, the fleet's sell at +421, the pull at +424. The RPC (every read and send), both
websockets, the key file and the wall clock are stubbed; nothing reaches a network. The tolerant-tier cases replay the same stream at 2.0
ETH (the creation's value and every ETH-side amount scaled; the whole supply in the pool), since the real 15 ETH pair is refused by the
tier gate and holds 98.2% of its supply; a second creator is a fresh key whose CREATE address is the token (the engine's own derivation),
so a Flashblock can carry its signed creation. Each case prints "ok <name>"; the count at the end. Plain script:
python3 tests/test_base_v2_engine.py [names...]"""
import os, sys, json, copy, time, decimal, tempfile, threading, asyncio, types, fcntl
import brotli, rlp
from eth_account import Account
from eth_utils import keccak
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); TMP = tempfile.mkdtemp(prefix="base_v2_engine_test_"); LOG = os.path.join(TMP, "base_v2.jsonl")
BASE_ENV = {"BASE_V2_LOG_PATH": LOG, "BASE_V2_RPC_URL": "https://rpc.example.org/v1/k3y-rpc-secret", "BASE_V2_READ_ALT_URL": "https://alt.example.org/",
            "BASE_V2_ARCHIVE_URL": "https://arch.example.org/k3y-archive-secret/base", "BASE_V2_WS_URL": "wss://ws.example.org/ws/k3y-ws-secret",
            "BASE_V2_FLASH_URL": "wss://flash.example.org/ws", "BASE_V2_SEND_URLS": "https://seq.example.org,https://send2.example.org",
            "BASE_V2_KEY_FILE": os.path.join(TMP, "missing.key"), "BASE_V2_ROSTER_FILE": os.path.join(TMP, "roster.json")}
for k in [k for k in os.environ if k.startswith("BASE_V2_")]:
    os.environ.pop(k)
os.environ.update(BASE_ENV)
sys.path.insert(0, os.path.join(ROOT, "src"))
import base_v2_engine as E
E.RECEIPT_POLL_S = 0.005; E.POLL_S = 0.005; E.GUARD_WAIT_S = 0.3; E.RECEIPT_GRACE_S = 2.0

FX = json.load(open(os.path.join(ROOT, "tests", "data", "base_v2_pair.json")))
N = FX["creation"]["block"]; PAIR = FX["pair"]; TOKEN = "0x" + FX["token"]; T = FX["topics"]; CTX = FX["creation"]["transaction"]; CREATOR = CTX["from"].lower()
CREATION_HASH = FX["creation"]["tx"]; R_TOK0 = 5_500_000_000_000_000_000_000_000_000; SUPPLY = 5_600_000_000_000_000_000_000_000_000
PROBE = "0xe71a69f434a719cd5afa411568b69716aab3b84a"; ROUTER = E.S.ROUTER; FACTORY = E.S.FACTORY; WETH = E.S.WETH
W = E.W; word = E.word; aword = E.aword; cp_out = E.cp_out
blk = lambda lg: int(lg["blockNumber"], 16)
words = lambda d: [W(d, i) for i in range((len(d) - 2) // 64)]
inword = lambda inp, i: int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16); inaddr = lambda inp, i: "0x" + inp[10 + 64 * i + 24: 10 + 64 * (i + 1)].lower()   # calldata words
a32 = lambda a: "0x" + "0" * 24 + a[2:].lower()
BLOCKS = {int(k): v for k, v in FX["blocks"].items()}
KEY = Account.create(); RELAY = "0x" + "f1" * 20                              # our wallet (a fresh key, written to the key file by the live cases) and relay
FLEET_KEY = Account.create(); PROBE_KEY = Account.create(); STRANGER = Account.create()   # a roster wallet, a probe and an outsider we can sign for
FLEET = sorted({t["from"].lower() for t in FX["txs"].values() if t["input"][:10] == "0x7ff36ab5" and int(t["nonce"], 16) < 20000 and int(t["value"], 16) > 0})
json.dump({"built": "2026-10-20T00:00:00Z", "wallets": FLEET + [FLEET_KEY.address]}, open(BASE_ENV["BASE_V2_ROSTER_FILE"], "w"))
TESTS = []


def test(fn):
    TESTS.append(fn); return fn


# ---------------------------------------------------------------- the stubbed chain
def header(n):
    base = max([k for k in BLOCKS if k <= n], default=min(BLOCKS)); h = BLOCKS[base]
    return {"number": hex(n), "hash": "0x" + keccak(text=f"block{n}").hex(), "timestamp": hex(h["timestamp"] + 2 * (n - base)), "baseFeePerGas": hex(h["baseFeePerGas"])}


ts = lambda n: int(header(n)["timestamp"], 16)
CLOCK = [ts(N) - 6]
E.now = lambda: float(CLOCK[0])                                               # the wall clock: each fed block's timestamp


def creator_key(seed):
    """a creator whose CREATE address (the token) sorts after WETH, as on the fixture (token1; WETH token0)"""
    for i in range(256):
        k = Account.from_key(keccak(text=f"base_v2 test creator {seed}.{i}"))
        if E.create_address(k.address.lower()) > WETH:
            return k


def signed(key, nonce, to, value, data, prio=10 ** 6, max_fee=11 * 10 ** 6, gas=119_000, legacy=False):
    tx = {"nonce": nonce, "to": E.to_checksum_address(to), "value": value, "data": data, "gas": gas}
    tx.update({"gasPrice": prio} if legacy else {"type": 2, "chainId": 8453, "maxPriorityFeePerGas": prio, "maxFeePerGas": max_fee})
    return "0x" + bytes(key.sign_transaction(tx).raw_transaction).hex()


hash_of = lambda raw: "0x" + keccak(bytes.fromhex(raw[2:])).hex()


class Stream:
    """the fixture's event stream at a value (the creation's msg.value and every ETH-side amount scaled; the token side as recorded), optionally
    re-addressed to a creator we hold the key of (token = its CREATE address, pair = the factory's CREATE2), shifted by `shift` blocks, its
    logIndexes offset (two pairs in one block must not share a (blockHash, logIndex) key); `fleet=False` drops the fleet's buys"""
    def __init__(self, value_eth="15", creator=None, shift=0, li_offset=0, fleet=True, nonce=2, create_token=None):
        self.value = int(decimal.Decimal(value_eth) * 10 ** 18); sc = lambda x: x * self.value // (15 * 10 ** 18)
        logs = copy.deepcopy(FX["logs"]); rlogs = copy.deepcopy(FX["creation"]["receipt_logs"]); ctx = copy.deepcopy(CTX); txs = copy.deepcopy(FX["txs"])
        for l in logs + rlogs:
            t0 = l["topics"][0]; ws = words(l["data"])
            if t0 in (T["Sync"], T["Mint"], T["Burn"]):
                ws[0] = sc(ws[0])
            elif t0 == T["Swap"]:
                ws[0], ws[2] = sc(ws[0]), sc(ws[2])
            else:
                continue
            l["data"] = "0x" + "".join(word(x) for x in ws)
        ctx["value"] = hex(self.value); ctx["nonce"] = hex(nonce)
        self.N = N + shift; self.creator = CREATOR; self.token = TOKEN; self.pair = PAIR; self.key = None; self.creation_hash = CREATION_HASH; self.creation_raw = None
        if creator is not None:
            self.key = creator; self.creator = creator.address.lower(); self.token = E.create_address(self.creator); self.pair = E.pair_address(self.token)
            data = "0x" + ctx["input"][2:10] + aword(create_token or self.token) + ctx["input"][74:]
            self.creation_raw = signed(creator, nonce, ROUTER, self.value, data, int(ctx["maxPriorityFeePerGas"], 16), int(ctx["maxFeePerGas"], 16), int(ctx["gas"], 16))
            self.creation_hash = hash_of(self.creation_raw)
            text = json.dumps([logs, rlogs, ctx, txs])
            for a, b in ((PAIR, self.pair), (TOKEN, self.token), (CREATOR, self.creator), (CREATION_HASH, self.creation_hash)):
                text = text.replace(a[2:], b[2:])
            logs, rlogs, ctx, txs = json.loads(text); ctx["input"] = data
        for l in logs + rlogs:
            b = blk(l) + shift; l.update(blockNumber=hex(b), blockHash=header(b)["hash"], blockTimestamp=header(b)["timestamp"], logIndex=hex(int(l["logIndex"], 16) + li_offset))
        for t in txs.values():
            t["blockNumber"] = hex(int(t["blockNumber"], 16) + shift)
        if not fleet:
            pull = [l["transactionHash"] for l in logs if l["topics"][0] == T["Burn"]][0]
            logs = [l for l in logs if blk(l) == self.N or l["topics"][0] not in (T["Swap"], T["Sync"]) or l["transactionHash"] == pull]
        self.logs, self.rlogs, self.creation_tx, self.txs = logs, rlogs, ctx, txs
        self.r_eth0, self.r_tok0 = self.value, R_TOK0; self.weth_is0 = True
        self.pull_block = next(blk(l) for l in logs if l["topics"][0] == T["Burn"])

    def sync_at(self, b):
        """the reserves (ETH, tokens) at the end of block b from the recorded Syncs alone"""
        r = (self.r_eth0, self.r_tok0)
        for l in sorted(self.logs + self.rlogs, key=E.order):
            if blk(l) <= b and l["topics"][0] == T["Sync"]:
                r = tuple(words(l["data"])[:2])
        return r


class Chain:
    """the RPC: every read of the engine answered from the streams and the mined receipts; the sends recorded and mined on request"""
    def __init__(self, *streams, live=False):
        self.streams = {st.pair: st for st in streams}; self.by_token = {st.token: st for st in streams}; self.live = live
        self.txs = {}; self.receipts = {}; self.extra = []; self.calls = []; self.ranges = []; self.sent = []; self.nonces = set(); self.mined = set(); self.replies = []
        for st in streams:
            self.txs.update(st.txs); self.txs[st.creation_hash] = st.creation_tx
            self.receipts[st.creation_hash] = {"status": "0x1", "blockNumber": hex(st.N), "transactionHash": st.creation_hash, "logs": st.rlogs}
        self.fail = set(); self.chain_ids = {}; self.head = N - 3; self.archive_head = N + 5; self.code_size = 3553; self.supply = R_TOK0; self.verdict = "ok"
        self.owner = None; self.router = ROUTER; self.weth = WETH; self.relay_code = "0x6001"; self.balance = 10 ** 18; self.nonce = 7; self.tokens = 0
        self.exit_lag = 0.0; self.guard_calls = []; self.auto_mine = live; self.buy_ok = True; self.sell_ok = True; self.transfer_cut = 0; self.held = {}; self.subs = {}; self.pend = {}

    def all_logs(self):
        return [l for st in self.streams.values() for l in st.rlogs + st.logs] + self.extra + [l for r in self.receipts.values() for l in r.get("logs") or [] if "gasUsed" in r]

    def logs_of(self, n):
        return sorted([l for l in self.all_logs() if blk(l) == n and "gasUsed" not in str(l)], key=E.order)

    def reserves_at(self, pair, b):
        """(ETH, tokens) at the end of block b: the recorded Syncs, the injected ones and the mined receipts' in (block, logIndex) order"""
        st = self.streams[pair]; r = (st.r_eth0, st.r_tok0)
        for l in sorted([l for l in self.all_logs() if l["address"].lower() == pair and l["topics"][0] == T["Sync"] and blk(l) <= b], key=E.order):
            r = tuple(words(l["data"])[:2])
        return r

    def http(self, url, payload, timeout):
        m, prm = payload["method"], payload["params"]; h = E.host(url); self.calls.append((h, m))
        if (h, m) in self.fail or m in self.fail:
            raise RuntimeError(f"stub: {url} is down")
        if m == "eth_chainId":
            c = self.chain_ids.get(h, 8453)
            return {"error": {"code": -32601, "message": "rpc method is not allowed"}} if c == "send-only" else {"result": hex(c)}
        if m == "eth_sendRawTransaction":
            return {"error": {"code": -32602, "message": "typed transaction too short"}}
        if m == "eth_blockNumber":
            return {"result": hex(self.archive_head if h == "arch.example.org" else self.head)}
        if m == "eth_getBlockByNumber":
            return {"result": header(self.head)}
        if m == "eth_getLogs":
            f = prm[0]; a, b = int(f["fromBlock"], 16), int(f["toBlock"], 16); self.ranges.append((a, b))
            addrs = {x.lower() for x in (f["address"] if isinstance(f["address"], list) else [f["address"]])} if f.get("address") else None
            tps = f.get("topics") or []; t0s = (set(tps[0]) if isinstance(tps[0], list) else {tps[0]}) if tps and tps[0] else None
            out = [l for l in self.all_logs() if a <= blk(l) <= b and (addrs is None or l["address"].lower() in addrs) and (t0s is None or l["topics"][0] in t0s)
                   and all(tp is None or (len(l["topics"]) > i + 1 and l["topics"][i + 1].lower() == tp.lower()) for i, tp in enumerate(tps[1:]))]
            return {"result": copy.deepcopy(sorted(out, key=E.order))}
        if m == "eth_getTransactionByHash":
            return {"result": copy.deepcopy(self.txs.get(prm[0]))}
        if m == "eth_getTransactionReceipt":
            return {"result": copy.deepcopy(self.receipts.get(prm[0]))}
        if m == "eth_getCode":
            a = prm[0].lower()
            return {"result": "0x" + "60" * self.code_size if a in self.by_token else self.relay_code if a == RELAY else "0x"}
        if m == "eth_getBalance":
            return {"result": hex(self.balance)}
        if m == "eth_getTransactionCount":
            return {"result": hex(max(self.nonces, default=self.nonce - 1) + 1)}
        if m == "eth_call":
            sel = prm[0]["data"][2:10]; args = "0x" + prm[0]["data"][10:]; to = prm[0]["to"].lower()
            if sel == E.SEL_TOTAL_SUPPLY:
                return {"result": "0x" + word(self.supply)}
            if sel == E.SEL_OWNER:
                return {"result": a32(self.owner or E.S.WALLET)}
            if sel == E.SEL_ROUTER:
                return {"result": a32(self.router)}
            if sel == E.SEL_WETH:
                return {"result": a32(self.weth)}
            if sel == E.SEL_BALANCE_OF:
                return {"result": "0x" + word(self.tokens)}
            if sel == "0902f1ac":                                              # getReserves (the self-test)
                re_, rt_ = self.reserves_at(to, int(prm[1], 16)); return {"result": "0x" + word(re_) + word(rt_) + word(0)}
            if sel == E.SEL_ROUND_TRIP:
                return self.round_trip(h, args, prm[1], prm[2])
            return {"result": "0x" + word(0)}
        raise RuntimeError(m)

    def round_trip(self, h, args, tag, override):
        """V2RoundTrip.roundTrip(router, weth, token, stake, doSell) at `tag`: (tokens bought, ETH back, the quote) by the constant product on the
        reserves at the end of that block, or the verdict's distortion"""
        token = E.A(args, 2); stake = W(args, 3); do_sell = W(args, 4); self.guard_calls.append((h, tag, do_sell, override))
        if self.exit_lag:
            time.sleep(self.exit_lag)
        if self.verdict == "unreadable" or tag == "pending":
            return {"error": {"code": -32000, "message": "header not found"}}
        st = self.by_token[token]; re_, rt_ = self.reserves_at(st.pair, int(tag, 16)); tokens = cp_out(stake, re_, rt_)
        if self.verdict == "honeypot":
            return {"error": {"code": 3, "message": "execution reverted"}} if do_sell else {"result": "0x" + word(tokens) + word(0) + word(0)}
        back = cp_out(tokens, rt_ - tokens, re_ + stake); quote = back
        if self.verdict == "taxed":
            back = back * 90 // 100
        if self.verdict == "buy_tax":
            tokens = tokens * 95 // 100
        return {"result": "0x" + word(tokens) + word(back) + word(quote)}

    def post(self, url, body):
        raw = json.loads(body)["params"][0]; self.sent.append((E.host(url), raw)); self.nonces.add(E.decode_tx(bytes.fromhex(raw[2:]))["nonce"])
        if self.replies:
            return self.replies.pop(0)
        return {"jsonrpc": "2.0", "id": 1, "result": hash_of(raw)}

    def mine(self, b, only=None):
        """every sent transaction not mined yet lands in block b (behind the block's recorded swaps) with its receipt: a buy's Transfer to the
        relay, Sync and Swap; a sell's Sync and Swap (or a reverted receipt); their pair logs reach the engine as the websocket's"""
        out = []
        for _, raw in list(self.sent):
            h = hash_of(raw)
            if h in self.mined or (only is not None and h not in only):
                continue
            self.mined.add(h); tx = E.decode_tx(bytes.fromhex(raw[2:])); sel = tx["data"][:4].hex(); d = "0x" + tx["data"][4:].hex(); st = self.by_token[E.A(d, 0)]
            re_, rt_ = self.reserves_at(st.pair, b); li = 0x800 + 4 * len(self.mined)
            base = dict(blockNumber=hex(b), blockHash=header(b)["hash"], transactionHash=h, transactionIndex="0x5", removed=False, blockTimestamp=header(b)["timestamp"])
            rc = {"status": "0x1", "blockNumber": hex(b), "blockHash": header(b)["hash"], "transactionHash": h, "logs": []}
            if sel == E.SEL_BUY and self.buy_ok:
                stake = W(d, 1); tokens = cp_out(stake, re_, rt_); got = tokens - tokens * self.transfer_cut // 100; self.held[st.pair] = got
                rc["logs"] = [dict(base, address=st.token, topics=[T["Transfer"], a32(st.pair), a32(RELAY)], data="0x" + word(got), logIndex=hex(li)),
                              dict(base, address=st.pair, topics=[T["Sync"]], data="0x" + word(re_ + stake) + word(rt_ - tokens), logIndex=hex(li + 1)),
                              dict(base, address=st.pair, topics=[T["Swap"], a32(ROUTER), a32(RELAY)], data="0x" + word(stake) + word(0) + word(0) + word(tokens), logIndex=hex(li + 2))]
                rc.update(gasUsed=hex(125_000), effectiveGasPrice=hex(35_000_000), l1Fee=hex(2_090_000_000))
            elif sel == E.SEL_BUY:
                rc.update(status="0x0", gasUsed=hex(60_000), effectiveGasPrice=hex(35_000_000), l1Fee=hex(2_090_000_000))
            elif sel == E.SEL_SELL and self.sell_ok:
                tokens = self.held.get(st.pair, 0); eth_out = cp_out(tokens, rt_, re_); self.held[st.pair] = 0
                rc["logs"] = [dict(base, address=st.pair, topics=[T["Sync"]], data="0x" + word(re_ - eth_out) + word(rt_ + tokens), logIndex=hex(li)),
                              dict(base, address=st.pair, topics=[T["Swap"], a32(ROUTER), a32(ROUTER)], data="0x" + word(0) + word(tokens) + word(eth_out) + word(0), logIndex=hex(li + 1))]
                rc.update(gasUsed=hex(118_000), effectiveGasPrice=hex(35_000_000), l1Fee=hex(2_000_000_000))
            else:
                rc.update(status="0x0", gasUsed=hex(40_000), effectiveGasPrice=hex(35_000_000), l1Fee=hex(2_000_000_000))
            self.receipts[h] = rc; out.append((h, rc))
            for l in rc["logs"]:
                if l["address"].lower() in E.pairs:
                    push(self, l)
        return out


def push(c, lg):
    """one log as the websocket delivers it: the factory's subscription, or the followed pair's (registered on demand, as the subscriber does)"""
    addr = lg["address"].lower()
    if addr == FACTORY:
        sid = "0xl"
    elif addr in E.pairs and lg["topics"][0] in E.PAIR_TOPICS:
        sid = next((k for k, v in c.subs.items() if v == addr), None)
        if sid is None:
            sid = "0xp" + addr[2:8]; c.subs[sid] = addr; E.pairs[addr]["sub"] = sid
    else:
        return
    E.on_ws_message(json.dumps({"jsonrpc": "2.0", "method": "eth_subscription", "params": {"subscription": sid, "result": lg}}), c.subs, c.pend)


def head(c, n):
    h = header(n); CLOCK[0] = ts(n)
    E.on_ws_message(json.dumps({"jsonrpc": "2.0", "method": "eth_subscription", "params": {"subscription": "0xh", "result": {"number": h["number"], "timestamp": h["timestamp"], "baseFeePerGas": h["baseFeePerGas"]}}}), c.subs, c.pend)


def feed(c, a, b, skip_heads=()):
    """the websocket from block a to b: each block's logs, the sent transactions mined into it (live, with auto_mine), its head, one burst each"""
    for n in range(a, b + 1):
        CLOCK[0] = ts(n); c.head = n
        for lg in c.logs_of(n):
            push(c, lg)
        if c.auto_mine:
            c.mine(n)
        if n not in skip_heads:
            head(c, n)
        with E.lock:
            E.end_burst()


def fresh(*streams, dry=True, **env):
    """a new engine state with these settings, a stubbed chain over the streams (the 2.0 ETH replay by default) and an empty log; the
    websocket connected, its first head to come at N - 2"""
    for k in [k for k in os.environ if k.startswith("BASE_V2_")]:
        os.environ.pop(k)
    os.environ.update(BASE_ENV); os.environ["BASE_V2_DRY_RUN"] = "1" if dry else "0"; os.environ.update({k: str(v) for k, v in env.items()})
    E.S = E.settings(); E.S.STAKE_WEI_MAX = lambda: min(E.S.STAKE_ETH_WEI, E.S.STAKE_CAP_WEI)
    E.reset(); E.SIGNER = None; E.state["started_at"] = E.mono()
    if E.KEY_LOCK:
        E.KEY_LOCK.close(); E.KEY_LOCK = None
    for f in (LOG, E.S.HALT_FILE, E.S.POSITIONS_FILE):
        if os.path.exists(f):
            os.remove(f)
    open(LOG, "w").close(); CLOCK[0] = ts(N) - 6
    c = Chain(*(streams or [Stream("2.0")]), live=not dry); E.http_json = c.http; E.post_one = c.post
    E.load_roster(at_start=True)
    if not dry:
        E.S.WALLET = KEY.address.lower(); E.S.RELAY = RELAY; E.SIGNER = KEY; E.state.update(nonce=7, relay_wei=10 ** 18)
    E.state["logs_to"] = N - 2                                                  # complete to N - 2: the websocket covers from its first head
    E.on_ws_message(json.dumps({"jsonrpc": "2.0", "id": 1, "result": "0xh"}), c.subs, c.pend)
    E.on_ws_message(json.dumps({"jsonrpc": "2.0", "id": 2, "result": "0xl"}), c.subs, c.pend)
    return c


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


def wait_status(pair, statuses, timeout=5.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        with E.lock:
            P = E.pairs.get(pair)
            if P is not None and P["status"] in statuses:
                return P["status"]
        time.sleep(0.005)
    raise AssertionError(f"pair status {E.pairs.get(pair, {}).get('status')} not in {statuses}; log tail: {open(LOG).read()[-1500:]}")


def fired(c, st=None, upto=None):
    """blocks N - 2 to N (the creation), the guard, the fire at head N: the would_fire / fire line (or the skip)"""
    st = st or next(iter(c.streams.values())); feed(c, N - 2, st.N if upto is None else upto)
    wait_status(st.pair, ("fired", "watched", "traded"))
    if not c.live:
        return events("would_fire", pair=st.pair) or events("skip", pair=st.pair)
    wait_ev("buy_sent", pair=st.pair) if E.pairs[st.pair]["status"] == "fired" else None
    return events("fire", pair=st.pair) or events("skip", pair=st.pair)


def flash(n, txs, index=1, base_fee=None):
    msg = {"payload_id": "0x01", "index": index, "diff": {"transactions": txs}, "metadata": {"block_number": n}}
    if index == 0:
        msg["base"] = {"block_number": hex(n), "timestamp": header(n)["timestamp"], "base_fee_per_gas": base_fee or header(n)["baseFeePerGas"]}
    E.on_flash(brotli.compress(json.dumps(msg).encode()))


def mk(st, kind, b, li, words_, topics_extra=(), tx=None):
    return {"address": st.pair, "topics": [T[kind]] + list(topics_extra), "data": "0x" + "".join(word(x) for x in words_), "blockNumber": hex(b), "blockHash": header(b)["hash"],
            "logIndex": hex(li), "transactionHash": tx or "0x" + keccak(text=f"inj {st.pair} {kind} {b} {li}").hex(), "transactionIndex": "0x9", "removed": False, "blockTimestamp": header(b)["timestamp"]}


def inject_buy(c, st, b, eth, to, sender=None, li=900, tx=None, sel="0x7ff36ab5"):
    """a buy of `eth` at block b by `sender` (the Swap's `to` is `to`; the transaction behind it readable): the pair's Sync and Swap"""
    re_, rt_ = c.reserves_at(st.pair, b); out = cp_out(eth, re_, rt_)
    sw = mk(st, "Swap", b, li + 1, [eth, 0, 0, out], [a32(ROUTER), a32(to)], tx); sy = mk(st, "Sync", b, li, [re_ + eth, rt_ - out], (), sw["transactionHash"])
    c.txs[sw["transactionHash"]] = {"from": (sender or to).lower(), "to": ROUTER, "nonce": "0x5", "value": hex(eth), "input": sel + aword(st.token), "type": "0x2", "blockNumber": hex(b),
                                    "maxPriorityFeePerGas": "0xf4240", "maxFeePerGas": "0xa7d8c0", "gas": "0x2370d", "transactionIndex": "0x9"}
    c.extra += [sy, sw]; return sw


def inject_sell(c, st, b, tok_in, sender, li=900):
    """a sell of `tok_in` tokens through the router at block b by `sender` (the Swap's `to` is the router, as a router sell shows)"""
    re_, rt_ = c.reserves_at(st.pair, b); out = cp_out(tok_in, rt_, re_)
    sw = mk(st, "Swap", b, li + 1, [0, tok_in, out, 0], [a32(ROUTER), a32(ROUTER)]); sy = mk(st, "Sync", b, li, [re_ - out, rt_ + tok_in], (), sw["transactionHash"])
    c.txs[sw["transactionHash"]] = {"from": sender.lower(), "to": ROUTER, "nonce": "0x6", "value": "0x0", "input": "0x18cbafe5" + word(tok_in), "type": "0x2", "blockNumber": hex(b)}
    c.extra += [sy, sw]; return sw, out


def inject_burn(c, st, b, li=900, share=1000):
    """the pull: a Burn of share/1000 of the reserves (the fixture's: all but dust)"""
    re_, rt_ = c.reserves_at(st.pair, b); e, t = re_ * share // 1000, rt_ * share // 1000
    bn = mk(st, "Burn", b, li + 1, [e, t], [a32(ROUTER), a32(st.creator)]); sy = mk(st, "Sync", b, li, [re_ - e, rt_ - t], (), bn["transactionHash"])
    c.extra += [sy, bn]; return bn


def raw_sent(c, i):
    return E.decode_tx(bytes.fromhex(c.sent[i][1][2:]))


def dry_value(c, st, pos_tokens, stake, b):
    """the dry run's sell price at the end of block b: the recorded reserves with our own buy put into them"""
    re_, rt_ = c.reserves_at(st.pair, b); return cp_out(pos_tokens, rt_ - pos_tokens, re_ + stake)


# ---------------------------------------------------------------- the cases: the fixture and the pure functions
@test
def fixture_shape():
    """the real 15 ETH pair: the creator's CREATE address is the token, the factory's CREATE2 the pair; the creation's shape; the stream"""
    assert os.path.getsize(os.path.join(ROOT, "tests", "data", "base_v2_pair.json")) < 200_000 and len(FX["logs"]) == 48 and len(FX["txs"]) == 22 and len(FX["blocks"]) == 21
    assert E.create_address(CREATOR) == TOKEN and E.pair_address(TOKEN) == PAIR and FX["weth_is0"] and WETH < TOKEN
    assert int(CTX["nonce"], 16) == 2 and CTX["input"][2:10] == "f305d719" and CTX["to"].lower() == ROUTER and int(CTX["value"], 16) == 15 * 10 ** 18 and CTX["type"] == "0x2"
    assert int(CTX["maxPriorityFeePerGas"], 16) == int(CTX["maxFeePerGas"], 16) == 6_000_000 and int(CTX["gas"], 16) == 2_791_667 and inaddr(CTX["input"], 0) == TOKEN
    assert {E.T_PC, E.T_MINT, E.T_BURN, E.T_SWAP, E.T_SYNC, E.T_TRANSFER} == {E.T_PC, *T.values()} and len(FLEET) == 11 and PROBE in E.S.PROBE
    pc = [l for l in FX["creation"]["receipt_logs"] if l["address"].lower() == FACTORY][0]
    assert pc["topics"][0] == E.T_PC and E.topic_addr(pc["topics"][1]) == WETH and E.topic_addr(pc["topics"][2]) == TOKEN and E.A(pc["data"], 0) == PAIR
    mint = [l for l in FX["creation"]["receipt_logs"] if l["topics"][0] == T["Mint"]][0]
    assert words(mint["data"]) == [15 * 10 ** 18, R_TOK0] and R_TOK0 * 10 ** 6 // SUPPLY == 982_142            # 98.2% of the supply in the pool
    kinds = [(blk(l) - N, {v: k for k, v in T.items()}.get(l["topics"][0], "other"), FX["txs"][l["transactionHash"]]["from"].lower()) for l in FX["logs"]]
    assert kinds[4:6] == [(0, "Sync", PROBE), (0, "Swap", PROBE)] and kinds[7] == (2, "Swap", FLEET[0]) and kinds[8] == (4, "other", CREATOR)
    assert [k[0] for k in kinds if k[1] == "Swap"][:5] == [0, 2, 15, 41, 67] and kinds[-7][:2] == (424, "Burn") and kinds[-7][2] == CREATOR
    out_ = [(k[0], FX["txs"][l["transactionHash"]]["input"][:10]) for k, l in zip(kinds, FX["logs"]) if k[1] == "Swap" and k[2] not in FLEET and k[2] != PROBE]
    assert out_[0] == (419, "0xaff9ec28") and all(ts(N + k) - ts(N) == 2 * k for k in BLOCKS and [k - N for k in BLOCKS] if 0 <= k)
    # the constant product against the chain: every recorded swap (buys and sells) to the unit from the reserves before its transaction
    # (a pair emits its Sync, post-swap, before its Swap)
    pre = cur = (15 * 10 ** 18, R_TOK0); last = None; n = 0
    for l in sorted(FX["logs"], key=E.order):
        if l["topics"][0] == T["Sync"]:
            pre = cur if l["transactionHash"] != last else pre; cur = tuple(words(l["data"])[:2]); last = l["transactionHash"]
        elif l["topics"][0] == T["Swap"]:
            a0i, a1i, a0o, a1o = words(l["data"])
            assert cp_out(a0i, pre[0], pre[1]) == a1o if a0i else cp_out(a1i, pre[1], pre[0]) == a0o, (blk(l) - N, words(l["data"]), pre); n += 1
    assert n == 19
    st = Stream("2.0"); assert st.value == 2 * 10 ** 18 and inword(st.creation_tx["input"], 1) == R_TOK0
    assert st.sync_at(N)[0] == W(FX["logs"][4]["data"], 0) * 2 // 15 == 2_000_000_399_994_000_000 and st.sync_at(N)[1] == R_TOK0 - W(FX["logs"][5]["data"], 3) and st.pull_block == N + 424


@test
def settings_bounds():
    """a wrong setting stops the start naming it; every amount an exact integer of its unit"""
    bad = {"BASE_V2_STAKE_ETH": "abc", "BASE_V2_BUY_SLIP": "0.9", "BASE_V2_DRY_RUN": "2", "BASE_V2_TIER_BAND": "2.3,1.3", "BASE_V2_TIER_BAND": "1.3",
           "BASE_V2_TIER_EXCLUDE": "x", "BASE_V2_PROBE": "0x12", "BASE_V2_RELAY": "0x12", "BASE_V2_PRIO_GWEI": "2", "BASE_V2_STAKE_CAP_ETH": "0.0000000000000000001",
           "BASE_V2_SEND_URLS": "ftp://x.org", "BASE_V2_HARD_BLOCK": "201", "BASE_V2_SELL_RESEND_BLOCK": "181", "BASE_V2_SELL_SEND_BLOCK": "178", "BASE_V2_SCHEDULE_MIN": "100",
           "BASE_V2_TOKEN_CODE_SIZES": "3553,abc", "BASE_V2_CREATE_SELECTOR": "f305d7", "BASE_V2_CREATOR_NONCE": "1.5", "BASE_V2_MAX_POSITIONS": "0", "BASE_V2_WS_URL": "https://x.org",
           "BASE_V2_MIN_SUPPLY_IN_POOL": "1.01", "BASE_V2_EXIT_MIN": "0.4", "BASE_V2_WATCH_BLOCKS": "100", "BASE_V2_LAND_MAX": "11", "BASE_V2_MAX_FEE_GWEI": "0.01",
           "BASE_V2_ARCHIVE_URL": "wss://x.org/", "BASE_V2_BACKRUN": "yes", "BASE_V2_WALLET": "0xzz", "BASE_V2_OUTSIDER_MIN_ETH": "2"}
    for k, v in bad.items():
        os.environ.update(BASE_ENV); os.environ[k] = v
        try:
            E.settings()
        except SystemExit as e:
            assert k in str(e) or (k == "BASE_V2_MAX_FEE_GWEI" and "BASE_V2_MAX_FEE_GWEI" in str(e)) or (k in ("BASE_V2_SELL_SEND_BLOCK", "BASE_V2_SELL_RESEND_BLOCK") and "SELL_RESEND_BLOCK" in str(e)), (k, str(e))
        else:
            raise AssertionError(f"{k}={v} was accepted")
        os.environ.pop(k)
    s = E.settings()
    assert s.STAKE_ETH_WEI == s.STAKE_CAP_WEI == 2 * 10 ** 16 and s.PRIO_WEI == 3 * 10 ** 7 and s.MAX_FEE_WEI == 5 * 10 ** 8 and s.BUY_SLIP_PPM == 30_000 and s.SELL_SLIP_PPM == 50_000
    assert (s.BAND_LO_WEI, s.BAND_HI_WEI, s.TIER_LABEL) == (13 * 10 ** 17, 23 * 10 ** 17, "1.3-2.3") and s.EXCLUDE_MILLI == {1200} and s.PROBE == {PROBE} and s.TOKEN_CODE_SIZES == {3553}
    assert s.MIN_SUPPLY_PPM == 990_000 and s.EXIT_MIN_PPM == 980_000 and s.TP_PPM == 250_000 and s.SHARE_CAP_PPM == 50_000 and s.PULL_SHARE_PPM == 300_000 and s.DAILY_STOP_WEI == 15 * 10 ** 16
    assert (s.HARD_BLOCK, s.SELL_SEND_BLOCK, s.SELL_RESEND_BLOCK, s.SCHEDULE_MIN, s.REACT_BLOCKS, s.LAND_MAX, s.MAX_POSITIONS, s.MAX_PER_DAY) == (180, 176, 178, 220, 10, 1, 3, 20)
    assert all(isinstance(x, int) for x in (s.STAKE_ETH_WEI, s.PRIO_WEI, s.MARGIN_WEI, s.OUTSIDER_MIN_WEI, s.CREATOR_NONCE)) and s.HALT_FILE == os.path.join(TMP, "HALTED.base_v2")
    os.environ["BASE_V2_TOKEN_CODE_SIZES"] = "0"; assert E.settings().TOKEN_CODE_SIZES == set(); os.environ["BASE_V2_TIER_EXCLUDE"] = ""; assert E.settings().EXCLUDE_MILLI == set()
    os.environ["BASE_V2_READ_ALT_URL"] = "0"; os.environ["BASE_V2_FLASH_URL"] = "0"; s = E.settings(); assert s.READ_ALT_URL == "" and s.FLASH_URL is None
    os.environ.update(BASE_ENV); os.environ["BASE_V2_LOG_PATH"] = os.path.join(TMP, "base.jsonl"); E.S = E.settings()
    try:
        E.start(); raise AssertionError("started on another engine's log")
    except SystemExit as e:
        assert "BASE_V2_LOG_PATH" in str(e) and "base_v2.jsonl" in str(e), str(e)
    os.environ.update(BASE_ENV); E.S = E.settings()


@test
def raw_transactions_and_the_constant_product():
    """decode_tx and tx_sender on every type; CREATE2 from a synthetic creator; the Flashblocks decoder's rejects and bad frames"""
    k = creator_key("decode"); bot = STRANGER.address.lower()
    for legacy in (False, True):
        raw = signed(k, 3, bot, 5, "0x27f7e6ee" + "00" * 32, legacy=legacy); d = E.decode_tx(bytes.fromhex(raw[2:]))
        assert d["to"] == bot and d["value"] == 5 and d["data"][:4] == bytes.fromhex("27f7e6ee") and d["nonce"] == 3 and d["type"] == (0 if legacy else 2) and E.tx_sender(raw) == k.address.lower()
        assert d["prio"] == 10 ** 6 and (d["max_fee"] == 11 * 10 ** 6 or legacy) and d["gas"] == 119_000
    raw = "0x" + bytes(k.sign_transaction({"nonce": 1, "gasPrice": 7, "gas": 21000, "to": E.to_checksum_address(bot), "value": 1, "data": "0x", "accessList": [], "chainId": 8453}).raw_transaction).hex()
    assert E.decode_tx(bytes.fromhex(raw[2:]))["type"] == 1 and E.tx_sender(raw) == k.address.lower()
    assert E.decode_tx(bytes.fromhex("7e" + "c0")) is None and E.decode_tx(b"\x02\xff") is None and E.tx_sender("0x02ff") is None
    tok = E.create_address(k.address.lower()); assert len(tok) == 42 and tok > WETH and E.pair_address(tok) != PAIR and E.create_address(k.address.lower(), 1) != tok
    assert E.buy_data(TOKEN, 5, 6, 7) == "0x1622dbe4" + aword(TOKEN) + word(5) + word(6) + word(7) and E.sell_data(TOKEN, 0, 9)[:10] == "0x6a272462"
    assert cp_out(10 ** 18, 10 ** 18, 10 ** 18) == 997 * 10 ** 18 // 1997 and cp_out(0, 1, 1) == 0 and cp_out(5, 0, 1) == 0
    c = fresh(); E.on_flash(b"not brotli at all"); E.on_flash(brotli.compress(b"{not json"))
    a = events("alarm")
    assert len(a) == 1 and "dropped" in a[0]["what"] and E.state["flash_bad"] == 2, a
    assert E.tier_of(2 * 10 ** 18) == ("1.3-2.3", "tradable", None) and E.tier_of(15 * 10 ** 18) == ("15", "watched", "value outside the band")
    assert E.tier_of(12 * 10 ** 17) == ("1.2", "watched", "excluded tier") and E.tier_of(1_200_400_000_000_000_000) == ("1.2", "watched", "excluded tier")
    assert E.tier_of(13 * 10 ** 17)[1] == E.tier_of(23 * 10 ** 17)[1] == "tradable" and E.tier_of(2_301_000_000_000_000_000) == ("2.3", "watched", "value outside the band")


# ---------------------------------------------------------------- the creation
@test
def creation_confirmed_on_the_fixture():
    """the real 15 ETH pair via PairCreated + the receipt's Mint: one creation line, watched, refused by the band; followed to its Burn: the
    probe and the outsider logged, the fleet never; the pull line; the reaction ends its tier for the day; the pair dropped"""
    st = Stream("15"); c = fresh(st); feed(c, N - 2, N)
    e = wait_ev("creation")[0]
    assert e["via"] == "logs" and e["cls"] == "watched" and e["tier"] == "15" and e["value_eth"] == 15.0 and e["block"] == N and e["tx"] == CREATION_HASH and e["pair"] == PAIR, e
    assert e["creator"] == CREATOR and e["nonce"] == 2 and e["token"] == TOKEN and e["weth_is0"] and e["r_eth_wei"] == 15 * 10 ** 18 and e["r_tok"] == R_TOK0 and e["supply_share"] is None
    assert e["tx_type"] == 2 and e["prio_gwei"] == 0.006 and e["max_fee_gwei"] == 0.006 and e["gas"] == 2_791_667 and e["seen_ms"] == 0.0
    s = events("skip")
    assert len(s) == 1 and s[0]["why"] == "value outside the band" and s[0]["value_eth"] == 15.0 and s[0]["pair"] == PAIR and s[0]["tier"] == "15", s
    assert E.pairs[PAIR]["status"] == "watched" and E.state["watched"] == 1 and E.state["tradable"] == 0 and not events("arm") and not events("guard")
    assert ("rpc.example.org", "eth_getTransactionByHash") in c.calls and ("rpc.example.org", "eth_getTransactionReceipt") in c.calls
    assert not any(m in ("eth_getCode", "eth_call") for _, m in c.calls)        # a watched pair costs no guard read
    feed(c, N + 1, N + 430)
    time.sleep(0.05)
    o = events("outsider_buy")
    assert [(x["block"] - N, x["who"], x["action"], x["ours"], x["pending"]) for x in o] == [(0, "probe", "none", False, False), (419, "outsider", "none", False, False)], o
    otx = next(t for t in FX["txs"].values() if t["input"][:10] == "0xaff9ec28" and int(t["value"], 16) > 0)      # the outsider's buy through an aggregator
    assert o[0]["sender"] == PROBE and o[0]["to"] != PROBE and o[0]["value_eth"] == 2999955000000 / 1e18 and o[1]["sender"] == otx["from"].lower() and o[1]["tier"] == "15"
    assert o[1]["to"] == otx["to"].lower() != o[1]["sender"] and o[1]["value_eth"] == int(otx["value"], 16) / 1e18 and o[1]["tx"] == next(h for h, t in FX["txs"].items() if t is otx)
    p = events("pull")
    assert len(p) == 1 and p[0]["block"] == N + 424 and p[0]["since_creation"] == 424 and p[0]["since_last_buy"] == 5 and p[0]["since_outsider"] == 5 and p[0]["reaction"] and p[0]["before"] == "after", p
    assert not p[0]["ours"] and not p[0]["pending"] and p[0]["via"] == "logs" and p[0]["eth_out_wei"] == words([l for l in FX["logs"] if l["topics"][0] == T["Burn"]][0]["data"])[0] and p[0]["tier"] == "15"
    t = events("stop")
    assert len(t) == 1 and t[0]["what"] == "tier" and t[0]["tier"] == "15" and "a reaction" in t[0]["reason"] and "5 blocks after an outsider" in t[0]["reason"], t
    assert E.state["tiers_ended"] == {"15": "2026-10-20"} and PAIR not in E.pairs and not events("would_fire") and not events("sell_sent") and not events("halt")


@test
def creation_pending_in_a_flashblock():
    """the creation seen pending: the sender recovered from the raw transaction, its nonce 2, the token its CREATE address, the pair by
    CREATE2; the code and supply checks run before N seals; PairCreated seals it with no transaction read; the fire aims at N + 1"""
    k = creator_key("flash"); st = Stream("2.0", creator=k); c = fresh(st)
    feed(c, N - 2, N - 1)
    flash(N, [], index=0); flash(N, ["0x7e" + "00" * 10, st.creation_raw], index=2)
    e = wait_ev("creation")[0]
    assert e["via"] == "flash" and e["cls"] == "tradable" and e["tier"] == "1.3-2.3" and e["creator"] == k.address.lower() and e["nonce"] == 2 and e["block"] == N, e
    assert e["token"] == E.create_address(k.address.lower()) == st.token and e["pair"] == E.pair_address(st.token) == st.pair and e["tx"] == st.creation_hash and e["weth_is0"]
    assert e["r_eth_wei"] == 2 * 10 ** 18 and e["r_tok"] == inword(st.creation_tx["input"], 1) == R_TOK0 and e["value_eth"] == 2.0 and e["seen_ms"] == -2000.0
    assert e["tx_type"] == 2 and e["prio_gwei"] == 0.006 and e["gas"] == 2_791_667 and E.state["flash_block"] == N and E.state["flash"]
    t0 = time.time()
    while time.time() - t0 < 2 and ("arch.example.org", "eth_call") not in c.calls:
        time.sleep(0.005)
    assert ("arch.example.org", "eth_getCode") in c.calls and E.pairs[st.pair]["code_size"] == 3553 and E.pairs[st.pair]["supply_share"] == 1.0 and not E.pairs[st.pair]["sealed"]
    assert not c.guard_calls and E.pairs[st.pair]["status"] == "arming"       # the exit test waits for block N
    feed(c, N, N)
    f = wait_ev("would_fire")[0]
    assert f["via"] == "flash" and f["aim"] == N + 1 and f["head"] == N and f["creation"] == N and E.pairs[st.pair]["sealed"] and E.pairs[st.pair]["creation_tx"] == st.creation_hash, f
    assert ("rpc.example.org", "eth_getTransactionByHash") not in c.calls[:c.calls.index(("arch.example.org", "eth_call")) + 1] and len(events("creation")) == 1
    assert c.guard_calls and c.guard_calls[0][1] == hex(N) and c.guard_calls[0][3][E.HARNESS_AT] == {"code": E.HARNESS_CODE, "balance": hex(2 * f["stake_wei"])}
    g = events("guard")[0]; assert g["verdict"] == "ok" and g["src"] == "arch.example.org" and g["code_size"] == 3553 and g["supply_share"] == 1.0 and g["block"] == N
    assert "k3y" not in open(LOG).read()


@test
def creation_shape_refused():
    """the creator's shape: the wrong selector, not the router, the wrong nonce, a token that is not the sender's CREATE address: a skip
    naming it, via the logs (the pair dropped) and via a Flashblock (pending)"""
    for change, why in [(lambda t: t.update(input="0xdeadbeef" + t["input"][10:]), "selector"), (lambda t: t.update(to="0x" + "ab" * 20), "not the router"),
                        (lambda t: t.update(nonce="0x3"), "creator nonce"), (lambda t: t.update({"from": "0x" + "cd" * 20}), "create address")]:
        st = Stream("2.0"); change(st.creation_tx); c = fresh(st); feed(c, N - 2, N)
        s = wait_ev("skip")[0]
        assert s["why"] == why and s["via"] == "logs" and not s.get("pending") and s["pair"] == PAIR and s["token"] == TOKEN and s["value_eth"] == 2.0, (why, s)
        assert s["nonce"] == (3 if why == "creator nonce" else 2) and s["creator"] == st.creation_tx["from"].lower() and s["selector"] == st.creation_tx["input"][2:10]
        time.sleep(0.02)
        assert PAIR not in E.pairs and not events("creation") and not events("arm"), why
    k = creator_key("shape")
    for st, why in [(Stream("2.0", creator=k, nonce=3), "creator nonce"), (Stream("2.0", creator=k, create_token=TOKEN), "create address")]:
        c = fresh(st); feed(c, N - 2, N - 1); flash(N, [st.creation_raw], index=1)
        s = events("skip")
        assert len(s) == 1 and s[0]["why"] == why and s[0]["pending"] and s[0]["via"] == "flash" and s[0]["creator"] == k.address.lower() and s[0]["value_eth"] == 2.0, (why, s)
        assert s[0]["nonce"] == (3 if why == "creator nonce" else 2) and not E.pairs and not events("creation")
    c = fresh(Stream("2.0", creator=k)); feed(c, N - 2, N - 1)
    flash(N, [signed(k, 2, ROUTER, 0, "0x" + CTX["input"][2:])], index=1)       # no value: not a creation
    assert not events() and not E.pairs


@test
def tier_gate():
    """15.0 and 1.2 refused and logged as watched with the right why; 2.0 armed and fired; the band's edges; the exclusion wins over the band"""
    for value, tier, why in (("15", "15", "value outside the band"), ("1.2", "1.2", "excluded tier"), ("1.2003", "1.2", "excluded tier"), ("2.301", "2.3", "value outside the band")):
        c = fresh(Stream(value)); feed(c, N - 2, N)
        e = wait_ev("creation")[0]; s = wait_ev("skip")[0]
        assert e["cls"] == "watched" and e["tier"] == tier and s["why"] == why and s["tier"] == tier and abs(s["value_eth"] - float(value)) < 1e-9, (value, e, s)
        assert E.pairs[PAIR]["status"] == "watched" and not events("arm") and not events("guard") and not events("would_fire")
    for value in ("2.0", "1.3", "2.3"):
        c = fresh(Stream(value)); f = fired(c)[0]
        e = events("creation")[0]; a = events("arm")[0]
        assert e["cls"] == "tradable" and e["tier"] == "1.3-2.3" and f["ev"] == "would_fire" and f["tier"] == "1.3-2.3" and not events("skip"), (value, f)
        assert a["block"] == N and a["r_eth_wei"] == c.reserves_at(PAIR, N)[0] and a["r_tok"] == c.reserves_at(PAIR, N)[1] and a["followed"] == 1 and a["tier"] == "1.3-2.3"
        assert E.state["tradable"] == 1 and E.state["creations"] == 1
    c = fresh(Stream("1.2"), BASE_V2_TIER_BAND="1.1,2.3"); feed(c, N - 2, N)
    assert wait_ev("skip")[0]["why"] == "excluded tier"
    c = fresh(Stream("1.2"), BASE_V2_TIER_BAND="1.1,2.3", BASE_V2_TIER_EXCLUDE=""); f = fired(c)[0]
    assert f["ev"] == "would_fire" and f["tier"] == "1.1-2.3" and f["stake_wei"] == 2 * 10 ** 16


if __name__ == "__main__":
    t0 = time.time(); n = 0
    only = sys.argv[1:]
    for fn in TESTS:
        if only and fn.__name__ not in only:
            continue
        fn(); n += 1
        print("ok", fn.__name__, flush=True)
    print(f"{n} tests passed in {time.time() - t0:.1f} s")
