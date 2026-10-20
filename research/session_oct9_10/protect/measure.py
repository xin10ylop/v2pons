#!/usr/bin/env python3
"""The operator's reaction, measured on every operator launch Oct 8 00:00 UTC -> now (89 orig + 49 copy; Oct 8 data from
../yday/react_data.json, Oct 9 from react9_data.json).

* The crowd: every buy carrying the operator crowd's transaction fingerprint (Universal Router execute(), 1,124 bytes of calldata,
  deadline 2^256-1, EIP-1559, priority fee exactly 0.02 gwei, gas limit 220,000 / 880,000 / 260,000), split by wallet behaviour into
  A (the recurring set on the classic launches + the two wallets that joined it Oct 8 11:29), B (the set that buys only the 7
  low-fee long launches), fresh (nonce <= 3, one or two launches: the copies' per-launch wallets, the quick-pull pairs), and the
  speck buyer 0xb4d43149. Non-crowd = our relay / wallet, and any buy without the fingerprint (outsiders).
* Real size: ETH in >= 0.0002 (the engine's MIN_TRIGGER_ETH). The pull: the first ModifyLiquidity with a negative liquidityDelta.
* Lags are in blocks (the pull's block - the buy's block); milliseconds = blocks x the mean block time measured from the block
  timestamps over +-3000 blocks around the buy (timestamps are whole seconds, so a single block's time is not measurable).
Writes measure.json; prints the tables."""
import sys, json, collections, statistics as st
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from classify import *
from chain import batch, rpc
HERE = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect/"
OCT9 = 83719339
ARM = 6; MAXT = 150; HOLD = 3                      # engine: armed ~+6 after the launch block, trigger <= +150, sell lands buy + 3
pools = load(); cw = annotate(pools)
head = json.load(open(HERE + "react9_data.json"))["head"]

# ---------------------------------------------------------------- crowd families
L = collections.defaultdict(set); N = collections.defaultdict(list)
for p in pools:
    for x in p["sw"]:
        if x["from"] in cw: L[x["from"]].add(p["pid"]); N[x["from"]].append(x["nonce"])
SPECK = next(w for w in cw if w.startswith("0xb4d43149"))
B7 = set.intersection(*[L[w] for w in cw if w.startswith("0x4c45af68")]) if False else None
w4 = next(w for w in cw if w.startswith("0x4c45af68")); B7 = L[w4]
fam = {}
for w in cw:
    if w == SPECK: fam[w] = "speck"
    elif L[w] <= B7 and len(L[w]) >= 3: fam[w] = "B"
    elif min(N[w]) <= 3 and len(L[w]) <= 2: fam[w] = "fresh"
    elif len(L[w]) >= 20: fam[w] = "A"
    else: fam[w] = "other_fp"
famc = collections.Counter(fam.values())
B_launch_set_exact = sum(1 for w in cw if L[w] == B7)
for p in pools:
    for x in p["sw"]:
        x["fam"] = fam.get(x["from"]) if x["cls"] == "crowd" else x["cls"]


def launch_family(p):
    c = collections.Counter(x["fam"] for x in p["sw"] if x["cls"] == "crowd" and x["a0"] <= -REAL and before_pull(p, x))
    if p["kind"] == "copy": return "copy"
    if not c: return "no_crowd_buy"
    return c.most_common(1)[0][0]


for p in pools: p["family"] = launch_family(p)

# ---------------------------------------------------------------- block times (ms) around each event
ts_cache = {}
def tss(bs):
    need = sorted({b for b in bs if b not in ts_cache and b <= head})
    for b, blk in zip(need, batch([("eth_getBlockByNumber", [hex(b), False]) for b in need])):
        ts_cache[b] = int(blk["timestamp"], 16)
def block_ms(b):
    lo, hi = b - 3000, min(b + 3000, head)
    tss([lo, hi]); return 1000 * (ts_cache[hi] - ts_cache[lo]) / (hi - lo)

# ---------------------------------------------------------------- every non-crowd real-size buy before the pull, and the pull after it
def clean(p):
    return not any(x["cls"] in ("us", "outsider", "?") and x["a0"] <= -REAL and before_pull(p, x) for x in p["sw"])


def chance(p, X, lag):
    """among clean launches of the same family still alive at offset X, the share pulled within (X, X + lag]"""
    al = [q for q in pools if q["family"] == p["family"] and clean(q) and (q["pull"] is None or q["pull"]["bn"] - q["b0"] > X) and q["b0"] + X + lag <= head]
    hit = [q for q in al if q["pull"] is not None and q["pull"]["bn"] - q["b0"] <= X + lag]
    return f"{len(hit)}/{len(al)}"


def crowd_phase(p, x, span=20):
    """is the crowd still trading around the buy: crowd swaps (buys or sells) in the 20 blocks before it"""
    return sum(1 for y in p["sw"] if y["cls"] == "crowd" and x["bn"] - span <= y["bn"] < x["bn"] and abs(y["a0"]) >= REAL)


