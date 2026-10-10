import pickle, collections, json
UR = "8876789976decbfcbbbe364623c63652db8c0904"
P = pickle.load(open("pools.pkl","rb")); FP = pickle.load(open("fwd_pools.pkl","rb"))
PM_POS = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
cen = [p for p in P.values() if p.get("to")==PM_POS and p.get("inlen")==1444 and p.get("fee")==10000 and p.get("ts")==200 and round(p.get("value") or 0,3)==5.0 and "sw" in p]
fwd = [p for p in FP.values() if p["fam"].endswith("v5.0")]
def sender(s): return s[6] if len(s) > 6 else None
for name, ps in (("census", cen), ("forward", fwd)):
    ev = []; esc = []
    for p in ps:
        b0 = p["b0"]; pull = next((m[0]-b0 for m in p["mls"] if m[4]<0), None)
        nb = [s for s in p["sw"] if (s[6] if isinstance(s[6], str) else "")[-40:] != UR and s[2] < 0 and -s[2] > 2e13]
        if not nb: continue
        t = nb[0][0]-b0
        if pull is not None and pull <= t: continue
        lag = pull - t if pull is not None else None
        # non-UR sells after the outsider buy and before the pull (an outsider getting out)
        outs = [(s[0]-b0, round(s[2]/1e18, 5)) for s in p["sw"] if (s[6] if isinstance(s[6], str) else "")[-40:] != UR and s[2] > 0 and t <= s[0]-b0 and (pull is None or s[0]-b0 < pull)]
        ev.append((lag, t, round(-nb[0][2]/1e18, 5), outs[:3]))
    lags = [e[0] for e in ev]
    big = [e for e in ev if e[2] >= 1.1e-4]
    print(f"== {name}: pools {len(ps)}, with an outsider buy before any pull {len(ev)}; pulled within 24 blocks {sum(1 for x in lags if x is not None and x <= 24)}; "
          f"outsider >= 1.1e-4 ETH: {len(big)}, pulled within 24: {sum(1 for e in big if e[0] is not None and e[0] <= 24)}")
    print("   outsider sells between its buy and the pull:", [e for e in ev if e[3]][:12])
    print("   lags:", sorted((e[0] if e[0] is not None else 9999, e[1], e[2]) for e in ev))
