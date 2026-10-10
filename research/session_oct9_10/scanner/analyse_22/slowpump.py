"""analyse_22 / the 2-ETH fresh-wallet operator (family F1 = POSM 1444/500/10 and its sibling 1444/100/1): its own rule.
The operator: a fresh launch wallet (nonce 3) mints 1.5/1.8/2.0 ETH + 1e10 tokens full range through the POSM multicall (1,444 bytes); then
exactly 10 buys from fresh nonce-0 wallets via the Universal Router (execute, 1,284 bytes, V4_SWAP 070b0e, minOut = 0.8 x its live quote)
push the pool's ETH reserve to ~2.48 ETH, one every ~140 blocks from ~+300; then the launch wallet pulls (POSM dd46508f) 58-1266 blocks after
the 10th. Rules priced with common22.Pool (the exact replay). Writes slowpump.json."""
import sys, os, json, statistics as st, collections, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common22 import *  # noqa
K = json.load(open(os.path.join(HERE, "keys.json")))
P = load_pools(); F = load_families(); T = load_txs(); M = load_blocks_meta()
T.update(json.load(open(os.path.join(HERE, "extra_txs.json"))))
F100 = "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|100|1|true"
G = {"F1 (fee 500, 5 pools)": F[K[0]]["pids"], "F1-WIDE (fee 500 + fee 100, 22 pools)": F[K[0]]["pids"] + F[F100]["pids"]}
G["F1-WIDE Oct 9 launches"] = [x for x in G["F1-WIDE (fee 500 + fee 100, 22 pools)"] if P[x]["launch_ts"] < 1791590400]
G["F1-WIDE Oct 10 launches"] = [x for x in G["F1-WIDE (fee 500 + fee 100, 22 pools)"] if P[x]["launch_ts"] >= 1791590400]
E = load_events(set(G["F1-WIDE (fee 500 + fee 100, 22 pools)"]))
POOL = {x: Pool(P[x], E[x], T, M) for x in E}
def is_crowd(x): return x["buy"] and x["to"] == UR and x["clen"] == 1284 and x["nonce"] == 0
def crowd(pl): return [x for x in pl.buys() if is_crowd(x)]


def kth(pl, k, cap=3000, stake=STAKE, entry=1):
    """buy landing at launch + entry (end of block), sell landing 1 block after the k-th crowd buy, else at launch + cap"""
    B = pl.b0 + entry; c = [x for x in crowd(pl) if x["bn"] > B]
    S = c[k - 1]["bn"] + 1 if len(c) >= k and c[k - 1]["bn"] + 1 <= pl.b0 + cap else pl.b0 + cap
    r = pl.trade(B, S, stake); r["pid"] = pl.pid; return r


def follow_crowd(pl, k, stake=STAKE):
    """buy landing 1 block after the first crowd buy, sell 1 block after the k-th crowd buy"""
    c = crowd(pl)
    if len(c) < max(k, 1): return None
    r = pl.trade(c[0]["bn"] + 1, c[k - 1]["bn"] + 1, stake); r["pid"] = pl.pid; return r


out = {}
utc = lambda ts: datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%m-%d %H:%M")
out["launch_times_utc"] = [utc(P[x]["launch_ts"]) for x in sorted(G["F1-WIDE (fee 500 + fee 100, 22 pools)"], key=lambda x: P[x]["launch_block"])]
for g, pids in G.items():
    pls = [POOL[x] for x in pids]; R = {}
    for k in (8, 9, 10):
        R["front_k%d" % k] = summarize([kth(pl, k) for pl in pls], days=WINDOW_DAYS)
    R["front_k10 at 0.02 ETH"] = summarize([kth(pl, 10, stake=int(0.02e18)) for pl in pls])
    R["front_k10 at 0.05 ETH"] = summarize([kth(pl, 10, stake=int(0.05e18)) for pl in pls])
    R["front_k10 entry +5"] = summarize([kth(pl, 10, entry=5) for pl in pls])
    R["front_k10 entry +60"] = summarize([kth(pl, 10, entry=60) for pl in pls])
    R["follow_crowd k2 (buy after crowd #1, sell after crowd #2)"] = summarize([r for r in (follow_crowd(pl, 2) for pl in pls) if r])
    R["follow_crowd k10 (buy after crowd #1, sell after crowd #10)"] = summarize([r for r in (follow_crowd(pl, 10) for pl in pls) if r])
    out[g] = R
    print("==", g, len(pls))
    for k, v in R.items(): print("   %-62s %s" % (k, fmt_rule(v)))
