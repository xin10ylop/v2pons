"""careful rate probe on arb1: 40 rapid eth_blockNumber calls, measure achieved req/s and any 429; then confirm vbot router absent"""
import sys, json, time, urllib.request, urllib.error
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/scout")
from rpc1 import rpc, LOG
U = "https://arb1.arbitrum.io/rpc"; H = {"Content-Type":"application/json","User-Agent":"arb-scout/0.1 (read-only research)"}
body = json.dumps({"jsonrpc":"2.0","id":1,"method":"eth_blockNumber","params":[]}).encode()
codes = []; t0 = time.time()
for i in range(40):
    try:
        r = urllib.request.urlopen(urllib.request.Request(U, body, H), timeout=30); r.read(); codes.append(200)
    except urllib.error.HTTPError as e: codes.append(e.code)
    except Exception as e: codes.append(str(e)[:30])
dt = time.time()-t0
print("40 rapid calls in %.2fs = %.1f req/s; status codes:" % (dt, 40/dt), {c: codes.count(c) for c in set(codes)})
# vbot router code on Arbitrum
for a in ["0x1cbaf24d53fe930fce8eff149fa797d2611da149"]:
    c = rpc(U, "eth_getCode", [a, "latest"]).get("result","0x"); print("code at", a, "->", (len(c)-2)//2, "bytes")
print("requests", len(LOG))
