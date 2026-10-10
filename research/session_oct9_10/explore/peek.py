import pickle, sys, random
P = pickle.load(open("pools.pkl", "rb"))
Z = "0x" + "0" * 40
def sel(p, f):
    return "sw" in p and p["hooks"] == Z and f(p)
fams = {
 "v2.433": lambda p: p["inlen"] == 1444 and p["fee"] == 2500,
 "v5.0": lambda p: p["inlen"] == 1444 and p["fee"] == 10000 and round(p["value"], 3) == 5.0,
 "PM2276": lambda p: p["inlen"] == 2276,
 "PMdirect": lambda p: p["sel"] == "0x6276cbbe" and p["fee"] == 500,
 "orig": lambda p: p["ours"] == "orig",
}
random.seed(1)
for nm, f in fams.items():
    ps = [p for p in P.values() if sel(p, f)]
    for p in random.sample(ps, 2):
        b0 = p["b0"]
        print("=====", nm, p["pid"][:12], "fee", p["fee"], "nonce", p["nonce"], "nsw", len(p["sw"]))
        ev = [(x[0] - b0, x[1], "B" if x[2] < 0 else "S", round(abs(x[2]) / 1e18, 5), x[6][:6]) for x in p["sw"] if x[0] - b0 <= 80]
        ml = [(m[0] - b0, "ML", m[4] / 1e18) for m in p["mls"] if m[0] - b0 <= 3000]
        print("   ", ev[:45]); print("    ML", ml[:6])
