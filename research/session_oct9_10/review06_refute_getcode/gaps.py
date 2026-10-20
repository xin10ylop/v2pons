import json, urllib.request, sys, time
RPC = "https://rpc.mainnet.chain.robinhood.com"; H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"}
def rpc(m, p):
    for i in range(8):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(), H), timeout=30))
            if "result" in r: return r["result"]
            time.sleep(1)
        except Exception as e:
            time.sleep(1 + i)
    raise RuntimeError(m)
gaps = []
for line in open(sys.argv[1]).read().split("\n")[:int(sys.argv[2])]:
    if not line.strip(): continue
    bl, to, frm = line.split(); bl = int(bl)
    for k in range(1, 60):
        blk = rpc("eth_getBlockByNumber", [hex(bl - k), True]); time.sleep(0.1)
        hit = [x for x in blk["transactions"] if x.get("to") is None and x["from"].lower().startswith(frm)]
        if hit:
            rc = rpc("eth_getTransactionReceipt", [hit[0]["hash"]])
            ok = (rc.get("contractAddress") or "").lower() == to
            print(bl, to[:12], "created", k, "blocks before" + ("" if ok else " (another contract: " + str(rc.get("contractAddress")) + ")"), flush=True)
            if ok: gaps.append(k); break
    else:
        print(bl, to[:12], "no creation within 60 blocks")
import collections; print("gaps", sorted(collections.Counter(gaps).items()))
