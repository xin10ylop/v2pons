import pickle, collections, statistics as st, numpy as np
P = pickle.load(open("pools.pkl","rb"))
PM_POS = "0x58daec3116aae6d93017baaea7749052e8a04fa7"; UR="8876789976decbfcbbbe364623c63652db8c0904"
fam = sorted([p for p in P.values() if p.get("to")==PM_POS and p.get("inlen")==1444 and p.get("fee")==10000 and p.get("ts")==200 and round(p.get("value") or 0,3)==5.0 and "sw" in p], key=lambda p:p["b0"])
stats = []
for p in fam:
    b0 = p["b0"]
    pull = next((m for m in p["mls"] if m[4]<0), None)
    nb = [s for s in p["sw"] if s[6]!=UR and s[2]<0 and -s[2] > 2e13]
    if not nb or pull is None or pull[0] <= nb[0][0]: continue
    t = nb[0][0]; lag = pull[0]-t
    if lag > 30: continue
    between = [s for s in p["sw"] if t <= s[0] <= pull[0] and (s[0], s[1]) > (nb[0][0], nb[0][1])]
    # price change for the outsider from its buy to just before pull
    sp_t = nb[0][4]; sp_pre = between[-1][4] if between else sp_t
    gain = (sp_t/sp_pre)**2 - 1
    bb = [s for s in between if s[2]<0 and s[6]==UR]; ss = [s for s in between if s[2]>0]
    stats.append((lag, len(bb), len(ss), round(gain*100,2), sum(-s[2] for s in bb)/1e18))
    if len(stats) <= 10:
        print(p["pid"][:10], "outsider at", t-b0, round(-nb[0][2]/1e18,5), nb[0][6][:8], "pull at", pull[0]-b0, "dl", pull[4], "mls before:", [(m[0]-b0, m[4]) for m in p["mls"] if m[0] <= pull[0]][-3:])
        print("    between:", [(s[0]-t, round(-s[2]/1e18,5) if s[2]<0 else -round(s[2]/1e18,4), s[6][:4]) for s in between][:20], "gain to pre-pull", round(gain*100,2))
        print("    last 6 swaps before outsider:", [(s[0]-t, round(-s[2]/1e18,5) if s[2]<0 else -round(s[2]/1e18,4)) for s in p["sw"] if s[0] < t][-6:])
print("lag, UR buys between, sells between, outsider gross gain to pre-pull %, UR buy ETH between")
for x in sorted(stats): print("  ", x)
print("mean UR buys between", np.mean([x[1] for x in stats]), "share with 0 UR buys", np.mean([x[1]==0 for x in stats]))
# Does the full liquidity get removed?
fr = []
for p in fam:
    pl = [m for m in p["mls"] if m[4] < 0]
    if pl: fr.append(-pl[0][4] / p["mls"][0][4])
print("first pull fraction of launch liquidity: ", collections.Counter(round(x,3) for x in fr).most_common(5))
