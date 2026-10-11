"""Stage 5: the buyer wallet of T. Its token activity around T from Transfer logs (topic from = wallet or to = wallet, any token, blocks
[T-6000, T+300]); the transactions of the nearest ones before and after T (to read their nonces: the previous tx proper has nonce n-1).
-> wallet.json"""
import pickle, json
from lib import *
D = pickle.load(open("parsed.pkl", "rb"))
P = sorted([p for p in D["pools"] if p["line"] == "3.0" and p["T"] is not None], key=lambda p: p["L"])
kv = KV("wlogs"); kv_tx = KV("tx")
out = []
for i, p in enumerate(P):
    w = "0x" + "0" * 24 + p["buyer"][2:]; k = p["pid"]
    if k not in kv.d:
        a, b = p["Tbn"] - 6000, p["Tbn"] + 300
        ls = logs({"topics": [T_TRANSFER, w]}, a, b) + logs({"topics": [T_TRANSFER, None, w]}, a, b)
        kv.put(k, [{"bn": int(l["blockNumber"], 16), "ti": int(l["transactionIndex"], 16), "tx": l["transactionHash"], "a": l["address"].lower(),
                    "dir": "out" if l["topics"][1].lower() == w else "in", "amt": int(l["data"], 16) if l["data"] != "0x" else 0} for l in ls]); kv.flush()
    ls = sorted(kv.d[k], key=lambda x: (x["bn"], x["ti"]))
    txs = sorted(set((x["bn"], x["ti"], x["tx"]) for x in ls))
    before = [t for t in txs if (t[0], t[1]) < (p["Tbn"], p["Tti"])]; after = [t for t in txs if (t[0], t[1]) > (p["Tbn"], p["Tti"])]
    near = [t[2] for t in before[-3:] + after[:2]]
    need = [h for h in near if h not in kv_tx.d]
    if need:
        for h, t in zip(need, batch([("eth_getTransactionByHash", [h]) for h in need])):
            if t: kv_tx.put(h, {kk: t.get(kk) for kk in SLIM_TX})
        kv_tx.flush()
    def desc(t):
        x = kv_tx.d.get(t[2]) or {}
        toks = sorted(set((y["a"], y["dir"]) for y in ls if y["tx"] == t[2]))
        return {"bn": t[0], "d": p["Tbn"] - t[0], "ti": t[1], "tx": t[2], "to": (x.get("to") or "").lower(), "sel": (x.get("input") or "")[2:10],
                "nonce": int(x["nonce"], 16) if x.get("nonce") else None, "from": (x.get("from") or "").lower(), "tokens": toks}
    out.append({"pid": p["pid"], "L": p["L"], "T": p["T"], "Tbn": p["Tbn"], "buyer": p["buyer"], "nonce": p["buyer_nonce"],
                "n_before": len(before), "n_after": len(after), "prev": [desc(t) for t in before[-3:]], "next": [desc(t) for t in after[:2]]})
    if i % 20 == 0: print(f"  {i + 1}/{len(P)}", flush=True)
json.dump(out, open("wallet.json", "w"))
print("done", len(out))
