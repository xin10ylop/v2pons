import sys, pickle, random, json
sys.path.insert(0, ".."); sys.path.insert(0, ".")
from chain import batch, W, sgn
from eth_utils import keccak
from fams import families
T_TR = "0x" + keccak(text="Transfer(address,address,uint256)").hex()
P = pickle.load(open("pools.pkl", "rb")); M = pickle.load(open("meta.pkl", "rb")); pids = M["pids"]; F = families(P, pids)
PMGR = "8366a39cc670b4001a1121b8f6a443a643e40951"
random.seed(7)
out = {}
for fam in ("L:0x58daec31|0xac9650d8|len1444|fee10000|ts200|v5.0", "L:0x58daec31|0xac9650d8|len1444|fee10000|ts200|v3.0", "L:0x58daec31|0xac9650d8|len1444|fee2500|ts50|v2.433"):
    for i in random.sample(F[fam], 3):
        p = P[pids[i]]; b0 = p["b0"]; tok = p["token"].lower()
        sws = [x for x in p["sw"] if x[0] - b0 <= 80][:8]
        rc = batch([("eth_getTransactionReceipt", [x[7]]) for x in sws])
        print("==", fam[-22:], p["pid"][:12], "token", tok)
        for x, r in zip(sws, rc):
            if not r: continue
            trs = [(l["topics"][1][-40:], l["topics"][2][-40:], int(l["data"], 16)) for l in r["logs"] if l["address"].lower() == tok and l["topics"][0] == T_TR]
            a1 = x[3]
            if x[2] < 0:   # buy: tokens out of the PM = -? a1 positive for the swapper receiving
                frm_pm = [t for t in trs if t[0] == PMGR]
                print(f"  +{x[0]-b0:3d} BUY  eth {-x[2]/1e18:.5f} swap_tok {abs(a1):.4e} | transfers from PM: {[('%.4e' % t[2], t[1][:8]) for t in frm_pm]} other: {[('%.4e' % t[2], t[0][:6], t[1][:6]) for t in trs if t[0] != PMGR][:3]} status {r['status']}")
            else:
                to_pm = [t for t in trs if t[1] == PMGR]
                print(f"  +{x[0]-b0:3d} SELL eth {x[2]/1e18:.5f} swap_tok {abs(a1):.4e} | transfers to PM: {[('%.4e' % t[2], t[0][:8]) for t in to_pm]} other: {[('%.4e' % t[2], t[0][:6], t[1][:6]) for t in trs if t[1] != PMGR][:3]}")
