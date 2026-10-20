import sys, os, json, pickle, collections
S = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad"
sys.path.insert(0, S + "/vbot"); sys.path.insert(0, S)
import fetch_blocks as fb
R = [json.loads(l) for l in open(S + "/others/census.jsonl")]
f = [r for r in R if r.get('sel') == '0xac9650d8' and r.get('inlen') == 1444 and r.get('fee') == 2500 and r.get('ts') == 50]
PM = "58daec3116aae6d93017baaea7749052e8a04fa7"
MIN = int(0.0002e18)
cov = 0; hits = collections.Counter(); anyb = collections.Counter(); ex = []
for r in f:
    b0 = r["b0"]; B = fb.get(b0, b0 + 13)
    if not all(n in B for n in range(b0, b0 + 3)): continue
    cov += 1; tok = bytes.fromhex(r["token"][2:])
    seen = False
    for n in range(b0, b0 + 14):
        if n not in B: break
        for t in B[n][2]:
            idx, h, frm, to, val, nonce, typ, gas, tip, data = t
            if n == b0 and not seen:
                if h == r["tx"]: seen = True
                continue
            if val == 0 or len(data) < 20 or to[2:] == r["token"][2:] or tok not in data: continue
            off = n - b0
            anyb[off] += 1
            if val >= MIN:
                hits[off] += 1
                if off <= 2: ex.append((r["pid"], off, val / 1e18, to))
                break
        else:
            continue
        break
print("covered", cov)
print("first >=MIN buy offset", sorted(hits.items()))
print("any buy (feed rule) offsets", sorted(anyb.items()))
print("early examples", ex[:10])
