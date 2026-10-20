"""the census's pool rows for the graduated tokens (offline): the pool launched by the migration tx vs other pools of the same token."""
import json, collections
from krpc import *
G = json.load(open(os.path.join(OUT, "k12_grads.json")))
gt = {g["token"]: g for g in G}; migtx = {g["mig_tx"]: g for g in G if g["mig_tx"]}
rows = []
for line in open(os.path.join(CEN, "pools.jsonl")):
    if not any(t[2:] in line for t in ()): pass
    p = json.loads(line)
    if p["token"] in gt: rows.append(p)
print("census pools whose token graduated", len(rows), "tokens", len({p["token"] for p in rows}))
mig = [p for p in rows if p["launch_tx"] in migtx]; other = [p for p in rows if p["launch_tx"] not in migtx]
print("pools created by a migration tx", len(mig), "other pools of graduated tokens", len(other))
def summ(P, label):
    c = collections.Counter((p["dex"], p["quote"], p["fee"], p["tick_spacing"], p["hooks"], p["launch"]["target"] if p.get("launch") else None) for p in P)
    print(label, c.most_common(6))
summ(mig, "migration pools (dex, quote, fee, ts, hooks, launch target)")
summ(other, "other pools")
keep = []
for p in mig:
    g = migtx[p["launch_tx"]]
    keep.append({k: p.get(k) for k in ("pool", "token", "quote", "fee", "tick_spacing", "hooks", "sqrt_p0", "tick0", "launch_block", "launch_utc", "launch_tx", "n_swaps", "n_buys", "n_sells",
                                         "buy_eth_total", "n_pulls", "first_buy_off", "first_buy_eth", "swaps12", "first_buys")} | {"create_bn": g["create_bn"], "full_bn": g["full_bn"]})
json.dump(keep, open(os.path.join(OUT, "k13_mig_pools.json"), "w"), indent=0)
print(json.dumps(keep[0])[:3000])
# the census's 918 'graduated' tokens: how many have a migration (factory event) at all
B = json.load(open(os.path.join(CEN, "bonding.json")))
