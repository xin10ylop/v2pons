"""Over every cached block (ops/lch/bc + money/blocks.pkl): plain ETH transfers between A-side and B-side addresses, and third parties
that exchange plain ETH with both sides."""
import sys, os, json, glob, pickle, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops")
from sets import A, B, Asys, Bsys
M = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/money/"
loop = json.load(open(M + "loop.json"))
Bdisp = {"0xb0c4ef6751ac3165d489053467e553f63c2d5fb0", "0xc3c93b3e446e6058fd4fad1ad7fb42017a750996", "0x16339670fbb236a5e506a0c4e6cef726d54a76d5", "0xefa9bf82c1804e8d6cfcc8ab8b8e419d88f0867b"}
Bsw = {"0xf9c48bc5f019e4fa399e9a59555ad037b6d97918", "0xfc0db577c364cb0750a4b3374131a04b57410764", "0x8bc61010296f6e1dcf4499ddfef65f2773824be2", "0x9763030525b25a84d231cd96b452ac6613f8a834"}
Bextra = Bdisp | Bsw | {"0xa57fb285237f62ada4e9265e89321822e1719f98", "0x3298890ad7b94a88f70f8820fd4d263215c5e090", "0xae35895be6bd3d46df4745e1c5e13205e84ce75f",
    "0x9daaee61a5710c853f186cf738ae0d09d8f6d566", "0xd73e41655897c32dcf331e981eaea864ecbe16c6", "0x4f93bdb25c1ab820a6b64a42d763dd1ee8fff55e", "0xa2c79f3548cba933af86854ae79175c2a4f9fc67",
    "0xcb91f474f466d16e86c2a55f14d9c08414c7035f", "0x12f562d25fd0495e08d957940cf80eac64a53236", "0xb6579a7eda10e789332bd55a1fbf787359636f66", "0x8d576aab844687484b1f5fa5d4f383051593f63e",
    "0x5bf1a95a27170ef3cb9a6888a35b8355af42ad77", "0x402a8474f991b96b8b0550b1637aef8613fd4f54", "0xbd8a3b869b415f14fa80e567b846042c6ba4a7ec", "0x9abc777076e270f3cf6aace821020c8d20869d3e",
    "0xb5d3df364b02771f53837146e7ff268264bd5ea7", "0x82c6f69d725652da17688b1df98bf763d2d64b48", "0xb190c53f71e81c7d102c9973911b6034b3317ee5", "0xb5440ce176daf6e7bf98167a1121aa80f65ba883",
    "0xb4d94437cf0426daae6af53cf6e4370c09acf0ca", "0x58fc6f17ea0d2e472867fed709cedb6b131a40dc", "0xded28cc0001917222aa2b55ad55f1d236ef1be74", "0x1821144f9d9c8f773ba295641a5a730c9b8cb066",
    "0x1d18f10325a5b4fa584dbad259473107a29a79ac", "0xe50dd00a357018225b86e232e5cb8b762b533556", "0xdb1e05f3c7bb7da09b9e81362a247e5fc59d276e", "0xf73fa6525c2da6e0909f3ba707375c101cb88596"}
Aextra = (set(loop["disp"]) | set(loop["sweeps"]) | {d for c in loop["chains"] if len(c) > 5 for d in c}) - Bdisp - Bsw
AS = (Asys | Aextra) - {""}; BS = (Bsys | Bextra) - {""}
print("A-side", len(AS), "B-side", len(BS), "overlap", len(AS & BS), sorted(AS & BS)[:5], flush=True)
AS -= BS & AS  # ambiguous out
cross = []; third = collections.defaultdict(lambda: [0, 0, 0.0, 0.0, set()])
def visit(bn, tx):
    h, fr, to, v, nonce, sel = tx[0], tx[1], tx[2], int(tx[3]), tx[4], tx[5]
    if v <= 0 or sel not in ("0x", ""): return
    fa, fb, ta, tb = fr in AS, fr in BS, to in AS, to in BS
    if (fa and tb) or (fb and ta): cross.append((bn, h, fr, to, v / 1e18, nonce))
    if (fa or ta) and not (fb or tb):
        x = to if fa else fr
        if x not in AS: t = third[x]; t[0] += 1; t[2] += v / 1e18; t[4].add(bn // 100000)
    if (fb or tb) and not (fa or ta):
        x = to if fb else fr
        if x not in BS: t = third[x]; t[1] += 1; t[3] += v / 1e18; t[4].add(bn // 100000)
D = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/lch/bc/"
seen = set(); nb = 0
for fn in sorted(os.listdir(D)):
    if not fn.endswith(".json"): continue
    try: d = json.load(open(D + fn))
    except Exception: continue
    for k, (ts, tl) in d.items():
        bn = int(k)
        if bn in seen: continue
        seen.add(bn); nb += 1
        for t in tl: visit(bn, t)
print("bc blocks", nb, flush=True)
try:
    BL = pickle.load(open(M + "blocks.pkl", "rb"))
    for bn, tl in BL.items():
        if bn in seen: continue
        seen.add(bn); nb += 1
        for t in tl: visit(bn, (t[0], t[1], t[2], t[3], t[4], t[5]))
except Exception as e: print("pkl", e)
print("total blocks", nb, "range", min(seen), max(seen), flush=True)
print("A<->B plain transfers:", len(cross))
for c in sorted(cross)[:40]: print("  ", c[0], c[1][:14], c[2], "A" if c[2] in AS else "B", "->", c[3], "A" if c[3] in AS else "B", round(c[4], 5), "n", c[5])
both = {x: t for x, t in third.items() if t[0] and t[1]}
print("third parties with plain ETH to/from both sides:", len(both))
for x, t in sorted(both.items(), key=lambda kv: -(kv[1][2] + kv[1][3]))[:30]:
    print("  ", x, "A-side txs", t[0], "%.4f" % t[2], "B-side txs", t[1], "%.4f" % t[3])
json.dump({"cross": cross, "both": {x: [t[0], t[1], t[2], t[3]] for x, t in both.items()}}, open("cross.json", "w"))
