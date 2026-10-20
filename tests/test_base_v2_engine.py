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
threading.Thread(target=E.trader, daemon=True).start(); BASE_THREADS = threading.active_count()   # the trader: the only signer, for the live cases


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
        if (h, "roundTrip") in self.fail:
            raise RuntimeError(f"stub: {E.S.ARCHIVE_URL if h == 'arch.example.org' else E.S.READ_ALT_URL} is down")
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
            self.mined.add(h); tx = E.decode_tx(bytes.fromhex(raw[2:])); sel = tx["data"][:4].hex(); d = "0x" + tx["data"][4:].hex(); st = self.by_token.get(E.A(d, 0))
            if st is None:
                continue                                                       # another case's transaction (a lingering settlement): not this chain's
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


def quiesce(timeout=12.0):
    """the engine's worker threads of the last case (a guard's second endpoint, a sender's read, a settlement) done before the next one
    rebinds the stub: a late answer must not land in the next case's records"""
    t0 = time.time()
    while threading.active_count() > BASE_THREADS and time.time() - t0 < timeout:
        time.sleep(0.005)


def fresh(*streams, dry=True, **env):
    """a new engine state with these settings, a stubbed chain over the streams (the 2.0 ETH replay by default) and an empty log; the
    websocket connected, its first head to come at N - 2"""
    quiesce()
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


def hard_exits(c, n=1):
    """live: the blocks to N + SELL_SEND_BLOCK, the n hard sells awaited (the trader signs off the feed thread), mined at N + 177, settled"""
    feed(c, E.state["head"] + 1, N + 176); wait_ev("sell_sent", n); feed(c, N + 177, N + 178)
    return wait_ev("trade_done", n)


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
    o = wait_ev("outsider_buy", 2)
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


# ---------------------------------------------------------------- the guard
@test
def guard_verdicts():
    """the exit test's five verdicts: ok fires; taxed, honeypot (the sell reverts, the buy alone works), buy_tax and unreadable are each one
    guard line and a skip naming the verdict; nothing retries a failed guard"""
    want = {"ok": "would_fire", "taxed": "skip", "honeypot": "skip", "buy_tax": "skip", "unreadable": "skip"}
    for verdict, ev in want.items():
        st = Stream("2.0"); c = fresh(st); c.verdict = verdict; f = fired(c)[0]
        g = events("guard")[0]; re_, rt_ = c.reserves_at(PAIR, N); expect = cp_out(2 * 10 ** 16, re_, rt_)
        assert f["ev"] == ev and g["verdict"] == verdict and g["expect_tokens"] == expect and g["stake_wei"] == 2 * 10 ** 16 and g["block"] == N and g["ms"] is not None, (verdict, f, g)
        assert len(events("guard")) == 1 and g["code_size"] == 3553 and g["supply_share"] == 1.0 and "k3y" not in open(LOG).read()
        if verdict == "ok":
            back = cp_out(expect, rt_ - expect, re_ + 2 * 10 ** 16)
            assert g["tokens"] == expect and g["eth_back_wei"] == g["quote_wei"] == back and g["ratio"] == 1.0 and g["src"] == "arch.example.org" and g["error"] is None
            assert len(c.guard_calls) == 2 and {x[0] for x in c.guard_calls} == {"arch.example.org", "alt.example.org"} and all(x[2] == 1 for x in c.guard_calls)
            continue
        assert f["why"] == "guard" and f["verdict"] == verdict and E.pairs[PAIR]["status"] == "watched" and events("arm")
        if verdict == "taxed":
            assert g["ratio"] == 0.9 and g["tokens"] == expect and g["eth_back_wei"] * 10 == g["quote_wei"] * 9 and f["ratio"] == 0.9
        elif verdict == "buy_tax":
            assert g["tokens"] == expect * 95 // 100 and g["ratio"] == 1.0
        elif verdict == "honeypot":
            assert g["tokens"] == expect and g["eth_back_wei"] is None and "revert" in g["error"] and [x[2] for x in c.guard_calls].count(0) == 1   # the buy-only probe once
        else:
            assert g["tokens"] is None and g["src"] is None and "header not found" in g["error"] and g["ms"] >= 300 and "arch.example.org" not in g["error"]
        n_calls = len(c.guard_calls); feed(c, N + 1, N + 3)
        assert len(events("guard")) == 1 and not events("would_fire") and len(c.guard_calls) == n_calls and (verdict == "unreadable" or n_calls <= 3)
    c = fresh(Stream("2.0"), BASE_V2_EXIT_MIN="0.9"); c.verdict = "taxed"; f = fired(c)[0]
    assert f["ev"] == "would_fire" and events("guard")[0]["verdict"] == "ok" and events("guard")[0]["ratio"] == 0.9     # 0.9 passes a 0.9 floor
    c = fresh(Stream("2.0"), BASE_V2_READ_ALT_URL="0"); c.fail.add(("arch.example.org", "roundTrip")); f = fired(c)[0]
    g = events("guard")[0]                                                     # the exit test's own read failing: unreadable, the host named, never the key
    assert f["why"] == "guard" and g["verdict"] == "unreadable" and "arch.example.org is down" in g["error"] and "k3y" not in open(LOG).read() and g["src"] is None, g
    c = fresh(Stream("2.0"), BASE_V2_READ_ALT_URL="0"); c.fail.add(("arch.example.org", "eth_call")); f = fired(c)[0]
    assert f["why"] == "guard" and f["verdict"] == "unreadable" and "totalSupply" not in f["error"] and "arch.example.org is down" in f["error"] and "k3y" not in open(LOG).read(), f
    assert not events("guard") and not events("arm")                           # the supply read failed: refused before the exit test's verdict


@test
def guard_code_size_and_supply():
    """eth_getCode's size and totalSupply against the pool's token side, before N seals when the creation came pending; the real pair's
    98.2% refused at 0.99, armed at 0.98; 0 = any size"""
    c = fresh(Stream("2.0")); c.code_size = 3000; f = fired(c)[0]
    assert f["ev"] == "skip" and f["why"] == "code size" and f["code_size"] == 3000 and "supply_share" not in f and not events("arm") and not events("would_fire"), f
    assert ("arch.example.org", "eth_getCode") in c.calls and not any(m == "eth_call" and h == "arch.example.org" and "totalSupply" in str(c.calls) for h, m in c.calls[:1])
    c = fresh(Stream("2.0")); c.supply = SUPPLY; f = fired(c)[0]
    assert f["ev"] == "skip" and f["why"] == "supply share" and f["supply_share"] == 0.982142 and f["code_size"] == 3553 and events("creation")[0]["cls"] == "tradable", f
    c = fresh(Stream("2.0"), BASE_V2_MIN_SUPPLY_IN_POOL="0.98"); c.supply = SUPPLY; f = fired(c)[0]
    assert f["ev"] == "would_fire" and events("guard")[0]["supply_share"] == 0.982142
    c = fresh(Stream("2.0"), BASE_V2_TOKEN_CODE_SIZES="0"); c.code_size = 999; f = fired(c)[0]
    assert f["ev"] == "would_fire" and events("guard")[0]["code_size"] == 999
    c = fresh(Stream("2.0"), BASE_V2_TOKEN_CODE_SIZES="3553, 3600"); c.code_size = 3600; assert fired(c)[0]["ev"] == "would_fire"
    k = creator_key("pend"); st = Stream("2.0", creator=k); c = fresh(st); c.code_size = 1; feed(c, N - 2, N - 1)
    flash(N, [st.creation_raw], index=1)                                      # pending: refused before N seals, no exit test
    s = wait_ev("skip")[0]; got = (s["why"], s["code_size"], E.state["head"] - N, c.guard_calls, E.pairs[st.pair]["status"])
    assert got == ("code size", 1, -1, [], "watched"), got
    c = fresh(Stream("2.0")); c.fail.add("eth_getCode"); f = fired(c)[0]
    assert f["why"] == "guard" and f["verdict"] == "unreadable" and "alt.example.org is down" in f["error"] and "k3y" not in open(LOG).read(), f


@test
def arm_reads_the_creation_block():
    """the arm's eth_getLogs of block N: the probe's swap passes (its sender read: the Swap's `to` is not the probe), anyone else's in the
    creation block is an outsider before our fire"""
    c = fresh(Stream("2.0")); f = fired(c)[0]
    o = wait_ev("outsider_buy")[0]
    assert f["ev"] == "would_fire" and o["block"] == N and o["who"] == "probe" and o["sender"] == PROBE and o["action"] == "none" and not o["ours"] and o["via"] == "logs", (f, o)
    assert c.ranges and c.ranges[0] == (N, N) and c.calls.count(("rpc.example.org", "eth_getTransactionByHash")) <= 3 and E.pairs[PAIR]["buys"][0]["who"] == "probe", (c.ranges, c.calls)
    st = Stream("2.0"); c = fresh(st); inject_buy(c, st, N, 10 ** 15, STRANGER.address.lower()); f = fired(c)[0]
    assert f["ev"] == "skip" and f["why"] == "outsider before our fire" and f["block"] == N and not events("would_fire"), f
    o = wait_ev("outsider_buy", 2)
    assert {(x["who"], x["action"]) for x in o} == {("probe", "none"), ("outsider", "none")} and E.pairs[PAIR]["status"] == "watched", o
    st = Stream("2.0"); c = fresh(st); inject_buy(c, st, N, 10 ** 15, FLEET[3]); f = fired(c)[0]        # a roster wallet in the creation block: not an outsider
    assert f["ev"] == "would_fire" and E.pairs[PAIR]["fleet_first"] == N and len(wait_ev("outsider_buy")) == 1, (f, events("outsider_buy"))
    st = Stream("2.0"); c = fresh(st); inject_buy(c, st, N, 10 ** 15, "0x" + "ab" * 20, sender=CREATOR); f = fired(c)[0]   # the creator's own buy: not an outsider
    assert f["ev"] == "would_fire", f
    assert sorted(x["who"] for x in wait_ev("outsider_buy", 2)) == ["creator", "probe"] and all(x["action"] == "none" and x["tier"] == "1.3-2.3" for x in events("outsider_buy")), events("outsider_buy")


