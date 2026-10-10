import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from load_all import *
from chain import rpc
pools, head = load_all(); cw = annotate(pools)
p = next(q for q in pools if q["pid"].startswith("0x93e998f1"))
o = next(x for x in p["sw"] if (x["from"] or "").startswith("0x93b07902"))
c = next(x for x in p["sw"] if x["cls"] == "crowd" and x["a0"] < 0)
a = rpc("eth_getTransactionByHash", [o["tx"]])["input"][2:]; b = rpc("eth_getTransactionByHash", [c["tx"]])["input"][2:]
print("outsider bn", o["bn"] - p["b0"], "crowd first buy bn", c["bn"] - p["b0"], "sel", a[:8], b[:8])
diff = [i // 64 for i in range(8, len(a), 64) if a[i:i+64] != b[i:i+64]]
print("32-byte words that differ:", diff, "of", (len(a) - 8) // 64)
for w in diff[:8]: print(w, a[8 + 64*w: 8 + 64*(w+1)], b[8 + 64*w: 8 + 64*(w+1)])
