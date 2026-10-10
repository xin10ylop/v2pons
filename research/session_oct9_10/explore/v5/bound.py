"""Upper bound given the operator's reaction: buy at B (after the other swaps of B), sell at the head of the block right after the FIRST
operator buy behind ours (perfect foresight, no engine latency), P(pull <= S) from the 61 measured reaction lags. Cheap single-range pricer
(float) on every census + forward v5.0 pool."""
import pickle, json, statistics as st, os
HERE = os.path.dirname(os.path.abspath(__file__))
P = pickle.load(open("pools.pkl","rb")); FP = pickle.load(open("fwd_pools.pkl","rb"))
PM_POS = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
ps = [p for p in P.values() if p.get("to")==PM_POS and p.get("inlen")==1444 and p.get("fee")==10000 and p.get("ts")==200 and round(p.get("value") or 0,3)==5.0 and "sw" in p]
ps += [p for p in FP.values() if p["fam"].endswith("v5.0")]
LAGS = json.load(open(os.path.join(HERE, "lags.json")))["lags"]
Q96 = 2**96; G = 4.2e12
def st_after(p, bn):
    sp, L = p["sp0"], p["sw"][0][5] if p["sw"] else None
    for s in p["sw"]:
        if s[0] > bn: break
        sp, L = s[4], s[5]
    return sp, L
for X_ in (0.0012, 0.012):
    X = X_*1e18
    for B_off in (3, 4, 5):
        rs = []; rr = []; ps_ = []
        for p in ps:
            b0 = p["b0"]; B = b0 + B_off
            pull = next((m[0] for m in p["mls"] if m[4] < 0), None)
            if pull is not None and pull <= B: continue
            sp, L = st_after(p, B); fee = p["fee"]/1e6
            s0 = sp/Q96; xn = X*(1-fee); so = 1/(1/s0 + xn/L); tok = L*(s0-so); tn = tok*(1-fee)
            fb = next((s for s in p["sw"] if s[0] > B and s[2] < 0 and -s[2] >= 0.01e18), None)
            if fb is None: continue
            S = fb[0] + 1
            spc, Lc = st_after(p, S - 1)
            sc = 1/(1/(spc/Q96) + xn/Lc); s2 = sc + tn/Lc
            r = (Lc*(1/sc - 1/s2) - X - G)/X
            pp = sum(1 for l in LAGS if l <= S - B)/len(LAGS)
            if pull is not None and pull <= S: pp = 1.0
            rs.append(r); ps_.append(pp); rr.append((1-pp)*r + pp*(-1 - G/X))
        print(f"stake {X_}: buy at +{B_off}, sell right after the first operator buy behind ours: n {len(rs)} no-reaction mean {st.mean(rs)*100:+.2f}% | "
              f"P(pull<=sell) mean {st.mean(ps_):.2f} | with reaction mean {st.mean(rr)*100:+.2f}% median {st.median(rr)*100:+.2f}%")
