"""s04: every transaction that touched a family token (from s03's token logs): the tx (from, to, selector, calldata length, value, priority,
nonce, input head) and its receipt (status, gas, the Portal's TokenBought/TokenSold for this token, and every log topic0 of the tx).
Batched over sentio/blockmachine, threads. -> data/tx_cache.jsonl (one row per tx hash)"""
import sys, os, json, threading, queue, time
sys.path.insert(0, os.path.dirname(__file__))
import rpc
from eth_utils import keccak
D = os.path.join(os.path.dirname(__file__), "..", "data")
PORTAL = "0xe2ce6ab80874fa9fa2aae65d277dd6b8e65c9de0"
TB = "0x" + keccak(text="TokenBought(uint256,address,address,uint256,uint256,uint256,uint256)").hex()
TS = "0x" + keccak(text="TokenSold(uint256,address,address,uint256,uint256,uint256,uint256)").hex()
hs = set()
for l in open(os.path.join(D, "toklogs_cache.jsonl")):
    j = json.loads(l)
    for x in j["logs"]: hs.add(x[3])
cache = os.path.join(D, "tx_cache.jsonl"); have = set()
if os.path.exists(cache):
    for l in open(cache):
        try: have.add(json.loads(l)["h"])
        except Exception: pass
need = sorted(hs - have)
print("txs", len(hs), "need", len(need), flush=True)
lk = threading.Lock(); fh = open(cache, "a"); done = [0]
def trim(h, t, rc):
    inp = t["input"]
    pl = []
    for x in rc["logs"]:
        if x["address"].lower() == PORTAL and x["topics"] and x["topics"][0] in (TB, TS):
            d = x["data"][2:]; w = [d[i:i + 64] for i in range(0, len(d), 64)]
            pl.append(["B" if x["topics"][0] == TB else "S", int(x["logIndex"], 16), "0x" + w[1][-40:], "0x" + w[2][-40:], int(w[3], 16), int(w[4], 16), int(w[5], 16), int(w[6], 16)])
    return {"h": h, "b": int(t["blockNumber"], 16), "ti": int(t["transactionIndex"], 16), "from": t["from"].lower(), "to": (t.get("to") or "").lower(),
            "sel": inp[2:10], "clen": (len(inp) - 2) // 2, "value": int(t["value"], 16), "type": int(t.get("type", "0x0"), 16),
            "gp": int(t.get("gasPrice", "0x0"), 16), "prio": int(t.get("maxPriorityFeePerGas", t.get("gasPrice", "0x0")), 16), "nonce": int(t["nonce"], 16),
            "gas": int(t["gas"], 16), "inhead": inp[:2 + 8 + 64 * 8], "status": int(rc["status"], 16), "gasUsed": int(rc["gasUsed"], 16),
            "egp": int(rc.get("effectiveGasPrice", "0x0"), 16), "portal": pl, "t0": sorted(set((x["address"].lower()[:12] + ":" + (x["topics"][0][:10] if x["topics"] else "-")) for x in rc["logs"]))}
Q = queue.Queue()
for i in range(0, len(need), 20): Q.put(need[i:i + 20])
def work(urls):
    while True:
        try: hs_ = Q.get_nowait()
        except queue.Empty: return
        try:
            txs = rpc.batch([("eth_getTransactionByHash", [h]) for h in hs_], urls=urls)
            rcs = rpc.batch([("eth_getTransactionReceipt", [h]) for h in hs_], urls=urls)
        except Exception as e:
            print("batch err", str(e)[:100], flush=True); time.sleep(3); Q.put(hs_); continue
        rows = [trim(h, t, rc) for h, t, rc in zip(hs_, txs, rcs) if t and rc]
        with lk:
            for r in rows: fh.write(json.dumps(r) + "\n")
            fh.flush(); done[0] += len(rows)
            if done[0] % 2000 < 20: print("done", done[0], flush=True)
th = [threading.Thread(target=work, args=([u],)) for u in rpc.HIST for _ in range(2)]
for t in th: t.start()
for t in th: t.join()
print("finished", done[0])
