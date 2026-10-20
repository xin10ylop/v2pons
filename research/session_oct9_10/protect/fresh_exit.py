"""On the fresh-trigger launches (trigger wallet nonce <= 3) of the Oct 8 paper: the current trade (buy T+1, V0) against the delayed
entry (buy T+2, sell sent B+1 = V1) and against the minimum stake, at 0.1 and 1.0 ETH (exits_bt pricer, fast landing)."""
import sys, os, json, io, contextlib
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import exits_bt as E
F = E.F
PE = json.load(open(HERE + "/prot_eval.json"))
fresh = {t["pid"] for t in PE["triggers"] if t["nonce"] <= 3}
data = F.gather(); G = F.measure_gas(data)
rows = []
for p in data["orig"]:
    if p["pid"][:10] not in fresh: continue
    L = data["launch"][p["pid"]]
    ours = {t["hash"] for b in L["blocks"] for t in b["transactions"] if t["from"][2:].lower() == F.WALLET}
    c, why = E.prep(p, L, ours)
    if not c: print(p["pid"][:10], "not traded:", why); continue
    r = {"pid": p["pid"][:10], "pull_after_T": (c["pull"] - c["T"]) if c["pull"] else None}
    for stake in (0.1, 1.0):
        q1 = E.position(c, stake, 1); q2 = E.position(c, stake, 2)
        v0 = E.price(c, q1, E.plan_V0(c, q1, 1), G, dl=1, pull_at=c["pull"]); v1 = E.price(c, q2, E.plan_V1(c, q2, 1), G, dl=1, pull_at=c["pull"])
        r[stake] = {"V0_T+1": round(v0["ret"], 4), "V0_land": v0["lands"], "V1_T+2": round(v1["ret"], 4), "V1_land": v1["lands"]}
    rows.append(r); print(r)
for stake in (0.1, 1.0):
    a = sum(r[stake]["V0_T+1"] for r in rows) * stake; b = sum(r[stake]["V1_T+2"] for r in rows) * stake
    print(f"stake {stake}: {len(rows)} fresh launches, current exit {a:.5f} ETH, delayed entry {b:.5f} ETH, difference {a - b:.5f} ETH")
json.dump(rows, open(HERE + "/fresh_exit.json", "w"), indent=1, default=str)