# per pool, the k=10 rule and the margins
rows = []
for x in G["F1-WIDE (fee 500 + fee 100, 22 pools)"]:
    pl = POOL[x]; c = crowd(pl); r = kth(pl, 10)
    rows.append({"pid": x[:12], "utc": utc(P[x]["launch_ts"]), "fee": P[x]["fee"], "val": P[x]["launch_value_eth"], "n_crowd": len(c),
                 "crowd_eth": round(sum(z["eth"] for z in c) / 1e18, 4), "reserve_after_crowd": round(P[x]["launch_value_eth"] + sum(z["eth"] for z in c) / 1e18, 3),
                 "c1": (c[0]["bn"] - pl.b0) if c else None, "c10": (c[9]["bn"] - pl.b0) if len(c) >= 10 else None, "pull": (pl.pull_bn - pl.b0) if pl.pull_bn else None,
                 "pull_after_c10": (pl.pull_bn - c[9]["bn"]) if (pl.pull_bn and len(c) >= 10) else None, "k10_exit": r["exit"], "k10_ret": round(r["ret"], 4) if r.get("ret") is not None else None})
    print(rows[-1])
out["pools"] = rows
# the trap test: outsiders (not the crowd, not the dust wallets, not the launch wallet) and the pull
def outsiders(pl, before=None, min_eth=MIN_REAL):
    return [z for z in pl.buys() if not is_crowd(z) and z["from"] not in DUST_WALLETS and z["from"] != pl.p["launch_from"] and z["eth"] >= min_eth and (before is None or z["bn"] < before)]
pls = [POOL[x] for x in G["F1-WIDE (fee 500 + fee 100, 22 pools)"]]
with_, without = [], []
for pl in pls:
    c = crowd(pl); fc = c[0]["bn"] if c else None
    o = outsiders(pl, before=fc)
    rec = {"pid": pl.pid[:12], "outs": [(z["bn"] - pl.b0, round(z["eth"] / 1e18, 6), (z["from"] or "?")[:10]) for z in o], "pull": (pl.pull_bn - pl.b0) if pl.pull_bn else None,
           "pull_after_c10": (pl.pull_bn - c[9]["bn"]) if (pl.pull_bn and len(c) >= 10) else None, "n_crowd": len(c)}
    (with_ if o else without).append(rec)
def qq(v): return q([z for z in v if z is not None])
trap = {"pools_with_real_outsider_before_first_crowd": len(with_), "pools_without": len(without),
        "with: pulled_3000": sum(1 for z in with_ if z["pull"] is not None), "with: pull_off_launch_p10_50_90": qq([z["pull"] for z in with_]),
        "with: pull_after_10th_crowd_p10_50_90": qq([z["pull_after_c10"] for z in with_]),
        "without: pulled_3000": sum(1 for z in without if z["pull"] is not None), "without: pull_off_launch_p10_50_90": qq([z["pull"] for z in without]),
        "without: pull_after_10th_crowd_p10_50_90": qq([z["pull_after_c10"] for z in without]),
        "outsider_sizes_p10_50_90": q([o[1] for z in with_ for o in z["outs"]], nd=6),
        "outsider_wallets": collections.Counter(o[2] for z in with_ for o in z["outs"]).most_common(5),
        "real_size_outsiders_ge_0.001_any_time": [(pl.pid[:12], [(z["bn"] - pl.b0, round(z["eth"] / 1e18, 6), (z["from"] or "?")[:10], (z["to"] or "?")[:10]) for z in outsiders(pl, min_eth=int(0.001e18))],
                                                    "pull", (pl.pull_bn - pl.b0) if pl.pull_bn else None, "n_crowd", len(crowd(pl))) for pl in pls if outsiders(pl, min_eth=int(0.001e18))],
        "with_rows": with_}
out["trap"] = trap
for k, v in trap.items():
    if k != "with_rows": print("  ", k, v)
json.dump(out, open(os.path.join(HERE, "slowpump.json"), "w"), indent=1, default=str)
