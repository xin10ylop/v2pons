"""F4b hooks: eth_getCode of all 23 (one batch), code hashes, size, the PUSH4 constants (function selectors) and opcodes of interest; and the
same for the crowd routers. Cached in cache/hookcode.json"""
import sys, os, json, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from chain import batch
from load import *
from eth_utils import keccak
OUT = "cache/hookcode.json"
P = load_pools()
PMA = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
F4b = [p for p in P.values() if p["launch_to"] == PMA and p["selector"] == "6276cbbe" and p["calldata_len"] == 196 and p["fee"] == 500 and p["tick_spacing"] == 1 and not p["hooks_zero"]]
addrs = [p["hooks"] for p in F4b] + ["0x410499a03705092ed02a231783d6e96332d84feb", "0xebe93d2f86639869af18b9fc77a3439092ee0e90", "0x628bd69ecbc135cdda02ffd6d6db918f5cd835ce",
                                     "0x055de4ce27753aab185eb4387851ea12b00bb341", "0xe394ba9ff1b3d7337e01f89537a5c4980af1e439"]
C = json.load(open(OUT)) if os.path.exists(OUT) else {}
need = [a for a in addrs if a not in C]
for a, r in zip(need, batch([("eth_getCode", [a, "latest"]) for a in need])): C[a] = r
json.dump(C, open(OUT, "w"))
def push4(code):
    b = bytes.fromhex(code[2:]); i = 0; out = []; ops = collections.Counter()
    while i < len(b):
        op = b[i]
        if op == 0x63: out.append(b[i + 1:i + 5].hex())
        if op in (0x42, 0x43, 0x32, 0x33): ops[{0x42: "TIMESTAMP", 0x43: "NUMBER", 0x32: "ORIGIN", 0x33: "CALLER"}[op]] += 1
        i += 1 + (op - 0x5f if 0x60 <= op <= 0x7f else 0)
    return out, ops
hs = collections.Counter()
for a in addrs:
    code = C[a] or "0x"; h = keccak(hexstr=code).hex()[:16] if len(code) > 2 else None; hs[(h, (len(code) - 2) // 2)] += 1
print("code hash / size:", hs.most_common())
for a in [F4b[0]["hooks"]] + addrs[-5:]:
    sel, ops = push4(C[a]); print(a[:10], "size", (len(C[a]) - 2) // 2, "ops", dict(ops), "push4", sorted(set(sel))[:60])
