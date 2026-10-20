"""shared loader for the PM1444-family reaction study: pools (census + recent), their logs, the tx cache"""
import sys, os, pickle, json, collections
SCR = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad"; sys.path.insert(0, SCR)
HERE = os.path.dirname(os.path.abspath(__file__))
from chain import T_SWAP, T_ML, W, sgn
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"; UR = "0x8876789976decbfcbbbe364623c63652db8c0904"; POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
def load(tx=True):
    D = pickle.load(open(os.path.join(HERE, "fam.pkl"), "rb")); RC = json.load(open(os.path.join(HERE, "recent.json")))
    RL = pickle.load(open(os.path.join(HERE, "recentlogs.pkl"), "rb")); M = pickle.load(open(os.path.join(HERE, "mlall.pkl"), "rb"))
    P = {}
    for p, r in D["rows"].items():
        if not r["logs"]: continue
        P[p] = {"pid": p, "b0": r["b0"], "fam": r["fam"], "dep": r["from"].lower(), "nonce": r["nonce"], "tx": r["tx"], "token": r["token"].lower(), "src": "census", "logs": D["plogs"][p], "span": 3000}
    for x in RC["launches"]:
        if x["fam"] in ("v3.0", "v5.0", "v2.433") and x["pid"] in RL["plogs"]:
            P[x["pid"]] = {"pid": x["pid"], "b0": x["b0"], "fam": x["fam"], "dep": x["deployer"], "nonce": x["nonce"], "tx": x["tx"], "token": None, "src": "recent", "logs": RL["plogs"][x["pid"]], "span": min(6000, RL["head"] - x["b0"])}
    for p, v in P.items():
        rem = sorted(y for y in M["ml"].get(p, []) if y[2] < 0)
        v["pull"] = rem[0][0] - v["b0"] if rem else None; v["pull_tx"] = rem[0][3] if rem else None
        sw = []
        for bn, li, t0, snd, d, th in sorted(v["logs"], key=lambda z: (z[0], z[1])):
            if t0 == T_SWAP:
                a0 = s128(W(d, 0)); a1 = s128(W(d, 1))
                sw.append({"bn": bn, "rel": bn - v["b0"], "li": li, "eth": -a0 / 1e18, "tok": a1, "sp": W(d, 2), "L": W(d, 3), "snd": "0x" + snd[-40:], "th": th})
        v["sw"] = sw
    TX = {}
    if tx:
        for f in (os.path.join(HERE, "cache_tx.pkl"), os.path.join(HERE, "cache_tx2.pkl")):
            for _ in range(20):
                try:
                    if os.path.exists(f): TX.update(pickle.load(open(f, "rb")))
                    break
                except Exception:
                    import time; time.sleep(3)
    return P, TX, M
COV = {"census": 300, "recent": 600}
def classifier(TX):
    BOTW = {t["from"] for t in TX.values() if t["to"] == ROUTER}
    def cls(v, s):
        t = TX.get(s["th"])
        if not t: return None, None
        if t["from"] == v["dep"]: return "dep", t
        if t["to"] == ROUTER or t["from"] in BOTW: return "bot", t
        return "out", t
    return BOTW, cls