rows = []
for p in pools:
    b0 = p["b0"]; pb = p["pull"]["bn"] if p["pull"] else None
    nc = [x for x in p["sw"] if x["cls"] in ("us", "outsider", "?") and x["a0"] <= -REAL and before_pull(p, x)]
    for i, x in enumerate(nc):
        ms = block_ms(x["bn"])
        lag = (pb - x["bn"]) if pb else None
        rows.append({"time_utc": utc(p["ts"] + round((x["bn"] - b0) * ms / 1000)), "launch_utc": utc(p["ts"]), "day": "Oct 9" if b0 >= OCT9 else "Oct 8",
                     "pid": p["pid"][:10], "kind": p["kind"], "family": p["family"], "fee": p["fee"], "who": "us" if x["cls"] == "us" else "outsider",
                     "wallet": x["from"], "nonce": x["nonce"], "to": x["to"], "via": x["via"][:8], "size_eth": round(-x["a0"] / 1e18, 6), "offset": x["bn"] - b0,
                     "first_noncrowd_on_launch": i == 0, "crowd_swaps_prev20": crowd_phase(p, x),
                     "pull_offset": (pb - b0) if pb else None, "lag_blocks": lag, "ms_per_block": round(ms, 2), "lag_ms": round(lag * ms) if lag is not None else None,
                     "pull_tx_index": p["pull"]["idx"] if pb else None, "chance_same_family_clean": chance(p, x["bn"] - b0, lag) if lag is not None else None})
rows.sort(key=lambda r: (r["lag_blocks"] is None, r["lag_blocks"] if r["lag_blocks"] is not None else 0))

# ---------------------------------------------------------------- the follow engine's trigger on every orig launch
trig = []
for p in pools:
    if p["kind"] != "orig": continue
    b0 = p["b0"]; pb = p["pull"]["bn"] if p["pull"] else None
    rb = [x for x in p["sw"] if x["a0"] <= -REAL and before_pull(p, x) and x["cls"] != "us"]
    before_arm = [x for x in rb if x["bn"] - b0 < ARM]
    t = next((x for x in rb if ARM <= x["bn"] - b0 <= MAXT), None)
    ours = [x for x in p["sw"] if x["cls"] == "us"]
    ent = {"launch_utc": utc(p["ts"]), "pid": p["pid"][:10], "fee": p["fee"], "family": p["family"], "pull_offset": (pb - b0) if pb else None,
           "first_real_before_arm": bool(before_arm), "traded_by_us": bool(ours), "our_buy_offset": (ours[0]["bn"] - b0) if ours else None}
    if t is None or before_arm:
        ent["trigger"] = None; ent["why_no_trigger"] = "real buy before arming" if before_arm else ("no real buy" if not rb else f"first real buy at +{rb[0]['bn'] - b0} > {MAXT}")
    else:
        ent.update({"trigger": {"offset": t["bn"] - b0, "who": t["fam"] if t["cls"] == "crowd" else t["cls"], "wallet": t["from"], "size_eth": round(-t["a0"] / 1e18, 5), "nonce": t["nonce"]},
                    "pull_after_trigger": (pb - t["bn"]) if pb else None,
                    "sell_lands_T+1buy": t["bn"] + 1 + HOLD - b0, "sell_lands_T+2buy": t["bn"] + 2 + HOLD - b0,
                    "pull_minus_sell_land_T+2buy": (pb - (t["bn"] + 2 + HOLD)) if pb else None,
                    "noncrowd_buys_before_pull_excl_us": sum(1 for x in rb if x["cls"] in ("outsider", "?"))})
        if ours: ent["actual_buy_after_trigger"] = ours[0]["bn"] - t["bn"]
    trig.append(ent)

# ---------------------------------------------------------------- outputs
out = {"about": __doc__, "crowd": {"fingerprint_wallets": len(cw), "families": dict(famc), "B_wallets_with_exactly_the_7_launch_set": B_launch_set_exact,
                                   "B_launches": sorted(utc(p["ts"]) + " " + p["pid"][:10] + f" fee {p['fee']}" for p in pools if p["pid"] in B7),
                                   "launch_families": dict(collections.Counter(p["family"] for p in pools))},
       "noncrowd_buys": rows, "engine_triggers": trig}
json.dump(out, open(HERE + "measure.json", "w"), indent=1, default=str)

print("crowd families:", dict(famc), "| B wallets with exactly the 7-launch set:", B_launch_set_exact)
print("launch families:", dict(collections.Counter(p["family"] for p in pools)))
print("\nNON-CROWD REAL-SIZE BUYS -> FIRST PULL AFTER (blocks, ms = blocks x local mean block time)")
for r in rows:
    print(f"  {r['time_utc']} {r['day']} {r['kind']:4s} {r['family']:12s} fee {r['fee']:5d} {r['who']:8s} {r['wallet'][:10]} n {r['nonce']!s:>8s} {r['size_eth']:.5f} ETH +{r['offset']:5d} "
          f"crowd20 {r['crowd_swaps_prev20']:2d} first {str(r['first_noncrowd_on_launch'])[0]} pull +{r['pull_offset']} lag {r['lag_blocks']} blk = {r['lag_ms']} ms (chance {r['chance_same_family_clean']})")
print("\nENGINE TRIGGERS ON ORIG LAUNCHES (arm +%d, trigger <= +%d)" % (ARM, MAXT))
for e in trig:
    t = e.get("trigger")
    if t: print(f"  {e['launch_utc']} {e['pid']} {e['family']:12s} T +{t['offset']:4d} {t['who']:8s} {t['wallet'][:10]} {t['size_eth']:.4f} pull +{e['pull_offset']} pull-T {e['pull_after_trigger']} pull-sell(T+2 buy) {e['pull_minus_sell_land_T+2buy']} us {e['our_buy_offset']}")
    else: print(f"  {e['launch_utc']} {e['pid']} {e['family']:12s} no trigger: {e['why_no_trigger']} (pull +{e['pull_offset']})")
