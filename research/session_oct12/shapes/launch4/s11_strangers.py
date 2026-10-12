"""Did strangers who bought early get out with a profit? (offline, s06_pools.json) Every non-launcher, non-sentinel wallet that bought in a core
pool: ETH-eq paid and received, net of the hook's measured take (S1 1% of the output each way; S2 1% of the WETH in and out, 2% in the runner;
S3/S4 no hook, the LP fee is inside the Swap amounts), and the coins still held, valued at the pool's last price (marginal, no impact).
Prints s11_strangers.out."""
from common import *
import collections
D = json.load(open(J("s06_pools.json"))); SENT = "0xe71a69f434a719cd5afa411568b69716aab3b84a"
for p in D["pools"]:
    hk = {"S1": 0.01, "S2": 0.02 if p["launcher"].startswith("0x6901126c") else 0.01}.get(p["shape"], 0.0)
    wl = collections.OrderedDict()
    for w in p["sw"]:
        if w["inlaunch"] or w["from"] in (SENT, p["launcher"]) or w["eth"] is None: continue
        e = wl.setdefault(w["from"], {"first": w["off"], "fmult": w["mult"], "paid": 0.0, "got": 0.0, "coins": 0, "last": None})
        if w["buy"]:
            # S2: the hook takes from the WETH in (the event shows the 99%); S1: the hook takes 1% of the coins out
            e["paid"] += w["eth"] / (1 - hk) if p["shape"] == "S2" else w["eth"]; e["coins"] += w["c"] * (1 - hk if p["shape"] == "S1" else 1)
        else:
            e["got"] += w["eth"] * (1 - hk); e["coins"] -= w["c"]; e["last"] = w["off"]
    if not wl: continue
    x = (p["sw"][-1]["sqrtP"] / 2 ** 96) ** 2; pr = (1 / x if p["qs"] == 0 else x) * (p["sw"][-1]["eth"] / p["sw"][-1]["q"] if p["sw"][-1]["q"] else 0)
    print(f"{p['shape']} pool {p['pid'][:10]} ({p['qname']}), {len(wl)} outside wallets; price now x{p['last_mult']:.2f} of launch")
    for k, (a, e) in enumerate(wl.items()):
        if k >= 10: break
        held = max(e["coins"], 0) * pr
        print(f"   {a[:10]} first buy +{e['first']:<5d} at x{e['fmult']:.3f}: paid {e['paid']:.5f} got {e['got']:.5f} (last sell +{e['last']}) held now {held:.4f} -> realized {e['got'] - e['paid']:+.5f}, with holdings {e['got'] + held - e['paid']:+.5f} ETH-eq")
