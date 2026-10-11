"""Stage 9: summary of the live monitor (u_mon.jsonl): T's buyer wallet's ETH balance and nonce at every block T-15..T (state read from the
node while still available), and its last balance change before T (block, lead, own tx or incoming, the txs of that block naming it)."""
import json, collections, os
from lib import *
os.chdir(HERE)
R = [json.loads(l) for l in open("u_mon.jsonl") if l.strip()]
R = [r for r in R if "bal" in r]
print("pools read live:", len(R), "| skipped rows:", sum(1 for l in open("u_mon.jsonl") if '"why"' in l))
flat_b = flat_n = covered = 0; leads = []; kinds = collections.Counter(); ex = []
for r in R:
    b = [r["bal"][str(d)] for d in range(-15, 0)]; n = [r["nonce"][str(d)] for d in range(-15, 0)]
    fb = len(set(b)) == 1; fn = len(set(n)) == 1; flat_b += fb; flat_n += fn
    cov = b[-1] is not None and b[-1] >= r["buy_q"]; covered += cov
    lc = r.get("last_change", {})
    if "lead" in lc:
        leads.append(lc["lead"]); own = lc["nonce_after"] != lc["nonce_before"]
        k = ("own tx" if own else "incoming") + (": " + ",".join(f"{t['from'][:10]}->{t['to'][:10]}:{t['sel'] or 'eth'}" for t in lc["txs"]) if lc["txs"] else ": no tx names it (internal)")
        kinds[("own tx" if own else "incoming", "tx names it" if lc["txs"] else "internal")] += 1
        if len(ex) < 12: ex.append((r["pid"][:12], "T", r["T"], "lead", lc["lead"], "delta ETH %.5f" % ((lc["bal_after"] - lc["bal_before"]) / 1e18), k))
    elif "none_since" in lc: kinds[("no change since T%+d" % lc["none_since"],)] += 1
    elif not lc: kinds[("not measured (first monitor version)",)] += 1
    else: kinds[("err", lc.get("err", "")[:60])] += 1
print(f"balance identical at every block T-15..T-1: {flat_b} of {len(R)}; nonce identical: {flat_n} of {len(R)}; balance at T-1 covers the buy: {covered} of {len(R)}")
print("T's buy size p50 %.4f ETH; deadline - (unknown here) | T offsets:" % (pct([r['buy_q'] / 1e18 for r in R], .5)), sorted(r["T"] for r in R))
print("last balance change before T: lead (blocks) sorted:", sorted(leads))
if leads: print(f"   p10/50/90 {pct(leads,.1)}/{pct(leads,.5)}/{pct(leads,.9)}; within 1-4 blocks: {sum(1 for x in leads if 1 <= x <= 4)}; within 1-15: {sum(1 for x in leads if x <= 15)}")
print("kind:", kinds.most_common())
for e in ex: print("  e.g.", e)
