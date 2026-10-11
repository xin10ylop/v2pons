import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/scout")
from rpc1 import rpc, LOG
from eth_utils import keccak
U = "https://arb1.arbitrum.io/rpc"; HEAD = 513904384
T_INIT = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
print("T_INIT", T_INIT)
# who emits Initialize: topic-only filter over the last 2,000 blocks, then 20,000
for span in (2000, 20000):
    r = rpc(U, "eth_getLogs", [{"fromBlock": hex(HEAD - span), "toBlock": hex(HEAD), "topics": [T_INIT]}])
    if "result" not in r: print(span, "ERR", str(r)[:300]); continue
    c = collections.Counter(l["address"].lower() for l in r["result"]); print("span", span, "Initialize logs", len(r["result"]), "emitters", c.most_common(5))
cand = {"PoolManager(docs)": "0x360e68faccca8ca495c1b759fd9eee466db9fb32", "PositionManager(docs)": "0xd88f38f930b7952f2db2432cb002e7abbf3dd869",
        "UniversalRouter(docs)": "0xa51afafe0263b40edaef0df8781ea9aa03e381a3", "StateView(docs)": "0x76fd297e2d437cd7f76d50f01afe6160f86e9990",
        "V3Factory": "0x1f98431c8ad98523631ae4a59f267346ea31f984", "V2Factory": "0xf1d7cc64fb4452f05c498126312ebe29f30fbcf9",
        "vbot_router_RH": "0x1cbaf24d53fe930fce8eff149fa797d2611da149", "RH_POSM_addr": "0x58daec3116aae6d93017baaea7749052e8a04fa7",
        "RH_PM_addr": "0x8366a39cc670b4001a1121b8f6a443a643e40951"}
out = {}
for k, a in cand.items():
    c = rpc(U, "eth_getCode", [a, "latest"])["result"]; b = bytes.fromhex(c[2:])
    out[k] = {"addr": a, "size": len(b), "keccak": keccak(b).hex() if b else None}
    print(k, a, "code bytes", len(b), "hash", out[k]["keccak"])
json.dump(out, open("/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/scout/s02_codes.json", "w"), indent=1)
print("requests", len(LOG), "non-ok", [x for x in LOG if x[1] != "ok"])
