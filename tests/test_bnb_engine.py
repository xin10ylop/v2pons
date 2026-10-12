"""The BNB Chain dry run (src/bnb_engine.py) against one real launch of the launcher 0xc9b7cc61: pair 0xea87b24f, block 127093739,
1 BNB, read from the public BNB RPC on Oct 12 (tests/data/bnb_launch.json, built by research/session_oct12/bnb/code/s2_engine_fixture.py):
its PairCreated and creating transaction, the pair's Sync/Mint/Swap logs to +1100 (the crowd's four buys at +80..+249, the creator's dump
at +1039: a sell through the router, as in every pool of this line, which never had a Burn), the swaps' transactions, a router launch of
another WBNB pair 65 blocks earlier and the USDT/WBNB pair's reserves. The RPC and the websocket are stubbed; nothing reaches a network.
Plain script: python3 tests/test_bnb_engine.py"""
import os, sys, json, copy, asyncio, tempfile, time, types, ast, re, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); LOG = tempfile.mktemp(suffix=".jsonl")
for k in [k for k in os.environ if k.startswith("BNB_")]:
    os.environ.pop(k)
os.environ.update({"BNB_LOG_PATH": LOG, "BNB_RPC_URL": "https://rpc.example.org/v1/k3y-rpc-secret", "BNB_WS_URL": "wss://ws.example.org/ws/k3y-ws-secret",
                   "BNB_WATCH_TO": "1100", "BNB_MAX_RANGE": "40"})
sys.path.insert(0, os.path.join(ROOT, "src"))
import bnb_engine as E
E.RETRY_S = 0; E.TX_NULL_PAUSE_S = 0                                         # no pauses between tries here

FX = json.load(open(os.path.join(ROOT, "tests", "data", "bnb_launch.json")))
L = FX["launch_block"]; PAIR = FX["pair"]; CREATOR = FX["launch_tx"]["from"]; ROUTER = E.ROUTER
w = lambda x: "%064x" % x
blk = lambda lg: int(lg["blockNumber"], 16)


# --- the stubbed chain
class Chain:
    def __init__(self):
        self.logs, self.txs, self.fail, self.calls = [], {}, [], {}
        self.usdt = FX["usdt_reserves"][str(L + 49)]

    def add(self, logs, txs):
        self.logs += logs
        self.txs.update({t["hash"]: t for t in txs})

    def rpc(self, method, params, tries=3, timeout=10):
        self.calls[method] = self.calls.get(method, 0) + 1
        if self.fail and self.fail[0][0] == method and self.fail[0][1] != "PASS":
            what = self.fail.pop(0)[1]
            if isinstance(what, Exception):
                raise what
            return what
        if self.fail and self.fail[0] == (method, "PASS"):
            self.fail.pop(0)
        if method == "eth_chainId":
            return "0x38"
        if method == "eth_blockNumber":
            return hex(L + 400)
        if method == "eth_call":
            return "0x" + w(int(FX["usdt_token0"], 16)) if params[0]["data"] == "0x0dfe1681" else self.usdt
        if method == "eth_getTransactionByHash":
            return copy.deepcopy(self.txs.get(params[0]))
        if method == "eth_getLogs":
            f = params[0]; a, b = int(f["fromBlock"], 16), int(f["toBlock"], 16)
            addrs = {x.lower() for x in ([f["address"]] if isinstance(f["address"], str) else f["address"])}; t0 = set(f["topics"][0])
            out = []
            for lg in self.logs:
                try:
                    ok = a <= blk(lg) <= b and lg["address"].lower() in addrs and lg["topics"][0] in t0
                except Exception:
                    ok = True                                                  # a malformed log reaches the engine as a node would hand it over
                if ok:
                    out.append(copy.deepcopy(lg))
            return out
        raise RuntimeError(method)


def clone(pair, shift=0, tag="00", logs=None, txs=None):
    """the fixture's launch as another pair (shifted by `shift` blocks, its transactions renamed with `tag`): pools that overlap"""
    rename = lambda h: h[:-2] + tag
    out = []
    lc = copy.deepcopy(FX["launch_log"]); lc["data"] = "0x" + "0" * 24 + pair[2:] + lc["data"][66:]
    for lg in [lc] + copy.deepcopy(logs if logs is not None else FX["pair_logs"]):
        if lg is not lc:
            lg["address"] = pair
        lg["blockNumber"] = hex(blk(lg) + shift); lg["transactionHash"] = rename(lg["transactionHash"]); out.append(lg)
    tx = [copy.deepcopy(t) for t in [FX["launch_tx"]] + list((txs if txs is not None else FX["txs"]).values())]
    for t in tx:
        t["hash"] = rename(t["hash"])
    return out, tx


def reset(chain):
    E.rpc = chain.rpc; E.pools.clear()
    E.state.update({"head": None, "head_at": 0.0, "head_src": None, "done_to": None, "launches": 0, "pairs_wbnb": 0, "pairs_unread": 0, "trades": [], "median_alarmed": False,
                    "price": None, "price_block": None, "fails": 0, "alarms_quiet": {}, "stop": False})
    open(LOG, "w").close()


def run(chain, a, b):
    reset(chain); E.state["done_to"] = a - 1; E.refresh_price(a)
    while E.state["done_to"] < b:
        E.step(replay_to=b)


def events(ev=None, pair=None):
    out = [json.loads(x) for x in open(LOG)]
    return [e for e in out if (ev is None or e["ev"] == ev) and (pair is None or e.get("pair") == pair)]


def reserves_before(logs, off):
    """(WBNB, token) after the last Sync of the pair before block L + off (the token is token0 here: WBNB is token1)"""
    r = (0, 0)
    for lg in logs:
        if lg["topics"][0] == E.T_SYNC and blk(lg) - L < off:
            d = lg["data"][2:]; r = (int(d[64:128], 16), int(d[:64], 16))
    return r


def replay(q, logs, a=50, b=260):
    """an independent exact-input replay: our buy at the start of L+a, every swap of [L+a, L+b) on the pool with it, our sale at L+b"""
    rq, rt = reserves_before(logs, a); tok = q * 9975 * rt // (rq * 10000 + q * 9975); sq, st = rq + q, rt - tok
    for lg in logs:
        if lg["topics"][0] == E.T_SWAP and a <= blk(lg) - L < b:
            d = lg["data"][2:]; t_in, q_in, t_out, q_out = (int(d[i:i + 64], 16) for i in range(0, 256, 64))
            if q_in > q_out:
                o = (q_in - q_out) * 9975 * st // (sq * 10000 + (q_in - q_out) * 9975); sq += q_in - q_out; st -= o
            else:
                o = (t_in - t_out) * 9975 * sq // (st * 10000 + (t_in - t_out) * 9975); sq -= o; st += t_in - t_out
    return tok, tok * 9975 * sq // (st * 10000 + tok * 9975)


GAS = int(round(370000 * 0.1e9))
r = FX["usdt_reserves"][str(L + 49)][2:]; Q = 15_000_000 * int(r[64:128], 16) * 10 ** 12 // int(r[:64], 16)   # $15 at the pair's price, to the wei

# 1. the launch is recognised; the router's WBNB launch 65 blocks earlier is not; the stake and the buy priced to the wei at L+50
ch = Chain(); ch.add([FX["launch_log"]] + FX["pair_logs"], [FX["launch_tx"]] + list(FX["txs"].values())); ch.add([FX["other_log"]], [FX["other_tx"]])
run(ch, L - 70, L + 300)
la = events("launch")
assert len(la) == 1 and la[0]["pair"] == PAIR and la[0]["L"] == L and la[0]["pool_bnb"] == 1.0 and la[0]["value_bnb"] == 1.0 and la[0]["creator"] == CREATOR, la
assert la[0]["wbnb_side"] == 1 and la[0]["skip"] is None and la[0]["token"] == "0x" + FX["launch_log"]["topics"][1][-40:] and E.state["pairs_wbnb"] == 2
wf = events("would_fire")
rq, rt = reserves_before(FX["pair_logs"], 50)
assert len(wf) == 1 and wf[0]["at"] == L + 50 and wf[0]["stake_wei"] == Q and (wf[0]["r_wbnb"], wf[0]["r_token"]) == (rq, rt) == (10 ** 18, 10 ** 18), wf
assert wf[0]["tokens"] == Q * 9975 * rt // (rq * 10000 + Q * 9975) == 19507677382189946 and abs(wf[0]["bnb_usd"] - 752.0432) < 1e-3 and wf[0]["swaps_before"] == 0
assert L + 50 <= wf[0]["ran_in_block"] <= L + 80                                # the pool's next log after L+49 is at +80: the same reserves until then
print("ok the decoder: the launcher's 50b6f139 call (196 bytes) with a WBNB PairCreated is a launch of 1 BNB (the first Mint) by its creator; the router's "
      "WBNB launch is not; the $15 stake at the USDT/WBNB pair's price and the buy at L+50 priced from the reserves to the wei")

# 2. the dry sale at L+260 from the real swaps (the crowd's four buys replayed on the pool with our buy in it), against an independent replay
td = events("trade_done")
tok, back = replay(Q, FX["pair_logs"])
assert len(td) == 1 and td[0]["tokens"] == tok and td[0]["back_wei"] == back and td[0]["dry_ret_gross"] == round((back - Q) / Q, 6), (td, tok, back)
assert td[0]["dry_ret"] == round((back - Q - GAS) / Q, 6) and abs(td[0]["dry_ret"] - 2.3046) < 1e-3 and not td[0]["pulled_before_sell"] and td[0]["dump_off"] is None
assert td[0]["crowd_buys"] == 4 and td[0]["crowd_bnb"] == 0.8556 and td[0]["first_crowd_off"] == 80 and td[0]["crowd_gate"] == 4 and td[0]["crowd_minout"] == 0.9999
assert td[0]["strangers"] == 0 and td[0]["sells"] == 0 and td[0]["entry_block_swaps"] == 0 and td[0]["breaks"] == 0 and not events("alarm"), events("alarm")
assert ch.calls["eth_getTransactionByHash"] == 2 + 4                           # the two WBNB pairs' creating transactions, the four buys before +260
assert td[0]["clean"] is True and L + 260 <= td[0]["sold_in_block"] <= L + 283     # (the next log after L+259 is at +283)
print("ok the dry sale at L+260: +%.1f%% (net of 370k gas at 0.1 gwei), the crowd's 4 buys of 0.8556 BNB from +80 with minOut 0.9999 of the price "
      "before each, no stranger, equal to an independent replay to the wei" % (100 * td[0]["dry_ret"]))

# 3. the research's own replay (verify/replay_..._83af7929/code/rp.py trade(), K=50 H=210, census events): the same tokens and BNB back to the wei
ch3 = Chain(); ch3.add([FX["launch_log"]] + FX["pair_logs"], [FX["launch_tx"]] + list(FX["txs"].values()))
_sw = E.stake_wei; E.stake_wei = lambda: 19945628469917928
run(ch3, L - 2, L + 300); E.stake_wei = _sw
td = events("trade_done")[0]
assert (td["tokens"], td["back_wei"]) == (19507644891997603, 65950139526826465), td
print("ok the research's replay of this pool (rp.trade, a stake of 19945628469917928 wei): tokens 19507644891997603, back 65950139526826465, the same")


