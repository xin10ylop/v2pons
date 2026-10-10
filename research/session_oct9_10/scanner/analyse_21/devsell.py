"""deployer 0x841ac064 (family 1): the deployer's own sells (the analogue of a pull: it never removes liquidity) and the buys around them"""
import sys, os, json, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pricer21 import *
P = load_pools(); T = load_txs(); M = load_blocks_meta()
D1 = "0x841ac064763c75a6b6b916ef676420d6ffdd281f"
pids = [p["pid"] for p in P.values() if p["launch_from"] == D1]
E = load_events(set(pids)); out = []
for pid in pids:
    p = P[pid]; pl = Pool21(p, E[pid], T, M)
    sells = [x for x in pl.seq if not x["buy"]]
    dev_sell = next((x for x in sells if x["from"] == D1), None)
    buys = [x for x in pl.buys()]
    row = {"pid": pid, "family": p["family"], "fee": p["fee"], "utc": datetime.datetime.utcfromtimestamp(p["launch_ts"]).strftime("%Y-%m-%d %H:%M:%S"),
           "dev_buy_eth": p["launch_value_eth"], "dev_sell_off": (dev_sell["bn"] - pl.b0) if dev_sell else None,
           "dev_sell_eth": dev_sell["eth"] / 1e18 if dev_sell else None,
           "buys": [(x["bn"] - pl.b0, round(x["eth"] / 1e18, 6), x["from"][:10] if x["from"] else None, x["to"][:10] if x["to"] else None) for x in buys],
           "sells": [(x["bn"] - pl.b0, round(x["eth"] / 1e18, 6), x["from"][:10] if x["from"] else None) for x in sells], "clamped": pl.clamped}
    out.append(row); print(row)
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "devsell.json"), "w"), indent=1)
