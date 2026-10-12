"""Contracts created in the hourly sampled blocks (w14_creations.json): runtime size and hash, compared with the bot router's code."""
from common import *
import collections
cr = json.load(open(J("w14_creations.json"))); meta = json.load(open(J("w03_meta.json")))
rc = rpc.batch("eth_getTransactionReceipt", [[h] for _, h, _ in cr], n=20)
addrs = [(r or {}).get("contractAddress") for r in rc]
codes = rpc.batch("eth_getCode", [[a, "latest"] for a in addrs if a], n=20)
cm = dict(zip([a for a in addrs if a], codes))
c = collections.Counter(); same = []
for (b, h, f), a in zip(cr, addrs):
    code = cm.get(a) or "0x"; hh = keccak(hexstr=code).hex() if len(code) > 2 else "-"
    c[((len(code) - 2) // 2, hh[:12])] += 1
    if hh == meta["code_hash"]: same.append((b, a, f))
print("creations", len(cr), "with a contract", sum(1 for a in addrs if a))
print("router code", meta["code_len"], meta["code_hash"][:12], "| same hash among creations:", same)
print("runtime sizes/hashes:", c.most_common(12))
