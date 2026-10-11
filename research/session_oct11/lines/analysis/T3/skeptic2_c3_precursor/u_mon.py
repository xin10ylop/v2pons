"""Live monitor (state check the chain's history cannot give): the public node keeps state for only ~6,000 recent blocks (~10 min), so for
every new 3.0 launch this polls until the bot's first buy T, then reads T's buyer wallet's ETH balance and nonce at every block T-15..T
(eth_getBalance / eth_getTransactionCount at that block). An internal ETH transfer to the buyer (funding with no log and no calldata
mention) or any own transaction would show as a change ahead of T. Also the balance at L-1 and L+3 where still available.
-> u_mon.jsonl (one row per pool). Usage: python3 u_mon.py MINUTES"""
import sys, json, time, os
from lib import *
os.chdir(HERE)
minutes = float(sys.argv[1]) if len(sys.argv) > 1 else 75
t_end = time.time() + minutes * 60
kv_tx = KV("tx_mon"); out = open("u_mon.jsonl", "a")
done = set()
if os.path.exists("u_mon.jsonl"):
    for l in open("u_mon.jsonl"):
        try: done.add(json.loads(l)["pid"])
        except Exception: pass
head = int(rpc("eth_blockNumber", []), 16); scanned = head - 3000; track = {}
def tx(h):
    if h not in kv_tx.d:
        t = rpc("eth_getTransactionByHash", [h]); kv_tx.put(h, {k: t.get(k) for k in SLIM_TX}); kv_tx.flush()
    return kv_tx.d[h]
while time.time() < t_end:
    try:
        head = int(rpc("eth_blockNumber", []), 16)
        for l in logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, scanned + 1, head):
            if not (W(l["data"], 2) == 0 and W(l["data"], 3) == SQRT30 and W(l["data"], 0) == 10000 and sgn(W(l["data"], 1)) == 200): continue
            t = tx(l["transactionHash"])
            if (t.get("to") or "").lower() != POSM or int(t["value"], 16) != 3 * 10 ** 18 or (len(t["input"]) - 2) // 2 != 1444: continue
            pid = l["topics"][1].lower()
            if pid not in done: track[pid] = {"pid": pid, "L": int(l["blockNumber"], 16), "token": "0x" + l["topics"][3][-40:]}
        scanned = head
        for pid, p in list(track.items()):
            sw = logs({"address": PM, "topics": [T_SWAP, pid]}, p["L"], head)
            Tlog = None
            for s in sorted(sw, key=lambda s: (int(s["blockNumber"], 16), int(s["logIndex"], 16))):
                if sgn(W(s["data"], 0)) >= 0: continue
                t = tx(s["transactionHash"])
                if (t.get("to") or "").lower() == BOT and t["input"][2:10] == "c1120e3d": Tlog = (s, t); break
            if Tlog is None:
                if head - p["L"] > 900: p["why"] = "no bot buy by L+900"; out.write(json.dumps(p) + "\n"); out.flush(); done.add(pid); del track[pid]
                continue
            s, t = Tlog; Tbn = int(s["blockNumber"], 16); buyer = t["from"].lower()
            if head - Tbn > 5500: p["why"] = "state gone"; out.write(json.dumps(p) + "\n"); out.flush(); done.add(pid); del track[pid]; continue
            blocks = list(range(Tbn - 15, Tbn + 1)) + [p["L"] - 1, p["L"] + 3]
            res = batch([("eth_getBalance", [buyer, hex(b)]) for b in blocks] + [("eth_getTransactionCount", [buyer, hex(b)]) for b in blocks], 20)
            bal = {b: (int(x, 16) if x else None) for b, x in zip(blocks, res[:len(blocks)])}
            non = {b: (int(x, 16) if x else None) for b, x in zip(blocks, res[len(blocks):])}
            p.update(T=Tbn - p["L"], Tbn=Tbn, Tti=int(s["transactionIndex"], 16), buyer=buyer, Ttx=s["transactionHash"], buy_q=-sgn(W(s["data"], 0)),
                     tx_nonce=int(t["nonce"], 16), deadline=int(t["input"][10 + 64 * 6: 10 + 64 * 7], 16), gasPrice=t.get("gasPrice"),
                     maxPrio=t.get("maxPriorityFeePerGas"), maxFee=t.get("maxFeePerGas"), head_at_read=head,
                     bal={str(b - Tbn): v for b, v in bal.items()}, nonce={str(b - Tbn): v for b, v in non.items()})
            out.write(json.dumps(p) + "\n"); out.flush(); done.add(pid); del track[pid]
            print(utc(time.time()), "pool", pid[:12], "T", p["T"], "buyer", buyer[:10], "bal T-15..T", sorted(set(v for k, v in p["bal"].items() if int(k) >= -15 and int(k) <= 0)),
                  "nonce", sorted(set(v for k, v in p["nonce"].items() if -15 <= int(k) <= 0)), flush=True)
    except Exception as e:
        print("error", str(e)[:150], flush=True)
    time.sleep(60)
print("monitor done; pools written", len(done), flush=True)
