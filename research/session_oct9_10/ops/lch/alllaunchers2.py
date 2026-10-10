"""Every contract other than the original that emitted the launcher's event topic, scanned newest-first in 250k-block steps (progress printed)."""
import sys, json, collections, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import *
TOP = "0x03f29fb2049a216108887bac46b54b1f8d8db31efb6e3cc67bb6a63f2441e84f"
L0 = "0x3194e32622c5d860a0572c74edda99dcfd8fc827"
head = int(rpc("eth_blockNumber", []), 16)
lo_all = int(sys.argv[1]) if len(sys.argv) > 1 else 19_300_000
out = []; step = 250_000
b = head
while b > lo_all:
    a = max(lo_all, b - step + 1); t0 = time.time()
    r = logs({"topics": [TOP]}, a, b)
    o = [x for x in r if x["address"].lower() != L0]
    out += o
    print(a, b, "all", len(r), "non-original", len(o), dict(collections.Counter(x["address"].lower()[:10] for x in o).most_common(3)), "%.0fs" % (time.time() - t0), flush=True)
    json.dump(out, open("other_launcher_logs.json", "w"))
    b = a - 1
c = collections.Counter(x["address"].lower() for x in out)
print("non-original emitters:", len(c), "events:", len(out))
