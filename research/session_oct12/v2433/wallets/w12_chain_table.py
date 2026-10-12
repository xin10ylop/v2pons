"""Reads w06_chain.json: per launch wallet, who funded it (the previous launch wallet's sweep, the bot's buyer wallets, others), its own
transactions (7422a284 to the bot router, launch, approve, pull, sweep) and where its sweep went. Writes w12_chain_rows.json."""
from common import *
import collections
d = json.load(open(J("w06_chain.json")))
L = d["launches"]; ev = d["events"]
idx = {x["w"]: i for i, x in enumerate(L)}
by_to = collections.defaultdict(list); by_from = collections.defaultdict(list)
for e in ev:
    by_to[e["to"]].append(e); by_from[e["f"]].append(e)
rows = []
kinds = collections.Counter(); buyers = collections.Counter(); others = collections.Counter(); sweep_to = collections.Counter()
for i, x in enumerate(L):
    w = x["w"]
    fin = [e for e in by_to[w] if int(e["v"]) > 0 and e["b"] <= x["L"]]
    prev = L[i - 1]["w"] if i > 0 else None
    f_prev = [e for e in fin if e["f"] == prev]; f_launch = [e for e in fin if e["f"] in idx and e["f"] != prev]
    f_buy = [e for e in fin if e["f"] not in idx and e["nonce"] > 30000]; f_oth = [e for e in fin if e["f"] not in idx and e["nonce"] <= 30000]
    for e in f_buy: buyers[e["f"]] += 1
    for e in f_oth: others[(e["f"], e["nonce"])] += 1
    own = sorted(by_from[w], key=lambda e: e["nonce"])
    sw = [e for e in own if e["sel"] == "0x" and int(e["v"]) > 0 and x.get("P") and e["b"] >= x["P"]]
    nxt = L[i + 1]["w"] if i + 1 < len(L) else None
    tgt = sw[0]["to"] if sw else None
    kind = "next launch wallet" if tgt and tgt == nxt else "another launch wallet" if tgt in idx else ("none seen" if not tgt else "outside")
    kinds[kind] += 1; sweep_to[tgt if kind == "outside" else kind] += 1
    r = {"i": i, "L": x["L"], "w": w, "P": x.get("P"), "pull_after": (x["P"] - x["L"]) if x.get("P") else None, "fee": x["fee"],
         "in_prev": sum(int(e["v"]) for e in f_prev) / 1e18, "in_prev_n": len(f_prev), "in_launchw_other": len(f_launch),
         "in_buyers": sum(int(e["v"]) for e in f_buy) / 1e18, "in_buyers_n": len(f_buy), "in_other": [(e["f"], e["nonce"], int(e["v"]) / 1e18) for e in f_oth],
         "fund_off": sorted({e["b"] - x["L"] for e in fin})[:1] + sorted({e["b"] - x["L"] for e in fin})[-1:],
         "own": [(e["nonce"], e["sel"], e["to"][:10], int(e["v"]) / 1e18, e["b"] - x["L"]) for e in own],
         "sweep_to": tgt, "sweep_eth": int(sw[0]["v"]) / 1e18 if sw else None, "sweep_kind": kind, "ts": None}
    rows.append(r)
json.dump(rows, open(J("w12_chain_rows.json"), "w"))
print("launches", len(rows), L[0]["L"], "..", L[-1]["L"])
print("funded by the previous launch wallet's sweep:", sum(1 for r in rows if r["in_prev_n"]), "| by other launch wallets:", sum(1 for r in rows if r["in_launchw_other"]),
      "| with buyer-wallet transfers:", sum(1 for r in rows if r["in_buyers_n"]), "| with other senders:", sum(1 for r in rows if r["in_other"]))
print("sweep after the pull goes to:", dict(kinds))
print("outside sweep targets:", {k: v for k, v in sweep_to.items() if k not in ("next launch wallet", "another launch wallet", "none seen")})
print("distinct buyer wallets funding launch wallets:", len(buyers), "transfers", sum(buyers.values()))
print("other senders:", others.most_common(10))
ip = [r["in_prev"] for r in rows if r["in_prev_n"]]; ib = [r["in_buyers"] for r in rows if r["in_buyers_n"]]; se = [r["sweep_eth"] for r in rows if r["sweep_eth"]]
print("ETH in from previous wallet p10/50/90", pct(ip, .1), pct(ip, .5), pct(ip, .9), "| from buyers", pct(ib, .1), pct(ib, .5), pct(ib, .9), "| sweep out", pct(se, .1), pct(se, .5), pct(se, .9))
print("own-tx shapes:", collections.Counter(tuple((o[0], o[1]) for o in r["own"]) for r in rows).most_common(5))
print("funding offset (first, last) before launch p50:", pct([r["fund_off"][0] for r in rows if r["fund_off"]], .5), pct([r["fund_off"][-1] for r in rows if r["fund_off"]], .5))
print("7422a284 value p10/50/90:", *(pct([o[3] for r in rows for o in r["own"] if o[1] == "0x7422a284"], q) for q in (.1, .5, .9)))
print("pull after launch p10/50/90 (blocks):", *(pct([r["pull_after"] for r in rows if r["pull_after"] is not None], q) for q in (.1, .5, .9)))
print("\nlast 12:")
for r in rows[-12:]:
    print(r["L"], r["w"][:10], "fee", r["fee"], "in prev", round(r["in_prev"], 4), "buyers", r["in_buyers_n"], round(r["in_buyers"], 4), "other", r["in_other"][:2], "pull+", r["pull_after"], "sweep", r["sweep_eth"] and round(r["sweep_eth"], 4), "->", (r["sweep_to"] or "")[:10], r["sweep_kind"])