@test
def late_or_pulled_before_the_fire():
    """a slow guard: the head at N + LAND_MAX refuses the fire (late); the creator's pull seen pending before the fire skips the pair;
    an outsider's pending buy before the fire too"""
    c = fresh(Stream("2.0")); c.exit_lag = 0.25; feed(c, N - 2, N)
    wait_ev("arm"); feed(c, N + 1, N + 1)                                       # the exit test still running: the head reaches N + LAND_MAX
    s = wait_ev("skip")[0]
    assert s["why"] == "late" and s["block"] == N and s["head"] == N + 1 and not events("would_fire"), s
    g = wait_ev("guard")[0]; time.sleep(0.05)
    assert g["verdict"] == "ok" and not events("would_fire") and E.pairs[PAIR]["status"] == "watched"      # the verdict of a skipped pair is discarded
    c = fresh(Stream("2.0"), BASE_V2_LAND_MAX="3"); c.exit_lag = 0.25; feed(c, N - 2, N + 1)
    f = wait_ev("would_fire")[0]; assert f["head"] == N + 1 and f["aim"] == N + 2 and events("arm")[0]["block"] == N
    st = Stream("2.0", creator=creator_key("pull")); c = fresh(st); c.exit_lag = 0.25; feed(c, N - 2, N)
    wait_ev("creation"); flash(N + 1, [signed(st.key, 4, ROUTER, 0, "0x02751cec" + aword(st.token) + word(1) + word(0) + word(0) + aword(st.creator) + word(ts(N) + 60))], index=1)
    p = events("pull")[0]
    assert p["pending"] and p["before"] == "fire" and p["via"] == "flash" and p["block"] == N + 1 and not p["ours"] and p["since_creation"] == 1, p
    s = wait_ev("skip")[0]
    assert s["why"] == "pulled before our fire" and s["pending"] and s["block"] == N + 1 and not events("would_fire")
    wait_ev("guard"); time.sleep(0.05); assert not events("would_fire") and len(events("skip")) == 1
    st = Stream("2.0"); c = fresh(st); c.exit_lag = 0.25; feed(c, N - 2, N)
    wait_ev("creation"); flash(N + 1, [signed(STRANGER, 9, ROUTER, 10 ** 15, "0x7ff36ab5" + word(0) + word(128) + aword(STRANGER.address) + word(ts(N) + 60) + word(2) + aword(WETH) + aword(TOKEN))], index=1)
    o = events("outsider_buy", pending=True)[0]
    assert o["who"] == "outsider" and o["sender"] == STRANGER.address.lower() and o["action"] == "skip" and o["value_eth"] == 0.001 and o["via"] == "flash", o
    s = wait_ev("skip")[0]
    assert s["why"] == "outsider before our fire" and s["block"] == N + 1 and not events("would_fire")


# ---------------------------------------------------------------- the dry run
@test
def dry_fire_and_hard_exit():
    """would_fire aimed at N + 1 with minOut = (1 - BUY_SLIP) x the constant-product output on the Mint's reserves; the dry fill priced at the
    end of N + 1 behind the creation block's swaps; the hard sell at N + SELL_SEND_BLOCK priced at the next block; the fleet behind us"""
    st = Stream("2.0"); c = fresh(st); f = fired(c)[0]
    stake = 2 * 10 ** 16; expect = cp_out(stake, 2 * 10 ** 18, R_TOK0); min_out = expect * 970_000 // 10 ** 6
    assert f["ev"] == "would_fire" and f["dry"] and f["aim"] == N + 1 and f["head"] == N and f["creation"] == N and f["stake_wei"] == stake and f["min_out"] == min_out, f
    assert f["expect_tokens"] == expect and f["nonce"] is None and f["prio_gwei"] == 0.03 and f["max_fee_gwei"] == 0.04 and f["via"] == "logs" and f["positions"] == 1
    assert 0 <= f["ready_ms"] < 1500 and f["tier"] == "1.3-2.3" and f["token"] == TOKEN and E.state["trades_today"] == 1 and E.pairs[PAIR]["status"] == "fired"
    pos = E.positions[PAIR]; assert pos["D"] == N + 1 and pos["tokens"] is None and pos["dry"] and not c.sent
    feed(c, N + 1, N + 2)
    tokens = cp_out(stake, *c.reserves_at(PAIR, N + 1))                      # the probe's swap ahead of us
    assert pos["tokens"] == tokens and tokens != expect and tokens >= min_out and pos["buy_block"] == N + 1 and pos["eth_in"] == stake and not pos["sell_sent"]
    feed(c, N + 3, N + 175)
    assert not events("sell_sent") and pos["peak"] > 0.05 and E.positions[PAIR] is pos
    feed(c, N + 176, N + 176)
    s = events("sell_sent")
    assert len(s) == 1 and s[0]["dry"] and s[0]["reason"] == "hard" and s[0]["block_seen"] == N + 176 and s[0]["priced_at_block"] == N + 177 and s[0]["via"] == "head" and s[0]["hash"] is None, s
    assert "N + 176 reached" in s[0]["why"] and not events("trade_done")
    feed(c, N + 177, N + 178)
    t = wait_ev("trade_done")[0]; eth_out = dry_value(c, st, tokens, stake, N + 177); gas = 250_000 * (5_000_000 + 30_000_000) + 4_200_000_000
    assert t["exit"] == "hard" and t["dry"] and not t["live"] and t["buy_block"] == N + 1 and t["sell_block"] == N + 177 and t["eth_in_wei"] == stake and t["tokens"] == tokens, t
    assert t["eth_out_wei"] == eth_out and t["gas_wei"] == gas and t["l1_fee_wei"] == 4_200_000_000 and t["net_wei"] == eth_out - stake - gas and t["ret"] == round((eth_out - stake - gas) / stake, 6)
    assert 0.05 < t["ret"] < 0.08 and t["usd"] == round(t["net_wei"] / 1e18 * 2570, 4) and t["pulled_at"] is None and t["outsider_at"] is None and t["fleet_first_buy"] == N + 2
    fleet_eth = sum(W(l["data"], 0) for l in st.logs if l["topics"][0] == T["Swap"] and N + 1 <= blk(l) <= N + 178 and W(l["data"], 0) > 0)
    assert t["fleet_eth"] == round(fleet_eth / 1e18, 6) and t["peak_ret"] == round(pos["peak"], 6) and t["trades_today"] == 1 and t["pnl_today_eth"] == round(t["net_wei"] / 1e18, 6)
    assert t["loss_streak"] == 0 and t["stake_wei"] == stake and t["min_out"] == min_out and t["expect_tokens"] == expect and PAIR not in E.positions and E.pairs[PAIR]["status"] == "traded"
    assert E.state["trades_done"] == 1 and E.state["pnl_today_wei"] == t["net_wei"] and not events("halt") and not events("stop")
    c = fresh(Stream("2.0"), BASE_V2_STAKE_ETH="0.5", BASE_V2_STAKE_CAP_ETH="0.5"); f = fired(c)[0]
    assert f["stake_wei"] == 10 ** 17 and f["expect_tokens"] == cp_out(10 ** 17, 2 * 10 ** 18, R_TOK0)       # the share cap: 5% of the ETH reserve
    c = fresh(Stream("2.0"), BASE_V2_STAKE_ETH="0.05", BASE_V2_STAKE_CAP_ETH="0.03"); assert fired(c)[0]["stake_wei"] == 3 * 10 ** 16


@test
def dry_buy_reverts_under_its_min_out():
    """the dry fill is priced at the end of N + 1: a buy ahead of us there beyond the slip reverts the dry buy"""
    st = Stream("2.0"); c = fresh(st); inject_buy(c, st, N + 1, 10 ** 17, FLEET[2]); fired(c)
    feed(c, N + 1, N + 2)
    t = wait_ev("trade_done")[0]
    assert t["exit"] == "buy_reverted" and t["eth_in_wei"] == 0 and t["eth_out_wei"] == 0 and t["tokens"] is None and t["buy_block"] is None and "under the buy's minOut" in t["why"], t
    assert t["gas_wei"] == (250_000 * 35_000_000 + 4_200_000_000) // 2 and t["ret"] < 0 and PAIR not in E.positions and E.state["trades_done"] == 1


@test
def dry_take_profit():
    st = Stream("2.0"); c = fresh(st); fired(c); feed(c, N + 1, N + 19); pos = E.positions[PAIR]
    inject_buy(c, st, N + 20, 3 * 10 ** 17, FLEET[4]); feed(c, N + 20, N + 20)        # a 0.3 ETH buy: +30% and more
    s = events("sell_sent")
    assert len(s) == 1 and s[0]["reason"] == "take_profit" and s[0]["priced_at_block"] == N + 21 and s[0]["via"] == "logs" and "BASE_V2_TAKE_PROFIT" in s[0]["why"], s
    feed(c, N + 21, N + 22)
    t = wait_ev("trade_done")[0]; eth_out = dry_value(c, st, pos["tokens"], pos["stake"], N + 21)
    assert t["exit"] == "take_profit" and t["sell_block"] == N + 21 and t["eth_out_wei"] == eth_out and t["ret"] > 0.25 and t["fleet_eth"] >= 0.3 and t["outsider_at"] is None, t
    assert len(wait_ev("outsider_buy")) == 1                                  # the probe only: the fleet's buys are never logged


