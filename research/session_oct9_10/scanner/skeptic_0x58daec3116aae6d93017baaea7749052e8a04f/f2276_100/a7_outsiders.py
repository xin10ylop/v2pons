"""Skeptic f2276/100 step 7: (a) the census pools where an outsider (not the app router, not the dust wallets) bought >= 0.001 ETH among the
first 8 swaps: before or after the crowd, the crowd's money, the pull; a matched control (pools with the same crowd state and no such
buy) for the pull delay; (b) the outsiders' own realised round trips in the 66 fully attributed pools (the closest analogue of the ride)."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common_s import *
pools, TX = load_sample()
P = load_pools(); F = load_families(); T = load_txs(); pids = F[K]["pids"]; E = load_events(set(pids))
OUT_EX = {DUST, "0x93b0790287720a922bb7e3cf0712062c1669847d"}
info = {}
for pid in pids:
    e = E[pid]; b0 = P[pid]["launch_block"]; sw = e["swaps"]
    cr = [s for s in sw if s["tx"] in T and T[s["tx"]]["to"] == CROWD and s["a0"] < 0]
    pull = e["pulls"][0]["bn"] if e["pulls"] else None
    info[pid] = {"b0": b0, "c1": cr[0]["bn"] if cr else None, "pull": pull, "sw": sw}
print("(a) census first-8 outsider buys >= 0.001 ETH")
treat = []
for pid in pids:
    I = info[pid]
    for s in I["sw"]:
        t = T.get(s["tx"])
        if t and s["a0"] < 0 and t["to"] != CROWD and t["from"] not in OUT_EX and -s["a0"] >= 1e15:
            eth_cr_before = sum(-x["a0"] for x in I["sw"] if x["bn"] <= s["bn"] and x["a0"] < 0) / 1e18
            treat.append({"pid": pid[:10], "off": s["bn"] - I["b0"], "eth": round(-s["a0"] / 1e18, 4), "from": t["from"][:10], "to": t["to"][:10],
                          "c1": (I["c1"] - I["b0"]) if I["c1"] else None, "rel_c1": (s["bn"] - I["c1"]) if I["c1"] else None,
                          "eth_in_before": round(eth_cr_before, 3), "pull_after": (I["pull"] - s["bn"]) if I["pull"] else None,
                          "pull_off": (I["pull"] - I["b0"]) if I["pull"] else None})
            break
for r in treat: print("  ", r)
# matched control: for each treated pool, pools with no outsider >= 0.001 in the first 8 swaps, alive at the same offset, with the
# crowd state 'same side' (c1 before/after that offset) and pool ETH within x0.5..x2 at that offset: P(pull within 100 blocks)
tre_pids = set(r["pid"] for r in treat)
def eth_at(I, bn): return sum(-x["a0"] for x in I["sw"] if x["bn"] <= bn and x["a0"] < 0) / 1e18 - sum(x["a0"] for x in I["sw"] if x["bn"] <= bn and x["a0"] > 0) / 1e18
ctrl_hits = []; tr_hits = []
for r in treat:
    tr_hits.append(1 if r["pull_after"] is not None and r["pull_after"] <= 100 else 0)
    off = r["off"]; hits = []
    for pid in pids:
        if pid[:10] in tre_pids: continue
        I = info[pid]; bn = I["b0"] + off
        if I["pull"] is not None and I["pull"] <= bn: continue
        has_c = I["c1"] is not None and I["c1"] <= bn
        if has_c != (r["rel_c1"] is not None and r["rel_c1"] >= 0): continue
        e_ = eth_at(I, bn); e_t = r["eth_in_before"] - r["eth"]
        if not (e_t * 0.5 - 0.01 <= e_ <= e_t * 2 + 0.01): continue
        hits.append(1 if I["pull"] is not None and I["pull"] - bn <= 100 else 0)
    ctrl_hits.append((sum(hits), len(hits)))
print("treated: pulled within 100 blocks of the outsider buy:", sum(tr_hits), "of", len(tr_hits))
print("matched controls per treated (pulled within 100 / n):", ctrl_hits, "pooled rate", round(sum(a for a, b in ctrl_hits) / max(1, sum(b for a, b in ctrl_hits)), 3))
# (b) outsiders' realised round trips in the attributed pools
print("(b) outsider round trips (buy then a later sell by the same wallet, same pool) in the 66 attributed pools")
rt = collections.defaultdict(list)
for pl in pools:
    pos = {}
    for s in pl["swaps"]:
        w = s["from"]
        if s["crowd"] or w in OUT_EX: continue
        if s["buy"]: pos.setdefault(w, []).append(s)
        elif w in pos:
            b = pos.pop(w); eth_in = sum(x["eth"] for x in b)
            rt[w].append({"pid": pl["pid"][:10], "buy_rel_c1": (b[0]["bn"] - pl["crowd1"]) if pl["crowd1"] else None, "hold": s["bn"] - b[0]["bn"],
                          "eth_in": eth_in / 1e18, "ret": s["eth"] / eth_in - 1})
    for w, b in pos.items():
        rt[w].append({"pid": pl["pid"][:10], "buy_rel_c1": (b[0]["bn"] - pl["crowd1"]) if pl["crowd1"] else None, "hold": None, "eth_in": sum(x["eth"] for x in b) / 1e18,
                      "ret": -1.0 if (pl["pull_bn"] is not None) else None, "unsold": True})
summ = []
for w, v in rt.items():
    done = [x for x in v if x["ret"] is not None]
    summ.append({"wallet": w, "trades": len(v), "sold": sum(1 for x in v if not x.get("unsold")), "lost_to_pull": sum(1 for x in v if x.get("unsold") and x["ret"] == -1.0),
                 "mean_ret": round(sum(x["ret"] for x in done) / len(done), 4) if done else None, "eth_in_med": q([x["eth_in"] for x in v], (.5,)),
                 "buy_rel_c1": q([x["buy_rel_c1"] for x in v], (0, .5, 1)), "hold": q([x["hold"] for x in v if x["hold"] is not None], (0, .5, 1))})
summ.sort(key=lambda x: -x["trades"])
for s in summ[:15]: print("  ", s)
json.dump({"treated": treat, "ctrl": ctrl_hits, "round_trips": summ}, open(os.path.join(HERE, "a7_outsiders.json"), "w"), indent=1)
