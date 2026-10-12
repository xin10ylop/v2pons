"""Byte-level drift check of the 2.4333 launch calldata (all 91 in the window): the 32-byte words that vary across launches, and what they hold
(token, recipient, deadline, amounts), with the last launch's values against the first's."""
import json
from clusters import load
from common import load_jsonl
rows = [r for r in load() if r["fam"].startswith("VB 2.4333")]; hs = {r["h"] for r in rows}
inp = {x["h"]: bytes.fromhex(x["input"][2:]) for x in load_jsonl("s02_tx_cache.jsonl") if x["h"] in hs}
bs = [inp[r["h"]] for r in rows]
print("calldata lengths", {len(b) for b in bs}, "selector", bs[0][:4].hex())
words = sorted({(i - 4) // 32 for i in range(4, len(bs[0])) if len({b[i] for b in bs}) > 1})
for w in words:
    a = 4 + 32 * w; vals = [b[a:a + 32] for b in bs]
    print("word %3d (byte %4d): %2d distinct; first %s  last %s" % (w, a, len(set(vals)), vals[0].hex().lstrip("0")[:44] or "0", vals[-1].hex().lstrip("0")[:44] or "0"))
r0, r1 = rows[0], rows[-1]
print("first launch token", r0["c1"], "sender", r0["from"], "| last launch token", r1["c1"], "sender", r1["from"])
print("other fields identical across all 91:", {k: len({str(r[k]) for r in rows}) for k in ("to", "sel", "value", "clen", "fee", "ts", "hooks", "sqrtp", "liq", "lo", "hi", "gas", "nonce")})
