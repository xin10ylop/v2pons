"""for the Oct 8 A-pot and B-pot wallets: last outgoing tx seen anywhere in the block cache vs the latest nonce now; and every cached
tx they sent to the copy collector"""
import os, json, sys, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2")
from lib2 import gentle_post
from potsets import A_OCT8, B_OCT8
from labels import A as CA, B as CB
D = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/lch/bc/"
C = "0x3fc5b8b8dada622d7f41a35a0ad8ac2e5d0f8d8a"
X = A_OCT8 | B_OCT8 | CA | CB
last = {}; toC = []; seen = set()
for f in sorted(os.listdir(D)):
    if not f.endswith(".json"): continue
    try: d = json.load(open(D + f))
    except Exception: continue
    for k, (ts, tl) in d.items():
        bn = int(k)
        if bn in seen: continue
        seen.add(bn)
        for t in tl:
            if t[1] in X:
                if t[4] >= last.get(t[1], (-1,))[0]: last[t[1]] = (t[4], bn, t[2], t[5])
                if t[2] == C: toC.append((bn, t[1], t[4], int(t[3]) / 1e18))
addrs = sorted(X); lat = {}
for i in range(0, len(addrs), 50):
    ch = addrs[i:i + 50]
    r = gentle_post([{"jsonrpc": "2.0", "id": j, "method": "eth_getTransactionCount", "params": [a, "latest"]} for j, a in enumerate(ch)])
    for x in r:
        if "result" in x: lat[ch[x["id"]]] = int(x["result"], 16)
for name, S in (("A pot Oct 8 hubs/capital", A_OCT8), ("B pot Oct 8 hubs/capital", B_OCT8)):
    print("==", name, len(S))
    for a in sorted(S, key=lambda a: last.get(a, (0, 0))[1]):
        l = last.get(a)
        print("  ", a, "last cached sent n%s blk %s -> %s %s" % ((l[0], l[1], l[2][:10], l[3]) if l else ("?", "?", "?", "")), "| latest nonce", lat.get(a),
              "| unseen later txs:", (lat.get(a) - l[0] - 1) if l and a in lat else "?")
print("== cached txs into the collector from these sets:")
for x in sorted(toC): print("  ", x, "A-pot" if x[1] in A_OCT8 else "B-pot" if x[1] in B_OCT8 else "crowdA" if x[1] in CA else "crowdB")
print("blocks searched", len(seen))
