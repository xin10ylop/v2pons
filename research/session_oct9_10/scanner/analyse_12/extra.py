"""extras: (1) how widespread the family-3/4 early buyers are across the census; (2) family 3 capacity at the liquidity-add state
(the Initialize has no liquidity; the 0x1e7634e5 buy comes right after the add); (3) a front variant keyed on family 3's add"""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from px import *  # noqa
P = load_pools(); T = load_txs(); M = load_blocks_meta(); F = load_families()
out = {}
# (1) chain-wide reach of the early buyers (first-8-swap txs only)
who = {"to:0x563fee5015943ec183250e63e2b723c49d3eaf1b": lambda t: t["to"] == "0x563fee5015943ec183250e63e2b723c49d3eaf1b",
       "to:0x95731eecdec385854b30cf2e88c350352b70ae2d": lambda t: t["to"] == "0x95731eecdec385854b30cf2e88c350352b70ae2d",
       "from:0xa9acc7fd (UR)": lambda t: t["from"].startswith("0xa9acc7fd"),
       "to:0x1e7634e5a89556640d83ad15075996ab2ab2a609": lambda t: t["to"] == "0x1e7634e5a89556640d83ad15075996ab2ab2a609",
       "from:0xe71a69f4 dust": lambda t: t["from"] == DUST}
for k, f in who.items():
    pools = set(); fams = collections.Counter(); vals = []
    for t in T.values():
        if "swap" not in (t.get("kind") or []) or not f(t): continue
        for pid, kind, rank in t["refs"]:
            if kind == "swap" and pid not in pools:
                pools.add(pid); fams[P[pid]["known"]] += 1
        vals.append(t["value_eth"])
    out[k] = {"pools": len(pools), "known": fams.most_common(), "tx_value_p10_50_90": q(vals, nd=8)}
# (2)+(3) family 3 at the add state
K3 = "0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|3000|60|true"
E = load_events(set(F[K3]["pids"]))
rows = []
for pid in F[K3]["pids"]:
    p = P[pid]; pl = Pool(p, E[pid], T, M); add = E[pid]["adds"][0]
    s0 = float(p["sqrt_p0"]); L = pl.L_at(s0, add["bn"])
    b = pl.buys(); sn = [x for x in b if x["to"] == "0x1e7634e5a89556640d83ad15075996ab2ab2a609"]
    r = {"pid": pid, "add_rel": add["bn"] - pl.b0, "add_ti": add["ti"], "L_add": L}
    if sn:
        x = sn[0]; r.update(sniper_rel_add=x["bn"] - add["bn"], sniper_ti=x["ti"], sniper_eth=x["eth"] / 1e18,
                            sniper_minout_word2=word(x["input"], 2) if x["input"] and len(x["input"]) >= 10 + 64 * 3 and x["sel"] == "02d32002" else None)
        q0 = v4math.buy_out_int(int(s0), L, x["eth"], 3000)
        r["cap_assumed_0.99"] = room(s0, L, x["eth"], 3000, int(q0 * 0.99))
    # the earliest we could land after the add: add + 1 (end of block); sell at add + 5 (nothing real comes behind)
    Bq = add["bn"] + 1
    r["front_add+1_sell+5"] = pl.trade(Bq, Bq + 4)
    rows.append(r)
out["family3"] = rows
out["family3_front_from_add"] = summarize([r["front_add+1_sell+5"] for r in rows])
print(json.dumps(out, indent=1, default=str))
json.dump(out, open(os.path.join(HERE, "extra.json"), "w"), indent=1, default=str)
