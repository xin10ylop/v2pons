import sys, json, os
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc
HERE = os.path.dirname(os.path.abspath(__file__)); F = os.path.join(HERE, "execcode.json")
C = json.load(open(F)) if os.path.exists(F) else {}
if "exec" not in C:
    C["exec"] = rpc("eth_getCode", ["0x10845617e6e67a32085837a52da8637be2429d22", "latest"])
    json.dump(C, open(F, "w"))
c = C["exec"]; b = bytes.fromhex(c[2:]); print(len(b)); print(c)
i = 0
while i < len(b):
    op = b[i]
    if 0x60 <= op <= 0x7f:
        n = op - 0x5f
        if n >= 4: print("PUSH%d" % n, b[i+1:i+1+n].hex(), "at", i)
        i += n
    elif op in (0xf4, 0xf1, 0xfa, 0x54, 0x55): print({0xf4: "DELEGATECALL", 0xf1: "CALL", 0xfa: "STATICCALL", 0x54: "SLOAD", 0x55: "SSTORE"}[op], "at", i)
    i += 1
