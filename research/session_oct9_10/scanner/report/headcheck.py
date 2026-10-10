# Post-census watch: ETH-pair v4 Initialize logs from the census head to the chain head, counted by fingerprint (fee, ts, sqrtP).
import sys, json, time, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc, logs, PM, T_INIT, W, sgn
OUT = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/report/headcheck.json"
a = 85203898
head = int(rpc("eth_blockNumber", []), 16)
hb = rpc("eth_getBlockByNumber", [hex(head), False]); hts = int(hb["timestamp"], 16)
ZERO = "0x" + "0"*64
L = logs({"address": PM, "topics": [T_INIT, None, ZERO]}, a, head)
FP = {(2500, 50, 1604517591721945638372359205383840): "v2.433", (10000, 200, 679394651928963067279918579724198): "v3.0",
      (10000, 200, 526364174002223567019744861584709): "v5.0", (100, 1, 792280926924313289846529216293289): "PM2276-crowd(0xd6d35b56)"}
cnt = collections.Counter(); last = {}; byhour = collections.defaultdict(collections.Counter)
for l in L:
    d = l["data"]; fee = W(d, 0); ts = sgn(W(d, 1)); hooks = "0x" + d[2+64*2+24:2+64*3]; sp = W(d, 3)
    k = FP.get((fee, ts, sp))
    if k is None:
        if fee in (100, 500) and ts in (1, 10) and hooks == "0"*40: k = f"fee{fee}/ts{ts}/hookless(other sqrtP)"
        else: k = "other"
    bn = int(l["blockNumber"], 16); cnt[k] += 1; last[k] = max(last.get(k, 0), bn)
    byhour[k][(bn - a) // 36000] += 1
res = {"from_block": a, "head": head, "head_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(hts)), "n_eth_inits": len(L),
       "by_fingerprint": dict(cnt), "last_block": last,
       "last_utc_approx": {k: time.strftime("%H:%M:%S", time.gmtime(hts - (head - b) * 0.1033)) for k, b in last.items()},
       "per_hour_bucket": {k: dict(sorted(v.items())) for k, v in byhour.items()}}
json.dump(res, open(OUT, "w"), indent=1); print(json.dumps(res, indent=1))
