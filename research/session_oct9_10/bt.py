import json, gzip, sys, collections, statistics as st
sys.path.insert(0, "/home/user/v2pons/src")
import v4math
D = json.load(gzip.open("/home/user/v2pons/research/data/slowrug_op.json.gz"))
P, S, L, T = D["pools"], D["swaps"], D["liquidity"], D["txs"]
OP = "3194e32622c5d860a0572c74edda99dcfd8fc827"; STAKE = int(0.0012e18); GAS = 2 * 110000 * 0.0201e9
low = [p for p in P if P[p]["fee"] < 10000 and T.get(P[p]["tx"], ["",""])[1] == OP]
def state(sw, upto_bn, p):
    prev = [x for x in sw if x[0] <= upto_bn]
    if prev: return prev[-1][5], prev[-1][6]
    adds = [x for x in L.get(p, []) if x[5] > 0 and x[3] < P[p]["tick0"] <= x[4]]
    return P[p]["sqrtP0"], sum(x[5] for x in adds)
def run(land, tp, deadline_land, react=None):
    out = []
    for p in low:
        b0 = P[p]["bn"]; fee = P[p]["fee"]; sw = sorted(S.get(p, []), key=lambda x: (x[0], x[1]))
        real = [x for x in sw if x[3] < 0 and -x[3] >= 2e14 and x[0] > b0]
        if not real: continue
        B = real[0][0] + land
        sp, Lq = state(sw, B - 1, p); tok = v4math.buy_out_int(sp, Lq, STAKE, fee)
        if tok <= 0: continue
        pulls = [x[0] for x in L.get(p, []) if x[5] < 0]; pull = min(pulls) if pulls else None
        exit_land = B + deadline_land
        for x in sw:
            if B <= x[0] <= B + deadline_land - 2 and x[3] < 0 and -x[3] >= 2e14:
                # price after this buy as if ours sat ahead of it: re-derive from the swap's post-state
                spx, Lx = x[5], x[6]
                if (v4math.sell_out_int(spx, Lx, tok, fee) - STAKE - GAS) / STAKE >= tp:
                    exit_land = x[0] + 2; break
        if pull is not None and pull <= exit_land: r = -1.0
        else:
            sp2, L2 = state(sw, exit_land - 1, p); r = (v4math.sell_out_int(sp2, L2, tok, fee) - STAKE - GAS) / STAKE
        out.append((r, exit_land - B))
    v = [r for r, _ in out]
    return f"n {len(v)} mean {st.mean(v):+.2%} median {st.median(v):+.2%} win {sum(1 for r in v if r > 0)/len(v):.0%} worst {min(v):+.1%} exits at +{collections.Counter(e for _, e in out).most_common()}"
for land in (1, 2):
    for tp in (0.005, 0.01, 0.02):
        print(f"land first+{land}, take profit {tp:.1%}, deadline land +4: " + run(land, tp, 4))
    print(f"land first+{land}, fixed hold 4 (no take profit): " + run(land, 9, 4))
    print(f"land first+{land}, fixed hold 7 (no take profit): " + run(land, 9, 7))
