import sys, threading, json, time
sys.setswitchinterval(float(sys.argv[1]))
raw = bytes(200)
SENT = []
def body(r): return json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_sendRawTransaction", "params": ["0x" + r.hex()]})
def reply_kind(r): return "ok"
def post(i, b):
    SENT.append((i, bytes.fromhex(json.loads(b)["params"][0][2:])))
    return {"result": "0x"}
def deliver():
    for k in range(4):
        rep = post(1, body(raw))
        if reply_kind(rep) == "ok": break
lost = 0; N = int(sys.argv[2])
for n in range(N):
    SENT.clear()
    threading.Thread(target=deliver, daemon=True).start()
    if len(SENT) != 1: lost += 1
    while len(SENT) != 1: time.sleep(0)
print("switch", sys.argv[1], "lost", lost, "of", N)
