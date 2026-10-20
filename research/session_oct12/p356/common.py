"""shared loaders for p356 (offline): launches (p03), per-pool compact events in analysis C's row format (p04), the replay of analysis/C."""
import os, sys, json, bisect, collections as C
HERE = os.path.dirname(os.path.abspath(__file__))
J = lambda n: os.path.join(HERE, n)
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(HERE, "..", "..", "session_oct11", "lines", "analysis", "C"))
import replay as CR                                                     # analysis/C/replay.py (V3Sim, replay), imported read-only
WETH = "0bd7d308f8e1639fab988df18a8011f41eacad73"; NPM = "73991a25c818bf1f1128deaab1492d45638de0d3"; ROUTER = "caf681a66d020601342297493863e78c959e5cb2"
T_SWAP = "c42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"; T_MINT = "7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde"
T_BURN = "0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c"; T_COLLECT = "70935338e69775456a85ddef226c395fb668b63fa0115f5f20610b388e6ca9c0"
LINE_L = 31_622_807_953_636_212_567_716; LO, HI = -887272, 207243
ETH_USD = 2570.0; GAS = 0.02; WIN = 3000


def s(x): return x - (1 << 256) if x >> 255 else x
def u(h, i): return int(h[64 * i:64 * i + 64], 16)


def launches():
    return sorted(json.load(open(J("p03_launches.json"))), key=lambda x: x["block"])


def events():
    """pool -> {"lb", "ev_to", "ev"} with C's compact V3 rows: ["s", bn, ti, li, pool, sender, recipient, a0, a1, sqrtP, liq, tick, tx],
    ["mi", bn, ti, li, pool, owner, lo, hi, amount, a0, a1, tx], ["b", ...same], ["c", bn, ti, li, pool, owner, lo, hi, a0, a1, tx] (collect)"""
    X = launches(); lb = {x["pool"]: x["block"] for x in X}
    head = json.load(open(J("p04_head.json")))["head"]
    ev = C.defaultdict(dict)
    for line in open(J("p04_events.jsonl")):
        l = json.loads(line); p = l["address"][2:].lower(); t = l["topics"][0][2:]; bn = int(l["blockNumber"], 16); ti = int(l["transactionIndex"], 16); li = int(l["logIndex"], 16)
        if p not in lb or not lb[p] <= bn <= lb[p] + WIN: continue
        d = l["data"][2:]; h = l["transactionHash"]
        if t == T_SWAP:
            e = ["s", bn, ti, li, p, l["topics"][1][-40:], l["topics"][2][-40:], s(u(d, 0)), s(u(d, 1)), u(d, 2), u(d, 3), s(u(d, 4)), h]
        elif t == T_MINT:
            e = ["mi", bn, ti, li, p, l["topics"][1][-40:], s(int(l["topics"][2], 16)), s(int(l["topics"][3], 16)), u(d, 1), u(d, 2), u(d, 3), h]
        elif t == T_BURN:
            e = ["b", bn, ti, li, p, l["topics"][1][-40:], s(int(l["topics"][2], 16)), s(int(l["topics"][3], 16)), u(d, 0), u(d, 1), u(d, 2), h]
        elif t == T_COLLECT:
            e = ["c", bn, ti, li, p, l["topics"][1][-40:], s(int(l["topics"][2], 16)), s(int(l["topics"][3], 16)), u(d, 1), u(d, 2), h]
        else: continue
        ev[p][(bn, li)] = e
    out = {}
    for x in X:
        p = x["pool"]; es = [ev[p][k] for k in sorted(ev[p])]
        out[p] = {"lb": x["block"], "ev_to": min(x["block"] + WIN, head), "ev": [e for e in es if e[0] != "c"], "collects": [e for e in es if e[0] == "c"]}
    return out


def row(x):
    return {"dex": "v3", "quote_side": 0, "fee": 100, "pool": x["pool"]}


def trade(x, o, a, b, q):
    """the rule as REPORT_V23/G3: buy q at the head of launch + a, sell at the head of launch + b (C's replay); no trade if a pull (Burn with
    liquidity > 0) is at or before launch + a - 2; a pull at or before the sell = -100%; net of $0.02 gas"""
    lb = o["lb"]
    pulls = [e[1] for e in o["ev"] if e[0] == "b" and e[8] > 0]
    if pulls and min(pulls) <= lb + a - 2: return None
    r = CR.replay(row(x), o, a, b, q_eth=q)
    if not r.get("ok"): return {"ok": False, "reason": r.get("reason")}
    g = GAS / ETH_USD / q
    return {"ok": True, "ret": (-1.0 - g) if r["pulled"] else r["ret_nopull"] - g, "gross": r["ret_nopull"], "pulled": r["pulled"], "q": q}
