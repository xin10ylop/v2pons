import json, urllib.request
H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
URLS = ["https://bsc-dataseed.bnbchain.org", "https://bsc-rpc.publicnode.com"]
def post(body):
    for U in URLS:
        try: return json.load(urllib.request.urlopen(urllib.request.Request(U, json.dumps(body).encode(), H), timeout=60))
        except Exception: pass
tok = "0x950e681819a68f595bb3db313346393d64f66bb5"; pair = "0x2de2620b04a0382390b18441cd033da7b798e57e"
hits = []
for a in range(127550480, 127550760, 20):
    r = post([{"jsonrpc": "2.0", "id": i, "method": "eth_getBlockByNumber", "params": [hex(a + i), True]} for i in range(20)])
    for x in r or []:
        b = x.get("result")
        if not b: continue
        for t in b["transactions"]:
            if (t.get("to") or "").lower() == tok or tok[2:] in t["input"].lower():
                hits.append((int(b["number"], 16), t["from"], t.get("to"), t["input"][:10], len(t["input"]) // 2 - 1, t["hash"]))
for h in hits: print(h)
print("tx touching the token in blocks 127550480..127550760:", len(hits))
