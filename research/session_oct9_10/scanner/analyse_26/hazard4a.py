"""F4a trap test by hazard: outsider buys identified from the Swap event's sender (the contract calling the PoolManager): the crowd's 7169b574 routers
go through the Universal Router (sender = UR), the 0x4f881c6a tester calls the PoolManager itself; any other sender is an outside router.
For the first outside buy (>= 0.0002 ETH) of each pool at age a (blocks after live): was the pool pulled within W blocks? vs the pull rate within W
blocks of pools alive at the same age with no outside buy before it (age-matched)."""
import sys, os, json, collections, statistics as st
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools()
PMA = "0x8366a39cc670b4001a1121b8f6a443a643e40951"; UR = "0x8876789976decbfcbbbe364623c63652db8c0904"; TESTER = "0x4f881c6afe5ced5e4469b15269fd0c1390f089c6"
OUR_RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"
F4 = [p["pid"] for p in P.values() if p["launch_to"] == PMA and p["selector"] == "6276cbbe" and p["calldata_len"] == 196]
out = {}
for g, pids in (("F4a", [x for x in F4 if P[x]["fee"] == 500 and P[x]["tick_spacing"] == 1 and P[x]["hooks_zero"]]),
                ("F4b", [x for x in F4 if P[x]["fee"] == 500 and P[x]["tick_spacing"] == 1 and not P[x]["hooks_zero"]])):
    E = load_events(set(pids))
    rows = []
    senders = collections.Counter()
    for pid in pids:
        e = E[pid]; lb = e["adds"][0]["bn"]; end = e["ev_to"]
        pb = e["pulls"][0]["bn"] if e["pulls"] else None
        ob = [s for s in e["swaps"] if s["a0"] < 0 and s["sender"] not in (UR, TESTER) and -s["a0"] >= 2 * 10**14]
        for s in ob: senders[s["sender"]] += 1
        rows.append({"pid": pid, "lb": lb, "end": end, "pb": pb, "ob": ob[0]["bn"] if ob else None, "ob_eth": -ob[0]["a0"] / 1e18 if ob else None, "n_ob": len(ob)})
    print("==", g, len(rows), "pools; with an outside-router buy >= 0.0002:", sum(1 for r in rows if r["ob"]), "senders:", senders.most_common(8))
    res = {}
    for W in (20, 50, 100, 200):
        hit = n = 0; exp = []
        for r in rows:
            if r["ob"] is None or r["ob"] + W > r["end"]: continue
            if r["pb"] is not None and r["pb"] <= r["ob"]: continue
            n += 1; hit += 1 if (r["pb"] is not None and r["pb"] <= r["ob"] + W) else 0
            a = r["ob"] - r["lb"]
            # age-matched control: pools alive at age a, no outside buy at or before age a, window fully observed
            ctl = [c for c in rows if (c["pb"] is None or c["pb"] - c["lb"] > a) and (c["ob"] is None or c["ob"] - c["lb"] > a + W) and c["lb"] + a + W <= c["end"]]
            if ctl: exp.append(sum(1 for c in ctl if c["pb"] is not None and c["pb"] - c["lb"] <= a + W) / len(ctl))
        res[W] = {"outside_buys": n, "pulled_within_W": hit, "rate": round(hit / n, 3) if n else None, "age_matched_control_rate": round(st.mean(exp), 3) if exp else None}
        print("   W=%d: after the first outside buy, pulled within W in %d of %d (%.1f%%); age-matched control %.1f%%" % (W, hit, n, 100 * hit / max(n, 1), 100 * (st.mean(exp) if exp else 0)))
    d = sorted(r["pb"] - r["ob"] for r in rows if r["ob"] and r["pb"] and r["pb"] > r["ob"])
    print("   pull minus first outside buy (pulled pools) p10/50/90:", d[len(d) // 10] if d else None, d[len(d) // 2] if d else None, d[9 * len(d) // 10] if d else None, "n", len(d))
    wo = [r for r in rows if r["ob"] is None]; wi = [r for r in rows if r["ob"] is not None]
    print("   pulled within the window: with an outside buy %d/%d, without %d/%d" % (sum(1 for r in wi if r["pb"]), len(wi), sum(1 for r in wo if r["pb"]), len(wo)))
    ages = sorted(r["ob"] - r["lb"] for r in wi); print("   age of the first outside buy p10/50/90:", ages[len(ages) // 10] if ages else None, ages[len(ages) // 2] if ages else None, ages[9 * len(ages) // 10] if ages else None)
    out[g] = {"res": res, "pull_minus_outside_p10_50_90": [d[len(d) // 10], d[len(d) // 2], d[9 * len(d) // 10]] if d else None,
              "with_outside": [sum(1 for r in wi if r["pb"]), len(wi)], "without": [sum(1 for r in wo if r["pb"]), len(wo)], "senders": senders.most_common(10)}
json.dump(out, open("hazard.json", "w"), indent=1)
