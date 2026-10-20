import pickle, collections, sys, numpy as np
sys.path.insert(0, ".")
from fams import hours, MID_H
P = pickle.load(open("pools.pkl", "rb")); FP = pickle.load(open("fwd_pools.pkl", "rb"))
PM_POS = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
isf = lambda p: p.get("to") == PM_POS and p.get("inlen") == 1444 and p.get("fee") == 2500 and p.get("ts") == 50 and abs((p.get("value") or 0) - 2.4333285) < 1e-9 and "sw" in p
inw = sorted([p for p in P.values() if isf(p)], key=lambda p: p["b0"]); fwd = sorted([p for p in FP.values() if isf(p)], key=lambda p: p["b0"])
print("in-window", len(inw), "forward", len(fwd))
UR = "8876789976decbfcbbbe364623c63652db8c0904"
for name, ps in (("inwin", inw), ("fwd", fwd)):
    fb = []; fbsz = []; pull = []; pulls_early = []; nsw = []; pre = collections.Counter(); pre_eth = []; urdust = 0; second = []
    for p in ps:
        b0 = p["b0"]; sw = p["sw"]
        big = [x for x in sw if -x[2] >= 0.01e18]
        if big: fb.append(big[0][0] - b0); fbsz.append(-big[0][2] / 1e18)
        else: fb.append(None)
        if len(big) > 1: second.append(big[1][0] - b0)
        pl = [m for m in p["mls"] if m[4] < 0]
        pull.append(pl[0][0] - b0 if pl else None)
        nsw.append(len(sw))
        if big:
            for x in sw:
                if x[0] < big[0][0] and x[2] < 0:
                    pre[(x[6][:8], x[0] - b0)] += 1; pre_eth.append(-x[2])
    a = np.array([x for x in fb if x is not None])
    print(f"== {name}: pools {len(ps)}; with a >=0.01 buy {len(a)}; first big buy offset p5/25/50/75/95 {np.percentile(a, [5, 25, 50, 75, 95])}; <=+3 {np.mean(a <= 3):.3f} <=+4 {np.mean(a <= 4):.3f} <=+5 {np.mean(a <= 5):.3f} <=+6 {np.mean(a <= 6):.3f} <=+7 {np.mean(a <= 7):.3f} <=+8 {np.mean(a <= 8):.3f}")
    print("   offsets histogram:", sorted(collections.Counter(a.tolist()).items())[:20])
    print("   first big buy size ETH p5/25/50/75/95", np.round(np.percentile(fbsz, [5, 25, 50, 75, 95]), 4))
    print("   second big buy offset p5/25/50/75", np.percentile(second, [5, 25, 50, 75]) if second else None)
    pr = [x for x in pull if x is not None]
    print("   pulls within 3000:", len(pr), " p5/25/50 offset", np.percentile(pr, [5, 25, 50]) if pr else None, " pulls <= +30:", sum(1 for x in pr if x <= 30), " <= +100:", sum(1 for x in pr if x <= 100))
    print("   pre-bot buys (sender, offset) top:", pre.most_common(12))
    print("   swaps per pool p5/50/95", np.percentile(nsw, [5, 50, 95]))
# by hour: first-big-buy offset and competitor presence
print("\nper 3h bucket (in-window + forward): n, median first-big offset, share <=+6, share with a non-UR pre-bot buy, share with a UR pre-bot buy >=1e-5 ETH, pull<=+30")
allp = inw + fwd
bk = collections.defaultdict(list)
for p in allp: bk[int(hours(p["b0"]) // 3)].append(p)
for k in sorted(bk):
    ps = bk[k]; fo = []; nonur = 0; urpre = 0; pe = 0
    for p in ps:
        b0 = p["b0"]; big = [x for x in p["sw"] if -x[2] >= 0.01e18]
        if not big: continue
        fo.append(big[0][0] - b0)
        pre = [x for x in p["sw"] if x[0] < big[0][0] and x[2] < 0]
        if any(x[6] != UR for x in pre): nonur += 1
        if any(x[6] == UR and -x[2] >= 1e13 for x in pre): urpre += 1
        pl = [m for m in p["mls"] if m[4] < 0]
        if pl and pl[0][0] - b0 <= 30: pe += 1
    fo = np.array(fo)
    print(f"  h{3*k:3d}-{3*k+3:3d} n {len(ps):3d} med {np.median(fo):4.0f} <=+6 {np.mean(fo <= 6):.2f} nonUR-pre {nonur/len(fo):.2f} URpre {urpre/len(fo):.2f} pull<=30 {pe}")
