"""Log activity of a few wallets: any log with the wallet in topic1, topic2 or topic3 (ERC20 Transfer/Approval, etc.), 30000-block windows
from HI down to LO. Usage: act2.py w1,w2 lo hi out.jsonl"""
import sys, json, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import rpc
D = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/origins/"
ws = [w.lower() for w in sys.argv[1].split(",")]; LO, HI = int(sys.argv[2]), int(sys.argv[3]); out = open(D + sys.argv[4], "a")
tops = ["0x" + "0" * 24 + w[2:] for w in ws]
hi = HI
while hi >= LO:
    lo = max(LO, hi - 29999); res = []
    for pos in (1, 2, 3):
        q = [None] * pos + [tops]
        for k in range(10):
            try: res += rpc("eth_getLogs", [{"fromBlock": hex(lo), "toBlock": hex(hi), "topics": q}]); break
            except Exception as e: print("retry", lo, str(e)[:100], flush=True); time.sleep(3 + 3 * k)
        time.sleep(0.3)
    hits = []
    for l in res:
        for i, t in enumerate(l["topics"][1:], 1):
            if t in tops: hits.append([int(l["blockNumber"], 16), l["transactionHash"], l["address"], l["topics"][0][:10], i, "0x" + t[26:]])
    hits = sorted({tuple(h) for h in hits})
    out.write(json.dumps({"lo": lo, "hi": hi, "hits": hits}) + "\n"); out.flush()
    if hits: print(lo, hi, len(hits), "first", hits[0][0], "last", hits[-1][0], flush=True)
    hi = lo - 1
print("done", flush=True)
