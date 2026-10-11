"""Stage 2: the transactions behind the 3.0 pools' events. Phase A (default): every ModifyLiquidity, every buy not sent through the bot's
router (Swap sender topic != 0x1cbaf24d: outside buys, the sentinel, ours, anything else) and the bot's first router buy per pool (its minOut
and wallet). Phase B (arg "sells"): the sells in pools with an outside buy, from that buy to +250 (to find the outside buyer's own sell),
needs cache/parsed.pkl. Seeds from ../precursor/cache/tx.jsonl (same public RPC answers). Cached in cache/tx.jsonl."""
import json, os, sys, pickle
from lib import *
kv_tx = KV("tx")
sib = os.path.join(HERE, "..", "precursor", "cache", "tx.jsonl")
if os.path.exists(sib):
    n0 = len(kv_tx.d)
    for l in open(sib):
        try: x = json.loads(l)
        except Exception: continue
        if x.get("k") and x["k"] not in kv_tx.d and isinstance(x.get("v"), dict) and x["v"].get("input") is not None:
            kv_tx.put(x["k"], {k: x["v"].get(k) for k in SLIM_TX})
    kv_tx.flush(); print("seeded from the precursor angle's cache:", len(kv_tx.d) - n0, flush=True)
need = []
if len(sys.argv) > 1 and sys.argv[1] == "sells":
    D = pickle.load(open(os.path.join(CACHE, "parsed.pkl"), "rb"))
    for p in D["pools"]:
        outs = [s["off"] for s in p["sw"] if s["buy"] and s["cls"] == "out"]
        if not outs: continue
        need += [s["tx"] for s in p["sw"] if not s["buy"] and outs[0] <= s["off"] <= outs[-1] + 250]
else:
    E = json.load(open(os.path.join(CACHE, "events.json")))
    for p in E["pools"]:
        nb = 0
        for e in p["ev"]:
            if e["kind"] == "ml": need.append(e["tx"]); continue
            buy = sgn(W(e["data"], 0)) < 0
            if not buy: continue
            if e["sender"] != BOT: need.append(e["tx"])
            elif nb < 1: need.append(e["tx"]); nb += 1
need = [h for h in dict.fromkeys(need) if h not in kv_tx.d]
print("txs to fetch:", len(need), flush=True)
for i in range(0, len(need), 400):
    ch = need[i:i + 400]; res = batch([("eth_getTransactionByHash", [h]) for h in ch], int(os.environ.get("BATCH", "20")))
    for h, t in zip(ch, res):
        if t: kv_tx.put(h, {k: t.get(k) for k in SLIM_TX})
    kv_tx.flush(); print(f"  txs {i + len(ch)}/{len(need)}", flush=True)
print("done", flush=True)
