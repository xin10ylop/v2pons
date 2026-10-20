"""Fetch 3 bot-router buys and 2 bot-router sells in full from the chain (eth_getTransactionByHash) -> router_full.json; print the words."""
import pickle, random
from sim import *
import rpc
rows = {r["pool"]: r for r in jl(os.path.join(V, "c1_rows.jsonl")) if r["quote"] == "ETH"}
E = pickle.load(open(os.path.join(V, "ev.pkl"), "rb")); T = json.load(open(os.path.join(V, "c1_txs.json")))
buys, sells = [], []
for pid in sorted(rows):
    P = Pool(rows[pid], E[pid])
    for x in P.sw:
        t = T.get(x[8])
        if t and t["to"] == BOT: (buys if x[3] else sells).append((pid, x))
random.seed(7)
pick = random.sample(buys, 3) + random.sample(sells, 2)
out = []
for pid, x in pick:
    t = rpc.call("eth_getTransactionByHash", [x[8]])
    out.append({"pool": pid, "token": rows[pid]["token"], "buy": x[3], "q_wei": x[4], "t": x[5], "bn": x[0], "tx": t})
json.dump(out, open(os.path.join(V, "router_full.json"), "w"), indent=1)
for o in out:
    t = o["tx"]; d = t["input"][10:]
    print(f"\n{'BUY ' if o['buy'] else 'SELL'} pool {o['pool'][:12]} token {o['token']} swap quote {o['q_wei']} token amt {o['t']} block {o['bn']} from {t['from']} value {int(t['value'],16)} gas {int(t['gas'],16)} gasPrice {int(t['gasPrice'],16)} prio {t.get('maxPriorityFeePerGas')} len {(len(t['input'])-2)//2}")
    for i in range(len(d) // 64):
        w = d[64*i:64*(i+1)]; v = int(w, 16)
        tag = []
        if v == o["q_wei"]: tag.append("= swap ETH")
        if v == o["t"]: tag.append("= swap token amount")
        if w[24:] == o["token"][2:]: tag.append("= TOKEN")
        if w[24:] == t["from"][2:]: tag.append("= tx.from")
        print(f"  w{i:2d} {w} {tag if tag else ''}")
print(rpc.STATS)
