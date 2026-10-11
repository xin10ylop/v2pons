"""compare the Arbitrum v4 PositionManager runtime code hash with Robinhood's PositionManager, and read the vbot addresses on Robinhood for reference"""
import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/scout")
from rpc1 import rpc, LOG
from eth_utils import keccak
ARB = "https://arb1.arbitrum.io/rpc"; RH = "https://rpc.mainnet.chain.robinhood.com"
def codehash(u, a):
    r = rpc(u, "eth_getCode", [a, "latest"])
    if "result" not in r: return None, str(r)[:150]
    b = bytes.fromhex(r["result"][2:]); return (len(b), keccak(b).hex()) if b else (0, None), None
arb_posm = "0xd88f38f930b7952f2db2432cb002e7abbf3dd869"
rh_posm = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
rh_vbot_router = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
for lbl, u, a in [("ARB POSM 0xd88f", ARB, arb_posm), ("RH POSM 0x58da", RH, rh_posm), ("RH vbot-router 0x1cba", RH, rh_vbot_router)]:
    (info, err) = codehash(u, a); print(lbl, info, err or "")
# arb POSM: does it answer poolManager()/WETH9()? selector poolManager() = 0x3e1b0862
r = rpc(ARB, "eth_call", [{"to": arb_posm, "data": "0x3e1b0862"}, "latest"]); print("ARB POSM poolManager():", r.get("result", r)[:70] if isinstance(r.get("result"), str) else r)
print("requests", len(LOG), "non-ok", [x for x in LOG if x[1] != "ok"])
