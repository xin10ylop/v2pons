"""Earliest token activity of each crowd-B (and crowd-A) wallet: ERC20 Transfer logs with topic2 (to) = wallet, 30k-block windows,
10 windows per batched request, walking backward from START until STOPGAP blocks pass with no hit for either crowd. Output firstseen.json"""
import sys, json, time, urllib.request
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import post, keccak, rpc
D = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/"
b = json.load(open(D + "ops/b_list.json")); CB = sorted(b["B"]); CA = sorted(b["A"])
TT = "0x" + keccak(text="Transfer(address,address,uint256)").hex()
W = CB + CA; TW = ["0x" + "0" * 24 + w[2:] for w in W]
START = int(sys.argv[1]); STOPGAP = int(sys.argv[2]); FLOOR = int(sys.argv[3]) if len(sys.argv) > 3 else 19300000
first = {}; per_window = []; last_hit = START; hi = START
out = D + "origins/firstseen.json"
while hi > FLOOR:
    wins = [(max(FLOOR, hi - 30000 * (k + 1) + 1), hi - 30000 * k) for k in range(10)]
    body = [{"jsonrpc": "2.0", "id": j, "method": "eth_getLogs", "params": [{"fromBlock": hex(a), "toBlock": hex(c), "topics": [TT, None, TW]}]} for j, (a, c) in enumerate(wins)]
    for k in range(12):
        try:
            r = post(body)
            if isinstance(r, list) and all("result" in x for x in r): break
            print("partial/err", str(r)[:200], flush=True)
        except Exception as e: print("err", e, flush=True)
        time.sleep(5 + 5 * k)
    else: raise SystemExit("logs failed at %d" % hi)
    r = sorted(r, key=lambda x: x["id"])
    for (a, c), x in zip(wins, r):
        nb = collections_b = 0; na = 0
        for l in x["result"]:
            w = "0x" + l["topics"][2][-40:]; bn = int(l["blockNumber"], 16)
            if w not in first or bn < first[w]: first[w] = bn
            if w in b["B"]: nb += 1
            else: na += 1
        per_window.append((a, c, nb, na))
        if nb or na: last_hit = a
    print(time.strftime("%H:%M:%S"), "down to", wins[-1][0], "hits B/A in batch", sum(p[2] for p in per_window[-10:]), sum(p[3] for p in per_window[-10:]),
          "wallets seen", len(first), "last hit", last_hit, flush=True)
    json.dump({"first": first, "windows": per_window}, open(out, "w"))
    hi = wins[-1][0] - 1
    if last_hit - hi > STOPGAP: break
    time.sleep(1.0)
print("done; earliest per wallet:")
for w in sorted(first, key=lambda w: first[w]): print(w, "B" if w in b["B"] else "A", first[w])
