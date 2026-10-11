#!/usr/bin/env python3
"""Stage 7: the bonding-curve factory 0x7ed598bc: count per day, creators, graduations into the census's pools (token match), a sample of
create transactions and, for the sample, the curve's own event topics in its first 3,000 blocks (to see what a curve emits)."""
import sys, os, time, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base import *
from f1_logs import compact_log
NS = 60

if __name__ == "__main__":
    t0 = time.time(); random.seed(11)
    L = [l for r in jl_read("bonding.jsonl") for l in r["logs"]]
    rows = [{"bn": l["bn"], "tx": l["tx"], "token": A(l["topics"][1]), "curve": A(l["topics"][2]), "creator": A(l["topics"][3]),
             "w": [W(l["data"], k) for k in range(3)]} for l in L]
    sample = random.sample(rows, min(NS, len(rows)))
    have = {x["hash"] for x in jl_iter("tx_bonding.jsonl")}
    fetch_txs([s["tx"] for s in sample], "tx_bonding.jsonl", "btx", have=have)
    ev = jget("bonding_curve_topics.json", {})
    for s in sample[:25]:
        if s["curve"] in ev: continue
        ls = logs({"address": [s["curve"], s["token"]]}, s["bn"], s["bn"] + SPAN)
        ev[s["curve"]] = {"token": s["token"], "n": len(ls), "topics": collections.Counter(f"{l['address'][:10]}:{l['topics'][0][:10]}" for l in ls).most_common(8)}
        jput("bonding_curve_topics.json", ev)
    T = {x["hash"]: x for x in jl_iter("tx_bonding.jsonl")}
    P = base_pools(); tokpools = collections.defaultdict(list)
    for p in P: tokpools[p["token"]].append(p)
    grad = []
    for r in rows:
        ps = tokpools.get(r["token"])
        if ps: grad.append({"token": r["token"], "create_bn": r["bn"], "pools": [[p["dex"], p["quote"], p["launch_block"] - r["bn"], p["pool"]] for p in ps]})
    w = window(); g = sorted((int(k), v) for k, v in jget("tsgrid.json").items())
    import bisect
    gb = [x[0] for x in g]
    def day(bn):
        i = min(max(bisect.bisect_left(gb, bn), 1), len(g) - 1); (b0, t0_), (b1, t1) = g[i - 1], g[i]
        return time.strftime("%Y-%m-%d", time.gmtime(t0_ + (t1 - t0_) * (bn - b0) / (b1 - b0)))
    out = {"factory": "0x7ed598bcef8bd9edd8c97a195c6d13f40801ec7e", "topic": "0x8d4aad4953d0ca700d468f3753aa14432d1b35b43ec6409f051fb6aa43a89607",
           "event_layout": "topics: [sig, token, curve, creator]; data: 3 words (w0, w1, w2; w2 = 4.2e18 in most creates)",
           "creates": len(rows), "per_day": dict(sorted(collections.Counter(day(r["bn"]) for r in rows).items())),
           "distinct_creators": len({r["creator"] for r in rows}), "creators_top": collections.Counter(r["creator"] for r in rows).most_common(15),
           "w_values_top": [[str(k), n] for k, n in collections.Counter(tuple(r["w"]) for r in rows).most_common(6)],
           "graduated_into_census_pools": len(grad), "graduation_dex": collections.Counter(f"{x[0]}/{x[1]}" for g_ in grad for x in g_["pools"]).most_common(),
           "graduation_blocks_after_create_p10_50_90": None,
           "sample_txs": [{"tx": s["tx"], "bn": s["bn"], "token": s["token"], "curve": s["curve"], "creator": s["creator"],
                           **({k: T[s["tx"]].get(k) for k in ("from", "to", "nonce", "value_wei", "selector", "calldata_len")} if s["tx"] in T else {})} for s in sample],
           "sample_tx_to_selector": collections.Counter(f"{T[s['tx']]['to']}:{T[s['tx']]['selector']}" for s in sample if s["tx"] in T).most_common(10),
           "sample_curve_event_topics": ev, "graduations": grad[:300]}
    d = sorted(x[2] for g_ in grad for x in g_["pools"])
    if d: out["graduation_blocks_after_create_p10_50_90"] = [d[len(d) // 10], d[len(d) // 2], d[9 * len(d) // 10]]
    json.dump(out, open(os.path.join(CEN, "bonding.json"), "w"), indent=1)
    timing("f7_bonding", time.time() - t0); log("bonding", len(rows), "graduated", len(grad), STATS)
