"""Follow a chain of funders backwards: for addr, find most recent incoming value tx before block; repeat while the funder's tx nonce <= maxn.
Usage: hops.py addr before_block nhops"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bc
from trace import T
a, before, n = sys.argv[1].lower(), int(sys.argv[2]), int(sys.argv[3])
for i in range(n):
    hit = None
    for bn, ts, t in bc.txs_desc(before - 60000, before - 1):
        if t[2] == a and int(t[3]) > 0: hit = T(bn, ts, t); break
    print(i + 1, a, "<-", hit, flush=True)
    if not hit or hit["nonce"] > 50: break
    a, before = hit["from"], hit["bn"]
