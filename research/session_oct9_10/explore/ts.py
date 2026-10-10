import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chain import batch
bs = list(range(82878144, 84238620 + 1, 68000)) + [84238619]
r = batch([("eth_getBlockByNumber", [hex(b), False]) for b in bs])
out = [(b, int(x["timestamp"], 16)) for b, x in zip(bs, r) if x]
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "blockts.json"), "w"))
import time
for b, t in out: print(b, t, time.strftime("%m-%d %H:%M:%S", time.gmtime(t)))
