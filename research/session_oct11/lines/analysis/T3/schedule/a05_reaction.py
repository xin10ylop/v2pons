"""The operator's reaction to a non-dust outside buy before the bot's first buy, 3.0/5.0 pools of this window: lag from that buy to the
first pull, and whether the bot still bought. Buyer = recipient of the PM's token transfer (or the UR's forward)."""
import pickle, json, collections
D = pickle.load(open("cache/data.pkl", "rb")); pools = D["pools"]
SENT = "0xe71a69f434a719cd5afa411568b69716aab3b84a"; UR = "0x8876789976decbfcbbbe364623c63652db8c0904"; PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
rows = []
for p in pools:
    if p["line"] not in ("3.0", "5.0"): continue
    T = p["T"] if p["T"] is not None else 10 ** 9
    pulls = [m["off"] for m in p["ml"] if m["dL"] < 0]
    for s in p["sw"]:
        if not s["buy"] or s["bot"] or s["off"] > T or s["q"] < 0.00003: continue
        rc = [r for r in p["rcpt"].get(s["tx"], []) if r[0] in (PM, UR)]
        who = next((r[1] for r in rc if r[1] not in (UR, PM)), "?")
        if who == SENT: continue
        nxt = [x for x in pulls if x >= s["off"]]
        rows.append((p["line"], p["L"], s["off"], round(s["q"], 5), who[:10], p["T"], (nxt[0] - s["off"]) if nxt else None))
for r in rows: print(r)
lags = sorted(r[6] for r in rows if r[6] is not None)
print("pre-T outside buys:", len(rows), "pulled after (lag hist):", sorted(collections.Counter(lags).items()), "not pulled:", sum(1 for r in rows if r[6] is None),
      "bot still bought:", sum(1 for r in rows if r[5] is not None))
