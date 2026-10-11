# Operator C-1 (POSM ac9650d8, 2,276 bytes, fee 100/ts 1) after the census, to the head: every launch, its swaps/pulls to +3,000 (or head),
# the first buy through its router 0xd6d35b56 (c1), and the skeptic's ride (buy at the end of c1+1, sell at the head of c1+1+50) with the
# skeptic's exact replay (copied from skeptic_.../f2276_100/common_s.py replay()). Caches to report/work/c1/.
import sys, os, json, collections, statistics as st
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10"); sys.path.insert(0, "/home/user/v2pons/src")
from chain import rpc, batch, logs, PM, T_INIT, T_SWAP, T_ML, W, sgn
import v4math
D = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/report/work/c1"; os.makedirs(D, exist_ok=True)
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"; CROWD = "0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6"
Q96 = 1 << 96; STAKE = int(0.0058e18); GAS_ETH = 0.012 / 15 * 0.0058
START = 85_203_898
def cached(name, fn):
    p = os.path.join(D, name)
    if os.path.exists(p): return json.load(open(p))
    r = fn(); json.dump(r, open(p, "w")); return r
head = cached("head.json", lambda: int(rpc("eth_blockNumber", []), 16) - 10)
inits = cached("inits.json", lambda: logs({"address": PM, "topics": [T_INIT, None, "0x" + "0" * 64]}, START, head))
cand = []
for l in inits:
    d = l["data"]
    if W(d, 0) == 100 and sgn(W(d, 1)) == 1 and int(d[2 + 64 * 2 + 24: 2 + 64 * 3], 16) == 0:
        cand.append({"pid": l["topics"][1], "token": "0x" + l["topics"][3][-40:], "sp0": W(d, 3), "bn": int(l["blockNumber"], 16), "tx": l["transactionHash"]})
ltx = cached("ltx.json", lambda: batch([("eth_getTransactionByHash", [c["tx"]]) for c in cand]))
fresh = []
for c, t in zip(cand, ltx):
    if t and t["to"] == POSM and t["input"][:10] == "0xac9650d8" and (len(t["input"]) - 2) // 2 == 2276:
        c.update({"from": t["from"], "nonce": int(t["nonce"], 16), "value": int(t["value"], 16)}); fresh.append(c)
print("fee100/ts1 ETH inits", len(cand), "C-1 launches", len(fresh), "head", head)
def get_ev():
    out = {}
    for i in range(0, len(fresh), 20):
        grp = fresh[i:i + 20]; a = min(c["bn"] for c in grp); b = min(head, max(c["bn"] for c in grp) + 3000)
        for l in logs({"address": PM, "topics": [[T_SWAP, T_ML], [c["pid"] for c in grp]]}, a, b): out.setdefault(l["topics"][1], []).append(l)
    return out
ev = cached("logs.json", get_ev)
TXP = os.path.join(D, "txs.json"); TX = json.load(open(TXP)) if os.path.exists(TXP) else {}
pools = []
for c in fresh:
    sw, pu, ad = [], [], []
    for l in ev.get(c["pid"], []):
        bn = int(l["blockNumber"], 16)
        if bn > c["bn"] + 3000: continue
        d = l["data"]; li = int(l["logIndex"], 16)
        if l["topics"][0] == T_SWAP:
            a0 = sgn(W(d, 0)); a0 = a0 - (1 << 128) if a0 >= (1 << 127) else a0
            sw.append({"bn": bn, "li": li, "a0": a0, "sqrt_p": W(d, 2), "liq": W(d, 3), "fee": W(d, 5), "tx": l["transactionHash"], "buy": a0 < 0})
        else:
            dl = sgn(W(d, 2)); row = {"bn": bn, "li": li, "dl": dl, "tx": l["transactionHash"]}
            if dl < 0: pu.append(row)
            elif dl > 0: ad.append(row)
    sw.sort(key=lambda s: (s["bn"], s["li"])); pu.sort(key=lambda s: (s["bn"], s["li"])); ad.sort(key=lambda s: (s["bn"], s["li"]))
    L0 = sum(a["dl"] for a in ad if a["tx"] == c["tx"])
    pools.append({"pid": c["pid"], "b0": c["bn"], "sp0": c["sp0"], "L0": L0, "swaps": sw, "pulls": pu, "pull_bn": pu[0]["bn"] if pu else None, "launcher": c["from"], "window": min(head, c["bn"] + 3000) - c["bn"]})
