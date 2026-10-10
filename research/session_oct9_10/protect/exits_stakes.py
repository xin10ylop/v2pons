"""exits_bt's pricer at the larger stakes: V0 (current exit) with the buy at T+1, V1 (sell sent at B+1) with the buy at T+1 and
T+2 (the delayed entry), fast landing; paper and with a reaction at our buy + 3 / + 4. Validates V0 against follow_stakes.json."""
import sys, os, json, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import exits_bt as E
F = E.F
data = F.gather(); G = F.measure_gas(data)
ctxs = []
for p in data["orig"]:
    L = data["launch"][p["pid"]]
    ours = {t["hash"] for b in L["blocks"] for t in b["transactions"] if t["from"][2:].lower() == F.WALLET}
    c, why = E.prep(p, L, ours)
    if c: ctxs.append(c)
ref = json.load(open(os.path.join(F.SCRATCH, "yday", "follow_stakes.json")))
R = {r["block"]: r for r in ref["launches"] if r["results"]}
out = {}
for stake in (0.0012, 0.03, 0.1, 0.3, 0.5, 1.0):
    worst = 0
    for c in ctxs:
        q = E.position(c, stake, 1); m = E.price(c, q, E.plan_V0(c, q, 1), G, dl=1, pull_at=c["pull"])
        if str(stake) in R[c["b0"]]["results"]:
            worst = max(worst, abs(m["ret"] - R[c["b0"]]["results"][str(stake)]["land1_fast"]["ret"]))
    for land, name, plan in ((1, "V0", E.plan_V0), (1, "V1", E.plan_V1), (2, "V0", E.plan_V0), (2, "V1", E.plan_V1)):
        rows = []
        for c in ctxs:
            q = E.position(c, stake, land); pl = plan(c, q, 1)
            rec = {"b0": c["b0"], "paper": E.price(c, q, pl, G, dl=1, pull_at=c["pull"])}
            for lag in (2, 3, 4):
                pa = q["B"] + lag if c["pull"] is None else min(c["pull"], q["B"] + lag)
                rec[lag] = E.price(c, q, pl, G, dl=1, pull_at=pa)
            rows.append(rec)
        k = f"{stake}|T+{land}|{name}"
        rr = [r["paper"]["ret"] for r in rows]
        out[k] = {"n": len(rows), "mean": st.mean(rr), "median": st.median(rr), "mean_ex_outlier": st.mean([r["paper"]["ret"] for r in rows if r["b0"] != E.OUTLIER]),
                  "lag3_mean": st.mean([r[3]["ret"] for r in rows]), "lag3_caught": sum(1 for r in rows if r[3]["exit"] == "pull_first"),
                  "lag4_caught": sum(1 for r in rows if r[4]["exit"] == "pull_first"), "lag2_caught": sum(1 for r in rows if r[2]["exit"] == "pull_first"),
                  "valid_V0_vs_follow_stakes": worst if (land == 1 and name == "V0") else None}
        o = out[k]
        print(f"{k:22s} n {o['n']} mean {100*o['mean']:+.2f}% median {100*o['median']:+.2f}% ex-outlier {100*o['mean_ex_outlier']:+.2f}% | caught at lag2/3/4: {o['lag2_caught']}/{o['lag3_caught']}/{o['lag4_caught']}"
              + (f" | V0 vs follow_stakes max diff {worst:.1e}" if o["valid_V0_vs_follow_stakes"] is not None else ""))
json.dump(out, open(os.path.join(HERE, "exits_stakes.json"), "w"), indent=1)
