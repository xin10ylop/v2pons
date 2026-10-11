"""Check the router-call layout on cached bot transactions (input_head = selector + 6 words): w1 = tx.from on buys / the router on sells,
w2 = the swap's input amount (ETH wei on buys, token units on sells), w3 = 0 (min out). 20 random ones printed, then every cached one counted."""
import pickle, random
from sim import *
rows = {r["pool"]: r for r in jl(os.path.join(V, "c1_rows.jsonl"))}
E = pickle.load(open(os.path.join(V, "ev.pkl"), "rb")); T = json.load(open(os.path.join(V, "c1_txs.json")))
from evload import norm
recs = []
for pid, r in rows.items():
    sw, _, _ = norm(r, E[pid])
    for s in sw:
        t = T.get(s["tx"])
        if t and t["to"] == BOT: recs.append((pid, s, t))
def words(t):
    h = t.get("input_head") or t.get("input"); d = h[10:]
    return [int(d[64*i:64*(i+1)], 16) for i in range(min(6, len(d)//64))]
def check(pid, s, t):
    w = words(t)
    return {"w1_from": w[1] == int(t["from"], 16), "w1_router": w[1] == int(BOT, 16), "w2_amount": w[2] == (s["q"] if s["buy"] else s["t"]), "w3_zero": w[3] == 0,
            "w0_80": w[0] == 0x80, "w4_1": w[4] == 1, "value0": t["value_wei"] == 0, "gas1M": t["gas"] == 1_000_000, "prio_eq_gp": t.get("max_prio") == t.get("gas_price"), "clen484": t["calldata_len"] == 484}
random.seed(11)
print("20 random cached router txs:")
for pid, s, t in random.sample(recs, 20):
    c = check(pid, s, t); w = words(t)
    print(f"  {'B' if s['buy'] else 'S'} {t['hash'][:12]} quote {s['q']/1e18:.6f} w2 {w[2]} {'ETH' if s['buy'] else 'tok'} amt {s['q'] if s['buy'] else s['t']} | " + " ".join(k for k, v in c.items() if not v) + (" all ok" if all(c.values()) else ""))
agg = C.Counter()
for pid, s, t in recs:
    c = check(pid, s, t); side = "B" if s["buy"] else "S"
    for k, v in c.items(): agg[(side, k, v)] += 1
nb = sum(1 for _, s, _ in recs if s["buy"]); ns = len(recs) - nb
print(f"\nall cached router txs: {len(recs)} ({nb} buys, {ns} sells; ETH and WETH pools)")
for side, n in (("B", nb), ("S", ns)):
    print(side, {k: f"{agg[(side, k, True)]}/{n}" for k in ("w1_from", "w1_router", "w2_amount", "w3_zero", "w0_80", "w4_1", "value0", "gas1M", "prio_eq_gp", "clen484")})
bad = [(pid, s, t) for pid, s, t in recs if s["buy"] and not check(pid, s, t)["w2_amount"]]
for pid, s, t in bad[:12]:
    w = words(t); print("  w2 != swap ETH:", t["hash"][:14], "w2", w[2], "swap q", s["q"], "ratio", round(s["q"] / w[2], 6) if w[2] else None, rows[pid]["quote"])
