#!/usr/bin/env python3
"""Compact per-pool dataset from others/cache_plogs.pkl + cache_inits.pkl + census.jsonl -> explore/pools.pkl
per pool: b0, fee, ts, hooks, sp0, tick0, sw = [(bn, li, a0, a1, sp, L)] (our relay excluded), mls = [(bn, li, lo, hi, dl, tx)], launch tx fields."""
import sys, os, json, pickle
HERE = os.path.dirname(os.path.abspath(__file__)); SCR = os.path.dirname(HERE); O = os.path.join(SCR, "others")
sys.path.insert(0, SCR)
from chain import T_SWAP, T_ML, W, sgn
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
R = {json.loads(l)["pid"]: json.loads(l) for l in open(os.path.join(O, "census.jsonl"))}
inits = {l["topics"][1]: l for l in pickle.load(open(os.path.join(O, "cache_inits.pkl"), "rb"))["logs"]}
plogs = pickle.load(open(os.path.join(O, "cache_plogs.pkl"), "rb"))
out = {}
nrel = 0
for pid, r in R.items():
    l = inits[pid]; d = l["data"]
    p = {k: r.get(k) for k in ("pid", "b0", "tx", "token", "fee", "ts", "hooks", "from", "to", "nonce", "sel", "inlen", "value", "prio", "code", "codesize", "ours", "liq", "logs")}
    p["sp0"] = W(d, 3); p["tick0"] = sgn(W(d, 4)); p["txindex"] = int(l["transactionIndex"], 16)
    if pid in plogs:
        sw = []; mls = []
        for bn, li, t0, snd, dd, th in sorted(plogs[pid], key=lambda x: (x[0], x[1])):
            if t0 == T_SWAP:
                if snd[-40:] == RELAY: nrel += 1; continue
                sw.append((bn, li, s128(W(dd, 0)), s128(W(dd, 1)), W(dd, 2), W(dd, 3), snd[-40:], th))
            else:
                mls.append((bn, li, sgn(W(dd, 0)), sgn(W(dd, 1)), sgn(W(dd, 2)), th, snd[-40:]))
        p["sw"] = sw; p["mls"] = mls
    out[pid] = p
pickle.dump(out, open(os.path.join(HERE, "pools.pkl"), "wb"))
print("pools", len(out), "with logs", sum(1 for p in out.values() if "sw" in p), "relay swaps dropped", nrel)
