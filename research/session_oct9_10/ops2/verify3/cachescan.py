"""no-RPC scan of every cached block (ops/lch/bc + money/blocks.pkl) for plain/any value transfers touching a target set; writes cachescan.json"""
import os, json, pickle, sys
S = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/"
sys.path.insert(0, S + "ops2")
from labels import A, B, DISP, SWEEP, BDISP, BSWEEP
from potsets import A_OCT8, B_OCT8
T = {x.lower() for x in """0x8a10f14e609e6df253b2a34b3739e3cc2d7f0e98 0x106747126cc4fac6ac96f5a2d0759e3953967ea5 0xd1c8ff8d2ee6c551cb20a05426edf470a144dfde
0xce5eb19cef82297cda4c6306e4187b8c6aa69867 0x61ffb10e5c5a121b12b072269212558065b31a28 0x28121e74a0fb51270162995b6532b37b72283b81 0x892249a9ccf49889e0c469d188106698ac63fc59
0x0e4e8ebe2a3ea7b949648946a40bffbc935adc43 0xbd36fb9937bd022d2c83052cc67928fcd9bb52b9 0x5f97c2a22bcd54949fa97f5d1d51525fee920737 0xb4b1377890f35ea6d24be5fa7d0c419216db2f4a
0x484ea7c241216c2a8cabcf0b515bde62807cf460 0x0f77ceece905c99200cb9f12b7e993a57ac7abb7 0x092be2b474a9a7009d8c3161ce842f59bc27f89b
0x3ee51814a1b2d336a9da81019148aa76da470b2f 0xab7650b2ccfb0b7e5c371f909df80111cc5df16e 0xdef59ef12a5b4a40f2ee0ab4d063532c943670c2 0x0c8c381eddf7be5e1b5f888b12c418d75f788584
0x8ef3c8f1f06054677f63a75dd4cde6f881e4c253 0xe7a1c2fb86bd4755254a1f8de24e50ccc34c662e 0x1fd5451b27d8e68c8f49ef14aea7336b8ea1ac79 0xb63b68dc20b09430f1010ff88deefb83a349fba3
0x30837a8facbbdedc7753cb79a16bd030a2860a22 0xb3db60c79fdd92ec50220961d843194e93028f44""".split()}
D = S + "ops/lch/bc/"
hits = []; seen = set(); nblk = 0
def take(bn, tl):
    global nblk
    if bn in seen: return
    seen.add(bn); nblk += 1
    for t in tl:
        h, f, to, v, n, sel = t[0], t[1], t[2], int(t[3]), t[4], t[5]
        if (f in T or to in T) and v > 0: hits.append((bn, h, f, to, v, n, sel))
for fn in sorted(os.listdir(D)):
    if not fn.endswith(".json"): continue
    try: d = json.load(open(D + fn))
    except Exception: continue
    for k, (ts, tl) in d.items(): take(int(k), tl)
try:
    BL = pickle.load(open(S + "money/blocks.pkl", "rb"))
    for bn, tl in BL.items(): take(bn, [(x[0], x[1], x[2], x[3], x[4], x[5]) for x in tl])
except Exception as e: print("blocks.pkl", e)
hits.sort()
lab = lambda a: ("A" if a in A | DISP | SWEEP | A_OCT8 else "") + ("B" if a in B | BDISP | BSWEEP | B_OCT8 else "")
json.dump({"blocks": nblk, "lo": min(seen), "hi": max(seen), "hits": [list(h) + [lab(h[2]), lab(h[3])] for h in hits]}, open(S + "ops2/verify3/cachescan.json", "w"))
print("blocks scanned", nblk, "hits", len(hits))
