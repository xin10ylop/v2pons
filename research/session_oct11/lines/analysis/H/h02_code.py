"""H: hook and token bytecode of recent a98b3b9e core pools: size, keccak, equality after masking immutables/addresses."""
import json, os, sys, collections as C
sys.dont_write_bytecode = True
import rpc
from eth_utils import keccak
H = os.path.dirname(os.path.abspath(__file__)); DD = os.path.join(H, "data")
P = json.load(open(os.path.join(H, "core_pools.json")))
head = int(rpc.call("eth_blockNumber", []), 16); print("head", head)
sel = P[-6:] + [P[0], P[len(P)//2]]
res = []
for r in sel:
    hc = rpc.call("eth_getCode", [r["hooks"], "latest"]); tc = rpc.call("eth_getCode", [r["token"], "latest"])
    open(os.path.join(DD, f"hook_{r['hooks']}.hex"), "w").write(hc); open(os.path.join(DD, f"token_{r['token']}.hex"), "w").write(tc)
    hb = bytes.fromhex(hc[2:]); tb = bytes.fromhex(tc[2:])
    res.append({"pool": r["pool"], "launch_utc": r["launch_utc"], "hook": r["hooks"], "hook_len": len(hb), "hook_keccak": keccak(hb).hex(), "token": r["token"], "token_len": len(tb), "token_keccak": keccak(tb).hex()})
    print(r["launch_utc"], "hook", r["hooks"], len(hb), keccak(hb).hex()[:16], "| token", r["token"], len(tb), keccak(tb).hex()[:16])
json.dump({"head": head, "codes": res}, open(os.path.join(H, "h02_code.json"), "w"), indent=1)
print(rpc.STATS)
