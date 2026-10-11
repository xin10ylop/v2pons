"""The recent line tokens' code: sizes, skeleton hash (opcodes without push data, metadata stripped; the census 'skel' key), and where
the NUMBER / ORIGIN / GASPRICE / CALL-type opcodes sit (with the surrounding instructions) in one token of each template."""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpc
from eth_utils import keccak
from v3dec import WETH
D = json.load(open("w05_recent_8h.json"))
toks = [(x["lb"], x["token1"] if x["token0"] == "0x" + WETH else x["token0"]) for x in D["line"]]
codes = rpc.batch("eth_getCode", [[t, "latest"] for _, t in toks])
def strip(b):
    n = int.from_bytes(b[-2:], "big")
    return b[:-n - 2] if n + 2 < len(b) and b[-n - 2] in (0xa1, 0xa2) else b
def dis(b):
    i = 0; out = []
    while i < len(b):
        op = b[i]; n = op - 0x5f if 0x60 <= op <= 0x7f else 0; out.append((i, op, b[i + 1:i + 1 + n])); i += 1 + n
    return out
tmpl = {}
for (lb, t), c in zip(toks, codes):
    b = bytes.fromhex(c[2:]); core = strip(b); ins = dis(core); sk = keccak(bytes(op for _, op, _ in ins)).hex()[:8]
    tmpl.setdefault((len(b), sk), []).append((lb, t, ins))
NAMES = {0x43: "NUMBER", 0x32: "ORIGIN", 0x3a: "GASPRICE", 0xf1: "CALL", 0xfa: "STATICCALL", 0xf4: "DELEGATECALL", 0xff: "SELFDESTRUCT", 0x42: "TIMESTAMP", 0x31: "BALANCE"}
for (size, sk), v in tmpl.items():
    print(f"template size {size} skel {sk}: {len(v)} tokens, launches {[lb for lb, _, _ in v][:6]}...")
    lb, t, ins = v[0]
    # where the first INVALID (0xfe) after the last JUMP sits: code after it is data
    for k, (i, op, arg) in enumerate(ins):
        if op in NAMES:
            ctx = " ".join(f"{o:02x}" + (arg2.hex() if arg2 else "") for _, o, arg2 in ins[max(0, k - 4):k + 4])
            print(f"   {t} @{i} {NAMES[op]}  ctx: {ctx}")
    fe = [i for i, op, _ in ins if op == 0xfe]
    print(f"   0xfe (INVALID) at {fe[:5]} of {len(strip(bytes.fromhex([c for (l2, t2), c in zip(toks, codes) if t2 == t][0][2:])))} bytes")
print(rpc.STATS)
