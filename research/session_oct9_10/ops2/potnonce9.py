"""Oct 9 hubs (pots.json: A_7.01 and B_4.86 dispatchers/sweeps): last sent tx seen in the block caches (bc + money/blocks.pkl +
money plain-transfer logs) vs latest nonce: does either pot run a dust-cleanup afterwards?"""
import os, json, sys, glob, pickle
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2")
from lib2 import gentle_post
from labels import DISP, SWEEP, BDISP, BSWEEP
D = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/lch/bc/"
M = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/money/"
X = DISP | SWEEP | BDISP | BSWEEP
last = {}
def see(a, nonce, bn, to):
    if nonce >= last.get(a, (-1,))[0]: last[a] = (nonce, bn, to)
for f in sorted(os.listdir(D)):
    if not f.endswith(".json") or not (f.startswith("q336") or f.startswith("q337")): continue   # Oct 9 chunks (>= 84000000)
    d = json.load(open(D + f))
    for k, (ts, tl) in d.items():
        for t in tl:
            if t[1] in X: see(t[1], t[4], int(k), t[2])
for fn in glob.glob(M + "part*.jsonl") + [M + "win.jsonl"]:
    for line in open(fn):
        bn, h, fr, to, v, nonce = json.loads(line)
        if fr in X: see(fr, nonce, bn, to)
BL = pickle.load(open(M + "blocks.pkl", "rb"))
for n, tl in BL.items():
    for t in tl:
        if t[1] in X: see(t[1], t[4], n, t[2])
addrs = sorted(X); lat = {}
for i in range(0, len(addrs), 50):
    ch = addrs[i:i + 50]
    r = gentle_post([{"jsonrpc": "2.0", "id": j, "method": "eth_getTransactionCount", "params": [a, "latest"]} for j, a in enumerate(ch)])
    for x in r:
        if "result" in x: lat[ch[x["id"]]] = int(x["result"], 16)
for name, S in (("A dispatchers", DISP), ("A sweeps", SWEEP), ("B dispatchers", BDISP), ("B sweeps", BSWEEP)):
    ex = [(lat.get(a, 0) - last[a][0] - 1) for a in S if a in last and a in lat]
    print(f"{name}: {len(S)}; with a known last tx {len(ex)}; extra txs after it: {sorted(ex)}")
    for a in sorted(S, key=lambda a: last.get(a, (0, 0))[1]):
        if a in last and lat.get(a, 0) - last[a][0] - 1 != 0: print("    ", a, "last known n%d blk %d -> %s; latest nonce %d" % (last[a][0], last[a][1], last[a][2][:10], lat[a]))
