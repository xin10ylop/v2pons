import json, sys, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import batch, rpc
from eth_utils import keccak
D = json.load(open("/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/oct8_pools.json"))
cp = [p for p in D["pools"] if p["kind"] == "copy"]
codes = batch([("eth_getCode", [p["to"], "latest"]) for p in cp])
hs = collections.Counter()
for p, c in zip(cp, codes):
    h = keccak(bytes.fromhex(c[2:])).hex() if c and len(c) > 2 else "nocode"
    hs[h] += 1
print("copy launcher code hashes at launch block:", dict(hs))
oc = rpc("eth_getCode", ["0x3194e32622c5d860a0572c74edda99dcfd8fc827", "latest"]); print("original launcher code hash:", keccak(bytes.fromhex(oc[2:])).hex(), (len(oc) - 2) // 2, "bytes")
# selectors of orig launch txs
txs = batch([("eth_getTransactionByHash", [p["tx"]]) for p in D["pools"] if p["kind"] == "orig"])
print("orig launch selectors:", collections.Counter(t["input"][:10] for t in txs))
