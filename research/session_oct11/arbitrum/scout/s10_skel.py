"""mask32 + skeleton of the Arbitrum v4 PositionManager and PoolManager vs Robinhood's, computed locally from eth_getCode"""
import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/scout")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/census/code")
from rpc1 import rpc, LOG
from eth_utils import keccak
def skeleton(code_hex):
    b = bytes.fromhex(code_hex[2:]); 
    if not b: return None
    if len(b) > 2:
        ml = int.from_bytes(b[-2:], "big")
        if 0 < ml < len(b) - 2 and b[-2 - ml] in (0xa1, 0xa2, 0xa3): b = b[:-2 - ml]
    out = bytearray(); i = 0; n = len(b)
    while i < n:
        op = b[i]; out.append(op)
        if 0x60 <= op <= 0x7f: i += op - 0x5f
        i += 1
    return keccak(bytes(out)).hex()
def mask32(code_hex):
    b = bytes.fromhex(code_hex[2:])
    if not b: return None
    if len(b) > 2:
        ml = int.from_bytes(b[-2:], "big")
        if 0 < ml < len(b) - 2 and b[-2 - ml] in (0xa1, 0xa2, 0xa3): b = b[:-2 - ml]
    out = bytearray(b); i = 0; n = len(b)
    while i < n:
        op = b[i]
        if op == 0x7f: out[i+1:i+33] = bytes(min(32, n - i - 1))
        if 0x60 <= op <= 0x7f: i += op - 0x5f
        i += 1
    return keccak(bytes(out)).hex()
ARB = "https://arb1.arbitrum.io/rpc"; RH = "https://rpc.mainnet.chain.robinhood.com"
T = [("ARB POSM", ARB, "0xd88f38f930b7952f2db2432cb002e7abbf3dd869"),
     ("RH  POSM", RH, "0x58daec3116aae6d93017baaea7749052e8a04fa7"),
     ("ARB PoolManager", ARB, "0x360e68faccca8ca495c1b759fd9eee466db9fb32"),
     ("RH  PoolManager", RH, "0x8366a39cc670b4001a1121b8f6a443a643e40951")]
for lbl, u, a in T:
    c = rpc(u, "eth_getCode", [a, "latest"]).get("result", "0x")
    print(lbl, a, "size", (len(c)-2)//2, "exact", keccak(bytes.fromhex(c[2:])).hex()[:16], "mask32", (mask32(c) or "")[:16], "skel", (skeleton(c) or "")[:16])
print("requests", len(LOG), "non-ok", [x for x in LOG if x[1] != "ok"])
