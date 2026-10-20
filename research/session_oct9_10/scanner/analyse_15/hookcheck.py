"""Check the ETH-side hook-tax model of common15 on family 0xc763b179|1828: re-price the launchpad wallet's own real round trips (buy at +5/+5/+8,
sell at +316/+162/+137) with its swaps removed from the chain state and re-inserted as ours (stake = the ETH the hook saw), and compare the
ETH the hook released on the sell (Swap a0 x (1 - hook rate), from the receipts) with the pricer's eth_out."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import common15
from common15 import *  # noqa
P = load_pools(); T = load_txs(); F = load_families(); M = load_blocks_meta()
K = json.load(open(os.path.join(HERE, "keys.json")))
HF = json.load(open(os.path.join(HERE, "hookfee.json")))
pids = F[K[1]]["pids"]; E = load_events(set(pids))
out = []
for pid in pids:
    rows = [r for r in HF if pid.startswith(r["pid"])]
    b = next((r for r in rows if r["side"] == "buy"), None); s = next((r for r in rows if r["side"] == "sell"), None)
    if not (b and s): continue
    d_b = dict((t, v) for t, v in b["hook_events"]); d_s = dict((t, v) for t, v in s["hook_events"])
    gross_in = d_b["0x8d1f1ed7"][0]; hb = round(d_b["0x8d1f1ed7"][2] / gross_in * 1e6); hs = round(d_s["0x5a2eb160"][2] / d_s["0x5a2eb160"][1] * 1e6)
    released = d_s["0x5a2eb160"][1] - d_s["0x5a2eb160"][2]
    common15.ETH_TAX[pid] = (hb, hs)
    pool = Pool(P[pid], E[pid], T, M)
    for x in pool.seq: x["relay"] = True        # the wallet's own two swaps are the only swaps: treat them as ours
    sim = pool.trade(pool.b0 + b["rel"], pool.b0 + s["rel"], stake=gross_in)
    sim_out = (sim["gross"] * gross_in + gross_in)  # gross = (eth_out - stake)/stake
    out.append({"pid": pid[:12], "buy_rel": b["rel"], "sell_rel": s["rel"], "hook_buy_ppm": hb, "hook_sell_ppm": hs, "gross_in": gross_in,
                "real_released": released, "sim_eth_out": round(sim_out), "rel_err": sim_out / released - 1})
    print(out[-1])
json.dump(out, open(os.path.join(HERE, "hookcheck.json"), "w"), indent=1)
