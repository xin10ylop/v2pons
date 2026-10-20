"""the 200 most recent ETH creates (complete 3,000-block window): their create transactions (EOA, entry point, value, metadata host), the
EOAs behind their buys (tx 'from' of every buy in the first 3,000 blocks), repeat EOAs across the 200, creator EOAs' own buys."""
import pickle, json, collections, re
from kreplay import *
P = pickle.load(open(os.path.join(DATA, "packed.pkl"), "rb")); CE = P["creates"]; TR = P["trades"]
head = json.load(open(os.path.join(DATA, "trades_head.json")))["head"]
S = sorted([c for c in CE if CE[c]["bn"] <= head - 3100], key=lambda c: -CE[c]["bn"])[:200]
cache = os.path.join(DATA, "k34_txs.json")
TX = json.load(open(cache)) if os.path.exists(cache) else {}
need = set(CE[c]["tx"] for c in S)
for c in S:
    for r in TR.get(c, []):
        if r[3] in "BS" and r[0] <= CE[c]["bn"] + 3000: need.add(r[2])
need = [h for h in need if h not in TX]; print("txs to fetch", len(need))
for i in range(0, len(need), 200):
    ch = need[i:i + 200]; R = batch([("eth_getTransactionByHash", [h]) for h in ch])
    for h, t in zip(ch, R):
        if t: TX[h] = {"from": t["from"].lower(), "to": (t["to"] or "").lower(), "value": int(t["value"], 16), "sel": t["input"][:10], "len": (len(t["input"]) - 2) // 2,
                       "hosts": sorted(set(re.findall(r"https?://([a-z0-9.-]+)", bytes.fromhex(t["input"][10:]).decode("latin-1")))) if h in {CE[c]["tx"] for c in S} else None}
    json.dump(TX, open(cache, "w"))
print("fetched", STATS)
out = {"n": len(S), "from_day": day(CE[S[-1]]["bn"]), "to_day": day(CE[S[0]]["bn"])}
ct = [TX[CE[c]["tx"]] for c in S if CE[c]["tx"] in TX]
out["entry_point"] = collections.Counter(f"{t['to']}:{t['sel']}" for t in ct).most_common(5)
out["create_value_eth_median"] = sorted(t["value"] for t in ct)[len(ct) // 2] / 1e18
out["metadata_hosts"] = collections.Counter(h for t in ct for h in (t["hosts"] or []) if "x.com" not in h and "twitter" not in h).most_common(12)
out["distinct_creator_eoas"] = len({t["from"] for t in ct})
buyers = collections.defaultdict(set); n_b = 0; eth = 0; creator_buys = 0; creator_eth = 0; sells = 0
for c in S:
    cr = CE[c]; ceoa = TX.get(cr["tx"], {}).get("from")
    for r in TR.get(c, []):
        if r[0] > cr["bn"] + 3000 or r[3] not in "BS": continue
        t = TX.get(r[2]); 
        if not t: continue
        if r[3] == "B":
            n_b += 1; eth += r[5][0]; buyers[t["from"]].add(c)
            if t["from"] == ceoa: creator_buys += 1; creator_eth += r[5][0]
        else: sells += 1
out.update({"buys": n_b, "buy_eth": round(eth / 1e18, 3), "sells": sells, "buyer_eoas": len(buyers), "creator_eoa_buys": creator_buys, "creator_eoa_buy_eth": round(creator_eth / 1e18, 3),
            "eoas_in_ge2": sum(1 for v in buyers.values() if len(v) >= 2), "eoas_in_ge5": sum(1 for v in buyers.values() if len(v) >= 5), "eoas_in_ge20": sum(1 for v in buyers.values() if len(v) >= 20),
            "top_repeat_eoas": [(w, len(v)) for w, v in sorted(buyers.items(), key=lambda kv: -len(kv[1]))[:8]]})
out["curves_with_buy_by_ge20_eoa"] = len({c for w, v in buyers.items() if len(v) >= 20 for c in v})
print(json.dumps(out, indent=1))
json.dump(out, open(os.path.join(OUT, "k34_recent200.json"), "w"), indent=1)
