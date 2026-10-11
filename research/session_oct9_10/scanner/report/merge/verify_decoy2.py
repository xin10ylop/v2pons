# 0x8cf143dd: its sell offset from launch, and against the bot's offset (is it a timer or does it wait for the bot?).
import sys, json, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import T_SWAP, T_ML, W, sgn
D = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/report/work/fresh2"
pools = json.load(open(D + "/pools.json")); ev = json.load(open(D + "/events.json")); txs = json.load(open(D + "/txs.json"))
ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"; F = "0x8cf143dd"
def s128(x): x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
tab = collections.Counter(); boff = collections.Counter(); buyoff = collections.Counter(); first_b0 = None; sizes = collections.Counter()
nofront = 0; v3after = 0
for p in pools:
    if p["sub"] != "v3.0": continue
    lg = sorted(ev[p["pid"]]["logs"], key=lambda x: (x["bn"], x["li"]))
    sw = []
    for x in lg:
        if x["t"] != T_SWAP: continue
        t = txs.get(x["tx"]); sw.append((x["bn"] - p["b0"], x["li"], s128(W(x["data"], 0)), t["from"] if t else "", t["to"] if t else "", t["input"][2:10] if t else ""))
    fb = next((s for s in sw if s[2] < 0 and s[4] == ROUTER and s[5] == "c1120e3d"), None)
    mine = [s for s in sw if s[3].startswith(F)]
    if not mine: continue
    if first_b0 is None or p["b0"] < first_b0: first_b0 = p["b0"]
    b = [s for s in mine if s[2] < 0]; se = [s for s in mine if s[2] > 0]
    for s in b: buyoff[s[0]] += 1; sizes[round(-s[2] / 1e18, 6)] += 1
    if se: tab[(fb[0] if fb else None, se[0][0])] += 1
    if fb: boff[fb[0]] += 1
print("first pool block", first_b0)
print("buy offsets", sorted(buyoff.items())); print("sizes", sorted(sizes.items()))
print("bot offsets in its pools", sorted(boff.items()))
print("(bot off, its sell off)", sorted(tab.items(), key=lambda x: (x[0][0] or 0, x[0][1])))
