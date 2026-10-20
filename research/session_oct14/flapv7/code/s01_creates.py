"""s01: every Portal TokenCreated over the last ~3 days to the head (publicnode getLogs, topic-filtered, 5,000-block chunks split on error).
Keeps version-7 candidates (token address ending 8888) and all creates' counts per hour (for the rate check).
-> data/creates_cache.jsonl (one row per TokenCreated: b, ti, li, tx, token, creator, ts), data/s01.json (window, counts)"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(__file__))
import rpc
from eth_utils import keccak
from eth_abi import decode
D = os.path.join(os.path.dirname(__file__), "..", "data")
PORTAL = "0xe2ce6ab80874fa9fa2aae65d277dd6b8e65c9de0"
T_CREATED = "0x" + keccak(text="TokenCreated(uint256,address,uint256,address,string,string,string)").hex()
FROM = int(sys.argv[1]) if len(sys.argv) > 1 else 126982000
HEAD = int(sys.argv[2]) if len(sys.argv) > 2 else rpc.bn()
out = os.path.join(D, "creates_cache.jsonl")
done = set()
if os.path.exists(out):
    for l in open(out):
        j = json.loads(l)
        if j.get("chunk"): done.add(tuple(j["chunk"]))
CH = 5000
fh = open(out, "a")
U = None
cur = FROM; n = 0
while cur <= HEAD:
    end = min(HEAD, cur + CH - 1)
    if (cur, end) in done: cur = end + 1; continue
    try:
        L = rpc.logs(PORTAL, [T_CREATED], cur, end, urls=U)
    except rpc.RPCError as e:
        print("err", cur, end, str(e)[:120], flush=True); time.sleep(2)
        try: L = rpc.logs_range(PORTAL, [T_CREATED], cur, end, chunk=1000)
        except rpc.RPCError as e2: print("fail", cur, end, str(e2)[:120]); time.sleep(5); continue
    rows = []
    for x in L:
        ts, creator, nonce, token, name, symbol, meta = decode(["uint256", "address", "uint256", "address", "bytes", "bytes", "bytes"], bytes.fromhex(x["data"][2:]))
        rows.append({"b": int(x["blockNumber"], 16), "ti": int(x["transactionIndex"], 16), "li": int(x["logIndex"], 16), "tx": x["transactionHash"],
                     "token": token.lower(), "creator": creator.lower(), "ts": ts, "name": name.decode("utf-8", "replace")[:60], "symbol": symbol.decode("utf-8", "replace")[:30]})
    fh.write(json.dumps({"chunk": [cur, end], "rows": rows}) + "\n"); fh.flush()
    n += len(rows); cur = end + 1
    if (cur - FROM) // CH % 20 == 0: print(cur, n, flush=True)
fh.close()
json.dump({"from": FROM, "head": HEAD}, open(os.path.join(D, "s01.json"), "w"))
print("done", FROM, HEAD, n)
