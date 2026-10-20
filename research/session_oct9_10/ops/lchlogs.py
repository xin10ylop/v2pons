import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import *
L = "0x3194e32622c5d860a0572c74edda99dcfd8fc827"
head = int(rpc("eth_blockNumber", []), 16)
print("head", head)
# try a single big query first
out = []
step = 2_000_000
for a in range(0, head + 1, step):
    b = min(head, a + step - 1)
    try:
        r = logs({"address": L}, a, b)
    except Exception as e:
        print("err", a, b, e); continue
    out += r
    if r: print(a, b, len(r))
json.dump(out, open("launcher_logs.json", "w"))
print("total", len(out))