# find c1: fetch buy txs in order, 10 at a time per pool, until one goes to the crowd router
for pl in pools:
    buys = [s for s in pl["swaps"] if s["buy"]]; pl["crowd1"] = None
    for i in range(0, min(len(buys), 60), 10):
        ch = [s["tx"] for s in buys[i:i + 10] if s["tx"] not in TX]
        if ch:
            for h, t in zip(ch, batch([("eth_getTransactionByHash", [h]) for h in ch])):
                if t: TX[h] = {"from": t["from"], "to": t["to"], "value": int(t["value"], 16), "sel": t["input"][2:10]}
        hit = next((s for s in buys[i:i + 10] if TX.get(s["tx"], {}).get("to") == CROWD), None)
        if hit: pl["crowd1"] = hit["bn"]; pl["crowd1_eth"] = -hit["a0"] / 1e18; break
    if pl["pulls"]:
        h = pl["pulls"][0]["tx"]
        if h not in TX:
            t = rpc("eth_getTransactionByHash", [h]); TX[h] = {"from": t["from"], "to": t["to"], "value": int(t["value"], 16), "sel": t["input"][2:10]}
json.dump(TX, open(TXP, "w"))
def replay(pl, B, S, stake=STAKE):
    if pl["pull_bn"] is not None and pl["pull_bn"] <= B: return None, "pulled_before_buy"
    prev = pl["sp0"]; L = pl["L0"]; s_cf = float(pl["sp0"]); bought = False; tokens = 0; feeb = 100
    for x in pl["swaps"]:
        if not bought and x["bn"] > B:
            fee = x["fee"]; tokens = v4math.buy_out(s_cf, L, stake * (1 - fee / 1e6)); s_cf = v4math.sqrt_after_buy(s_cf, L, stake * (1 - fee / 1e6)); bought = True; feeb = fee
        if bought and x["bn"] >= S: break
        if x["buy"]: s_cf = Q96 / (Q96 / s_cf + (Q96 / x["sqrt_p"] - Q96 / prev))
        else: s_cf = s_cf + (x["sqrt_p"] - prev)
        prev = x["sqrt_p"]; L = x["liq"]
    if not bought:
        tokens = v4math.buy_out(s_cf, L, stake * (1 - feeb / 1e6)); s_cf = v4math.sqrt_after_buy(s_cf, L, stake * (1 - feeb / 1e6))
    if pl["pull_bn"] is not None and pl["pull_bn"] <= S: return -1.0 - GAS_ETH * 1e18 / stake, "pulled"
    return v4math.sell_out(s_cf, L, tokens * (1 - feeb / 1e6)) / stake - 1 - GAS_ETH * 1e18 / stake, "sold"
rows = []
for pl in pools:
    r = {"pid": pl["pid"], "b0": pl["b0"], "crowd1_off": (pl["crowd1"] - pl["b0"]) if pl["crowd1"] else None, "crowd1_eth": pl.get("crowd1_eth"),
         "pull_off": (pl["pull_bn"] - pl["b0"]) if pl["pull_bn"] else None, "pull_by": (TX[pl["pulls"][0]["tx"]]["to"], TX[pl["pulls"][0]["tx"]]["sel"], TX[pl["pulls"][0]["tx"]]["from"] == pl["launcher"]) if pl["pulls"] else None,
         "n_swaps": len(pl["swaps"]), "window": pl["window"]}
    if pl["crowd1"] and pl["crowd1"] + 51 <= head:
        r["ride"], r["why"] = replay(pl, pl["crowd1"] + 1, pl["crowd1"] + 51)
    rows.append(r)
v = [r["ride"] for r in rows if r.get("ride") is not None]
summ = {"head": head, "launches": len(rows), "with_crowd_buy": sum(1 for r in rows if r["crowd1_off"] is not None),
        "crowd1_off_p10_50_90": [sorted(r["crowd1_off"] for r in rows if r["crowd1_off"] is not None)[int(q * (sum(1 for r in rows if r["crowd1_off"] is not None) - 1))] for q in (0.1, 0.5, 0.9)] if any(r["crowd1_off"] for r in rows) else None,
        "pulled": sum(1 for r in rows if r["pull_off"] is not None), "pull_by": collections.Counter(str(r["pull_by"]) for r in rows if r["pull_by"]).most_common(3),
        "ride_n": len(v), "ride_mean": round(st.mean(v), 4) if v else None, "ride_median": round(st.median(v), 4) if v else None,
        "ride_win": round(sum(1 for x in v if x > 0) / len(v), 3) if v else None, "ride_pulled": sum(1 for r in rows if r.get("why") == "pulled"),
        "first_b0": min(r["b0"] for r in rows), "last_b0": max(r["b0"] for r in rows)}
json.dump({"summary": summ, "rows": rows}, open(os.path.join(D, "c1_fresh.json"), "w"), indent=1)
print(json.dumps(summ, indent=1))
for r in rows: print(r["b0"], r["crowd1_off"], r["crowd1_eth"], r["pull_off"], r.get("ride") and round(r["ride"], 4), r.get("why"), r["n_swaps"])
