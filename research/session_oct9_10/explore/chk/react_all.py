"""Outsider-buy reaction in the three PM1444 families: pulls within 15 blocks after an outsider's first buy in a pool (outsiders other than
the launch dust trio), against the base rate; the lag distribution; any outsider >= 0.0002 ETH before the volume bot's first buy."""
import json, pickle, collections, numpy as np
R = json.load(open("../vbot/react/react.json"))
P = pickle.load(open("pools.pkl", "rb"))
TRIO = {"0xe71a69f434a719cd5afa411568b69716aab3b84a", "0xf6e55480c5939da146092301e388654879c6e6fb", "0xb002e8a04b2822d8f2890b022ddea3d25f9c3df8"}
def famof(p):
    if p.get("inlen") != 1444 or p.get("to") != "0x58daec3116aae6d93017baaea7749052e8a04fa7" or "sw" not in p: return None
    if p["fee"] == 2500 and p["ts"] == 50: return "v2.433"
    if p["fee"] == 10000 and round(p["value"], 3) == 5.0: return "v5.0"
    if p["fee"] == 10000 and round(p["value"], 3) == 3.0: return "v3.0"
pull = collections.defaultdict(dict)
for p in P.values():
    f = famof(p)
    if not f: continue
    neg = [m for m in p["mls"] if m[4] < 0]; pull[f][p["pid"]] = (neg[0][0] - p["b0"]) if neg else None
def base(f, r, w=15):
    alive = [q for q, v in pull[f].items() if v is None or v > r]
    return sum(1 for q in alive if pull[f][q] is not None and pull[f][q] <= r + w) / max(1, len(alive))
out = {}
for f in ("v2.433", "v3.0", "v5.0"):
    xs = [x for x in R if x["fam"] == f and x["src"] == "census" and x["wallet"] not in TRIO]
    first = {}
    for x in sorted(xs, key=lambda x: x["rel"]): first.setdefault((x["pid"], x["wallet"]), x)
    fx = list(first.values())
    hit = [x for x in fx if x["lag"] is not None and 0 <= x["lag"] <= 15]
    exp = sum(base(f, x["rel"]) for x in fx)
    lags = sorted(x["lag"] for x in hit)
    big = [x for x in fx if x["eth"] >= 2e-4]
    bighit = [x for x in big if x["lag"] is not None and 0 <= x["lag"] <= 15]
    early = [x for x in R if x["fam"] == f and x["eth"] >= 2e-4 and (x["next_bot_buy"] is not None) and x["rel"] < 12]
    out[f] = {"outsider_first_buys": len(fx), "pulled_within_15": len(hit), "expected_at_base_rate": round(exp, 1), "lags": lags,
              ">=0.0002": [len(big), len(bighit)], "lag_quantiles": np.percentile(lags, [10, 25, 50, 75, 90]).tolist() if lags else None,
              "outsider >=0.0002 before +12": len(early)}
    print(f, json.dumps(out[f]))
    for x in sorted(big, key=lambda x: x["rel"])[:0]: print("  ", x)
json.dump(out, open("chk/react_all.json", "w"), indent=1)