@test
def dry_outsider_sells_at_once():
    """an outsider's confirmed buy behind ours: the instant sell, priced at the next block; pending in a Flashblock: before the block seals"""
    st = Stream("2.0"); c = fresh(st); fired(c); feed(c, N + 1, N + 29); pos = E.positions[PAIR]
    sw = inject_buy(c, st, N + 30, 10 ** 15, STRANGER.address.lower()); feed(c, N + 30, N + 30)
    s = events("sell_sent"); o = wait_ev("outsider_buy", block=N + 30)[0]
    assert len(s) == 1 and s[0]["reason"] == "outsider" and s[0]["priced_at_block"] == N + 31 and "confirmed at" in s[0]["why"], s
    assert o["who"] == "outsider" and o["action"] == "sell" and o["ours"] and o["sender"] == STRANGER.address.lower() and o["tx"] == sw["transactionHash"] and not o["pending"], o
    feed(c, N + 31, N + 32)
    t = wait_ev("trade_done")[0]
    assert t["exit"] == "outsider" and t["outsider_at"] == N + 30 and t["sell_block"] == N + 31 and t["eth_out_wei"] == dry_value(c, st, pos["tokens"], pos["stake"], N + 31), t
    st = Stream("2.0"); c = fresh(st); fired(c); feed(c, N + 1, N + 4)
    raw = signed(STRANGER, 9, ROUTER, 2 * 10 ** 15, "0x7ff36ab5" + word(0) + word(128) + aword(STRANGER.address) + word(ts(N) + 60) + word(2) + aword(WETH) + aword(TOKEN))
    flash(N + 5, [raw], index=2)
    s = events("sell_sent"); o = events("outsider_buy", pending=True)[0]
    assert len(s) == 1 and s[0]["reason"] == "outsider" and s[0]["via"] == "flash" and s[0]["priced_at_block"] == N + 5 and s[0]["block_seen"] == N + 5 and "seen pending" in s[0]["why"], s
    assert o["who"] == "outsider" and o["action"] == "sell" and o["ours"] and o["sender"] == STRANGER.address.lower() and o["value_eth"] == 0.002 and o["to"] == ROUTER, o
    inject_buy(c, st, N + 5, 2 * 10 ** 15, STRANGER.address.lower(), tx=hash_of(raw)); feed(c, N + 5, N + 6)
    t = wait_ev("trade_done")[0]
    assert t["exit"] == "outsider" and len(events("sell_sent")) == 1 and len(events("outsider_buy")) == 2 and t["outsider_at"] == N + 5 and t["sell_block"] == N + 5, t
    c = fresh(Stream("2.0"), BASE_V2_OUTSIDER_MIN_ETH="0.01"); st = next(iter(c.streams.values())); fired(c); feed(c, N + 1, N + 9)
    inject_buy(c, st, N + 10, 10 ** 15, STRANGER.address.lower()); feed(c, N + 10, N + 11)
    o = wait_ev("outsider_buy", block=N + 10)[0]
    assert o["action"] == "none" and not events("sell_sent")                  # under the floor: logged, no sell


@test
def probe_creator_and_fleet_never_trigger():
    """after our buy: the probe's, the creator's and a roster wallet's buys, confirmed and pending, never sell; the probe and the creator are
    logged, the fleet never"""
    c = fresh(Stream("2.0"), BASE_V2_PROBE=PROBE + "," + PROBE_KEY.address); st = next(iter(c.streams.values())); fired(c); feed(c, N + 1, N + 4)
    inject_buy(c, st, N + 5, 3 * 10 ** 12, PROBE, li=900, sel="0xb6f9de95"); inject_buy(c, st, N + 5, 9 * 10 ** 13, CREATOR, li=910)   # the creator's self-buy at +5
    inject_buy(c, st, N + 5, 10 ** 16, FLEET[5], li=920)
    feed(c, N + 5, N + 5)
    time.sleep(0.05)
    o = events("outsider_buy", block=N + 5)
    assert sorted(x["who"] for x in o) == ["creator", "probe"] and all(x["action"] == "none" and x["ours"] for x in o) and not events("sell_sent"), o
    assert E.pairs[PAIR]["fleet_first"] == N + 2 and len([b for b in E.pairs[PAIR]["buys"] if b["who"] == "fleet"]) == 2
    buy = lambda key, nonce, eth: signed(key, nonce, ROUTER, eth, "0x7ff36ab5" + word(0) + word(128) + aword(key.address) + word(ts(N) + 60) + word(2) + aword(WETH) + aword(TOKEN))
    flash(N + 6, [buy(PROBE_KEY, 1, 3 * 10 ** 12), buy(FLEET_KEY, 2, 10 ** 16)], index=1)
    o = events("outsider_buy", pending=True)
    assert [x["who"] for x in o] == ["probe"] and o[0]["action"] == "none" and not events("sell_sent"), o
    flash(N + 6, [buy(STRANGER, 3, 10 ** 15)], index=2)
    assert len(events("sell_sent")) == 1 and events("outsider_buy", pending=True)[-1]["who"] == "outsider"
    st = Stream("2.0", creator=creator_key("self-buy")); c = fresh(st); fired(c); feed(c, N + 1, N + 4)
    flash(N + 5, [signed(st.key, 4, ROUTER, 9 * 10 ** 13, "0x7ff36ab5" + word(0) + word(128) + aword(st.creator) + word(ts(N) + 60) + word(2) + aword(WETH) + aword(st.token))], index=1)
    o = events("outsider_buy", pending=True)
    assert len(o) == 1 and o[0]["who"] == "creator" and o[0]["action"] == "none" and not events("sell_sent"), o
    # the design's rule on the confirmed feed: a buy whose Swap `to` is none of the roster, the probe, the creator, our wallet or the relay is an
    # outsider at once (an aggregator's buy shows the aggregator as `to`), the sender read only for the line: the sell goes, the line says who sent it
    st = Stream("2.0"); c = fresh(st); fired(c); feed(c, N + 1, N + 4)
    inject_buy(c, st, N + 5, 3 * 10 ** 12, "0x6aa98924" + "00" * 16, sender=PROBE, sel="0xb6f9de95"); feed(c, N + 5, N + 5)
    o = wait_ev("outsider_buy", block=N + 5)[0]
    assert o["who"] == "probe" and o["action"] == "sell" and o["sender"] == PROBE and events("sell_sent")[0]["reason"] == "outsider", o


@test
def dry_fleet_sell_and_the_dump_rule():
    """the fleet's first sell on our pair (its sender read: a router sell shows the router as `to`) is the exit; a sell taking PULL_SHARE
    of the ETH reserve on a pair of the tier ends the tier for the day"""
    st = Stream("2.0"); c = fresh(st); fired(c); feed(c, N + 1, N + 39); pos = E.positions[PAIR]
    inject_sell(c, st, N + 40, 10 ** 24, FLEET[0]); feed(c, N + 40, N + 40)
    s = wait_ev("sell_sent")
    assert len(s) == 1 and s[0]["reason"] == "fleet_sell" and s[0]["priced_at_block"] == N + 41 and "fleet's first sell" in s[0]["why"], s
    feed(c, N + 41, N + 42)
    t = wait_ev("trade_done")[0]
    assert t["exit"] == "fleet_sell" and t["sell_block"] == N + 41 and t["eth_out_wei"] == dry_value(c, st, pos["tokens"], pos["stake"], N + 41) and not events("stop"), t
    st = Stream("2.0"); c = fresh(st); fired(c); feed(c, N + 1, N + 39)
    inject_sell(c, st, N + 40, 10 ** 24, STRANGER.address.lower()); feed(c, N + 40, N + 42)   # an outsider's small sell: no exit
    time.sleep(0.05); assert not events("sell_sent")
    inject_sell(c, st, N + 50, 3 * 10 ** 27, FLEET[1]); feed(c, N + 50, N + 50)              # a dump: 35% of the ETH reserve
    t = events("stop")
    assert len(t) == 1 and t[0]["what"] == "tier" and t[0]["tier"] == "1.3-2.3" and "BASE_V2_PULL_SHARE" in t[0]["reason"] and "35%" in t[0]["reason"], t
    assert events("sell_sent")[0]["reason"] == "fleet_sell"


@test
def dry_pulled_before_our_sell_halts():
    """a Burn before our sell: -100%, the line halts (in memory in the dry run), no new buy after it; the pull line's fields"""
    st = Stream("2.0"); c = fresh(st); fired(c); feed(c, N + 1, N + 9); pos = E.positions[PAIR]
    inject_burn(c, st, N + 10); feed(c, N + 10, N + 11)
    t = wait_ev("trade_done")[0]; gas = 250_000 * 35_000_000 + 4_200_000_000
    assert t["exit"] == "pulled" and t["eth_out_wei"] == 0 and t["pulled_at"] == N + 10 and t["net_wei"] == -(2 * 10 ** 16 + gas) and t["ret"] == round(-(2 * 10 ** 16 + gas) / 2e16, 6), t
    assert t["tokens"] == pos["tokens"] and t["sell_block"] is None and not events("sell_sent")
    p = events("pull")[0]
    assert p["block"] == N + 10 and p["before"] == "sell" and p["ours"] and p["reaction"] and p["since_creation"] == 10 and p["since_last_buy"] == 8 and p["since_outsider"] is None, p
    h = events("halt")
    assert len(h) == 1 and h[0]["reason"].startswith("pulled:") and h[0]["dry"] and h[0]["file"] is None and h[0]["pair"] == PAIR and h[0]["tier"] == "1.3-2.3", h
    assert E.state["halted"] == h[0]["reason"] and not os.path.exists(E.S.HALT_FILE)
    assert events("stop")[0]["what"] == "tier" and "BASE_V2_SCHEDULE_MIN" in events("stop")[0]["reason"]
    st2 = Stream("2.0", creator=creator_key("after-halt"), shift=20, li_offset=1000); c.streams[st2.pair] = st2; c.by_token[st2.token] = st2
    c.txs.update(st2.txs); c.txs[st2.creation_hash] = st2.creation_tx; c.receipts[st2.creation_hash] = {"status": "0x1", "blockNumber": hex(st2.N), "logs": st2.rlogs}
    feed(c, N + 12, N + 20)
    s = wait_ev("skip", pair=st2.pair)[0]
    assert s["why"] == "halted" and s["reason"].startswith("pulled:") and events("guard", pair=st2.pair) and not events("would_fire", pair=st2.pair), s


