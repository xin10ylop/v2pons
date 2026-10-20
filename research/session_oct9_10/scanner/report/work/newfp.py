# The new post-census fingerprint (fee 10000, ts 200, no hook, launch sqrtP 1908498483466244238266951834509291): launch txs, and for each pool
# its swaps and liquidity events in launch..launch+300, with the tx (to, selector, from, value, len) of the first swaps and the first pull.
import sys, json, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc, batch, logs, PM, T_INIT, T_SWAP, T_ML, W, sgn
OUT = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/report/work/newfp.json"
a = 85203898; head = int(rpc("eth_blockNumber", []), 16)
ZERO = "0x" + "0" * 64; SP = 1908498483466244238266951834509291
L = [l for l in logs({"address": PM, "topics": [T_INIT, None, ZERO]}, a, head)
     if W(l["data"], 0) == 10000 and sgn(W(l["data"], 1)) == 200 and W(l["data"], 3) == SP and l["data"][2+64*2+24:2+64*3] == "0"*40]
L = [l for l in L if int(l["blockNumber"], 16) + 300 <= head]
print("pools", len(L))
pools = []
for l in L:
    pools.append({"pid": l["topics"][1], "bn": int(l["blockNumber"], 16), "launch_tx": l["transactionHash"], "token": "0x" + l["topics"][3][-40:]})
# launch txs
lt = batch([("eth_getTransactionByHash", [p["launch_tx"]]) for p in pools])
for p, t in zip(pools, lt):
    p["launch"] = {"from": t["from"], "to": t["to"], "value_eth": int(t["value"], 16) / 1e18, "sel": t["input"][2:10], "len": (len(t["input"]) - 2) // 2, "nonce": int(t["nonce"], 16)}
# swaps and liquidity in launch..launch+300 (chunk by pool id topic, 20 pools per call)
for i in range(0, len(pools), 20):
    ch = pools[i:i+20]; lo = min(p["bn"] for p in ch); hi = max(p["bn"] for p in ch) + 300
    ids = [p["pid"] for p in ch]
    sw = logs({"address": PM, "topics": [T_SWAP, ids]}, lo, hi)
    ml = logs({"address": PM, "topics": [T_ML, ids]}, lo, hi)
    by = {p["pid"]: p for p in ch}
    for p in ch: p["swaps"] = []; p["mods"] = []
    for s in sw:
        p = by[s["topics"][1]]; bn = int(s["blockNumber"], 16)
        if bn > p["bn"] + 300: continue
        d = s["data"]; p["swaps"].append({"rel": bn - p["bn"], "a0": sgn(W(d, 0)), "a1": sgn(W(d, 1)), "tx": s["transactionHash"], "li": int(s["logIndex"], 16)})
    for m in ml:
        p = by[m["topics"][1]]; bn = int(m["blockNumber"], 16)
        if bn > p["bn"] + 300: continue
        d = m["data"]; p["mods"].append({"rel": bn - p["bn"], "dl": sgn(W(d, 2)), "tx": m["transactionHash"]})
# txs of the first 4 swaps and first pull
need = []
for p in pools:
    for s in p["swaps"][:4]: need.append(s["tx"])
    pl = [m for m in p["mods"] if m["dl"] < 0]
    if pl: need.append(pl[0]["tx"])
need = sorted(set(need))
tx = dict(zip(need, batch([("eth_getTransactionByHash", [h]) for h in need])))
def tinfo(h):
    t = tx[h]; return {"from": t["from"], "to": t["to"], "value_eth": int(t["value"], 16) / 1e18, "sel": t["input"][2:10], "len": (len(t["input"]) - 2) // 2, "nonce": int(t["nonce"], 16), "input": t["input"][:2+8+64*12]}
for p in pools:
    for s in p["swaps"][:4]: s.update(tinfo(s["tx"]))
    pl = [m for m in p["mods"] if m["dl"] < 0]
    p["pull"] = dict(pl[0], **tinfo(pl[0]["tx"])) if pl else None
json.dump(pools, open(OUT, "w"), indent=1)
lc = collections.Counter((p["launch"]["to"], p["launch"]["sel"], p["launch"]["len"], p["launch"]["value_eth"]) for p in pools)
print("launch shapes", lc.most_common(5))
print("launch nonces", collections.Counter(p["launch"]["nonce"] for p in pools).most_common(8))
print("distinct launch wallets", len({p["launch"]["from"] for p in pools}))
fb = collections.Counter(); fbto = collections.Counter(); rels = []; sizes = []; pullrel = []; pullto = collections.Counter(); margin = []
for p in pools:
    buys = [s for s in p["swaps"] if s["a0"] < 0]
    big = [s for s in buys if -s["a0"] >= 0.004e18]
    if big:
        b = big[0]; rels.append(b["rel"]); sizes.append(-b["a0"] / 1e18); fbto[(b.get("to"), b.get("sel"))] += 1
    if p["pull"]:
        pullrel.append(p["pull"]["rel"]); pullto[(p["pull"]["to"], p["pull"]["sel"], p["pull"]["from"] == p["launch"]["from"])] += 1
        if big: margin.append(p["pull"]["rel"] - big[0]["rel"])
print("first buy >= 0.004 ETH: pools", len(rels), "rel", sorted(collections.Counter(rels).items()))
print("sizes p10/50/90", sorted(sizes)[len(sizes)//10] if sizes else None, sorted(sizes)[len(sizes)//2] if sizes else None, sorted(sizes)[9*len(sizes)//10] if sizes else None)
print("first big buy to/sel", fbto.most_common(5))
print("pulled within 300", len(pullrel), "rel", sorted(collections.Counter(pullrel).items())[:20], "to/sel/by launcher", pullto.most_common(4))
print("pull minus first big buy", sorted(collections.Counter(margin).items()))
p = pools[0]; print(json.dumps({k: p[k] for k in ("pid", "bn", "launch", "token")}, indent=0)); 
for s in p["swaps"][:6]: print(s.get("rel"), s["a0"] / 1e18, s.get("to"), s.get("sel"), s.get("from"), s.get("len"))
print(p["pull"] and {k: p["pull"][k] for k in ("rel", "to", "sel", "from", "len")})
