"""Does the operator pull after a stranger buys? Per candidate family (core shape): pools with an outsider buy (census `outsider`,  vs control pools of the same family with no outsider buy. For each outsider
pool, t = its first outsider buy (all-fetched) / its last nf outsider buy; observed = first pull in (t, t + W]; expected = the share of
control pools still unpulled at t whose first pull falls in (t, t + W]. Also the census rates: outsider12_nf reaction vs baseline12.
Plus our own live trades (field `ours`): the pull delay after our buy."""
import math
from common import *
FAM = json.load(open(os.path.join(D, "fam_results.json")))
rows = load_rows()
def shape_of(r): return (r["quote"], r["fee"], r["tick_spacing"], r["hooks"] == "0x" + "0" * 40)
want = [k for k in FAM if FAM[k]["n"] >= 20]
groups = C.defaultdict(list)
fam_of = {}
for r in rows:
    k = key_of(r, "lt")
    if r["launch"]["to"] is None and r["fam"]["tok"].startswith("65daaea0"): k = "create#65daaea0"
    groups[k].append(r)
out = {}
for k in want:
    base = k.split("@")[0]; rs = groups.get(base, [])
    if "@core" in k:
        c = C.Counter(shape_of(r) for r in rs); top_shape = c.most_common(1)[0][0]; rs = [r for r in rs if shape_of(r) == top_shape]
    rs = [r for r in rs if r["ev_complete"]]
    ctrl = [r for r in rs if r["outsider"]["n_outsider_buys"] == 0 and r["n_buys"]]
    res = {}
    # unbiased variant (README Problems 1): outsiders among the first 12 swaps only (fetched for every pool); control = no outsider there
    ctrl = [r for r in rs if r["outsider12"]["n"] == 0 and r["n_buys"]]
    for var in ("o12", "o12nf"):
        if var == "o12": ops = [(r, r["outsider12"]["last_off"]) for r in rs if r["outsider12"].get("n")]
        else: ops = [(r, r["outsider12"]["nf_last_off"]) for r in rs if r["outsider12"].get("nf_n")]
        for W in (10, 30, 100, 166):
            obs = exp = 0.0
            for r, t in ops:
                fp = r["first_pull_off"]
                obs += fp is not None and t < fp <= t + W
                alive = [c for c in ctrl if c["first_pull_off"] is None or c["first_pull_off"] > t]
                if alive: exp += sum(1 for c in alive if c["first_pull_off"] is not None and c["first_pull_off"] <= t + W) / len(alive)
            res[f"{var}_W{W}"] = (len(ops), int(obs), round(exp, 1))
    n12p = [r for r in rs if r["outsider12"].get("nf_n")]
    b12p = [r for r in rs if r["outsider12"]["n"] == 0 and r["outsider12"]["n_buys12_before_pull"] > 0]
    res["census12"] = (f"{sum(1 for r in n12p if r['outsider12'].get('nf_reaction'))}/{len(n12p)}",
                       f"{sum(1 for r in b12p if r.get('pull_after_last_buy12') is not None and r['pull_after_last_buy12'] <= 30)}/{len(b12p)}")
    ours = [r["ours"] for r in rs if r.get("ours")]
    res["ours"] = (len(ours), sorted(o["pull_after_ours"] for o in ours if o.get("pull_after_ours") is not None))
    res["n_ctrl"] = len(ctrl)
    out[k] = res
    line = " ".join(f"{a}:{b[1]}/{b[0]} exp {b[2]}" for a, b in res.items() if a.startswith("o12"))
    print(f"{short(k):40s} ctrl {len(ctrl)} | {line} | census12 nf {res['census12'][0]} base {res['census12'][1]} | ours {res['ours'][0]} {res['ours'][1][:30]}")
json.dump(out, open(os.path.join(D, "reaction.json"), "w"))
