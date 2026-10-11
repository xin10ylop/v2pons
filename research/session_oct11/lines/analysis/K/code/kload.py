"""loaders: creates (census + new), trades grouped per curve, block->time."""
import json, os, bisect, collections, time
from krpc import *

def load_creates():
    C = {}
    for line in open(os.path.join(CEN, "cache", "bonding.jsonl")):
        r = json.loads(line)
        for l in r["logs"]:
            C[A(l["topics"][2])] = {"bn": l["bn"], "li": l["li"], "tx": l["tx"], "token": A(l["topics"][1]), "curve": A(l["topics"][2]), "creator": A(l["topics"][3]),
                                     "quote": W(l["data"], 0), "thr": W(l["data"], 2)}
    for r in jl_read(os.path.join(DATA, "creates_new.jsonl")):
        C.setdefault(r["curve"], {"bn": r["bn"], "li": r["li"], "tx": r["tx"], "token": r["token"], "curve": r["curve"], "creator": r["creator"], "quote": r["w"][0], "thr": r["w"][2]})
    return C

def load_trades(curves=None, maxbn=None):
    T = collections.defaultdict(list)
    with open(os.path.join(DATA, "trades.jsonl")) as f:
        for line in f:
            r = json.loads(line)
            if curves is not None and r[3] not in curves: continue
            if maxbn and r[0] > maxbn: continue
            T[r[3]].append(r)
    for k in T: T[k].sort(key=lambda r: (r[0], r[1]))
    return T

_g = None
def bts(bn):
    """block -> unix time (census 5,000-block grid + k_tsgrid.json extension), linear interpolation"""
    global _g
    if _g is None:
        g = {int(k): v for k, v in json.load(open(os.path.join(CEN, "cache", "tsgrid.json"))).items()}
        p = os.path.join(DATA, "k_tsgrid.json")
        if os.path.exists(p): g.update({int(k): v for k, v in json.load(open(p)).items()})
        _g = sorted(g.items())
    ks = [x[0] for x in _g]
    i = min(max(bisect.bisect_left(ks, bn), 1), len(_g) - 1); (b0, t0), (b1, t1) = _g[i - 1], _g[i]
    return t0 + (t1 - t0) * (bn - b0) / (b1 - b0)

def day(bn): return time.strftime("%Y-%m-%d", time.gmtime(bts(bn)))

VX0 = 1.68e18; Y0 = 10**27; LPRES = 285714285714285714285714285; THR = 4.2e18
