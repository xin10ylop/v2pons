"""Skeptic f2276/100 step 8: the ride (c1+1, hold 50) by 6-hour UTC slice and by the size of the first crowd buy; the token contracts'
code (one template or many: honeypot risk); the binomial tail of the trap test; launches per 6 h including the fresh window."""
import sys, os, datetime, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from common_s import *
from chain import batch
from eth_utils import keccak
pools, TX = load_sample()
P = load_pools(); F = load_families(); T = load_txs(); pids = F[K]["pids"]; E = load_events(set(pids))
allp = []
for pid in pids:
    p = P[pid]; e = E[pid]; sw = [dict(s, buy=s["a0"] < 0) for s in e["swaps"]]
    cr = [s for s in sw if s["tx"] in T and T[s["tx"]]["to"] == CROWD and s["buy"]]
    allp.append({"pid": pid, "b0": p["launch_block"], "ts0": p["launch_ts"], "sp0": p["sqrt_p0"], "L0": p["liq_launch"], "swaps": sw, "pulls": e["pulls"],
                 "pull_bn": e["pulls"][0]["bn"] if e["pulls"] else None, "crowd1": cr[0]["bn"] if cr else None, "c1eth": -cr[0]["a0"] / 1e18 if cr else None, "token": p["token"]})
sl = collections.defaultdict(list); sz = collections.defaultdict(list)
for pl in allp:
    if not pl["crowd1"]: continue
    r, why = replay(pl, pl["crowd1"] + 1, pl["crowd1"] + 51)
    d = datetime.datetime.utcfromtimestamp(pl["ts0"]); sl[d.strftime("%m-%d ") + "%02d" % (d.hour // 6 * 6)].append((r, why))
    sz["c1 < 0.01" if pl["c1eth"] < 0.01 else ("c1 0.01-0.1" if pl["c1eth"] < 0.1 else "c1 >= 0.1")].append((r, why))
def s(rs):
    v = [r for r, w in rs]; v.sort()
    return {"n": len(v), "mean": round(sum(v) / len(v), 4), "median": round(v[len(v) // 2], 4), "win": round(sum(1 for x in v if x > 0) / len(v), 2), "pulled": sum(1 for r, w in rs if w == "pulled")}
print("by 6h slice:"); [print("  ", k, s(v)) for k, v in sorted(sl.items())]
print("by first crowd buy size:"); [print("  ", k, s(v)) for k, v in sorted(sz.items())]
# token code
toks = [pl["token"] for pl in pools]
p = os.path.join(D, "token_code.json")
if os.path.exists(p): codes = json.load(open(p))
else:
    codes = dict(zip(toks, batch([("eth_getCode", [t, "latest"]) for t in toks]))); json.dump(codes, open(p, "w"))
hc = collections.Counter(("0x" + keccak(hexstr=c).hex()[:16], (len(c) - 2) // 2) if c and c != "0x" else None for c in codes.values())
print("token code (hash prefix, bytes):", hc.most_common(6))
# binomial tail for the trap test: 6 of 15 vs p = 0.123
n, k, pp = 15, 6, 0.123
tail = sum(math.comb(n, i) * pp ** i * (1 - pp) ** (n - i) for i in range(k, n + 1)); print("P(>=6 of 15 | p=0.123) =", round(tail, 4))
fresh_n = len([pl for pl in pools if pl["src"] == "fresh"]); head = json.load(open(os.path.join(D, "head.json")))
print("fresh window launches:", fresh_n, "in", round((head - 3100 - 85_203_898) * 0.1026 / 3600, 2), "h")
json.dump({"slices": {k: s(v) for k, v in sl.items()}, "c1size": {k: s(v) for k, v in sz.items()}, "token_code": [[str(a), b] for a, b in hc.most_common()]},
          open(os.path.join(HERE, "a8_slices_tokens.json"), "w"), indent=1)
