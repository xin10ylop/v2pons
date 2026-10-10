"""scan backwards from HI to LO (chunks of 250 via bc cache, gentle RPC) for txs touching B wallets, 0xb5d3df36, 0xa57fb285;
stop 2 chunks after the first B-wallet plain transfer is found. Output: gapscan.jsonl + gapscan.log"""
import sys, json, time
from libb import *
b = json.load(open('/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/b_list.json')); B = set(b['B'])
X = B | {"0xb5d3df364b02771f53837146e7ff268264bd5ea7", "0xa57fb285237f62ada4e9265e89321822e1719f98"}
HI, LO = int(sys.argv[1]), int(sys.argv[2])
f = open(O + "gapscan.jsonl", "a"); found = None
for c in range(HI // 250, LO // 250 - 1, -1):
    for k in range(6):
        try: d = bc.chunk(c); break
        except Exception as e: print("retry", c, e, flush=True); time.sleep(20 * (k + 1))
    n = 0
    for bn in sorted(d):
        ts, tl = d[bn]
        for t in tl:
            if t[1] in X or t[2] in X:
                r = R(bn, ts, t); f.write(json.dumps(r) + "\n"); n += 1
                if t[1] in B and t[5] in ("0x", "") and found is None: found = c
    f.flush()
    print(time.strftime("%H:%M:%S"), "chunk", c * 250, "hits", n, bc.STATS, flush=True)
    if found is not None and c <= found - 2: break
print("done; first B plain transfer chunk", found * 250 if found else None, flush=True)
