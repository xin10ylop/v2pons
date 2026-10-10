import pickle, collections, statistics as st, numpy as np
P = pickle.load(open("pools.pkl","rb"))
PM_POS = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
fam = sorted([p for p in P.values() if p.get("to")==PM_POS and p.get("inlen")==1444 and p.get("fee")==10000 and p.get("ts")==200 and round(p.get("value") or 0,3)==5.0 and "sw" in p], key=lambda p:p["b0"])
def sp_after(p, rel):
    sp = p["sp0"]
    for s in p["sw"]:
        if s[0]-p["b0"] > rel: break
        sp = s[4]
    return sp
offs = [4,5,8,10,15,20,30,40,50,60,65,80,100,130,200,300,500,1000,2000,3000]
M = []
for p in fam:
    sB = sp_after(p, 4)
    M.append([(sB/sp_after(p,o))**2 - 1 for o in offs])
M = np.array(M)
print("token value vs after block +4 (no fees), mean / median / p10 / p90")
for j,o in enumerate(offs):
    print(f"  +{o:4d}: mean {M[:,j].mean()*100:+6.2f}% med {np.median(M[:,j])*100:+6.2f}% p10 {np.percentile(M[:,j],10)*100:+6.2f}% p90 {np.percentile(M[:,j],90)*100:+6.2f}%")
# also vs launch price
print("token value after +4 vs launch: mean", np.mean([(p['sp0']/sp_after(p,4))**2-1 for p in fam])*100)
# net ETH flow per block window
flows = collections.defaultdict(list)
for p in fam:
    for lo,hi in [(0,3),(4,4),(5,20),(21,40),(41,64),(65,130),(131,300)]:
        f = sum(-s[2] for s in p["sw"] if lo <= s[0]-p["b0"] <= hi)/1e18   # ETH into pool (+ = net buy)
        flows[(lo,hi)].append(f)
for k,v in flows.items(): print("net ETH in", k, round(np.mean(v),4), "median", round(np.median(v),4))
# buy size histogram (first 64 blocks)
bs = collections.Counter(round(-s[2]/1e18,5) for p in fam for s in p["sw"] if s[2]<0 and s[0]-p["b0"]<=64)
print("buy sizes", bs.most_common(25))
ss = [round(s[2]/1e18,3) for p in fam for s in p["sw"] if s[2]>0 and s[0]-p["b0"]<=64]
print("sells in first 64 blocks", len(ss), "buys", sum(bs.values()))
# pulls
pl = []
for p in fam:
    x = [m for m in p["mls"] if m[4] < 0]
    pl.append(x[0][0]-p["b0"] if x else None)
pp = [x for x in pl if x is not None]
print("pulled pools", len(pp), "of", len(fam), "within 70 blocks", sum(1 for x in pp if x <= 70), "within 130", sum(1 for x in pp if x<=130))
print("pull offsets <= 200:", sorted(x for x in pp if x <= 200))
