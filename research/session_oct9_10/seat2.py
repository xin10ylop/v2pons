import collections, statistics as st
exec(open("seat.py").read().split("# 1. the first seat")[0])
offs = collections.Counter()
for p in pids:
    if not P[p]["fam"].startswith("operator"): continue
    sw = sorted((int(l["blockNumber"], 16), s128(W(l["data"], 0))) for l in ev[p] if l["topics"][0] == T_SWAP)
    real = [x for x in sw if x[1] <= -2e14]
    if real: offs[real[0][0] - P[p]["b0"]] += 1
print("the burst's block after the launch:", sorted(offs.items()))
for stake_eth in (0.00015, 0.0005, 0.0012, 0.005):
    STAKE = int(stake_eth * 1e18)
    for k in (3, 5):
        v = [r for p in pids if P[p]["fam"].startswith("operator") for r in [trade(p, P[p]["b0"] + k, tp_rule(12))] if r is not None]
        print(f"   ${stake_eth*2570:5.2f} at launch +{k}: mean {st.mean(v):+.1%} (gas included), worst {min(v):+.1%}, positive {sum(1 for x in v if x > 0)}/{len(v)}, about ${st.mean(v)*stake_eth*2570:+.3f} a trade")
