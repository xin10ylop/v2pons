"""Ethereum: tokens minted to the new router 0xfac75d23 (Transfer from 0x0 to router), their launches (Initialize by currency1) and deploy txs."""
import sys, json, os, collections, time; sys.path.insert(0, '.'); import rpcx
from eth_utils import keccak
R = "0xfac75d23e417ee39c180bbced4c665c9b57b83b2"; pad = lambda a: "0x" + "0" * 24 + a[2:].lower()
T = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
h, _ = rpcx.head("eth_h")
# router creation block: binary search code existence
lo, hi = 25000000, h
while hi - lo > 1:
    m = (lo + hi) // 2
    if len(rpcx.call("eth_h", "eth_getCode", [R, hex(m)])) > 2: hi = m
    else: lo = m
print("router code appears at block", hi, time.strftime("%m-%d %H:%M:%S", time.gmtime(rpcx.ts_of("eth_h", hi))))
blk = rpcx.call("eth_h", "eth_getBlockByNumber", [hex(hi), True])
for t in blk["transactions"]:
    if t.get("to") is None: print("  create tx", t["hash"], "from", t["from"], "nonce", int(t["nonce"], 16))
mints = rpcx.logs("eth_h", {"topics": [T, pad("0x" + "0" * 40), pad(R)]}, hi, h, maxspan=5000)
print("mints to router", len(mints))
rows = [{"b": int(l["blockNumber"], 16), "tok": l["address"].lower(), "tx": l["transactionHash"], "amt": int(l["data"], 16)} for l in mints]
json.dump(rows, open("c06_eth_router_mints.json", "w"), indent=1)
inits = [json.loads(l) for l in open("c05_eth_inits_cache.jsonl")]
byc1 = collections.defaultdict(list)
for r in inits: byc1[r["c1"]].append(r); byc1[r["c0"]].append(r)
for r in rows:
    ii = byc1.get(r["tok"], [])
    print(r["b"], r["tok"], r["amt"] / 1e18, "inits:", [(x["b"], x["fee"], x["ts_"], x["sqrtP"], x["hooks"][:8]) for x in ii])
