"""Every contract that ever emitted the launcher's Launched event topic 0x03f29fb2... (original, copies, any other deployment of the same code)."""
import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import *
TOP = "0x03f29fb2049a216108887bac46b54b1f8d8db31efb6e3cc67bb6a63f2441e84f"
L0 = "0x3194e32622c5d860a0572c74edda99dcfd8fc827"
head = int(rpc("eth_blockNumber", []), 16)
out = []
for a in range(18_000_000, head + 1, 2_000_000):
    b = min(head, a + 2_000_000 - 1)
    r = logs({"topics": [TOP]}, a, b)
    r = [x for x in r if x["address"].lower() != L0]
    out += r
    if r: print(a, b, len(r), collections.Counter(x["address"].lower() for x in r).most_common(3), flush=True)
json.dump(out, open("other_launcher_logs.json", "w"))
c = collections.Counter(x["address"].lower() for x in out)
print("non-original emitters:", len(c), "events:", len(out))