@test
def burn_on_another_pair_ends_the_tier():
    """a Burn earlier than SCHEDULE_MIN on another pair of the tier (followed, refused by MAX_POSITIONS): stop what:tier, no halt; our open
    position still sells at the hard block; the next creation of the tier is refused (tier ended) until the day rolls"""
    a = Stream("2.0"); b = Stream("2.0", creator=creator_key("pair-b"), li_offset=1000); c = fresh(a, b, BASE_V2_MAX_POSITIONS="1"); feed(c, N - 2, N)
    ours = c.streams[wait_ev("would_fire")[0]["pair"]]; theirs = b if ours is a else a      # two guards in one block: either may finish first
    s = wait_ev("skip", pair=theirs.pair)[0]
    assert s["why"] == "positions" and s["positions"] == [ours.pair] and len(events("would_fire")) == 1 and E.pairs[theirs.pair]["status"] == "watched", s
    feed(c, N + 1, N + 99); inject_burn(c, theirs, N + 100); feed(c, N + 100, N + 101)
    t = events("stop")
    assert len(t) == 1 and t[0]["what"] == "tier" and t[0]["tier"] == "1.3-2.3" and "+100" in t[0]["reason"] and "BASE_V2_SCHEDULE_MIN 220" in t[0]["reason"] and t[0]["day"] == "2026-10-20", t
    p = events("pull")[0]
    assert p["pair"] == theirs.pair and not p["ours"] and p["before"] == "after" and not p["reaction"] and p["since_creation"] == 100 and not events("halt") and theirs.pair not in E.pairs, p
    assert E.positions[ours.pair]["sell_sent"] is False and E.state["tiers_ended"] == {"1.3-2.3": "2026-10-20"}
    feed(c, N + 102, N + 178)
    d = wait_ev("trade_done", pair=ours.pair)[0]; assert d["exit"] == "hard" and d["ret"] > 0 and not E.positions
    d3 = Stream("2.0", creator=creator_key("pair-d"), shift=180, li_offset=2000); c.streams[d3.pair] = d3; c.by_token[d3.token] = d3
    c.txs.update(d3.txs); c.txs[d3.creation_hash] = d3.creation_tx; c.receipts[d3.creation_hash] = {"status": "0x1", "blockNumber": hex(d3.N), "logs": d3.rlogs}
    feed(c, N + 179, N + 180)
    s = wait_ev("skip", pair=d3.pair)[0]
    assert s["why"] == "tier ended" and events("guard", pair=d3.pair)[0]["verdict"] == "ok" and not events("would_fire", pair=d3.pair) and len(events("stop")) == 1, s
    CLOCK[0] = ts(N) + 86400; E.roll_day()                                    # 00:00 UTC: the tier's stop clears
    assert E.state["tiers_ended"] == {} and E.state["day"] == "2026-10-21" and E.state["trades_today"] == 0


@test
def daily_cap():
    """MAX_PER_DAY fires stop the day (stop what:day); the next creation is refused"""
    a = Stream("2.0"); b = Stream("2.0", creator=creator_key("cap-b"), li_offset=1000); c = fresh(a, b, BASE_V2_MAX_PER_DAY="2"); feed(c, N - 2, N)
    wait_ev("would_fire", 2)
    t = events("stop")
    assert len(t) == 1 and t[0]["what"] == "day" and "BASE_V2_MAX_PER_DAY 2 buys" in t[0]["reason"] and t[0]["trades_today"] == 2 and E.state["stopped"] == "2026-10-20", t
    d3 = Stream("2.0", creator=creator_key("cap-d"), shift=5, li_offset=2000); c.streams[d3.pair] = d3; c.by_token[d3.token] = d3
    c.txs.update(d3.txs); c.txs[d3.creation_hash] = d3.creation_tx; c.receipts[d3.creation_hash] = {"status": "0x1", "blockNumber": hex(d3.N), "logs": d3.rlogs}
    feed(c, N + 1, N + 5)
    s = wait_ev("skip", pair=d3.pair)[0]
    assert s["why"] == "stopped" and s["trades_today"] == 2 and not events("would_fire", pair=d3.pair) and len(events("stop")) == 1, s
    feed(c, N + 6, N + 178)
    assert len(wait_ev("trade_done", 2)) == 2 and len(events("would_fire")) == 2


# ---------------------------------------------------------------- live (the key, the relay and the sends stubbed)
def live_start(c, **env):
    """a live start through start(): the key file written, the wallet and the relay in the env"""
    open(os.path.join(TMP, "k.key"), "w").write("0x" + bytes(KEY.key).hex() + "\n"); E.SIGNER = None
    os.environ.update({"BASE_V2_KEY_FILE": os.path.join(TMP, "k.key"), "BASE_V2_WALLET": KEY.address, "BASE_V2_RELAY": RELAY, **{k: str(v) for k, v in env.items()}})
    E.S = E.settings(); E.S.STAKE_WEI_MAX = lambda: min(E.S.STAKE_ETH_WEI, E.S.STAKE_CAP_WEI)
    return E.start()


def add_stream(c, st):
    c.streams[st.pair] = st; c.by_token[st.token] = st; c.txs.update(st.txs); c.txs[st.creation_hash] = st.creation_tx
    c.receipts[st.creation_hash] = {"status": "0x1", "blockNumber": hex(st.N), "transactionHash": st.creation_hash, "logs": st.rlogs}


@test
def live_fire_signs_a_type2_buy():
    """the fire: a real signed type-2 transaction to the relay's buy selector with the token, the stake, minOut and the deadline, at the
    wallet's nonce and BASE_V2_PRIO_GWEI, max fee 2 x the base fee + the priority, to both send endpoints; the refusals before a live fire"""
    c = fresh(dry=False); f = fired(c)[0]; b = wait_ev("buy_sent")[0]; stake = 2 * 10 ** 16; min_out = cp_out(stake, 2 * 10 ** 18, R_TOK0) * 970_000 // 10 ** 6
    assert f["ev"] == "fire" and not f["dry"] and f["nonce"] == 7 and f["aim"] == N + 1 and f["head"] == N and f["min_out"] == min_out and f["prio_gwei"] == 0.03 and f["max_fee_gwei"] == 0.04, f
    assert b["nonce"] == 7 and b["kind"] == "ok" and b["reason"] == "fire" and b["via"] == "first" and b["min_out"] == min_out and b["deadline"] == ts(N) + 6 and b["prio_gwei"] == 0.03, b
    assert b["block_seen"] == N and set(b["replies"]) <= {"seq.example.org", "send2.example.org"} and [r["kind"] for r in b["replies"].values()] == ["ok"] and b["ms_since_fire"] >= 0, b
    assert len(c.sent) == 2 and {h for h, _ in c.sent} == {"seq.example.org", "send2.example.org"} and c.sent[0][1] == c.sent[1][1]
    raw = c.sent[0][1]; tx = raw_sent(c, 0); d = "0x" + tx["data"].hex()
    assert raw.startswith("0x02") and tx["type"] == 2 and tx["to"] == RELAY and tx["value"] == 0 and tx["nonce"] == 7 and tx["gas"] == 250_000, tx
    assert tx["prio"] == 3 * 10 ** 7 == E.S.PRIO_WEI and tx["max_fee"] == 2 * 5_000_000 + 3 * 10 ** 7 and int.from_bytes(rlp.decode(bytes.fromhex(raw[4:]))[0], "big") == 8453
    assert d[2:10] == E.SEL_BUY == "1622dbe4" and len(d) == 10 + 64 * 4 and inaddr(d, 0) == TOKEN and inword(d, 1) == stake and inword(d, 2) == min_out and inword(d, 3) == ts(N) + 6
    assert E.tx_sender(raw) == KEY.address.lower() and b["hash"] == hash_of(raw) and E.state["nonce"] == 8 and b["hash"] in E.state["our_hashes"]
    saved = json.load(open(E.S.POSITIONS_FILE))["positions"]
    assert list(saved) == [PAIR] and saved[PAIR]["buy_hash"] == b["hash"] and saved[PAIR]["buy_nonce"] == 7 and saved[PAIR]["stake"] == stake and not saved[PAIR]["sell_sent"]
    feed(c, N + 1, N + 1); hard_exits(c)
    c = fresh(dry=False); E.state["relay_wei"] = 10 ** 16; f = fired(c)[0]
    assert f["ev"] == "skip" and f["why"] == "relay balance" and f["relay_eth"] == 0.01 and f["needed_eth"] == 0.0205 and not c.sent and events("guard")[0]["verdict"] == "ok", f
    c = fresh(dry=False); open(E.S.HALT_FILE, "w").write("the owner's halt\\n"); f = fired(c)[0]
    assert f["ev"] == "skip" and f["why"] == "halted" and f["reason"] == "the owner's halt" and E.state["halted"] == "the owner's halt" and not c.sent, f
    c = fresh(dry=False); c.replies = [{"error": {"code": -32000, "message": "insufficient funds"}}, {"error": {"code": -32000, "message": "insufficient funds"}}]; fired(c)
    b = wait_ev("buy_sent")[0]; a = wait_ev("alarm")[0]
    assert b["kind"] == "rejected" and "refused by every endpoint" in a["what"] and E.state["trades_today"] == 0 and not E.positions and E.state["nonce"] == 7, (b, a)


@test
def live_trade_settles_from_the_receipts():
    """the hard exit live: the buy mined at N + 1, the sell sent at N + SELL_SEND_BLOCK (minOut 0, the next nonce) and mined; settled from
    the receipts: the tokens from the Transfer to the relay (not the Swap), the ETH out, gas = gasUsed x effectiveGasPrice + l1Fee of both"""
    c = fresh(dry=False); c.transfer_cut = 1; st = c.streams[PAIR]; fired(c); wait_ev("buy_sent"); stake = 2 * 10 ** 16
    feed(c, N + 1, N + 1)
    tokens = cp_out(stake, *st.sync_at(N)); got = tokens - tokens // 100; pos = E.positions[PAIR]
    assert c.held[PAIR] == got and pos["buy_at"] == (N + 1, 0x804 + 2) and pos["buy_block"] == N + 1 and not pos["sell_sent"]
    feed(c, N + 2, N + 175)
    assert not events("sell_sent") and len(c.sent) == 2 and pos["tokens"] == got            # the receipt's Transfer, read by the settlement
    feed(c, N + 176, N + 176)
    s = wait_ev("sell_sent")[0]
    assert s["reason"] == "hard" and s["nonce"] == 8 and s["min_out"] == 0 and s["via"] == "first" and s["deadline"] == ts(N + 176) + 6 and s["kind"] == "ok" and s["block_seen"] == N + 176, s
    tx = raw_sent(c, 2); d = "0x" + tx["data"].hex()
    assert d[2:10] == E.SEL_SELL == "6a272462" and inaddr(d, 0) == TOKEN and inword(d, 1) == 0 and inword(d, 2) == ts(N + 176) + 6 and tx["nonce"] == 8 and tx["prio"] == 3 * 10 ** 7
    feed(c, N + 177, N + 178)
    t = wait_ev("trade_done")[0]; re_, rt_ = st.sync_at(N + 177); eth_out = cp_out(got, rt_, re_)
    gas = 125_000 * 35_000_000 + 2_090_000_000 + 118_000 * 35_000_000 + 2_000_000_000
    assert t["live"] and not t["dry"] and t["exit"] == "hard" and t["buy_block"] == N + 1 and t["buy_index"] == 0x806 and t["sell_block"] == N + 177 and t["eth_in_wei"] == stake, t
    assert t["tokens"] == got and t["eth_out_wei"] == eth_out and t["gas_wei"] == gas and t["l1_fee_wei"] == 4_090_000_000 and t["net_wei"] == eth_out - stake - gas
    assert t["ret"] == round((eth_out - stake - gas) / stake, 6) and t["ret"] > 0.03 and t["nonce"] == 7 and t["buy_hash"] == events("buy_sent")[0]["hash"] and t["sell_hash"] == s["hash"], (t, s)
    assert t["loss_streak"] == 0 and not t["late"] and t["pulled_at"] is None and t["outsider_at"] is None and t["fleet_first_buy"] == N + 2 and t["fleet_eth"] > 0.05 and t["trades_today"] == 1
    assert json.load(open(E.S.POSITIONS_FILE))["positions"] == {} and not E.positions and E.state["nonce"] == 9 and E.state["relay_wei"] == 10 ** 18 + eth_out - stake
    assert len(c.sent) == 4 and not events("halt") and not events("alarm") and E.pairs[PAIR]["status"] == "traded"


