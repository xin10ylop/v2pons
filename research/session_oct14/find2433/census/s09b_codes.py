"""Step 9b: code size and keccak of every non-VB token ending in 777 launched after the stop, and of one VB 3.0 / 5.0 token for comparison.
The 2.433 token template is 1,526 bytes with code hash 63ad5291cdef..."""
from common import *
t = jload("s09_tells.json")
rows = launches()
toks = sorted({x["tok"] for x in t["token ending 777, not VB 3.0/5.0"]})
ref = [next(r["tok"] for r in rows if r["fam"] == "VB 3.0"), next(r["tok"] for r in rows if r["fam"] == "VB 5.0"), next(r["tok"] for r in rows if r["fam"] == "VB 2.433")]
codes = rpc.batch("eth_getCode", [[a, "latest"] for a in toks + ref], n=10)
import collections
for a, c in zip(toks + ref, codes):
    b = bytes.fromhex(c[2:]) if c and c != "0x" else b""
    tag = "REF " + ("3.0" if a == ref[0] else "5.0" if a == ref[1] else "2.433") if a in ref else ""
    print(a, len(b), ("0x" + keccak(b).hex()[:12]) if b else "-", tag)
