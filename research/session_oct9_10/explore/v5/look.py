import pickle, collections, statistics as st, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fams import hours
P = pickle.load(open("pools.pkl","rb"))
PM_POS = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
fam = sorted([p for p in P.values() if p.get("to")==PM_POS and p.get("inlen")==1444 and p.get("fee")==10000 and p.get("ts")==200 and round(p.get("value") or 0,3)==5.0], key=lambda p:p["b0"])
print("n", len(fam), "with sw", sum(1 for p in fam if "sw" in p))
print("hooks", collections.Counter(p["hooks"] for p in fam))
print("nonce", collections.Counter(p["nonce"] for p in fam).most_common(10))
print("from distinct", len({p["from"] for p in fam}))
print("tick0", collections.Counter(p["tick0"] for p in fam).most_common(5))
print("liq", collections.Counter(p.get("liq") for p in fam).most_common(3))
print("hours range", hours(fam[0]["b0"]), hours(fam[-1]["b0"]))
# per pool swap timings
senders = collections.Counter(); first_buy=[]; nbuys=[]; pulls=[]; ex=None
for p in fam:
    sw = p.get("sw", []); mls = p.get("mls", [])
    b0 = p["b0"]
    buys = [s for s in sw if s[2] < 0]
    sells = [s for s in sw if s[3] < 0]
    for s in sw: senders[s[6]] += 1
    if buys: first_buy.append(buys[0][0]-b0)
    nbuys.append(len(buys))
    pl = [m for m in mls if m[4] < 0]
    pulls.append(pl[0][0]-b0 if pl else None)
print("senders", senders.most_common(6))
print("first buy rel", collections.Counter(first_buy).most_common(15))
print("nbuys", st.mean(nbuys), collections.Counter(nbuys).most_common(10))
pl = [x for x in pulls if x is not None]
print("pulls", len(pl), "of", len(fam), "quantiles", sorted(pl)[::max(1,len(pl)//20)] if pl else None)
p = fam[100]
print(p["pid"], p["b0"], p["tx"], p["from"], p["nonce"])
for s in p["sw"][:40]: print(s[0]-p["b0"], s[1], s[2]/1e18, s[3]/1e18, s[6][:8], s[7][:12])
for m in p["mls"][:5]: print("ml", m[0]-p["b0"], m[4], m[5][:12], m[6][:8])