@test
def live_hard_sell_resent_when_unseen():
    """the hard sell unseen (no Flashblock, no Swap, no receipt) by N + SELL_RESEND_BLOCK: sent again at the same nonce with twice the
    priority and a bumped max fee; the replacement's receipt settles the trade"""
    c = fresh(dry=False); st = c.streams[PAIR]; fired(c); wait_ev("buy_sent"); feed(c, N + 1, N + 1); c.auto_mine = False
    feed(c, N + 2, N + 177)
    s = wait_ev("sell_sent")
    assert len(s) == 1 and s[0]["reason"] == "hard" and s[0]["nonce"] == 8 and len(c.sent) == 4
    feed(c, N + 178, N + 178)
    s = wait_ev("sell_sent", 2)
    assert s[1]["via"] == "resend" and s[1]["nonce"] == 8 and s[1]["prio_gwei"] == 0.06 and s[1]["min_out"] == 0 and s[1]["reason"] == "hard" and "SELL_RESEND_BLOCK" in s[1]["why"], s
    assert s[1]["hash"] != s[0]["hash"] and s[1]["deadline"] == ts(N + 178) + 6 and len(c.sent) == 6
    first, again = raw_sent(c, 2), raw_sent(c, 4)
    assert again["nonce"] == first["nonce"] == 8 and again["prio"] == 2 * first["prio"] == 6 * 10 ** 7 and again["max_fee"] == max(2 * 5_000_000 + 6 * 10 ** 7, first["max_fee"] * 11 // 10 + 1)
    assert again["data"][4:36] == first["data"][4:36] and E.positions[PAIR]["resent"]
    c.mine(N + 179, only={s[1]["hash"]}); feed(c, N + 179, N + 180)
    t = wait_ev("trade_done")[0]
    assert t["exit"] == "hard" and t["sell_block"] == N + 179 and t["sell_hash"] == s[1]["hash"] and t["eth_out_wei"] > 0 and len(events("sell_sent")) == 2, t
    assert t["gas_wei"] == 125_000 * 35_000_000 + 2_090_000_000 + 118_000 * 35_000_000 + 2_000_000_000       # one buy, one mined sell


@test
def live_take_profit_min_out():
    c = fresh(dry=False); st = c.streams[PAIR]; fired(c); wait_ev("buy_sent"); feed(c, N + 1, N + 19); pos = E.positions[PAIR]
    inject_buy(c, st, N + 20, 3 * 10 ** 17, FLEET[4]); feed(c, N + 20, N + 20)
    s = wait_ev("sell_sent")[0]; re_, rt_ = c.reserves_at(PAIR, N + 20); want = cp_out(pos["tokens"], rt_, re_) * 950_000 // 10 ** 6
    assert s["reason"] == "take_profit" and s["min_out"] == want and want > 24 * 10 ** 15 and s["nonce"] == 8 and "+29.82%" in s["why"] and "BASE_V2_TAKE_PROFIT" in s["why"], (s, want)
    d = "0x" + raw_sent(c, 2)["data"].hex(); assert inword(d, 1) == want and inaddr(d, 0) == TOKEN
    feed(c, N + 21, N + 22)
    t = wait_ev("trade_done")[0]
    assert t["exit"] == "take_profit" and t["sell_block"] == N + 21 and t["eth_out_wei"] == cp_out(pos["tokens"], rt_, re_) and t["ret"] > 0.25 and t["peak_ret"] > 0.25, t


@test
def live_outsider_pending_sells_before_the_block():
    c = fresh(dry=False); st = c.streams[PAIR]; fired(c); wait_ev("buy_sent"); feed(c, N + 1, N + 4)
    raw = signed(STRANGER, 9, ROUTER, 2 * 10 ** 15, "0x7ff36ab5" + word(0) + word(128) + aword(STRANGER.address) + word(ts(N) + 60) + word(2) + aword(WETH) + aword(TOKEN))
    flash(N + 5, [raw], index=3)
    s = wait_ev("sell_sent")[0]; o = events("outsider_buy", pending=True)[0]; pos = E.positions[PAIR]
    assert s["reason"] == "outsider" and pos["sell_via"] == "flash" and s["block_seen"] == N + 5 and s["min_out"] == 0 and s["nonce"] == 8 and "seen pending at" in s["why"], s
    assert s["via"] == "first" and E.state["head"] == N + 4 and len(c.sent) == 4                       # sent before block N + 5 sealed
    assert o["who"] == "outsider" and o["action"] == "sell" and o["ours"] and o["sender"] == STRANGER.address.lower() and o["tx"] == hash_of(raw), o
    flash(N + 5, [c.sent[2][1]], index=4)                                     # our sell seen in the next Flashblock
    assert E.positions[PAIR].get("sell_seen") == (N + 5, 4, 0)
    inject_buy(c, st, N + 5, 2 * 10 ** 15, STRANGER.address.lower(), tx=hash_of(raw)); feed(c, N + 5, N + 6)
    t = wait_ev("trade_done")[0]
    assert t["exit"] == "outsider" and t["outsider_at"] == N + 5 and t["sell_block"] == N + 5 and len(events("sell_sent")) == 1 and len(events("outsider_buy", block=N + 5)) == 1, t


@test
def live_pulled_before_our_sell_halts_with_the_file():
    """a Burn before our sell: the sell at minOut 0 still goes once (reverts), the trade is -100%, the halt file is written with the reason,
    no new buy after it; the pull line; the day's P&L"""
    c = fresh(dry=False); st = c.streams[PAIR]; fired(c); wait_ev("buy_sent"); feed(c, N + 1, N + 9); pos = E.positions[PAIR]; tokens = pos["tokens"]
    inject_burn(c, st, N + 10); c.sell_ok = False; feed(c, N + 10, N + 10)
    s = wait_ev("sell_sent")[0]
    assert s["reason"] == "pulled" and s["min_out"] == 0 and s["nonce"] == 8 and "pulled at" in s["why"], s
    p = events("pull")[0]
    assert p["block"] == N + 10 and p["before"] == "sell" and p["ours"] and p["reaction"] and p["since_last_buy"] == 8 and p["since_outsider"] is None and p["eth_out_wei"] > 0, p
    feed(c, N + 11, N + 12)
    t = wait_ev("trade_done")[0]; gas = 125_000 * 35_000_000 + 2_090_000_000 + 40_000 * 35_000_000 + 2_000_000_000
    assert t["exit"] == "pulled" and t["eth_out_wei"] == 0 and t["pulled_at"] == N + 10 and t["sell_block"] == N + 11 and t["gas_wei"] == gas and t["tokens"] == tokens, t
    assert t["net_wei"] == -(2 * 10 ** 16 + gas) and t["ret"] == round(-(2 * 10 ** 16 + gas) / 2e16, 6) and t["loss_streak"] == 1 and t["live"] and len(events("sell_sent")) == 1
    h = events("halt")
    assert len(h) == 1 and h[0]["reason"].startswith("pulled:") and "no outsider before it: -100%" in h[0]["reason"] and not h[0]["dry"] and h[0]["file"] == E.S.HALT_FILE, h
    assert open(E.S.HALT_FILE).read().strip() == h[0]["reason"] == E.state["halted"] and h[0]["tier"] == "1.3-2.3" and h[0]["pair"] == PAIR
    assert E.state["pnl_today_wei"] == t["net_wei"] and json.load(open(E.S.POSITIONS_FILE))["positions"] == {} and not E.positions
    d = Stream("2.0", creator=creator_key("after-file"), shift=20, li_offset=1000); add_stream(c, d); feed(c, N + 13, N + 20)
    s = wait_ev("skip", pair=d.pair)[0]
    assert s["why"] == "halted" and s["reason"].startswith("pulled:") and not events("fire", pair=d.pair) and len(c.sent) == 4, s
    # the reaction rule: a Burn within REACT_BLOCKS after our buy even when our sell landed first, no outsider before it: the line halts too
    c = fresh(dry=False); st = c.streams[PAIR]; fired(c); wait_ev("buy_sent"); feed(c, N + 1, N + 2)
    inject_buy(c, st, N + 3, 3 * 10 ** 17, FLEET[4]); feed(c, N + 3, N + 3); wait_ev("sell_sent"); feed(c, N + 4, N + 7)
    t = wait_ev("trade_done")[0]; assert t["exit"] == "take_profit" and t["sell_block"] == N + 4 and not events("halt")
    inject_burn(c, st, N + 8); feed(c, N + 8, N + 8)
    h = events("halt"); p = events("pull")[0]
    assert len(h) == 1 and h[0]["reason"].startswith("reaction:") and "7 blocks after our buy" in h[0]["reason"] and os.path.exists(E.S.HALT_FILE), h
    assert p["before"] == "after" and p["ours"] and p["reaction"] and events("stop")[0]["what"] == "tier"
    c = fresh(dry=False); st = c.streams[PAIR]; fired(c); wait_ev("buy_sent"); feed(c, N + 1, N + 2)     # an outsider between our buy and the Burn: no halt
    inject_buy(c, st, N + 3, 10 ** 15, STRANGER.address.lower()); feed(c, N + 3, N + 3); wait_ev("sell_sent"); feed(c, N + 4, N + 7); wait_ev("trade_done")
    inject_burn(c, st, N + 8); feed(c, N + 8, N + 8)
    assert not events("halt") and events("pull")[0]["reaction"] and events("pull")[0]["since_outsider"] == 5 and events("stop")[0]["what"] == "tier", events("pull")
    assert "BASE_V2_SCHEDULE_MIN" in events("stop")[0]["reason"] and len(events("stop")) == 1       # the earliest rule names the stop; the reaction rule is the same stop


@test
def live_max_positions_with_three_open():
    """three pairs open at once at distinct nonces; a fourth creation is refused (positions) and followed; every position settles"""
    a = Stream("2.0"); b = Stream("2.0", creator=creator_key("three-b"), li_offset=1000); c2 = Stream("2.0", creator=creator_key("three-c"), li_offset=2000)
    d = Stream("2.0", creator=creator_key("three-d"), shift=3, li_offset=3000); c = fresh(a, b, c2, d, dry=False); feed(c, N - 2, N)
    f = wait_ev("fire", 3); bs = wait_ev("buy_sent", 3)
    assert {x["pair"] for x in f} == {a.pair, b.pair, c2.pair} and sorted(x["nonce"] for x in bs) == [7, 8, 9] and E.state["nonce"] == 10, bs
    raws = {raw_sent(c, i)["nonce"]: raw_sent(c, i) for i in range(0, 6, 2)}
    assert sorted(raws) == [7, 8, 9] and len({inaddr("0x" + t["data"].hex(), 0) for t in raws.values()}) == 3 and all(t["to"] == RELAY for t in raws.values())
    assert [x["positions"] for x in sorted(f, key=lambda x: x["t"])] and len(E.positions) == 3 and len(json.load(open(E.S.POSITIONS_FILE))["positions"]) == 3
    feed(c, N + 1, N + 3)
    s = wait_ev("skip", pair=d.pair)[0]
    assert s["why"] == "positions" and sorted(s["positions"]) == sorted([a.pair, b.pair, c2.pair]) and E.pairs[d.pair]["status"] == "watched" and events("guard", pair=d.pair), s
    t = hard_exits(c, 3)
    assert {x["pair"] for x in t} == {a.pair, b.pair, c2.pair} and all(x["exit"] == "hard" and x["buy_block"] == N + 1 and x["sell_block"] == N + 177 for x in t), t
    ss = events("sell_sent"); assert sorted(x["nonce"] for x in ss) == [10, 11, 12] and len(c.sent) == 12 and not E.positions and E.state["nonce"] == 13
    assert json.load(open(E.S.POSITIONS_FILE))["positions"] == {} and E.state["trades_today"] == 3 and not events("halt") and d.pair in E.pairs


@test
def live_loss_streak_halts():
    a = Stream("2.0", fleet=False); b = Stream("2.0", creator=creator_key("loss-b"), li_offset=1000, fleet=False); c = fresh(a, b, dry=False); feed(c, N - 2, N)
    wait_ev("buy_sent", 2); feed(c, N + 1, N + 1); t = hard_exits(c, 2)
    assert all(x["exit"] == "hard" and x["net_wei"] < 0 and -0.01 < x["ret"] < 0 for x in t) and sorted(x["loss_streak"] for x in t) == [1, 2], t
    h = events("halt")
    assert len(h) == 1 and h[0]["reason"].startswith("2 live losses in a row") and "BASE_V2_LOSS_STREAK_HALT" in h[0]["reason"] and open(E.S.HALT_FILE).read().strip() == h[0]["reason"], h
    assert E.state["loss_streak"] == 2 and E.state["halted"] and not E.positions
    d = Stream("2.0", creator=creator_key("loss-d"), shift=185, li_offset=2000); add_stream(c, d); feed(c, N + 179, N + 185)
    assert wait_ev("skip", pair=d.pair)[0]["why"] == "halted"
    a = Stream("2.0", fleet=False); b = Stream("2.0", creator=creator_key("loss-b2"), li_offset=1000, fleet=False); c = fresh(a, b, dry=False, BASE_V2_LOSS_STREAK_HALT="0"); feed(c, N - 2, N)
    wait_ev("buy_sent", 2); feed(c, N + 1, N + 1); t = hard_exits(c, 2)
    assert sorted(x["loss_streak"] for x in t) == [1, 2] and not events("halt")                      # 0 = off


@test
def live_late_halt():
    """two live buys mined past N + LAND_MAX: the line halts (BASE_V2_LATE_HALT); the loss streak rule off"""
    a = Stream("2.0"); b = Stream("2.0", creator=creator_key("late-b"), li_offset=1000); c = fresh(a, b, dry=False, BASE_V2_LOSS_STREAK_HALT="0"); feed(c, N - 2, N)
    wait_ev("buy_sent", 2); c.auto_mine = False; feed(c, N + 1, N + 2)
    assert not events("trade_done") and all(p["buy_block"] is None for p in E.positions.values())
    c.mine(N + 3); c.auto_mine = True; t = hard_exits(c, 2)
    assert all(x["late"] and x["buy_block"] == N + 3 and x["exit"] == "hard" for x in t) and E.state["late_count"] == 2, t
    h = events("halt")
    assert len(h) == 1 and h[0]["reason"].startswith("2 live buys mined past N + BASE_V2_LAND_MAX 1") and "(the last at +3)" in h[0]["reason"] and os.path.exists(E.S.HALT_FILE), h


@test
def live_daily_stop():
    """the live net P&L at -BASE_V2_DAILY_STOP_ETH stops the day; the next creation is refused (stopped); no halt"""
    c = fresh(Stream("2.0", fleet=False), dry=False, BASE_V2_DAILY_STOP_ETH="0.0001", BASE_V2_LOSS_STREAK_HALT="0"); fired(c); wait_ev("buy_sent"); feed(c, N + 1, N + 1)
    t = hard_exits(c)[0]
    assert t["exit"] == "hard" and -0.01 < t["ret"] < -0.005 and t["net_wei"] <= -10 ** 14 and t["pnl_today_eth"] == round(t["net_wei"] / 1e18, 6), t
    s = events("stop")
    assert len(s) == 1 and s[0]["what"] == "day" and "-BASE_V2_DAILY_STOP_ETH 0.0001" in s[0]["reason"] and s[0]["trades_today"] == 1 and E.state["stopped"] == "2026-10-20", s
    d = Stream("2.0", creator=creator_key("stop-d"), shift=185, li_offset=2000); add_stream(c, d); feed(c, N + 179, N + 185)
    assert wait_ev("skip", pair=d.pair)[0]["why"] == "stopped" and not events("halt") and not events("fire", pair=d.pair)
    CLOCK[0] = ts(N) + 86400
    with E.lock:
        E.end_burst()
    assert E.state["stopped"] is None and E.state["pnl_today_wei"] == 0 and E.state["trades_today"] == 0


@test
def live_sold_none_halts():
    """a sell that reverted is sent again at minOut 0 at the next nonce, twice at most, then the line halts (sold none)"""
    c = fresh(dry=False); c.sell_ok = False; fired(c); wait_ev("buy_sent"); feed(c, N + 1, N + 176)
    wait_ev("sell_sent")
    for n in range(N + 177, N + 190):
        feed(c, n, n); time.sleep(0.03)
        if events("trade_done"):
            break
    t = wait_ev("trade_done")[0]; s = events("sell_sent"); a = [x["what"] for x in events("alarm")]
    assert t["exit"] == "hard" and t["eth_out_wei"] == 0 and t["ret"] < -1 and [x["via"] for x in s].count("retry") == 2 and all(x["min_out"] == 0 for x in s), (t, s)
    assert len({x["nonce"] for x in s if x["via"] != "resend"}) == 3 and sum("sent again at minOut 0" in x for x in a) == 2
    h = events("halt")
    assert len(h) == 1 and h[0]["reason"].startswith("sold none") and "reverted" in h[0]["reason"] and open(E.S.HALT_FILE).read().strip() == h[0]["reason"], h
    assert t["gas_wei"] >= 125_000 * 35_000_000 + 2_090_000_000 + 3 * (40_000 * 35_000_000 + 2_000_000_000) and E.state["sold_none"] == 1


@test
def live_buy_reverted_sends_no_sell():
    c = fresh(dry=False); c.buy_ok = False; fired(c); wait_ev("buy_sent"); feed(c, N + 1, N + 3)
    t = wait_ev("trade_done")[0]
    assert t["exit"] == "buy_reverted" and t["eth_in_wei"] == 0 and t["eth_out_wei"] == 0 and t["gas_wei"] == 60_000 * 35_000_000 + 2_090_000_000 and t["usd"] < 0, t
    assert "our buy reverted" in t["why"] and not events("sell_sent") and len(c.sent) == 2 and t["loss_streak"] == 0 and not events("halt") and not E.positions
    c = fresh(dry=False); fired(c); wait_ev("buy_sent"); feed(c, N + 1, N + 1); pos = E.positions[PAIR]       # the wall clock's fallback: no head after the buy
    CLOCK[0] = ts(N) + 370
    with E.lock:
        E.end_burst()
    s = wait_ev("sell_sent")[0]
    assert s["reason"] == "hard" and "wall clock" in s["why"] and s["min_out"] == 0 and E.positions[PAIR]["sell_via"] == "clock", s
    feed(c, N + 2, N + 3); assert wait_ev("trade_done")[0]["exit"] == "hard"


# ---------------------------------------------------------------- the start, the restart
@test
def restart_restores_the_day_and_the_halt_file():
    """today's fires, P&L, late buys, tier stops and the loss streak from the log; the halt file read (live) and ignored (dry); the start line"""
    c = fresh(dry=False); open(E.S.HALT_FILE, "w").write("pulled: by hand\\n")
    t0 = ts(N); lines = [{"ev": "fire", "t": t0 - 3600}, {"ev": "fire", "t": t0 - 1800}, {"ev": "would_fire", "t": t0 - 1700},
                         {"ev": "trade_done", "live": True, "dry": False, "net_wei": -5 * 10 ** 15, "loss_streak": 1, "late": True, "t": t0 - 1000},
                         {"ev": "trade_done", "live": False, "dry": True, "net_wei": 7 * 10 ** 15, "loss_streak": 0, "late": False, "t": t0 - 900},
                         {"ev": "stop", "what": "tier", "tier": "1.3-2.3", "t": t0 - 500}, {"ev": "fire", "t": t0 - 86400 * 2}, {"ev": "stop", "what": "day", "t": t0 - 86400 * 2}]
    open(LOG, "w").write("\\n".join(json.dumps(x) for x in lines) + "\\nnot json\\n")
    info = live_start(c)
    got = {k: E.state[k] for k in ("trades_today", "pnl_today_wei", "loss_streak", "late_count", "stopped", "day")}
    assert got == {"trades_today": 2, "pnl_today_wei": -5 * 10 ** 15, "loss_streak": 1, "late_count": 1, "stopped": None, "day": "2026-10-20"}, got
    assert E.state["tiers_ended"] == {"1.3-2.3": "2026-10-20"} and E.state["halted"] == "pulled: by hand" and info["nonce"] == 7 and info["relay_eth"] == 1.0
    st = events("start")[0]
    assert st["release"] == E.RELEASE and not st["dry"] and st["head"] == N - 3 and st["wallet"] == KEY.address.lower() and st["relay"] == RELAY and st["roster_n"] == 12, st
    assert st["halted"] == st["halt_file"] == "pulled: by hand" and st["trades_today"] == 2 and st["pnl_today_eth"] == -0.005 and st["loss_streak"] == 1 and st["tiers_ended"] == ["1.3-2.3"]
    assert st["positions"] == [] and st["settings"]["RPC_URL"] == "rpc.example.org" and st["settings"]["ARCHIVE_URL"] == "arch.example.org" and "KEY_FILE" not in st["settings"]
    assert st["settings"]["SEND_URLS"] == ["seq.example.org", "send2.example.org"] and st["settings"]["PROBE"] == [PROBE] and st["chains"]["rpc.example.org"] == 8453
    assert "k3y" not in open(LOG).read() and bytes(KEY.key).hex() not in open(LOG).read() and events("guard", self_test=True)[0]["verdict"] == "ok"
    E.state["logs_to"] = N - 2; fired(c)
    assert events("skip")[-1]["why"] == "halted" and events("skip")[-1]["reason"] == "pulled: by hand" and not c.sent
    c = fresh(dry=False); open(LOG, "w").write(json.dumps({"ev": "trade_done", "live": True, "dry": False, "net_wei": -1, "loss_streak": 2, "t": t0 - 100}) + "\\n" +
                                                 json.dumps({"ev": "halt", "reason": "2 live losses in a row: BASE_V2_LOSS_STREAK_HALT", "t": t0 - 99}) + "\\n")
    live_start(c); assert E.state["loss_streak"] == 0 and E.state["halted"] is None           # the owner removed the file it wrote: the streak starts again
    c = fresh(dry=False); open(LOG, "w").write(json.dumps({"ev": "trade_done", "live": True, "dry": False, "net_wei": -1, "loss_streak": 2, "t": t0 - 100}) + "\\n")
    open(E.S.HALT_FILE, "w").write("2 live losses in a row: BASE_V2_LOSS_STREAK_HALT\\n"); live_start(c); assert E.state["loss_streak"] == 2 and E.state["halted"].startswith("2 live")
    c = fresh(dry=False); open(LOG, "w").write("\\n".join(json.dumps({"ev": "fire", "t": t0 - k}) for k in range(1, 21)) + "\\n"); live_start(c)
    assert E.state["trades_today"] == 20 and E.state["stopped"] == "2026-10-20"              # MAX_PER_DAY reached before the restart: the day stays stopped
    c = fresh(); open(E.S.HALT_FILE, "w").write("pulled: by hand\\n"); open(LOG, "w").write(json.dumps({"ev": "would_fire", "t": t0 - 10}) + "\\n" + json.dumps({"ev": "fire", "t": t0 - 9}) + "\\n")
    E.start(); st = events("start")[0]
    assert st["dry"] and E.state["halted"] is None and st["halt_file"] == "pulled: by hand" and E.state["trades_today"] == 1 and E.SIGNER is None    # dry: the file is the live line's


@test
def restart_takes_back_an_open_position():
    """an open position from the last run: its buy's receipt read, the sell at once (minOut 0) at the chain's nonce; a sell already sent
    has its receipt awaited, nothing new signed"""
    c = fresh(dry=False); st = c.streams[PAIR]; stake = 2 * 10 ** 16; expect = cp_out(stake, 2 * 10 ** 18, R_TOK0)
    raw = signed(KEY, 7, RELAY, 0, E.buy_data(TOKEN, stake, expect * 97 // 100, ts(N) + 6), 3 * 10 ** 7, 4 * 10 ** 7, 250_000); hb = hash_of(raw); c.sent.append(("seq.example.org", raw)); c.nonces.add(7)
    c.mine(N + 1); tokens = c.held[PAIR]
    saved = {"pair": PAIR, "token": TOKEN, "weth_is0": True, "N": N, "tier": "1.3-2.3", "stake": stake, "expect": expect, "min_out": expect * 97 // 100, "via": "logs", "aim": N + 1, "D": N + 1,
             "creation_ts": ts(N), "prio": 3 * 10 ** 7, "nonce": 7, "buy_hash": hb, "buy_nonce": 7, "buy_block": None, "tokens": None, "sell_sent": False, "sell_hash": None, "sell_hashes": [],
             "sell_nonce": None, "sell_prio": None, "sell_max_fee": None, "exit": None, "sell_min_out": None}
    json.dump({"positions": {PAIR: saved}}, open(E.S.POSITIONS_FILE, "w")); c.head = N + 4
    info = live_start(c)
    assert info["nonce"] == 8 and events("start")[0]["positions"] == [PAIR] and "sold at once" in wait_ev("alarm")[-1]["what"]
    s = wait_ev("sell_sent")[0]
    assert s["reason"] == "hard" and s["why"].startswith("restart") and s["min_out"] == 0 and s["nonce"] == 8 and s["via"] == "first" and len(c.sent) == 3, s
    d = "0x" + raw_sent(c, 1)["data"].hex(); assert d[2:10] == E.SEL_SELL and inaddr(d, 0) == TOKEN and inword(d, 1) == 0
    c.mine(N + 5); c.head = N + 5
    t = wait_ev("trade_done")[0]
    assert t["exit"] == "hard" and t["tokens"] == tokens and t["buy_block"] == N + 1 and t["sell_block"] == N + 5 and t["eth_out_wei"] == cp_out(tokens, *reversed(st.sync_at(N + 1))) * 0 + t["eth_out_wei"] > 0, t
    assert t["eth_in_wei"] == stake and t["nonce"] == 7 and json.load(open(E.S.POSITIONS_FILE))["positions"] == {} and E.state["nonce"] == 9 and not E.positions
    c2 = fresh(dry=False); c2.sent.append(("seq.example.org", raw)); c2.nonces.add(7); c2.mine(N + 1)
    raw_s = signed(KEY, 8, RELAY, 0, E.sell_data(TOKEN, 0, ts(N) + 60), 3 * 10 ** 7, 4 * 10 ** 7, 250_000); hs = hash_of(raw_s); c2.sent.append(("seq.example.org", raw_s)); c2.nonces.add(8); c2.mine(N + 9)
    saved.update(sell_sent=True, sell_hash=hs, sell_hashes=[hs], sell_nonce=8, exit="hard"); json.dump({"positions": {PAIR: saved}}, open(E.S.POSITIONS_FILE, "w")); c2.head = N + 10
    live_start(c2)
    t = wait_ev("trade_done")[0]
    assert t["exit"] == "hard" and t["sell_block"] == N + 9 and t["eth_out_wei"] > 0 and not events("sell_sent") and len(c2.sent) == 2 and "receipt is awaited" in events("alarm")[0]["what"], t


@test
def live_start_refusals():
    """a live start needs the wallet, the relay, the stake under its cap, the roster, the key file (the wallet's, unlocked), the relay's owner,
    router and weth, chain 8453 on every endpoint, the relay's code and the guard's self-test answering ok"""
    def refused(why, setup=None, **env):
        c = fresh(dry=False)
        if setup:
            setup(c)
        try:
            live_start(c, **env)
        except SystemExit as e:
            assert why in str(e), (why, str(e))
        else:
            raise AssertionError(f"started: {why}")
        return c
    refused("BASE_V2_WALLET is not set", BASE_V2_WALLET=""); refused("BASE_V2_RELAY is not set", BASE_V2_RELAY=""); refused("over BASE_V2_STAKE_CAP_ETH", BASE_V2_STAKE_ETH="0.05")
    refused("BASE_V2_ROSTER_FILE", BASE_V2_ROSTER_FILE=os.path.join(TMP, "none.json")); refused("does not hold a key", BASE_V2_KEY_FILE=os.path.join(TMP, "none.key"))
    refused("not BASE_V2_WALLET's", BASE_V2_WALLET="0x" + "ab" * 20)
    refused("owner()", lambda c: setattr(c, "owner", "0x" + "cd" * 20)); refused("router()", lambda c: setattr(c, "router", "0x" + "ef" * 20)); refused("weth()", lambda c: setattr(c, "weth", "0x" + "12" * 20))
    refused("chain 1", lambda c: c.chain_ids.update({"send2.example.org": 1})); refused("chain 10", lambda c: c.chain_ids.update({"alt.example.org": 10})); refused("chain 11", lambda c: c.chain_ids.update({"arch.example.org": 11}))
    refused("no code", lambda c: setattr(c, "relay_code", "0x")); refused("not SELLABLE", lambda c: setattr(c, "verdict", "taxed")); refused("found no pair of the line", lambda c: setattr(c, "archive_head", N - 10))
    c = fresh(dry=False); open(os.path.join(TMP, "k.key"), "w").write("0x" + bytes(KEY.key).hex()); held = open(os.path.join(TMP, "k.key")); fcntl.flock(held, fcntl.LOCK_EX)
    try:
        live_start(c); raise AssertionError("started with the key file locked")
    except SystemExit as e:
        assert "locked by another process" in str(e), str(e)
    held.close()
    c = fresh(dry=False); c.balance = 10 ** 14; c.chain_ids["seq.example.org"] = "send-only"
    info = live_start(c)
    assert info["chains"]["seq.example.org"] == "send-only" and info["chains"]["arch.example.org"] == 8453 and E.SIGNER is not None and E.state["nonce"] == 7 and E.KEY_LOCK is not None
    probe = open(os.path.join(TMP, "k.key"))
    try:
        fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB); raise AssertionError("the running engine does not hold the key file's lock")
    except BlockingIOError:
        pass
    probe.close()
    assert "under the stake + margin" in events("alarm")[0]["what"] and events("start")[0]["dry"] is False and E.state["relay_wei"] == 10 ** 14
    g = events("guard", self_test=True)[0]; assert g["verdict"] == "ok" and g["pair"] == PAIR and g["block"] == hex(N + 5) and g["src"] == "arch.example.org"
    assert bytes(KEY.key).hex() not in open(LOG).read() and "k3y" not in open(LOG).read() and not any(h == "alt.example.org" and m == "eth_call" and "roundTrip" in str(m) for h, m in c.calls)
    assert E.state["roster"] == set(FLEET) | {FLEET_KEY.address.lower()} and E.state["roster_built"] == "2026-10-20T00:00:00Z"


@test
def dry_start_reads_no_key():
    c = fresh(); E.SIGNER = None
    info = E.start(); st = events("start")[0]
    assert st["dry"] and E.SIGNER is None and info["head"] == c.head == N - 3 and not any(m == "eth_getTransactionCount" for _, m in c.calls) and st["wallet"] is None
    assert st["settings"]["RPC_URL"] == "rpc.example.org" and "KEY_FILE" not in st["settings"] and E.state["logs_to"] == c.head - 14 and st["roster_n"] == 12
    assert "k3y" not in open(LOG).read() and not events("guard") and E.KEY_LOCK is None
    c = fresh(); c.fail.add(("alt.example.org", "eth_chainId")); E.start()
    assert "BASE_V2_READ_ALT_URL did not answer" in events("alarm")[0]["what"] and "k3y" not in open(LOG).read()     # dry: an alarm, not a refusal


# ---------------------------------------------------------------- the feeds
@test
def silent_websocket_polls():
    """the websocket silent for WS_SILENT_S: the head and the logs from eth_getLogs one block behind the head; a creation seen that way
    arms and fires (at the poller's lag: LAND_MAX 2 lands it; the default refuses it as late)"""
    c = fresh(Stream("2.0"), BASE_V2_LAND_MAX="2"); E.state["ws_last"] = E.mono() - 60; E.state["started_at"] = E.mono() - 20; c.head = N + 1
    while E.poll_step():
        pass
    assert E.state["head"] == N + 1 and E.state["head_src"] == "poll" and E.state["logs_to"] == N and c.ranges[0] == (N - 1, N) and not E.ws_healthy()
    assert events("alarm")[0]["what"].startswith("no websocket") and events("creation")[0]["via"] == "logs"
    f = wait_ev("would_fire")[0]
    assert f["head"] == N + 1 and f["aim"] == N + 2 and f["via"] == "logs" and events("arm")[0]["block"] == N
    c.head = N + 3
    while E.poll_step():
        pass
    assert E.state["logs_to"] == N + 2 and E.positions[PAIR]["tokens"] is not None and E.state["filled"] == 4
    c = fresh(Stream("2.0")); E.state["ws_last"] = E.mono() - 60; c.head = N + 1
    while E.poll_step():
        pass
    s = wait_ev("skip")[0]; assert s["why"] == "late" and s["head"] == N + 1


@test
def websocket_drop_gap_filled():
    c = fresh(Stream("2.0"), BASE_V2_LAND_MAX="3"); feed(c, N - 2, N - 1)
    E.ws_down(ConnectionError("dropped"))                                     # down before N; back at N + 1
    assert events("alarm")[-1]["what"].startswith("the websocket is down") and not E.state["ws"]
    c.subs = {}; c.pend = {}
    E.on_ws_message(json.dumps({"jsonrpc": "2.0", "id": 1, "result": "0xh"}), c.subs, c.pend); E.on_ws_message(json.dumps({"jsonrpc": "2.0", "id": 2, "result": "0xl"}), c.subs, c.pend)
    head(c, N + 1)
    assert E.state["ws_from"] == N + 1 and E.state["logs_to"] == N - 2 and E.state["ws"]
    c.head = N + 1
    while E.poll_step():
        pass
    assert c.ranges[0][0] == N - 1 and c.ranges[-1][1] == N + 1 and E.state["logs_to"] == N + 1 and E.state["head_src"] == "ws"
    f = wait_ev("would_fire")[0]; assert f["head"] == N + 1 and f["aim"] == N + 2
    dups = E.state["dups"]; push(c, [l for l in c.streams[PAIR].rlogs if l["address"].lower() == FACTORY][0])     # the websocket's own copy: deduped
    assert E.state["dups"] == dups + 1 and len(events("creation")) == 1
    feed(c, N + 2, N + 4); assert E.positions[PAIR]["tokens"] is not None and E.state["logs_to"] == N + 3


@test
def duplicate_and_removed_logs():
    st = Stream("2.0"); c = fresh(st); fired(c); feed(c, N + 1, N + 15); P = E.pairs[PAIR]
    before = E.reserves(P)[:2]; sync = [l for l in st.logs if blk(l) == N + 15 and l["topics"][0] == T["Sync"]][0]
    push(c, sync); assert E.state["dups"] == 1 and E.reserves(P)[:2] == before, (E.state["dups"], before, E.reserves(P), sorted(E.seen.items())[-3:])
    push(c, dict(sync, removed=True))
    assert E.state["reorgs"] == 1 and E.reserves(P)[:2] == tuple(c.reserves_at(PAIR, N + 14)) and "reorg" in events("alarm")[-1]["what"]
    assert (N + 15, int(sync["logIndex"], 16)) not in P["ev"] and len(P["ev"]) == 5


@test
def confirmed_session_subscribes_followed_pairs():
    """the asyncio session on a stubbed websockets module: newHeads and the factory subscribed, one logs subscription per followed pair
    (added as pairs come), the burst's actions after every message; silent for WS_SILENT_S: the session ends, the reconnection follows"""
    st = Stream("2.0"); c = fresh(st, BASE_V2_WS_SILENT_S="1"); sent = []; conns = []
    sub = lambda sid, r: json.dumps({"jsonrpc": "2.0", "method": "eth_subscription", "params": {"subscription": sid, "result": r}})
    hd = lambda n: sub("0xh", {"number": hex(n), "timestamp": header(n)["timestamp"], "baseFeePerGas": header(n)["baseFeePerGas"]})

    class Conn:
        def __init__(self):
            self.q = asyncio.Queue(); self.n = 0
        async def __aenter__(self):
            conns.append(self); return self
        async def __aexit__(self, *a):
            return False
        async def send(self, m):
            d = json.loads(m); sent.append(d)
            if d["method"] == "eth_subscribe" and d["params"][0] == "newHeads":
                await self.q.put(json.dumps({"jsonrpc": "2.0", "id": d["id"], "result": "0xh"}))
            elif d["method"] == "eth_subscribe" and d["params"][1]["address"] == FACTORY:
                await self.q.put(json.dumps({"jsonrpc": "2.0", "id": d["id"], "result": "0xl"}))
                for n in (N - 2, N - 1):
                    await self.q.put(hd(n))
                await self.q.put(sub("0xl", [l for l in st.rlogs if l["address"].lower() == FACTORY][0]))
            elif d["method"] == "eth_subscribe":
                assert d["params"][1] == {"address": PAIR, "topics": [E.PAIR_TOPICS]}, d
                await self.q.put(json.dumps({"jsonrpc": "2.0", "id": d["id"], "result": "0xp1"}))
                for l in sorted([l for l in st.rlogs + st.logs if blk(l) == N and l["address"].lower() == PAIR and l["topics"][0] in E.PAIR_TOPICS], key=E.order):
                    await self.q.put(sub("0xp1", l))
                await self.q.put(hd(N))
        async def recv(self):
            return await self.q.get()                                          # then silent: the watchdog ends the session
    fake = types.ModuleType("websockets"); fake.connect = lambda *a, **k: Conn(); sys.modules["websockets"] = fake

    async def run():
        await asyncio.wait_for(E.confirmed_loop(), 2.6)
    try:
        asyncio.run(run())
    except (asyncio.TimeoutError, TimeoutError):
        pass
    finally:
        sys.modules.pop("websockets", None)
    assert len(conns) >= 2 and [d["params"][0] for d in sent[:2]] == ["newHeads", "logs"] and sent[1]["params"][1] == {"address": FACTORY, "topics": [[E.T_PC]]}, sent[:3]
    assert any(d["method"] == "eth_subscribe" and d["params"][1].get("address") == PAIR for d in sent if len(d["params"]) > 1) and E.pairs[PAIR]["sub"] in ("0xp1", None)
    assert events("creation")[0]["via"] == "logs" and events("would_fire")[0]["head"] == N and E.state["head"] == N
    a = [x["what"] for x in events("alarm")]
    assert any(x.startswith("the websocket is down") and "silent for 1 s" in x for x in a), a


@test
def flash_stream_reconnects_when_silent():
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
            await asyncio.sleep(3600)
    plan = [[msg(N), msg(N + 1)], [msg(N + 2), msg(N + 3), msg(N + 4)]]
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
    assert len(conns) >= 2 and E.state["flash_total"] == 5 and E.state["flash_block"] == N + 4 and E.state["flash_reconnects"] >= 1, (len(conns), E.state["flash_total"])
    i_false = next(i for i, x in enumerate(seen) if x[1] == 2 and not x[0])
    assert any(x[0] and x[1] == 5 for x in seen[i_false:]) and any(a["what"].startswith("Flashblocks is down") for a in events("alarm"))


@test
def flow_line_and_the_ticker():
    c = fresh(Stream("2.0")); fired(c); feed(c, N + 1, N + 3); E.state["flow_at"] = E.mono() - 61
    with E.lock:
        E.tick()
    f = events("flow")[0]
    assert f["head"] == N + 3 and f["ws"] and f["positions"] == [PAIR] and f["trades_today"] == 1 and f["followed"] == 1 and f["tradable"] == 1 and f["roster_n"] == 12, f
    assert f["ready_ms_last"] is not None and f["guard_ms_last"] is not None and f["logs_to"] == N + 2 and f["halted"] is None and f["tiers_ended"] == [] and f["head_src"] == "ws"
    assert "k3y" not in open(LOG).read()


if __name__ == "__main__":
    t0 = time.time(); n = 0
    only = sys.argv[1:]
    for fn in TESTS:
        if only and fn.__name__ not in only:
            continue
        fn(); n += 1
        print("ok", fn.__name__, flush=True)
    print(f"{n} tests passed in {time.time() - t0:.1f} s")
