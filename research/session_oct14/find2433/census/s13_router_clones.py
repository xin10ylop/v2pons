"""Clone check: code hash of every contract that was the tx target of a fetched swap tx (s06), vs the old bot router 0x1cbaf24d
(20,443 B, keccak bd31d4da...). Output: s13_router_clones.out."""
from common import *
import collections
tos = sorted({r["to"] for r in jl_load("s06_tx_cache.jsonl") if "miss" not in r and r["to"]})
codes = rpc.batch("eth_getCode", [[a, "latest"] for a in tos], n=10)
print("distinct tx targets", len(tos))
same = []; near = []
for a, c in zip(tos, codes):
    b = bytes.fromhex(c[2:]) if c and c != "0x" else b""
    k = ("0x" + keccak(b).hex()[:16]) if b else "EOA"
    if k == "0xbd31d4da7db89e01": same.append(a)
    if b and abs(len(b) - 20443) < 200: near.append((a, len(b), k))
print("same code as the bot router:", same); print("contracts within 200 B of 20,443 B:", near)