# 3b. our buy is first in block L+50, our sale first in block L+260: crowd buys injected at L+49, L+50, L+259 and L+260 (an off-by-one shows)
def crowd_buy(rq, rt, off, a, n):
    """a crowd buy of `a` wei at L+off on reserves (rq, rt): its Sync and Swap (WBNB is token1) and its router transaction"""
    o = E.amount_out(a, rq, rt); h = "0x%064x" % (0xb00 + n); who = "0x%040x" % (0xc00 + n)
    logs = [{"address": PAIR, "topics": [E.T_SYNC], "data": "0x" + w(rt - o) + w(rq + a), "blockNumber": hex(L + off), "transactionHash": h, "logIndex": "0x1"},
            {"address": PAIR, "topics": [E.T_SWAP, "0x" + w(int(ROUTER, 16)), "0x" + w(int(who, 16))], "data": "0x" + w(0) + w(a) + w(o) + w(0),
             "blockNumber": hex(L + off), "transactionHash": h, "logIndex": "0x2"}]
    return logs, {"hash": h, "from": who, "to": ROUTER, "input": "0x7ff36ab5" + w(o * 9999 // 10000) + w(128) + w(int(who, 16)) + w(0)}, rq + a, rt - o


logs3 = [x for x in FX["pair_logs"] if blk(x) == L]; txs3 = [FX["launch_tx"]]; rq3, rt3 = 10 ** 18, 10 ** 18
for n, (off, a) in enumerate([(49, 10 ** 17), (50, 2 * 10 ** 17), (259, 3 * 10 ** 17), (260, 4 * 10 ** 17)]):
    lg_, tx_, rq3, rt3 = crowd_buy(rq3, rt3, off, a, n); logs3 += lg_; txs3.append(tx_)
ch3b = Chain(); ch3b.add([FX["launch_log"]] + logs3, txs3)
run(ch3b, L - 2, L + 300)
wf, td = events("would_fire")[0], events("trade_done")[0]; tok3, back3 = replay(Q, logs3)
assert wf["ran_in_block"] == L + 50 and (wf["r_wbnb"], wf["r_token"]) == reserves_before(logs3, 50) and wf["r_wbnb"] == 11 * 10 ** 17 and wf["tokens"] == tok3, wf
assert td["sold_in_block"] == L + 260 and td["back_wei"] == back3 and td["crowd_ahead"] == 1 and td["crowd_buys"] == 2 and td["crowd_bnb"] == 0.5, td
assert td["first_crowd_off"] == 49 and td["entry_block_swaps"] == 1 and td["crowd_gate"] == 1 and td["clean"] and abs(td["crowd_minout"] - 0.9999) < 1e-6, td
print("ok the boundaries: the buy priced in block L+50 after the +49 buy and before the +50 one, the sale in block L+260 after the +259 buy and "
      "before the +260 one (ran_in_block, sold_in_block), equal to the independent replay; +49 counts ahead of us, +50 and +259 in the hold")

# 4. the creator's dump: a sell taking the whole WBNB reserve at +1039, after the sale: logged, by the creator, no gate alarm
run(ch, L - 2, L + 1100)
du = events("dump"); pd = events("pool_done")
assert len(du) == 1 and du[0]["off"] == 1039 and du[0]["kind"] == "sell" and du[0]["by_creator"] is True and du[0]["share"] >= 0.9999 and du[0]["traded"], du
assert len(pd) == 1 and pd[0]["dump_off"] == 1039 and pd[0]["traded"] and PAIR not in E.pools and not [a for a in events("alarm") if "gate" in a["what"]]
print("ok the creator's dump at +1039 (a router sell of 100,000 tokens, 99.99% of the WBNB reserve): dump and pool_done lines, the pool dropped, no gate alarm")


# 4b. the same launch with WBNB as token0 (every log mirrored): the same lines, field for field, but the side
def mirror(lg):
    m = copy.deepcopy(lg); d = m["data"][2:]; ws_ = [d[i:i + 64] for i in range(0, len(d), 64)]
    if m["topics"][0] == E.T_PC:
        m["topics"] = [m["topics"][0], m["topics"][2], m["topics"][1]]
    elif m["topics"][0] in (E.T_SYNC, E.T_MINT, E.T_BURN):
        m["data"] = "0x" + ws_[1] + ws_[0] + "".join(ws_[2:])
    elif m["topics"][0] == E.T_SWAP:
        m["data"] = "0x" + ws_[1] + ws_[0] + ws_[3] + ws_[2]
    return m


lines = lambda: [{k: v for k, v in e.items() if k != "t"} for e in events() if e["ev"] in ("launch", "would_fire", "trade_done", "dump", "pool_done")]
base = lines(); chm = Chain(); chm.add([mirror(FX["launch_log"])] + [mirror(x) for x in FX["pair_logs"]], [FX["launch_tx"]] + list(FX["txs"].values()))
run(chm, L - 2, L + 1100); mirr = lines()
assert base[0]["wbnb_side"] == 1 and mirr[0]["wbnb_side"] == 0 and len(mirr) == len(base) == 5
mirr[0]["wbnb_side"] = 1
assert mirr == base, (mirr, base)
print("ok WBNB as token0: the mirrored launch gives the same launch, would_fire, trade_done, dump and pool_done lines field for field")

# 5. a dump before the sell is -1.0: the creator's sell moved to +200 (built on the real reserves after +186), and a Burn of 60% at +150
rq, rt = reserves_before(FX["pair_logs"], 200); t_in = 10 ** 23; q_out = E.amount_out(t_in, rt, rq); HX = "0x" + "d0" * 32
early = [lg for lg in FX["pair_logs"] if blk(lg) - L < 200]
dump = [{"address": PAIR, "topics": [E.T_SYNC], "data": "0x" + w(rt + t_in) + w(rq - q_out), "blockNumber": hex(L + 200), "transactionHash": HX, "logIndex": "0x1"},
        {"address": PAIR, "topics": [E.T_SWAP, "0x" + w(int(ROUTER, 16)), "0x" + w(int(ROUTER, 16))], "data": "0x" + w(t_in) + w(0) + w(0) + w(q_out),
         "blockNumber": hex(L + 200), "transactionHash": HX, "logIndex": "0x2"}]
ch5 = Chain(); ch5.add([FX["launch_log"]] + early + dump, [FX["launch_tx"]] + list(FX["txs"].values()) + [{"hash": HX, "from": CREATOR, "to": ROUTER, "input": "0x18cbafe5"}])
run(ch5, L - 2, L + 400)
td = events("trade_done"); al = [a["what"] for a in events("alarm")]
assert len(td) == 1 and td[0]["dry_ret"] == -1.0 and td[0]["pulled_before_sell"] and td[0]["dump_off"] == 200 and td[0]["crowd_buys"] == 3 and td[0]["sells"] == 1, td
assert any(a.startswith("gate: a dump at +200, before +997") for a in al) and events("dump")[0]["by_creator"] and PAIR not in E.pools, al
rq, rt = reserves_before(FX["pair_logs"], 150); lp = 6 * 10 ** 17                # a Burn of 60% of the liquidity (the pool's LP supply is 1e18)
burn = [{"address": PAIR, "topics": [E.T_SYNC], "data": "0x" + w(rt - rt * 6 // 10) + w(rq - rq * 6 // 10), "blockNumber": hex(L + 150), "transactionHash": HX, "logIndex": "0x1"},
        {"address": PAIR, "topics": [E.T_BURN, "0x" + w(int(ROUTER, 16)), "0x" + w(int(CREATOR, 16))], "data": "0x" + w(rt * 6 // 10) + w(rq * 6 // 10),
         "blockNumber": hex(L + 150), "transactionHash": HX, "logIndex": "0x2"}]
ch5b = Chain(); ch5b.add([FX["launch_log"]] + [lg for lg in FX["pair_logs"] if blk(lg) - L < 150] + burn, [FX["launch_tx"]] + list(FX["txs"].values()) + [{"hash": HX, "from": CREATOR, "to": ROUTER, "input": "0x02751cec"}])
run(ch5b, L - 2, L + 400)
td = events("trade_done")
assert len(td) == 1 and td[0]["dry_ret"] == -1.0 and events("dump")[0]["kind"] == "burn" and events("dump")[0]["share"] == 0.6 and td[0]["dump_off"] == 150, td
print("ok a dump before the sell: the creator's sell at +200 (all the WBNB) and a Burn of 60% at +150 each give dry_ret -1.0, pulled_before_sell, "
      "and the gate alarm 'a dump before +997'")

# 5b. the dump's threshold: a sell of 49.9% of the WBNB reserve at +200 is a sell (replayed on our copy), one of 50.1% is the dump
for share in (499, 501):
    rq, rt = reserves_before(FX["pair_logs"], 200); q_out = rq * share // 1000; t_in = rt * q_out * 10000 // ((rq - q_out) * 9975) + 1; HS = "0x%064x" % (0xe00 + share)
    sl = [{"address": PAIR, "topics": [E.T_SYNC], "data": "0x" + w(rt + t_in) + w(rq - q_out), "blockNumber": hex(L + 200), "transactionHash": HS, "logIndex": "0x1"},
          {"address": PAIR, "topics": [E.T_SWAP, "0x" + w(int(ROUTER, 16)), "0x" + w(int(ROUTER, 16))], "data": "0x" + w(t_in) + w(0) + w(0) + w(q_out),
           "blockNumber": hex(L + 200), "transactionHash": HS, "logIndex": "0x2"}]
    chs = Chain(); chs.add([FX["launch_log"]] + early + sl, [FX["launch_tx"]] + list(FX["txs"].values()) + [{"hash": HS, "from": CREATOR, "to": ROUTER, "input": "0x18cbafe5"}])
    run(chs, L - 2, L + 300); td = events("trade_done")
    if share == 499:
        assert len(td) == 1 and td[0]["back_wei"] == replay(Q, early + sl)[1] and not td[0]["pulled_before_sell"] and not events("dump") and td[0]["sells"] == 1, td
    else:
        assert len(td) == 1 and td[0]["dry_ret"] == -1.0 and td[0]["dump_off"] == 200 and events("dump")[0]["share"] == 0.501, td
print("ok the dump's threshold (BNB_DUMP_SHARE 0.5): a sell of 49.9% of the WBNB at +200 is replayed on our copy and the trade sold at +260; "
      "50.1% is the dump, -1.0")

# 6. another launcher, another selector, another calldata length: ignored; a 15-BNB pool: a launch line, skipped, no buy
P6 = "0x" + "66" * 20; ch6 = Chain(); bad = []
for i, (to, inp) in enumerate([("0x" + "12" * 20, FX["launch_tx"]["input"]), (E.LAUNCHER, "0xdeadbeef" + FX["launch_tx"]["input"][10:]), (E.LAUNCHER, FX["launch_tx"]["input"] + "00" * 32)]):
    lg, tx = clone("0x" + ("7%d" % i) * 20, tag="a%d" % i); tx[0]["to"] = to; tx[0]["input"] = inp; ch6.add(lg, tx)
lg15 = [x for x in FX["pair_logs"] if blk(x) == L]
lg15 = [dict(x, data=x["data"][:66] + w(15 * 10 ** 18)) for x in lg15]           # the launch's Sync and Mint with 15 BNB on the WBNB side
lg, tx = clone(P6, tag="b6", logs=lg15); ch6.add(lg, tx)
run(ch6, L - 2, L + 300)
la = events("launch")
assert len(la) == 1 and la[0]["pair"] == P6 and la[0]["pool_bnb"] == 15.0 and "skipped" in la[0]["skip"] and not events("would_fire") and not events("trade_done"), la
assert P6 in E.pools and E.state["pairs_wbnb"] == 4 and not events("alarm")    # still watched for its dump (the gate looks at every pool of the line)
print("ok a WBNB pair from another contract, the launcher with another selector or calldata length: not launches; a 15-BNB pool: its launch "
      "line says skipped (BNB_SKIP_POOL_BNB), no buy, watched for its dump")

# 7. pools overlap: the launch and a copy 20 blocks later are followed at once, each bought at its own L+50 and sold at its own L+260
P7 = "0x" + "77" * 20; ch7 = Chain(); ch7.add([FX["launch_log"]] + FX["pair_logs"], [FX["launch_tx"]] + list(FX["txs"].values()))
lg, tx = clone(P7, shift=20, tag="c7"); ch7.add(lg, tx)
reset(ch7); E.state["done_to"] = L - 3; E.refresh_price(L)
opened = 0
while E.state["done_to"] < L + 300:
    E.step(replay_to=L + 300); opened = max(opened, sum(1 for p in E.pools.values() if p["fired"] and not p["sold"]))
wf, td = events("would_fire"), events("trade_done")
assert [x["at"] for x in wf] == [L + 50, L + 70] and [x["pair"] for x in td] == [PAIR, P7] and opened == 2 and td[0]["dry_ret"] == td[1]["dry_ret"], (wf, td)
print("ok two pools at once: both bought (L+50, L+70), both open together, both sold at their own L+260 with the same result")

# 8. a malformed block never crashes: bad logs, an RPC that fails, a node answer that is not a list, a range skipped after 3 failures
ch8 = Chain(); ch8.add([FX["launch_log"]] + FX["pair_logs"], [FX["launch_tx"]] + list(FX["txs"].values()))
ch8.logs += [{"address": PAIR, "topics": [E.T_SWAP], "data": "0x" + w(1), "blockNumber": hex(L + 100), "transactionHash": "0x01", "logIndex": "0x0"},
             {"address": PAIR, "topics": [E.T_SYNC], "data": "0x1234", "blockNumber": hex(L + 101), "transactionHash": "0x02", "logIndex": "0x0"},
             {"address": E.FACTORY, "data": "0x", "blockNumber": hex(L + 102), "logIndex": "0x0"}, {"address": PAIR, "topics": [E.T_SYNC], "blockNumber": "0xzz"}, "garbage"]
ch8.fail = [("eth_getLogs", RuntimeError("eth_getLogs: limit exceeded")), ("eth_getLogs", {"not": "a list"})]
run(ch8, L - 2, L + 300)
td = events("trade_done"); al = [a["what"] for a in events("alarm")]
assert len(td) == 1 and td[0]["tokens"] == tok and td[0]["back_wei"] == back and td[0]["breaks"] >= 3 and td[0]["clean"] is False, td   # its bad logs flag it
assert sum(1 for a in al if a.startswith("a log was not understood")) == 1 and sum(1 for a in al if "not read" in a) == 1, al   # each kind once a minute
assert "k3y" not in open(LOG).read()                                           # the traces scrubbed too
ch8.fail = [("eth_getLogs", "PASS"), ("eth_getLogs", {"not": "a list"})]                 # the launch's own logs: an answer that is not a list
run(ch8, L - 2, L + 300)
assert any(a["what"].startswith("a launch's own logs were not read") for a in events("alarm")) and events("pool_done")[0]["why"] == "logs not read" and not events("would_fire")
print("ok malformed logs (short data, no topics, a bad block number, not an object), a failed eth_getLogs and an answer that is not a list: alarms, "
      "no crash, the same numbers, and the trade flagged (breaks, clean false) for its pool's bad logs; a launch whose own logs are not read "
      "is dropped with an alarm")

# 8b. a range that fails is never skipped: 7 failures leave the reader where it was, the 8th try reads it, the trade clean; live, a head
# MAX_BEHIND ahead makes the jump: the open trade gets a line with no result (dry_ret null, gaps 1, not clean) and the pool is dropped
ch8c = Chain(); ch8c.add([FX["launch_log"]] + FX["pair_logs"], [FX["launch_tx"]] + list(FX["txs"].values())); ch8c.fail = [("eth_getLogs", RuntimeError("down"))] * 7
reset(ch8c); E.state["done_to"] = L - 3; E.refresh_price(L)
for _ in range(7):
    E.step(replay_to=L + 300)
assert E.state["done_to"] == L - 3 and E.state["fails"] == 7
while E.state["done_to"] < L + 300:
    E.step(replay_to=L + 300)
td = events("trade_done")
assert len(td) == 1 and td[0]["back_wei"] == back and td[0]["clean"] and not any("skipped" in a["what"] for a in events("alarm")), td
run(ch8c, L - 2, L + 100)
assert events("would_fire") and not events("trade_done")
E.state["head"] = L + 100 + E.MAX_BEHIND + 50; E.state["head_at"] = time.monotonic(); E.step()
td = events("trade_done")
assert len(td) == 1 and td[0]["dry_ret"] is None and td[0]["gaps"] == 1 and td[0]["clean"] is False and events("pool_done")[0]["why"] == "the reader jumped" and not E.pools, td
print("ok a range that fails is tried again (7 times here), never skipped, and then read: the same clean trade; the jump past MAX_BEHIND "
      "leaves the open trade a line with no result, flagged (gaps 1)")

# 8c. a WBNB pair's creating transaction: an error, or null 6 times: not a launch, an alarm and pairs_unread; null twice: read on the 3rd try
for fail, launched, why in (([("eth_getTransactionByHash", RuntimeError("HTTP Error 429: Too Many Requests"))], False, "429"),
                            ([("eth_getTransactionByHash", None)] * 6, False, "null each time"), ([("eth_getTransactionByHash", None)] * 2, True, None)):
    ch8c.fail = list(fail); run(ch8c, L - 2, L + 300); al = [a["what"] for a in events("alarm")]
    assert len(events("launch")) == launched and E.state["pairs_unread"] == (0 if launched else 1), (why, al)
    assert launched or any(a.startswith("a WBNB pair's creating transaction was not read") and why in a for a in al), al
print("ok a launch's creating transaction: an error or null 6 times is an alarm and a count (pairs_unread), never a launch; null twice is "
      "tried again and read")

# 9. the gate: no crowd buy in +60..+260 (the four buys made strangers' by their transactions), a negative median over the first 10 trades
txs9 = copy.deepcopy(FX["txs"])
for t in txs9.values():
    if t["to"] == ROUTER and t["input"].startswith("0x7ff36ab5"):
        t["to"] = "0x" + "99" * 20
ch9 = Chain(); ch9.add([FX["launch_log"]] + FX["pair_logs"], [FX["launch_tx"]] + list(txs9.values()))
run(ch9, L - 2, L + 300)
td = events("trade_done")[0]; al = [a["what"] for a in events("alarm")]
assert td["crowd_buys"] == 0 and td["strangers"] == 4 and abs(td["stranger_bnb"] - 0.8556) < 1e-9 and td["first_crowd_off"] is None, td
assert any(a.startswith("gate: no crowd buy in +60..+260") for a in al), al
reset(ch9)
for x in (0.3, -0.1, -0.2, 0.05, -0.01, -0.3, 0.2, -0.05, -0.4, 0.1):
    E.gate_probe(x)
E.gate_probe(-1.0)
al = [a["what"] for a in events("alarm")]
assert al == ["gate: the median of the first 10 dry trades is -3.00%"], al
assert len(E.state["trades"]) == 10                                             # later trades are not kept
reset(ch9)
for x in [0.1] * 6 + [-1.0] * 4:
    E.gate_probe(x)
assert not events("alarm")
print("ok the gate as alarms: no crowd buy in +60..+260 (the same buys from another contract are strangers), a negative median over the first 10 "
      "trades (once); a positive median: none")


# 10. the websocket: newHeads subscribed, heads taken, a dropped connection reconnected, a refused subscription and a bad message survived
class FakeWS:
    def __init__(self, script):
        self.script, self.sent = list(script), []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def send(self, m):
        self.sent.append(json.loads(m))

    async def recv(self):
        await asyncio.sleep(0)
        x = self.script.pop(0)
        if isinstance(x, Exception):
            raise x
        if x == "STOP":
            E.state["stop"] = True; return json.dumps({"jsonrpc": "2.0", "id": 9, "result": None})
        return x


head = lambda n: json.dumps({"jsonrpc": "2.0", "method": "eth_subscription", "params": {"subscription": "0xab", "result": {"number": hex(n), "timestamp": hex(int(time.time()))}}})
conns = [FakeWS([json.dumps({"jsonrpc": "2.0", "id": 1, "result": "0xab"}), head(L + 1), head(L + 2), "not json", head(L + 3), ConnectionResetError("reset by peer at wss://ws.example.org/ws/k3y-ws-secret")]),
         FakeWS([json.dumps({"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "subscriptions disabled"}})]),
         FakeWS([json.dumps({"jsonrpc": "2.0", "id": 1, "result": "0xac"}), head(L + 4), "STOP"])]
used = []
sys.modules["websockets"] = types.SimpleNamespace(connect=lambda url, **kw: (used.append((url, kw)), conns[len(used) - 1])[1])
reset(Chain())
asyncio.run(asyncio.wait_for(E.feed_loop(), timeout=10))                       # two reconnects: 0.5 s, then 1 s
assert len(used) == 3 and all(c.sent == [{"jsonrpc": "2.0", "id": 1, "method": "eth_subscribe", "params": ["newHeads"]}] for c in conns), used
assert E.state["head"] == L + 4 and E.state["head_src"] == "ws" and len(events("feed_connected")) == 3 and len(events("feed_error")) == 2, events()
assert [a["what"][:40] for a in events("alarm")] == ["a websocket message was not understood: "] and all(e["host"] == "ws.example.org" for e in events("feed_connected"))
assert [e["retry_s"] for e in events("feed_error")] == [0.5, 1.0]               # heads over a connection younger than 60 s do not reset it
E.WS_STABLE_S = 0; reset(Chain()); used.clear()
conns = [FakeWS([json.dumps({"jsonrpc": "2.0", "id": 1, "result": "0xab"}), head(L + 5 + i), ConnectionResetError("reset")]) for i in range(2)] \
    + [FakeWS([json.dumps({"jsonrpc": "2.0", "id": 1, "result": "0xab"}), head(L + 9), "STOP"])]
asyncio.run(asyncio.wait_for(E.feed_loop(), timeout=10)); E.WS_STABLE_S = 60
assert [e["retry_s"] for e in events("feed_error")] == [0.5, 0.5], events("feed_error")   # a lasting connection with heads resets it
reset(Chain()); E.state["head"] = L + 5
assert E.on_ws_message(head(L + 5)) is False and E.state["head_at"] == 0.0     # the same number again: not a new head
assert E.on_ws_message(head(L + 6)) is True and E.state["head_at"] > 0 and E.state["head"] == L + 6
print("ok the websocket: eth_subscribe newHeads on each connection, the newest head taken, a reset connection and a refused subscription each "
      "reconnected (0.5 s, then 1 s; back to 0.5 s only after heads over a connection 60 s old), a repeated head number is not a head, a "
      "message that is not JSON an alarm; only the host is logged")

# 11. the head without the websocket: eth_blockNumber after 3 s of silence; the flow line; the start line (hosts only) and a replay through main()
reset(ch); E.state["head"] = L + 10; E.state["head_at"] = time.monotonic()
assert E.current_head() == L + 10 and "eth_blockNumber" not in ch.calls
E.state["head_at"] -= 5
assert E.current_head() == L + 400 and E.state["head_src"] == "poll" and len(events("feed_fallback")) == 1
E.state["done_to"] = L + 390; E.flow(force=True); fl = events("flow")[-1]
assert fl["lag_blocks"] == 10 and fl["feed"] == "poll" and {"blocks", "launches", "launches_new", "pairs_wbnb", "watching", "open", "bnb_usd", "head_age_s"} <= set(fl), fl
reset(ch); E.main(["--replay", str(L - 2), str(L + 300)])
st = events("start")[0]; text = open(LOG).read()
assert st["dry_run"] is True and st["ws"] == "ws.example.org" and st["rpc"] == "rpc.example.org" and st["chain"] == 56 and st["bnb_usd_src"] == "chain", st
assert len(events("trade_done")) == 1 and events("replay_done") and "k3y" not in text and "secret" not in text
reset(ch); E.state["head_at"] = time.monotonic() - 10; ch.fail = [("eth_blockNumber", RuntimeError("Temporary failure in name resolution"))] * 7; waits = []
for _ in range(7):
    E.state["polled_at"] = -100.0; E.current_head(); waits.append(E.state["poll_wait"])
n0 = ch.calls["eth_blockNumber"]; E.current_head()
assert waits == [1.0, 2.0, 4.0, 8.0, 16.0, 30.0, 30.0] and ch.calls["eth_blockNumber"] == n0, waits      # not asked again before its wait
E.state["polled_at"] = -100.0
assert E.current_head() == L + 400 and E.state["poll_wait"] == 0.5
print("ok without heads from the websocket the reader polls eth_blockNumber (a feed_fallback line), every 0.5 s, doubling to 30 s while it "
      "fails, back to 0.5 s on an answer; the flow line (blocks, launches, lag, pools); main() --replay: the start line with the endpoints' "
      "hosts only, the same trade")

# 11b. the start: an RPC that does not answer is waited for (up to START_WAIT_S), then an exit; --replay refuses the service's own log
chx = Chain(); reset(chx); E.START_WAIT_S = 0; chx.fail = [("eth_chainId", RuntimeError("Temporary failure in name resolution"))]
try:
    E.checks(); raise AssertionError("no exit")
except SystemExit as e:
    assert "did not answer" in str(e)
E.START_WAIT_S = 5; chx.fail = [("eth_chainId", RuntimeError("Temporary failure in name resolution"))]
assert E.checks()["chain"] == 56 and any(a["what"].startswith("BNB_RPC_URL did not answer at the start") for a in events("alarm"))
E.START_WAIT_S = 300; chx = Chain(); reset(chx); _lp = E.LOG_PATH; E.LOG_PATH = E.DEFAULT_LOG
try:
    E.main(["--replay", str(L), str(L + 1)]); raise AssertionError("no refusal")
except SystemExit as e:
    assert "BNB_LOG_PATH" in str(e)
finally:
    E.LOG_PATH = _lp
assert not chx.calls and not events()
print("ok the start: the RPC not answering is an alarm and a wait (1 s doubling) up to START_WAIT_S, then an exit for systemd; --replay "
      "refuses to write into the service's log")

# 12. dry run only: the engine imports only the standard modules it reads with and websockets, and calls only reading RPC methods
tree = ast.parse(open(os.path.join(ROOT, "src", "bnb_engine.py")).read()); mods, called = set(), set()
for n in ast.walk(tree):
    if isinstance(n, ast.Import):
        mods |= {a.name.split(".")[0] for a in n.names}
    elif isinstance(n, ast.ImportFrom):
        mods.add((n.module or "").split(".")[0])
    elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "rpc":
        assert isinstance(n.args[0], ast.Constant), ast.dump(n)[:120]; called.add(n.args[0].value)       # no method chosen at run time
    elif isinstance(n, ast.Dict):
        for k, v in zip(n.keys, n.values):
            if isinstance(k, ast.Constant) and k.value == "method":
                assert isinstance(v, ast.Constant) or (isinstance(v, ast.Name) and v.id == "method"), ast.dump(v)
                called |= {v.value} if isinstance(v, ast.Constant) else set()
READ = {"eth_blockNumber", "eth_call", "eth_chainId", "eth_getLogs", "eth_getTransactionByHash", "eth_subscribe"}
named = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and re.fullmatch(r"eth_\w+", n.value)}
assert mods <= {"os", "sys", "json", "time", "asyncio", "threading", "traceback", "statistics", "signal", "urllib", "websockets"}, mods
assert called <= READ and called >= {"eth_getLogs", "eth_subscribe"} and named <= READ | {"eth_subscription"}, (called, named)   # (the notification's name)
print("ok dry run only: the engine imports os, sys, json, time, asyncio, threading, traceback, statistics, signal, urllib and websockets only, "
      "and names no RPC method but eth_blockNumber, eth_call, eth_chainId, eth_getLogs, eth_getTransactionByHash and eth_subscribe")

# 12b. scrub: a URL's key never reaches the log, whole or in pieces (its path, its query, user:password@); a trace keeps its tail
_ru = E.RPC_URL; E.RPC_URL = "https://u:pw@rpc.example.org/v1/k3y?apikey=s3cr3t"
t = E.scrub("POST https://u:pw@rpc.example.org/v1/k3y?apikey=s3cr3t failed; GET /v1/k3y?apikey=s3cr3t as u:pw")
assert all(x not in t for x in ("k3y", "s3cr3t", "pw")) and "rpc.example.org" in t, t
assert E.scrub("x" * 500 + "the end", 7, tail=True) == "the end" and len(E.scrub("y" * 500)) == 200
E.RPC_URL = _ru
print("ok scrub: an endpoint's URL is its host in the log, and its path, query and user:password@ are removed wherever they appear")

# 13. the screen: trades with a missed log or a gap left out and counted; the gate's median over the first 10 clean trades since the
# engine's last start, from all the logs kept (a rotated one included), not the window's; the dump gate's offset from the start line; a slow reader
now = time.time(); S = tempfile.mktemp(suffix=".jsonl")
start = lambda t, gb: {"ev": "start", "t": t, "release": "bnb-0.1", "stake_usd": 15, "buy_at": 50, "sell_at": 260, "skip_pool_bnb": [15.0], "gate": {"dump_before": gb, "crowd_from": 60, "probes": 10}}
trade = lambda t, i, ret, **kw: dict({"ev": "trade_done", "dry": True, "t": t, "pair": "0x%040x" % i, "pool_bnb": 25.0, "dry_ret": ret, "breaks": 0, "gaps": 0,
                                      "crowd_gate": 1, "crowd_buys": 1, "crowd_bnb": 0.5, "pulled_before_sell": False, "why": "sell at +260"}, **kw)
rets = [0.05, 0.10, -0.02, 0.20, 0.01, 0.30, -0.10, 0.07, 0.03, 0.04, 0.50, 0.60]
old = [start(now - 40 * 3600, 997)] + [trade(now - 39 * 3600 + i, i, -0.5) for i in range(3)] + [start(now - 30 * 3600, 1500)] \
    + [trade(now - (29 - i) * 3600, 10 + i, rets[i]) for i in range(3)]
new = [trade(now - 10 * 3600 + i * 1800, 20 + i, x) for i, x in enumerate(rets[3:])] + [trade(now - 9.9 * 3600, 40, -0.9, breaks=1), trade(now - 9.8 * 3600, 41, None, gaps=1)] \
    + [{"ev": "dump", "t": now - 3600, "pair": "0x" + "42" * 20, "pool_bnb": 1.0, "off": 1200, "kind": "sell"}, {"ev": "flow", "t": now - 30, "blocks": 30, "done_to": 1, "lag_blocks": 2}]
open(S + ".1", "w").write("".join(json.dumps(e) + "\n" for e in old)); open(S, "w").write("".join(json.dumps(e) + "\n" for e in new))
out = subprocess.run([sys.executable, os.path.join(ROOT, "deploy", "bnb_results.py"), "24"], env=dict(os.environ, BNB_LOG_PATH=S), capture_output=True, text=True).stdout
allrow = next(x for x in out.splitlines() if x.strip().startswith("all "))
assert re.search(r"\|\s+9\s+\+18\.3%\s+\+7\.0%", allrow) and "LEFT OUT of every number above and of the gate: 2 dry trade(s)" in out, out   # 9 clean in the window
assert re.search(r"median of the first 10 since [-0-9: ]+:\s+\+4\.5%", out) and "SLOW: 30 blocks" in out, out             # rets[:10]: +4.5%
assert re.search(r"a dump before \+1500:\s+TRIPPED x1", out) and "<+1500" in out, out
for f in (S, S + ".1"):
    os.remove(f)
print("ok the screen: 2 flagged trades left out of the statistics and the gate and counted; the median of the first 10 clean trades since the "
      "engine's start read from the rotated log too (+4.5%, not the window's); the dump gate's +1500 from the start line; a slow flow line warned")


# ================================================================================ the LIVE path (BNB_LIVE=1: src/bnb_live.py)
# Every transaction below is signed with a dummy key made up for these tests and goes nowhere: eth_sendRawTransaction is a stub that
# decodes what it is given (rlp, the sender recovered, the calldata ABI-decoded), checks the nonce and plays the chain's part.
assert "bnb_live" not in sys.modules and E.LIVE is None                      # every dry test above ran without the live module
try:
    from eth_account import Account
    from eth_utils import keccak
    import rlp, eth_abi
except ImportError:
    print("SKIP the live path's tests: eth_account is not installed for this python (/opt/flip-venv/bin/python3 has it)")
    os.remove(LOG); sys.exit(0)
import http.server, threading, stat, shutil, statistics
import bnb_live as LV

ART = json.load(open(os.path.join(ROOT, "contracts", "BnbRoundTrip.json")))
KEY = "0x" + "5e" * 32                                                        # a dummy key for these tests only, never funded
WALLET = Account.from_key(KEY).address.lower(); TOKEN = "0x" + FX["launch_log"]["topics"][1][-40:]; WBNB = E.WBNB
TMP = tempfile.mkdtemp(); KEYF = os.path.join(TMP, "bnb.key"); POSF = os.path.join(TMP, "bnb_positions.json"); HALTF = os.path.join(TMP, "HALTED.bnb")
_fd = os.open(KEYF, os.O_WRONLY | os.O_CREAT, 0o600); os.write(_fd, (KEY + "\n").encode()); os.close(_fd)
LIVE_ENV = {"BNB_WALLET": WALLET, "BNB_KEY_FILE": KEYF, "BNB_POSITIONS_FILE": POSF, "BNB_HALT_FILE": HALTF, "BNB_SEND_ALT_URL": "0"}
TT = LV.T_TRANSFER; tp = lambda x: "0x" + w(int(x, 16))
G_BUY, G_APP, G_SELL = 131050, 46409, 106800                                   # gasUsed of the three calls (eth_simulateV1 on live pools, Oct 12)


def tlog(address, topics, data, block, h, i):
    return {"address": address, "topics": topics, "data": data, "blockNumber": hex(block), "transactionHash": h, "logIndex": hex(i)}


class LiveChain(Chain):
    """the stubbed chain with the wallet's side: the pre-buy check's eth_call (by state override only), each pair's reserves, the wallet's
    token balances, gas price, balance, nonce; a signed transaction posted is decoded (the sender recovered, chain 56), its nonce checked,
    and it is mined at once two blocks past the reader, with the router's logs in its receipt; eth_getTransactionReceipt is refused as
    publicnode refuses it (the engine reads its block's receipts)"""
    def __init__(self):
        super().__init__()
        self.pairs, self.our, self.bal_tok, self.check, self.byhash, self.blocks = {}, {}, {}, {}, {}, {}
        self.mined = 7; self.sent = []; self.toks = []; self.outs = []; self.balance = 10 ** 17; self.gp = 5 * 10 ** 7
        self.override = True; self.revert = []; self.replies = []; self.posts = 0

    def pool(self, pair, token, logs):
        self.pairs[pair] = (token, logs); self.our[pair] = (0, 0); self.bal_tok.setdefault(token, 0)

    def pair_of(self, token):
        return next(p_ for p_, (t_, _) in self.pairs.items() if t_ == token)

    def real(self, pair):
        """(WBNB, token) of the pair now: its logs up to the reader's block, our own trades on top"""
        token, logs = self.pairs[pair]; rq, rt = reserves_before(logs, (E.state["done_to"] or L) - L + 1); dq, dt = self.our[pair]
        return rq + dq, rt - dt

    def rpc(self, method, params, tries=3, timeout=10):
        c = params[0] if params and isinstance(params[0], dict) else {}
        if method == "eth_call" and c.get("to") == LV.HARNESS:
            self.calls["check"] = self.calls.get("check", 0) + 1
            if not self.override or len(params) < 3:
                raise RuntimeError("eth_call: {'code': -32602, 'message': 'too many arguments, want at most 2'}")
            o = params[2][LV.HARNESS]; d = c["data"][10:]; token = "0x" + d[152:192]; q = int(d[192:256], 16)
            assert o["code"] == ART["deployedBytecode"] and int(o["balance"], 16) == q and c["from"] == WALLET and params[1] == "latest"
            assert c["data"][2:10] == ART["selectors"]["run(address,address,address,uint256)"] and "0x" + d[24:64] == E.ROUTER and "0x" + d[88:128] == WBNB
            if token == LV.USDT:
                return "0x" + w(0) + w(10 ** 18) + w(q * 995 // 1000) + w(136550) + w(24932) + w(70714)
            rq, rt = self.real(self.pair_of(token)); stage, tax, g = self.check.get(token, (0, 1.0, (136550, 24932, 70714)))
            tok = E.amount_out(q, rq, rt); back = int(E.amount_out(tok, rt - tok, rq + q) * tax) if stage == 0 else 0
            return "0x" + w(stage) + w(tok if stage != 1 else 0) + w(back) + "".join(w(x) for x in g)
        if method == "eth_call" and c.get("data") == "0x0902f1ac" and c.get("to") in self.pairs:
            rq, rt = self.real(c["to"]); return "0x" + w(rt) + w(rq) + w(int(time.time()))      # token0 is the token, WBNB token1
        if method == "eth_call" and c.get("data", "").startswith("0x70a08231"):
            assert c["data"][-40:] == WALLET[2:]; return "0x" + w(self.bal_tok.get(c["to"], 0))
        if method in ("eth_gasPrice", "eth_getBalance", "eth_getTransactionCount", "eth_getBlockReceipts", "eth_getTransactionReceipt") \
                or (method == "eth_getTransactionByHash" and params[0] in self.byhash):
            self.calls[method] = self.calls.get(method, 0) + 1
            if method == "eth_getTransactionReceipt":
                raise RuntimeError("HTTP Error 403: Forbidden")
            return {"eth_gasPrice": lambda: hex(self.gp), "eth_getBalance": lambda: hex(self.balance), "eth_getTransactionCount": lambda: hex(self.mined),
                    "eth_getBlockReceipts": lambda: copy.deepcopy(self.blocks.get(int(params[0], 16), [])),
                    "eth_getTransactionByHash": lambda: copy.deepcopy(self.byhash.get(params[0]))}[method]()
        return super().rpc(method, params, tries, timeout)

    def post(self, url, raw):
        """eth_sendRawTransaction: decoded, checked and mined at once (a queued reply first, when one is set: (kind, message, mined))"""
        self.posts += 1
        b = bytes.fromhex(raw[2:]); f = rlp.decode(b); n = int.from_bytes(f[0], "big")
        assert Account.recover_transaction(b).lower() == WALLET and int.from_bytes(f[6], "big") in (147, 148)    # the wallet's, chain 56 (EIP-155)
        reply = self.replies.pop(0) if self.replies else ("ok", None, True)
        if not reply[2]:
            return reply[:2]
        if n != self.mined:
            return "nonce", "nonce too low" if n < self.mined else "nonce too high"
        h = "0x" + keccak(b).hex(); gp = int.from_bytes(f[1], "big"); value = int.from_bytes(f[4], "big"); data = f[5].hex()
        tx = {"hash": h, "from": WALLET, "to": "0x" + f[3].hex(), "nonce": n, "gasPrice": gp, "gas": int.from_bytes(f[2], "big"), "value": value, "data": data}
        self.sent.append(tx); self.mined += 1
        blk = (E.state["done_to"] or L) + 2; sel, args = data[:8], bytes.fromhex(data[8:]); logs, ok, kind = [], True, None
        if sel == LV.SEL_BUY:
            kind = "buy"; mo, path, _to, dl = eth_abi.decode(["uint256", "address[]", "address", "uint256"], args); token = path[1].lower(); pair = self.pair_of(token)
            rq, rt = self.real(pair); tok = E.amount_out(value, rq, rt); used = G_BUY
            ok = tok >= mo and dl >= time.time() and kind not in self.revert
            if ok:
                self.our[pair] = (self.our[pair][0] + value, self.our[pair][1] + tok); self.bal_tok[token] += tok; self.toks.append(tok)
                logs = [tlog(WBNB, [TT, tp(E.ROUTER), tp(pair)], "0x" + w(value), blk, h, 1), tlog(token, [TT, tp(pair), tp(WALLET)], "0x" + w(tok), blk, h, 2),
                        tlog(pair, [E.T_SYNC], "0x" + w(rt - tok) + w(rq + value), blk, h, 3),
                        tlog(pair, [E.T_SWAP, tp(E.ROUTER), tp(WALLET)], "0x" + w(0) + w(value) + w(tok) + w(0), blk, h, 4)]
        elif sel == LV.SEL_APPROVE:
            kind = "approve"; used = G_APP; ok = kind not in self.revert
        elif sel == LV.SEL_SELL:
            kind = "sell"; amount, mo, path, _to, dl = eth_abi.decode(["uint256", "uint256", "address[]", "address", "uint256"], args); token = path[0].lower()
            pair = self.pair_of(token); rq, rt = self.real(pair); out = E.amount_out(amount, rt, rq); used = G_SELL
            ok = out >= mo and amount <= self.bal_tok[token] and dl >= time.time() and kind not in self.revert
            if ok:
                self.our[pair] = (self.our[pair][0] - out, self.our[pair][1] - amount); self.bal_tok[token] -= amount; self.outs.append(out)
                logs = [tlog(token, [TT, tp(WALLET), tp(pair)], "0x" + w(amount), blk, h, 1), tlog(WBNB, [TT, tp(pair), tp(E.ROUTER)], "0x" + w(out), blk, h, 2),
                        tlog(pair, [E.T_SYNC], "0x" + w(rt + amount) + w(rq - out), blk, h, 3),
                        tlog(pair, [E.T_SWAP, tp(E.ROUTER), tp(E.ROUTER)], "0x" + w(amount) + w(0) + w(0) + w(out), blk, h, 4)]
        if not ok and kind in self.revert:
            self.revert.remove(kind)                                                      # each queued revert once
        self.blocks.setdefault(blk, []).append({"transactionHash": h, "blockNumber": hex(blk), "status": "0x1" if ok else "0x0", "gasUsed": hex(used),
                                                "effectiveGasPrice": hex(gp), "logs": logs})
        self.byhash[h] = dict(tx, blockNumber=hex(blk), value=hex(value), nonce=hex(n))
        return reply[:2]


def new_live(chain, **env_):
    keep = {k: os.environ.get(k) for k in list(LIVE_ENV) + list(env_)}
    os.environ.update(LIVE_ENV); os.environ.update({k: str(v) for k, v in env_.items()})
    try:
        lv = LV.Live(E)
    finally:
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    lv.POLL_S = 0; lv.post = chain.post
    return lv


def live_start(chain, lv, a, fresh=True):
    reset(chain); E.LIVE = lv; E.state["done_to"] = a - 1; E.refresh_price(a)
    for f in (POSF, HALTF) if fresh else ():
        if os.path.exists(f):
            os.remove(f)
    return lv.start(a + E.LAG_BLOCKS, thread=False)


def live_go(chain, lv, b):
    while E.state["done_to"] < b:
        E.step(replay_to=b); lv.tick()
    for _ in range(8):
        lv.tick()


def base_chain(logs=None, txs=None):
    ch_ = LiveChain(); logs = FX["pair_logs"] if logs is None else logs
    ch_.add([FX["launch_log"]] + logs, [FX["launch_tx"]] + list((FX["txs"] if txs is None else txs).values())); ch_.pool(PAIR, TOKEN, logs)
    return ch_


def clone_tok(pair, shift, tag, token):
    lg, tx = clone(pair, shift=shift, tag=tag); lg[0]["topics"] = [lg[0]["topics"][0], tp(token), lg[0]["topics"][2]]
    return lg, tx


lives = lambda: [e for e in events("trade_done") if e.get("live")]
drys = lambda: [e for e in events("trade_done") if e.get("dry")]
dec = lambda types, tx: eth_abi.decode(types, bytes.fromhex(tx["data"][8:]))
B_T, S_T = ["uint256", "address[]", "address", "uint256"], ["uint256", "uint256", "address[]", "address", "uint256"]
E.STAKE_USD = 5; E.MAX_RANGE = 5                                              # the live default stake; the reader 5 blocks a step (as at the head)
r5 = FX["usdt_reserves"][str(L + 49)][2:]; Q5 = 5_000_000 * int(r5[64:128], 16) * 10 ** 12 // int(r5[:64], 16)

# 14. BNB_LIVE: 0 or 1 only; 1 makes the stake default $5 and loads the live module in main() only; --replay never trades; the key file
# refused when others can read it, when it is not a key, or when it is another wallet's (the key never in the message)
envb = {k: v for k, v in os.environ.items() if not k.startswith("BNB_")}
sub = lambda extra, code: subprocess.run([sys.executable, "-c", code], env=dict(envb, **extra), capture_output=True, text=True, cwd=os.path.join(ROOT, "src"))
assert sub({}, "import bnb_engine as e, sys; print(e.STAKE_USD, e.LIVE_ON, 'bnb_live' in sys.modules)").stdout.split() == ["15.0", "False", "False"]
assert sub({"BNB_LIVE": "1"}, "import bnb_engine as e, sys; print(e.STAKE_USD, e.LIVE_ON, 'bnb_live' in sys.modules)").stdout.split() == ["5.0", "True", "False"]
assert sub({"BNB_LIVE": "1", "BNB_STAKE_USD": "7"}, "import bnb_engine as e; print(e.STAKE_USD)").stdout.split() == ["7.0"]
assert "BNB_LIVE must be 0 or 1" in sub({"BNB_LIVE": "yes"}, "import bnb_engine").stderr
assert "--replay never trades" in sub({"BNB_LIVE": "1", "BNB_LOG_PATH": os.path.join(TMP, "r.jsonl")}, "import bnb_engine as e; e.main(['--replay', '1', '2'])").stderr
assert "needs BNB_WALLET" in sub({"BNB_LIVE": "1", "BNB_LOG_PATH": os.path.join(TMP, "r.jsonl"), "BNB_KEY_FILE": KEYF}, "import bnb_engine as e; e.main([])").stderr
msgs = []
for mode, content, env_ in ((0o644, KEY, {}), (0o600, "0xzz" + KEY[4:], {}), (0o600, KEY, {"BNB_WALLET": "0x" + "12" * 20})):
    os.chmod(KEYF, 0o600); open(KEYF, "w").write(content + "\n"); os.chmod(KEYF, mode)
    try:
        new_live(Chain(), **env_); raise AssertionError("no refusal")
    except SystemExit as e:
        msgs.append(str(e))
os.chmod(KEYF, 0o600); open(KEYF, "w").write(KEY + "\n")
assert "open to other users" in msgs[0] and "does not hold a usable key" in msgs[1] and "is for " + WALLET in msgs[2] and not any(KEY[4:] in m for m in msgs), msgs
print("ok BNB_LIVE: 0 or 1 only (anything else stops the start); 1 makes the stake default $5 and loads src/bnb_live.py in main() only (a dry "
      "import never loads it); --replay refuses to trade; the key file refused when open to others, not a key, or another wallet's (the key "
      "never in the message)")

# 15. the round trip on the real launch (1 BNB; the first slot of a run is live): the pre-buy check, the buy at L+50 seen, the approve
# after its receipt, the sale at L+260 seen; the three signed transactions decoded back; the settlement from the receipts beside the dry price
ch15 = base_chain(); lv = new_live(ch15); t0 = time.time()
st15 = live_start(ch15, lv, L - 2)
assert st15["live"] and st15["wallet"] == WALLET and st15["nonce"] == 7 and st15["live_off"] is None and st15["send"] == ["rpc.example.org"] and st15["balance_bnb"] == 0.1, st15
live_go(ch15, lv, L + 300)
arm, chk, snd, rcp = events("live_arm"), events("live_check"), events("live_send"), events("live_receipt")
assert [(e["role"], e["slot"]) for e in arm] == [("live", 1)] and chk[0]["ok"] and chk[0]["factor_ppm"] == 10 ** 6 and chk[0]["stake_wei"] == Q5, (arm, chk)
assert [e["kind"] for e in snd] == ["buy", "approve", "sell"] and all(e["reply"] == "ok" for e in snd) and [e["status"] for e in rcp] == [1, 1, 1], (snd, rcp)
wf = events("would_fire")[0]; TOK5 = wf["tokens"]; bt, at, stx = ch15.sent
mo, path, to_, dl = dec(B_T, bt)
assert wf["stake_wei"] == Q5 and bt["data"][:8] == "b6f9de95" and bt["to"] == E.ROUTER and bt["value"] == Q5 and bt["nonce"] == 7 and bt["gas"] == 200000 and bt["gasPrice"] == 10 ** 8
assert mo == TOK5 * 950000 // 10 ** 6 and [x.lower() for x in path] == [WBNB, TOKEN] and to_.lower() == WALLET and int(t0) + 60 <= dl <= time.time() + 60, (mo, TOK5, dl)
sp, amt = dec(["address", "uint256"], at)
assert at["data"][:8] == "095ea7b3" and at["to"] == TOKEN and at["value"] == 0 and at["nonce"] == 8 and at["gas"] == 80000 and sp.lower() == E.ROUTER and amt == 2 ** 256 - 1
amount, mo2, path2, to2, dl2 = dec(S_T, stx); rq260, rt260 = reserves_before(FX["pair_logs"], 260)
assert stx["data"][:8] == "791ac947" and stx["to"] == E.ROUTER and stx["value"] == 0 and stx["nonce"] == 9 and stx["gas"] == 180000 and stx["gasPrice"] == 10 ** 8
assert amount == ch15.toks[0] and mo2 == E.amount_out(amount, rt260, rq260) * 950000 // 10 ** 6 and [x.lower() for x in path2] == [TOKEN, WBNB] and to2.lower() == WALLET
td, dd = lives(), drys(); gas = (G_BUY + G_APP + G_SELL) * 10 ** 8; pnl = ch15.outs[0] - Q5 - gas
assert len(td) == 1 and len(dd) == 1 and td[0]["bnb_in_wei"] == Q5 and td[0]["tokens"] == amount and td[0]["bnb_out_wei"] == ch15.outs[0] and td[0]["gas_wei"] == gas, td
assert td[0]["pnl_bnb"] == round(pnl / 1e18, 9) and td[0]["pnl_pct"] == round(pnl / Q5, 6) and td[0]["pnl_usd"] == round(pnl / 1e18 * E.bnb_usd(), 4) and td[0]["pnl_pct"] > 2
assert td[0]["dry_ret"] == dd[0]["dry_ret"] and td[0]["dry_back_wei"] == dd[0]["back_wei"] and td[0]["buy_off"] >= 50 and td[0]["sell_off"] >= 260 and td[0]["reverted"] is None
assert td[0]["gas_used"] == {"buy": [G_BUY], "approve": [G_APP], "sell": [G_SELL]} and td[0]["live"] is True and td[0]["dry"] is False and td[0]["role"] == "live"
assert dd[0]["role"] == "live" and dd[0]["live"] is False and (dd[0]["tokens"], dd[0]["back_wei"]) == replay(Q5, FX["pair_logs"]) and dd[0]["clean"]
pf = json.load(open(POSF))
assert pf["positions"] == {} and pf["gate_rets"] == [td[0]["pnl_pct"]] and pf["wallet"] == WALLET and PAIR in pf["traded"] and not os.path.exists(HALTF)
assert "eth_getTransactionReceipt" not in ch15.calls and ch15.calls["eth_getBlockReceipts"] == 3 and KEY[2:] not in open(LOG).read() + open(POSF).read()
print("ok the live round trip on the real launch: the pre-buy check passed, then from the wallet three transactions decoded back from their "
      "signed bytes (sender recovered, chain 56): swapExactETHForTokensSupportingFeeOnTransferTokens (nonce 7, 200k gas, 0.1 gwei, value the "
      "$5 stake, minOut the engine's tokens x 0.95, [WBNB, token], the wallet, now+60), approve(router, max) (nonce 8, 80k), "
      "swapExactTokensForETHSupportingFeeOnTransferTokens (nonce 9, 180k, the whole balance, minOut the BNB on the reserves at L+260 x 0.95); "
      "settled from the receipts (in, tokens, out, gas: %+.1f%%) beside the dry price of the same pool (%+.1f%%); the key nowhere"
      % (100 * td[0]["pnl_pct"], 100 * dd[0]["dry_ret"]))

# 16. the probe: every other launch of a traded size live, the rest dry as the control (each trade_done says which); BNB_MAX_OPEN
TOK2, TOK3, P2, P3 = "0x" + "a2" * 20, "0x" + "a3" * 20, "0x" + "b2" * 20, "0x" + "b3" * 20
for maxo in (2, 1):
    ch16 = base_chain()
    for pr, sh, tg, tk in ((P2, 20, "d2", TOK2), (P3, 40, "d3", TOK3)):
        lg, tx = clone_tok(pr, sh, tg, tk); ch16.add(lg, tx); ch16.pool(pr, tk, lg[1:])
    lv = new_live(ch16, BNB_MAX_OPEN=maxo); live_start(ch16, lv, L - 2); live_go(ch16, lv, L + 340)
    roles = {e["pair"]: e["role"] for e in drys()}; arms = [(e["slot"], e["role"]) for e in events("live_arm")]
    if maxo == 2:
        assert roles == {PAIR: "live", P2: "control", P3: "live"} and [e["pair"] for e in lives()] == [PAIR, P3] and arms == [(1, "live"), (2, "control"), (3, "live")], (roles, arms)
        assert [t["nonce"] for t in ch16.sent] == list(range(7, 13)) and [t["data"][:8] for t in ch16.sent] == ["b6f9de95", "095ea7b3"] * 2 + ["791ac947"] * 2
        assert len({e["dry_ret"] for e in drys()}) == 1                               # the three pools are the same launch: the same dry price
    else:
        assert roles == {PAIR: "live", P2: "control", P3: "held"} and [e["pair"] for e in lives()] == [PAIR] and len(ch16.sent) == 3, roles
        assert any(e["role"] == "held" and "BNB_MAX_OPEN 1" in e["why"] for e in events("live_arm"))
print("ok the probe (BNB_PROBE_EVERY 2): three overlapping launches are live, control, live; each trade_done says its role; the live ones' six "
      "transactions in nonce order 7..12 across the two pools; BNB_MAX_OPEN 1 holds the third (the first still open)")

# 17. the pre-buy check refuses: a simulated sell that reverts, a sale under 90% of the stake, a leg over its gas limit, an RPC without state
# overrides; a start whose self-test fails turns live off for the run; a buy that would go late is not sent
for setup, why in ((lambda c: c.check.__setitem__(TOKEN, (3, 1.0, (136550, 24932, 0))), "the simulated sell reverted"),
                   (lambda c: c.check.__setitem__(TOKEN, (0, 0.85, (136550, 24932, 70714))), "under BNB_CHECK_MIN 90%"),
                   (lambda c: c.check.__setitem__(TOKEN, (0, 1.0, (136550, 24932, 150000))), "the simulated sell needs ~190000 gas, over BNB_GAS_SELL 180000"),
                   (lambda c: setattr(c, "override", False), "the pre-buy check did not run")):
    ch17 = base_chain(); lv = new_live(ch17); live_start(ch17, lv, L - 2); setup(ch17); live_go(ch17, lv, L + 300)
    sk = events("live_skip")
    assert not ch17.sent and len(sk) == 1 and sk[0]["role"] == "refused" and why in sk[0]["why"] + str(events("live_check")[0]["why"]) and drys()[0]["role"] == "refused", (why, sk)
ch17 = base_chain(); ch17.override = False; lv = new_live(ch17); st17 = live_start(ch17, lv, L - 2); live_go(ch17, lv, L + 300)
assert "self-test failed" in st17["live_off"] and not ch17.sent and events("live_arm")[0]["role"] == "held" and "live is off for this run" in events("live_arm")[0]["why"]
E.MAX_RANGE = 40; ch17 = base_chain(); lv = new_live(ch17); live_start(ch17, lv, L - 2); live_go(ch17, lv, L + 300); E.MAX_RANGE = 5
assert not ch17.sent and "blocks late (BNB_BUY_LATE 10)" in events("live_skip")[0]["why"]
print("ok the pre-buy check (BnbRoundTrip by eth_call state override, from the wallet) refuses a pool whose simulated sell reverts, whose sale "
      "returns under 90% of the stake, or whose leg needs more gas than its limit, and when the RPC takes no override; a failed self-test at "
      "the start turns live off for the run (the dry run goes on); a buy more than 10 blocks late is not sent")

# 18. the gate halts (HALTED.bnb) and still sells: a dump at +200 on a traded pool (that position sold at once, a second open one sold on
# schedule, a launch after the halt held); no crowd buy in +60..+260; a reverted buy, approve or sell; a negative median over 10 trades
crt = [{"hash": HX, "from": CREATOR, "to": ROUTER, "input": "0x18cbafe5"}]
ch18 = LiveChain(); ch18.add([FX["launch_log"]] + early + dump, [FX["launch_tx"]] + list(FX["txs"].values()) + crt); ch18.pool(PAIR, TOKEN, early + dump)
for pr, sh, tg, tk in ((P2, 30, "f2", TOK2), (P3, 210, "f3", TOK3)):
    lg, tx = clone_tok(pr, sh, tg, tk); ch18.add(lg, tx); ch18.pool(pr, tk, lg[1:])
lv = new_live(ch18, BNB_PROBE_EVERY=1); live_start(ch18, lv, L - 2); live_go(ch18, lv, L + 480)
td = {e["pair"]: e for e in lives()}; roles = {e["pair"]: e["role"] for e in drys()}
assert td[PAIR]["why"] == "the dump at +200" and td[PAIR]["pnl_pct"] < -0.9 and 200 <= td[PAIR]["sell_off"] <= 212 and td[P2]["why"] == "sell at +260" and P3 not in td, td
assert open(HALTF).read().startswith("a dump at +200, before +997, on a traded pool") and roles == {PAIR: "live", P2: "live", P3: "held"}, roles
assert any("halted: a dump at +200" in e["why"] for e in events("live_arm") if e["pair"] == P3) and len(ch18.sent) == 6
assert json.load(open(POSF))["halted"].startswith("a dump at +200") and any(a["what"].startswith("the BNB line halted: a dump at +200") for a in events("alarm"))
ch18 = base_chain(txs=txs9); lv = new_live(ch18); live_start(ch18, lv, L - 2); live_go(ch18, lv, L + 300)
assert open(HALTF).read().startswith("no crowd buy in +60..+260 on a traded pool") and len(lives()) == 1 and lives()[0]["why"] == "sell at +260"
for kind, n_sent in (("buy", 1), ("approve", 4), ("sell", 4)):
    ch18 = base_chain(); ch18.revert = [kind]; lv = new_live(ch18); live_start(ch18, lv, L - 2); live_go(ch18, lv, L + 300)
    td = lives(); k_sent = [t["data"][:8] for t in ch18.sent]
    assert open(HALTF).read().startswith("a reverted %s" % kind) and len(ch18.sent) == n_sent and len(td) == 1, (kind, k_sent, td)
    if kind == "buy":
        assert td[0]["reverted"] == "buy" and td[0]["bnb_in_wei"] == 0 and td[0]["gas_wei"] == G_BUY * 10 ** 8 and td[0]["pnl_bnb"] == round(-G_BUY * 10 ** 8 / 1e18, 9)
        assert td[0]["pnl_pct"] is None and json.load(open(POSF))["gate_rets"] == [] and drys()[0]["role"] == "live"
    elif kind == "sell":
        s1, s2 = [e for e in events("live_send") if e["kind"] == "sell"]
        assert td[0]["sell_tries"] == 1 and len(td[0]["hashes"]["sell"]) == 2 and td[0]["gas_wei"] == (G_BUY + G_APP + 2 * G_SELL) * 10 ** 8, td
        assert s1["slip"] == 0.05 and s2["slip"] == 0.1 and dec(S_T, ch18.sent[3])[1] == s2["expected"] * 900000 // 10 ** 6 and td[0]["bnb_out_wei"] == ch18.outs[0]
    else:
        assert k_sent == ["b6f9de95", "095ea7b3", "095ea7b3", "791ac947"] and td[0]["gas_used"]["approve"] == [G_APP, G_APP] and td[0]["why"] == "sell at +260"
lv = new_live(ch18); os.remove(HALTF); lv.save()
for i, rt_ in enumerate([-0.1] * 6 + [0.2] * 4 + [-0.5]):
    x = {"pair": "0x%040x" % (0x900 + i), "token": TOKEN, "L": L, "pool_bnb": 1.0, "txs": [], "gas_wei": 0, "sell_tries": 0, "q": 10 ** 16, "bnb_in": 10 ** 16,
         "bnb_out": int(10 ** 16 * (1 + rt_)), "sell_due": {"why": "sell at +260"}}
    lv.pos[x["pair"]] = x; lv.settle(x, "sell at +260")
    assert (lv.halted is None) == (i < 9) and os.path.exists(HALTF) == (i >= 9), (i, lv.halted)
assert lv.halted == "the median of the first 10 live trades is -10.00%" and len(lv.gate_rets) == 10
print("ok the gate halts (HALTED.bnb, its own file) and still sells: a dump at +200 on a traded pool (sold at once at -100%; a second open "
      "position sold on schedule; a launch after the halt held), no crowd buy in +60..+260 on a traded pool, a reverted buy (settled: the gas "
      "lost), approve (sent again, then sold) or sell (sent again on fresh reserves at 10% slippage), and a negative median over the first 10 "
      "live trades (at the 10th, not before)")

# 19. the daily stop: a day's losses at BNB_DAILY_STOP_USD stop new buys (an alarm once) until the next UTC day; what is open still sells
ch19 = base_chain(); lv = new_live(ch19, BNB_PROBE_EVERY=1); live_start(ch19, lv, L - 2)
x = {"pair": "0x" + "9d" * 20, "token": TOKEN, "L": L, "pool_bnb": 1.0, "txs": [], "gas_wei": 0, "sell_tries": 0, "q": 2 * 10 ** 16, "bnb_in": 2 * 10 ** 16,
     "bnb_out": 6 * 10 ** 15, "sell_due": {"why": "sell at +260"}}
lv.pos[x["pair"]] = x; lv.settle(x, "sell at +260"); day_loss = lv.pnl_today; live_go(ch19, lv, L + 300)
assert lv.pnl_today < -10 and not ch19.sent and "the daily stop" in events("live_arm")[0]["why"] and drys()[0]["role"] == "held"
assert sum(1 for a in events("alarm") if a["what"].startswith("the BNB daily stop")) == 1
lv.today = lambda: "2099-01-01"; reset(ch19); E.state["done_to"] = L - 3; E.refresh_price(L); live_go(ch19, lv, L + 300)
assert lv.pnl_today > 0 and len(ch19.sent) == 3 and lives()[0]["why"] == "sell at +260"
print("ok the daily stop: $%.2f in a day (BNB_DAILY_STOP_USD 10) holds the next launch (an alarm once); the next UTC day trades again" % day_loss)

# 20. a restart keeps the open position (bnb_positions.json): past its sell block it is sold at once; before it, its pool is taken back and
# sold at L+260 (its dry line flagged: the blocks missed); a pool that lost its WBNB while the engine was stopped is sold at once and halts
ch20 = base_chain(); lv = new_live(ch20); live_start(ch20, lv, L - 2); live_go(ch20, lv, L + 120)
pf = json.load(open(POSF)); assert pf["positions"][PAIR]["state"] == "approved" and PAIR in pf["pools"] and len(ch20.sent) == 2
lv2 = new_live(ch20); E.pools.clear(); E.LIVE = lv2; st20 = lv2.start(L + 402, thread=False)
assert st20["resumed"] == 1 and lv2.pos[PAIR]["sell_due"]["why"] == "past its sell block at the start" and E.pools[PAIR]["gaps"] == 1
for _ in range(6):
    lv2.tick()
td = lives()
assert len(td) == 1 and td[0]["resumed"] and td[0]["why"] == "past its sell block at the start" and td[0]["bnb_in_wei"] == Q5 and td[0]["tokens"] == ch20.toks[0]
assert td[0]["gas_wei"] == (G_BUY + G_APP + G_SELL) * 10 ** 8 and [t["nonce"] for t in ch20.sent] == [7, 8, 9] and json.load(open(POSF))["positions"] == {}
ch20 = base_chain(); lv = new_live(ch20); live_start(ch20, lv, L - 2); live_go(ch20, lv, L + 120)
lv2 = new_live(ch20); E.pools.clear(); E.LIVE = lv2; E.state["done_to"] = L + 129; lv2.start(L + 132, thread=False); live_go(ch20, lv2, L + 300)
td, dd = lives(), drys()
assert len(td) == 1 and td[0]["resumed"] and td[0]["why"] == "sell at +260" and td[0]["sell_off"] >= 260 and dd[0]["gaps"] == 1 and dd[0]["clean"] is False and dd[0]["role"] == "live"
ch20 = base_chain(logs=early + dump); ch20.txs.update({t["hash"]: t for t in crt}); lv = new_live(ch20); live_start(ch20, lv, L - 2); live_go(ch20, lv, L + 120)
lv2 = new_live(ch20); E.pools.clear(); E.LIVE = lv2; E.state["done_to"] = L + 209; lv2.start(L + 212, thread=False)
assert lv2.pos[PAIR]["sell_due"]["why"] == "the pool lost its WBNB while the engine was stopped" and open(HALTF).read().startswith("a traded pool lost its WBNB before +997")
for _ in range(6):
    lv2.tick()
assert lives()[0]["pnl_pct"] < -0.9 and lives()[0]["resumed"]
print("ok a restart keeps the open position (bnb_positions.json, written before each send): past its sell block it is sold at once; before it, "
      "its pool is taken back (its dry line flagged: gaps 1) and sold at L+260; a pool that lost its WBNB while stopped is sold at once and halts")

# 21. the nonce: one sequence kept in memory, read again on a nonce error (the transaction signed anew with the chain's count), not when the
# node already holds this very transaction ("already known", or "nonce too low" for a copy already in); a refused buy sends nothing
ch21 = base_chain(); lv = new_live(ch21); live_start(ch21, lv, L - 2); ch21.mined = 12                  # five of the wallet's transactions sent elsewhere
live_go(ch21, lv, L + 300)
buys = [e for e in events("live_send") if e["kind"] == "buy"]
assert [(e["reply"], e["nonce"]) for e in buys] == [("nonce", 7), ("ok", 12)] and [t["nonce"] for t in ch21.sent] == [12, 13, 14] and ch21.posts == 4, buys
assert [e["nonce"] for e in events("live_nonce")] == [7, 12] and lives()[0]["why"] == "sell at +260"
for reply, kind in ((("in", "already known", True), "in"), (("nonce", "nonce too low", True), "in"), (("rejected", "insufficient funds for gas * price + value", False), None)):
    ch21 = base_chain(); ch21.replies = [reply]; lv = new_live(ch21); live_start(ch21, lv, L - 2); live_go(ch21, lv, L + 300)
    buys = [e for e in events("live_send") if e["kind"] == "buy"]
    if kind:
        assert [e["reply"] for e in buys] == [kind] and len(ch21.sent) == 3 and lives()[0]["why"] == "sell at +260", buys
    else:
        assert [e["reply"] for e in buys] == ["rejected"] and not ch21.sent and events("live_skip")[0]["role"] == "unsent" and lv.nonce == 7 and not lives()
print("ok the nonce: kept in memory from the pending count; a 'nonce too low' (the wallet used elsewhere) reads it again and signs anew (7, then "
      "12); 'already known' and 'nonce too low' for a copy already in count as in (no second transaction); a refused buy sends nothing, nonce kept")

# 22. sending: eth_sendRawTransaction's answers read from a local HTTP endpoint (the JSON-RPC error inside an HTTP 403 too); the next
# endpoint tried when one cannot answer; the receipt from eth_getBlockReceipts when eth_getTransactionReceipt is refused
REPLY, SEEN = {}, []


class Stub(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        SEEN.append((self.path, json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
        code, body = REPLY[self.path].pop(0)
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(body.encode())

    def log_message(self, *a):
        pass


srv = http.server.HTTPServer(("127.0.0.1", 0), Stub); threading.Thread(target=srv.serve_forever, daemon=True).start(); BASE = "http://127.0.0.1:%d" % srv.server_port
err = lambda m: json.dumps({"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": m}})
lv = new_live(base_chain()); lv.post = LV.Live.post.__get__(lv)
REPLY["/a"] = [(200, json.dumps({"jsonrpc": "2.0", "id": 1, "result": "0x" + "ab" * 32})), (403, err("Archive requests require a personal token")), (200, err("nonce too low")),
               (200, err("insufficient funds for gas * price + value")), (200, err("already known")), (500, "oops"), (200, err("replacement transaction underpriced"))]
kinds = [lv.post(BASE + "/a", "0x01") for _ in range(7)]
assert [k for k, _ in kinds] == ["ok", "unknown", "nonce", "rejected", "in", "unknown", "nonce"] and kinds[5][1] == "HTTP 500", kinds
assert all(b == {"jsonrpc": "2.0", "id": 1, "method": "eth_sendRawTransaction", "params": ["0x01"]} for _, b in SEEN)
lv.send_urls = [BASE + "/a", BASE + "/b"]
REPLY["/a"] = [(403, err("Archive requests require a personal token"))]; REPLY["/b"] = [(200, json.dumps({"jsonrpc": "2.0", "id": 1, "result": "0x" + "ab" * 32}))]
assert lv.broadcast("0x02") == ("ok", None, "127.0.0.1") and [p_ for p_, _ in SEEN[-2:]] == ["/a", "/b"]
REPLY["/a"] = [(429, "{}"), (429, "{}")]; REPLY["/b"] = [(502, "bad"), (502, "bad")]; n0 = len(SEEN)
assert lv.broadcast("0x03")[0] == "unknown" and len(SEEN) - n0 == 4                           # two rounds when nobody answers
REPLY["/a"] = [(200, err("nonce too low"))]; REPLY["/b"] = [(200, err("insufficient funds for gas * price + value"))]
assert lv.broadcast("0x04")[0] == "nonce"
srv.shutdown()
RC = json.load(open(os.path.join(ROOT, "tests", "data", "bnb_receipts.json")))
btx, brc = RC["buy"]["tx"], RC["buy"]["receipt"]; stx_, src_ = RC["sell"]["tx"], RC["sell"]["receipt"]
_, bpath, _, _ = eth_abi.decode(B_T, bytes.fromhex(btx["input"][10:])); samt, _, spath, _, _ = eth_abi.decode(S_T, bytes.fromhex(stx_["input"][10:]))
sw = lambda rc_: next(lg for lg in rc_["logs"] if lg["topics"][0] == E.T_SWAP); words_ = lambda lg: [int(lg["data"][2 + 64 * i: 66 + 64 * i], 16) for i in range(4)]
bpair, spair = sw(brc)["address"].lower(), sw(src_)["address"].lower(); bw, sw_ = words_(sw(brc)), words_(sw(src_))
wd = next(int(lg["data"], 16) for lg in src_["logs"] if lg["topics"][0] == "0x7fcf532c15f0a6db0bd6d0e038bea71d30d808c7d98cb3bf7268a95bf5081b65")
assert LV.transfers(brc, WBNB, frm=E.ROUTER, to=bpair) == int(btx["value"], 16) > 0 and LV.transfers(brc, bpath[1].lower(), to=btx["from"].lower()) == max(bw[2], bw[3]) > 0
assert LV.transfers(src_, WBNB, frm=spair, to=E.ROUTER) == wd == max(sw_[2], sw_[3]) > 0 and LV.transfers(src_, spath[0].lower(), frm=stx_["from"].lower(), to=spair) == samt
other = dict(copy.deepcopy(brc), transactionHash="0x" + "11" * 32)
stubs = {"eth_getTransactionByHash": lambda p_: {"hash": p_[0], "blockNumber": brc["blockNumber"]}, "eth_getBlockReceipts": lambda p_: [other, brc]}


def stub_rpc(method, params, tries=3, timeout=10):
    if method not in stubs:
        raise RuntimeError("HTTP Error 403: Forbidden")
    return stubs[method](params)


E.rpc = stub_rpc
assert lv.receipt(brc["transactionHash"]) == (brc, True)
stubs["eth_getTransactionReceipt"] = lambda p_: src_; del stubs["eth_getBlockReceipts"]
assert lv.receipt(stx_["hash"]) == (src_, True)
stubs["eth_getTransactionByHash"] = lambda p_: None; assert lv.receipt("0x" + "22" * 32) == (None, False)
print("ok sending: eth_sendRawTransaction's answers read (a result; 'nonce too low' and 'replacement ... underpriced'; 'insufficient funds' "
      "refused; 'already known' in; publicnode's JSON error inside an HTTP 403 and an HTTP 500 unknown), the next endpoint tried, two rounds when "
      "none answers; two real receipts of the router's calls read (WBNB in = the value, the tokens = the Swap's out; WBNB out = the Withdrawal = "
      "the Swap's out); the receipt from the block's receipts when eth_getTransactionReceipt is refused, else from it")

# 23. the dry replay is not touched by the live path: a control slot's lines equal a dry run's field for field (role and live aside); our
# own buy in the pool's logs stays out of the dry copy and of the crowd's counts
E.LIVE = None; ch23 = base_chain(); run(ch23, L - 2, L + 1100); base5 = lines()
lv = new_live(ch23); live_start(ch23, lv, L - 2); lv.eligible = 1; live_go(ch23, lv, L + 1100)
assert [{k: v for k, v in e.items() if k not in ("live", "role")} for e in lines()] == base5 and drys()[0]["role"] == "control" and not ch23.sent
logs23 = [x for x in FX["pair_logs"] if blk(x) == L]; rq_, rt_ = 10 ** 18, 10 ** 18; HO = "0x" + "0e" * 32; tok_o = E.amount_out(Q5, rq_, rt_)
logs23 += [{"address": PAIR, "topics": [E.T_SYNC], "data": "0x" + w(rt_ - tok_o) + w(rq_ + Q5), "blockNumber": hex(L + 53), "transactionHash": HO, "logIndex": "0x1"},
           {"address": PAIR, "topics": [E.T_SWAP, tp(E.ROUTER), tp(WALLET)], "data": "0x" + w(0) + w(Q5) + w(tok_o) + w(0), "blockNumber": hex(L + 53), "transactionHash": HO, "logIndex": "0x2"}]
rq_, rt_ = rq_ + Q5, rt_ - tok_o; txs23 = [FX["launch_tx"]]
for n, (off, a_) in enumerate([(80, 2 * 10 ** 17), (120, 3 * 10 ** 17)]):
    lg_, tx_, rq_, rt_ = crowd_buy(rq_, rt_, off, a_, 10 + n); logs23 += lg_; txs23.append(tx_)
ch23 = LiveChain(); ch23.add([FX["launch_log"]] + logs23, txs23 + [{"hash": HO, "from": WALLET, "to": ROUTER, "input": "0xb6f9de95"}]); ch23.pool(PAIR, TOKEN, logs23)
E.LIVE = None; run(ch23, L - 2, L + 300); stranger = drys()[0]
lv = new_live(ch23); live_start(ch23, lv, L - 2); lv.eligible = 1; lv.hashes.add(HO); live_go(ch23, lv, L + 300); ours = drys()[0]
assert stranger["strangers"] == 1 and ours["strangers"] == 0 and ours["crowd_buys"] == stranger["crowd_buys"] == 2 and not events("alarm")
assert (ours["tokens"], ours["back_wei"]) == replay(Q5, [x for x in logs23 if x["transactionHash"] != HO]) and ours["back_wei"] != stranger["back_wei"]
print("ok the dry replay untouched: a control slot's launch, would_fire, trade_done, dump and pool_done lines equal the dry run's field for "
      "field; our own buy in the pool's logs (its hash) stays out of the dry copy (equal to an independent replay without it) and is no stranger")

# 24. the files: bnb_live.py alone names eth_sendRawTransaction (in post() only), reads no other key and never engine.env; bnb_engine.py loads
# it by name in main() under BNB_LIVE=1 only; the halt and positions files are the line's own (the Robinhood engine's halt files untouched)
src_e = open(os.path.join(ROOT, "src", "bnb_engine.py")).read(); src_l = open(os.path.join(ROOT, "src", "bnb_live.py")).read(); tl = ast.parse(src_l)
fns = [f.name for f in ast.walk(tl) if isinstance(f, ast.FunctionDef) for d in ast.walk(f) if isinstance(d, ast.Dict)
       for k, v in zip(d.keys, d.values) if isinstance(k, ast.Constant) and k.value == "method" and isinstance(v, ast.Constant) and v.value == "eth_sendRawTransaction"]
assert src_l.count('"eth_sendRawTransaction"') == 1                            # the one JSON-RPC body that sends, in post()
assert fns == ["post"] and "eth_sendRawTransaction" not in src_e and "eth_account" not in src_e and "PRIVATE_KEY" not in src_l and "engine.env" not in src_l
main_src = ast.get_source_segment(src_e, next(f for f in ast.walk(ast.parse(src_e)) if isinstance(f, ast.FunctionDef) and f.name == "main"))
assert src_e.count('__import__("bnb_live")') == 1 and "    if LIVE_ON:" in main_src and '__import__("bnb_live")' in main_src
assert set(re.findall(r"acct\.\w+", src_l)) == {"acct.address", "acct.sign_transaction"} and os.path.basename(lv.HALT_FILE) == "HALTED.bnb"
named = {n.value for n in ast.walk(tl) if isinstance(n, ast.Constant) and isinstance(n.value, str) and re.fullmatch(r"eth_\w+", n.value)}
assert named == {"eth_call", "eth_gasPrice", "eth_getBalance", "eth_getTransactionCount", "eth_getTransactionByHash", "eth_getBlockReceipts",
                 "eth_getTransactionReceipt", "eth_sendRawTransaction"}, named
art = json.load(open(os.path.join(ROOT, "contracts", "BnbRoundTrip.json")))
assert art["source_sha256"] == __import__("hashlib").sha256(open(os.path.join(ROOT, "contracts", "BnbRoundTrip.sol"), "rb").read()).hexdigest()
print("ok the files: only bnb_live.py names eth_sendRawTransaction (in post()), it uses the key only to sign, never opens engine.env; "
      "bnb_engine.py loads it by name in main() under BNB_LIVE=1 only; the check's bytecode is built from contracts/BnbRoundTrip.sol")

# 25. deploy/bnb_wallet.py: a new key in a mode-600 file it creates (never one that exists, never engine.env); only the address printed
kp = os.path.join(TMP, "w", "bnb.key"); os.makedirs(os.path.dirname(kp))
wl = lambda path: subprocess.run([sys.executable, os.path.join(ROOT, "deploy", "bnb_wallet.py"), path], capture_output=True, text=True)
o1 = wl(kp); k1 = open(kp).read().strip(); a1 = Account.from_key(k1).address
assert o1.returncode == 0 and stat.S_IMODE(os.stat(kp).st_mode) == 0o600 and re.fullmatch(r"0x[0-9a-f]{64}", k1) and k1[2:] not in o1.stdout + o1.stderr
assert ("new BNB wallet: " + a1) in o1.stdout and ("BNB_WALLET=" + a1.lower()) in o1.stdout
o2 = wl(kp); o3 = wl(os.path.join(TMP, "w", "engine.env"))
assert o2.returncode != 0 and "exists: not replacing it" in o2.stderr and open(kp).read().strip() == k1 and o3.returncode != 0 and not os.path.exists(os.path.join(TMP, "w", "engine.env"))
print("ok deploy/bnb_wallet.py: a new key in a file it creates mode 600 (O_EXCL), only the address and the BNB_WALLET= line printed; an "
      "existing key file is never replaced; it never writes engine.env")

# 26. the screen with BNB_LIVE=1: LIVE (the receipts) vs the same pools' dry price vs CONTROL, the halt, the open positions and the day,
# the wallet's balance from the RPC (the key file never opened)
now = time.time(); S = os.path.join(TMP, "s.jsonl"); H2 = os.path.join(TMP, "H2.bnb"); P2F = os.path.join(TMP, "p2.json")
st_ = {"ev": "start", "t": now - 3600, "release": "bnb-0.2", "live": True, "probe_every": 2, "stake_usd": 5, "daily_stop_usd": 10, "wallet": WALLET, "buy_at": 50,
       "sell_at": 260, "skip_pool_bnb": [15.0], "gate": {"dump_before": 997, "crowd_from": 60, "probes": 10}, "bnb_usd": 750}
dryl = lambda i, ret, role: {"ev": "trade_done", "dry": True, "live": False, "role": role, "t": now - 3000 + i, "pair": "0x%040x" % i, "pool_bnb": 1.0, "dry_ret": ret, "breaks": 0,
                              "gaps": 0, "crowd_gate": 1, "crowd_buys": 2, "crowd_bnb": 0.5, "stake_wei": 6 * 10 ** 15}
livel = lambda i, pp, usd, dr, rev=None: {"ev": "trade_done", "live": True, "dry": False, "role": "live", "t": now - 2900 + i, "pair": "0x%040x" % i, "pool_bnb": 1.0,
                                           "pnl_pct": pp, "pnl_usd": usd, "gross_pct": pp, "dry_ret": dr, "dry_ret_gross": dr, "stake_wei": 6 * 10 ** 15, "bnb_usd": 750, "reverted": rev}
evs = [st_, dryl(1, 0.20, "live"), dryl(2, 0.30, "control"), dryl(3, 0.10, "live"), dryl(4, -0.06, "control"), livel(1, 0.15, 0.75, 0.20), livel(3, 0.05, 0.25, 0.10),
       livel(5, None, -0.01, None, "buy"), {"ev": "live_receipt", "t": now - 2000, "kind": "buy", "status": 0}, {"ev": "live_skip", "t": now - 1900, "role": "held", "why": "halted: a reverted buy"},
       {"ev": "live_check", "t": now - 1800, "ok": False, "why": "the simulated sell reverted"}, {"ev": "flow", "t": now - 30, "blocks": 130, "bnb_usd": 750}]
open(S, "w").write("".join(json.dumps(e) + "\n" for e in evs)); open(H2, "w").write("a reverted buy (0x05, 0xabc)\n")
json.dump({"positions": {"0x" + "77" * 20: {"state": "approved", "sell_due": None}}, "gate_rets": [0.15, 0.05], "day": "2026-10-12", "pnl_today_usd": 0.99}, open(P2F, "w"))
REPLY.clear(); SEEN.clear(); REPLY["/rpc"] = [(200, json.dumps({"jsonrpc": "2.0", "id": 1, "result": hex(264 * 10 ** 14)}))]
srv = http.server.HTTPServer(("127.0.0.1", 0), Stub); threading.Thread(target=srv.serve_forever, daemon=True).start()
renv = dict(envb, BNB_LOG_PATH=S, BNB_HALT_FILE=H2, BNB_POSITIONS_FILE=P2F, BNB_WALLET=WALLET, BNB_RPC_URL="http://127.0.0.1:%d/rpc" % srv.server_port, BNB_ENV_FILE=os.path.join(TMP, "none"))
out = subprocess.run([sys.executable, os.path.join(ROOT, "deploy", "bnb_results.py"), "24"], env=renv, capture_output=True, text=True).stdout; srv.shutdown()
assert out.startswith("=" * 100 + "\nBNB LIVE PROBE") and re.search(r"LIVE \(the receipts, after gas\)\s+2\s+\+10\.0%\s+\+10\.0%\s+100% \|\s+\+0\.99", out), out
assert re.search(r"LIVE's pools at the dry price\s+2\s+\+15\.0%\s+\+15\.0%\s+100% \|\s+\+1\.35", out) and re.search(r"CONTROL \(the other launches, dry\)\s+2\s+\+12\.0%\s+\+12\.0%\s+50% \|\s+\+1\.08", out), out
assert "HALTED: a reverted buy (0x05, 0xabc)" in out and re.search(r"a revert:\s+TRIPPED x1", out) and "open live positions: 1" in out and "2 of 10 live trades so far" in out, out
assert ("wallet %s: 0.026400 BNB, $19.80 (read from 127.0.0.1)" % WALLET) in out and SEEN[0][1]["method"] == "eth_getBalance" and "held 1" in out and "refused 1" in out, out
print("ok the screen with BNB_LIVE=1: LIVE from the receipts (+$0.99 with a reverted buy's gas), the same pools at the dry price, CONTROL; the "
      "halt with its reason and how to resume, the revert in the gate, the open positions and the gate's live count, the wallet's balance by RPC")

# 27. the buy's own window: a dump seen while the buy is due cancels it (nothing sent); a position sending its buy is never dropped by a
# halt; a buy no endpoint answered for is sent again and mined; one never mined is dropped and the nonce read again; a restart mid-send
ch27 = base_chain(); lv = new_live(ch27); live_start(ch27, lv, L - 2)
while not events("would_fire"):
    E.step(replay_to=L + 300)
    if not events("would_fire"):
        lv.tick()
assert lv.pos[PAIR]["state"] == "buy_due"
lv.on_dump(E.pools[PAIR], 51); lv.tick()
assert PAIR not in lv.pos and not ch27.sent and "dumped or dropped before the buy (the dump at +51)" in events("live_skip")[-1]["why"] and lv.halted is None
lv.pos["0x" + "88" * 20] = {"pair": "0x" + "88" * 20, "state": "buying", "L": L}; lv.halt("a test halt")
assert "0x" + "88" * 20 in lv.pos and open(HALTF).read() == "a test halt\n"
for replies, mined in (([("unknown", "timed out", False)] * 2, True), ([("unknown", "timed out", False)] * 4, False)):    # a broadcast: two rounds
    ch27 = base_chain(); ch27.replies = list(replies); lv = new_live(ch27); live_start(ch27, lv, L - 2); lv.RECEIPT_WAIT_S = 0.05; live_go(ch27, lv, L + 60)
    for _ in range(30):                                                         # the reader holds at L+60 (before the crowd) while the wait runs out
        time.sleep(0.01); lv.tick()
    live_go(ch27, lv, L + 300)
    assert len(events("live_rebroadcast")) == 1 and [e["reply"] for e in events("live_send")][:1] == ["unknown"]
    if mined:
        assert [t["nonce"] for t in ch27.sent] == [7, 8, 9] and lives()[0]["why"] == "sell at +260" and lives()[0]["hashes"]["buy"] == [ch27.sent[0]["hash"]]
    else:
        assert not ch27.sent and not lives() and events("live_skip")[-1]["why"] == "the buy was never mined" and lv.nonce is None and PAIR not in lv.traded
json.dump({"wallet": WALLET, "positions": {PAIR: {"pair": PAIR, "state": "buying", "txs": [], "L": L}}, "pools": {}}, open(POSF, "w"))
lv = new_live(ch27); E.LIVE = lv
assert lv.start(L + 10, thread=False)["resumed"] == 0 and events("live_resume")[-1]["what"] == "never bought: dropped" and not lv.pos
print("ok the buy's own window: a dump seen while the buy is due cancels it; a position sending its buy is not dropped by a halt; a buy no "
      "endpoint answered for is sent again after BNB_RECEIPT_WAIT_S and mined, or dropped (nonce read again) when never mined; a restart "
      "while sending a buy with no transaction recorded drops it")

E.LIVE = None; E.STAKE_USD = 15; E.MAX_RANGE = 40
shutil.rmtree(TMP, ignore_errors=True)
os.remove(LOG)
