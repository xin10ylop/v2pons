"""reaction lags (blocks from a non-operator buy > 2e-5 ETH to the 100% pull) in the v5.0 census -> v5/lags.json"""
import pickle, json, os
HERE = os.path.dirname(os.path.abspath(__file__)); EXP = os.path.dirname(HERE)
P = pickle.load(open(os.path.join(EXP, "pools.pkl"), "rb"))
PM_POS = "0x58daec3116aae6d93017baaea7749052e8a04fa7"; UR = "8876789976decbfcbbbe364623c63652db8c0904"
fam = [p for p in P.values() if p.get("to") == PM_POS and p.get("inlen") == 1444 and p.get("fee") == 10000 and p.get("ts") == 200 and round(p.get("value") or 0, 3) == 5.0 and "sw" in p]
ev = []
for p in fam:
    b0 = p["b0"]; pull = next((m[0] - b0 for m in p["mls"] if m[4] < 0), None)
    nb = [s for s in p["sw"] if s[6] != UR and s[2] < 0 and -s[2] > 2e13]
    if nb and (pull is None or pull > nb[0][0] - b0):
        ev.append({"pid": p["pid"], "off": nb[0][0] - b0, "eth": -nb[0][2] / 1e18, "via": nb[0][6], "lag": (pull - (nb[0][0] - b0)) if pull is not None else None})
lags = sorted(e["lag"] for e in ev if e["lag"] is not None and e["lag"] <= 30)
json.dump({"n_events": len(ev), "n_pulled_within_30": len(lags), "lags": lags, "events": ev}, open(os.path.join(HERE, "lags.json"), "w"), indent=1)
print(len(ev), len(lags), lags)
