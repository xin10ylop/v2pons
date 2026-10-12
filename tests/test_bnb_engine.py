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

os.remove(LOG)
