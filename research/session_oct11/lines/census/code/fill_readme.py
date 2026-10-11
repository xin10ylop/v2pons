#!/usr/bin/env python3
"""README.md from README_template.md + report_tables.md + summary.json + the stage logs (no RPC)."""
import os, sys, json, ast, glob, time, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib2 import CEN, CACHE, jget, jl_iter

J = lambda n: json.load(open(os.path.join(CEN, n)))
S = J("summary.json"); W = S["window"]; B = J("bonding.json")
tables = open(os.path.join(CEN, "report_tables.md")).read().split("\n\n")
DEX_MD, FAM_MD, OV_MD, FU_MD, TOP_MD = tables[0], tables[1], tables[2], tables[3], "\n\n".join(tables[4:])
utc = lambda t: time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(t))

# RPC load from the stage logs (the last cumulative STATS dict of each process)
tot = collections.Counter(); per = []
for f in sorted(glob.glob(os.path.join(CACHE, "f*.log"))):
    last = None
    for line in open(f):
        i = line.find("{'posts'")
        if i >= 0:
            try: last = ast.literal_eval(line[i:].strip())
            except Exception: pass
    if last:
        per.append((os.path.basename(f), last)); tot.update({k: v for k, v in last.items() if isinstance(v, int)})
RPC = (f"RPC load over all stages (from the stage logs; killed-and-resumed runs counted to their last progress line): {tot['posts']:,} POSTs, "
       f"{tot['items']:,} batch items, {tot['429']:,} HTTP 429 answers (each retried after a back-off; none was lost: "
       f"{len(list(jl_iter('missing_txs.jsonl')))} transactions came back null), {tot['errs']} other transport errors (retried), "
       f"{tot['bytes_wire'] / 1e6:,.0f} MB on the wire (gzip) for {tot['bytes'] / 1e6:,.0f} MB of JSON. At most three stages ran at once, each "
       f"with a minimum gap of 0.45-0.8 s between its POSTs.")

ev_head = None
for g in jl_iter("ev.jsonl"):
    ev_head = max(ev_head or 0, g["head"])
nfb = sum(1 for _ in open(os.path.join(CACHE, "fblocks.jsonl")))
nsw = sum(1 for _ in open(os.path.join(CACHE, "tx_swap.jsonl"))) + sum(1 for _ in open(os.path.join(CACHE, "tx_swap_b.jsonl")))
inits = sum(len(r["logs"]) for r in jl_iter("inits.jsonl"))
v4 = S["per_dex"]["v4"]["pools"]
BOND = (f"{B['creates']:,} creates in the window ({', '.join(f'{d[5:]}: {n:,}' for d, n in B['per_day'].items())}; the last day is partial), "
        f"{B['distinct_creators']:,} distinct creators (top {B['creators_top'][0][0]} x{B['creators_top'][0][1]}). The event is "
        f"`{B['topic'][:10]}…` with topics [sig, token, curve, creator] and 3 data words (`(0, 0, 4.2e18)` in {B['w_values_top'][0][1]:,} creates). "
        f"The sampled create txs go mostly to `0xe33e9e47…` (`f85f8e41`, the front contract studied in ops/bcurve*.py) or to the factory itself "
        f"(`a72101af`, `f35abbcf`): {B['sample_tx_to_selector'][:4]}. {B['graduated_into_census_pools']} curve tokens appear as the token of a census pool "
        f"(graduations: {B['graduation_dex']}; blocks from the create to the pool p10/p50/p90 {B['graduation_blocks_after_create_p10_50_90']}), so those "
        f"launches are in `pools.jsonl` under their v4 families. The curves' own trading was not decoded (the 25 sampled curves' logs: "
        f"`bonding.json` `sample_curve_event_topics`).")

cov = [0, 0, 0, 0]; c = collections.Counter()
with open(os.path.join(CEN, "pools.jsonl")) as fh:
    for line in fh:
        r = json.loads(line); o = r.get("outsider")
        if o:
            cov[0] += o["n_with_eoa"]; cov[1] += o["n_buys_before_pull"]
            if not r.get("n_pulls"): cov[2] += o["n_with_eoa"]; cov[3] += o["n_buys_before_pull"]
        if r.get("has_events") and not r.get("ev_complete"): c["incomplete"] += 1
        if r["launch"] and r["launch"]["target_code_hash"] is None: c["target_nocode"] += 1
        if r["dex"] != "v4" and r.get("liq_off") not in (None, 0): c["liq_later"] += 1
        if r.get("ours"): c["ours"] += 1
fs = S["funding_sample"]
rpc_found = sum(1 for x in jl_iter("funding.jsonl") if x.get("first"))
FUND_LINE = (f"{fs['wallets_scanned']} launch wallets were scanned over the RPC (a funding found for {rpc_found}) and {fs['wallets_from_cache']} more resolved from the cached blocks; "
             f"status {fs['status']}; {fs['hop2_scanned']} fresh funders got a second hop ({fs['hop2_found']} found). {fs['pools_with_funder']:,} pools "
             f"({fs['pools_covered']:,} covered) have a funder.")
PFILL = {"COV_ALL": f"{cov[0]:,} of {cov[1]:,} ({cov[0] / max(1, cov[1]):.0%})", "COV_NOPULL": f"{cov[2]:,} of {cov[3]:,} ({cov[2] / max(1, cov[3]):.0%})",
         "N_SHARED": S.get("shared_fps"), "FUND_LINE": FUND_LINE, "TOKX": f"{S['families']['tokx']['all']:,}", "POOLSNQ": f"{S['pools'] - S['quote_pairs']:,}",
         "TARGET_NOCODE": c["target_nocode"], "LIQ_LATER": c["liq_later"], "OURS": f"{c['ours']:,}", "INCOMPLETE": c["incomplete"],
         "RPC_LINE": f"{tot['429']:,} HTTP 429 answers over {tot['posts']:,} POSTs, all retried with back-off; no item was lost."}
PROB = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "problems.md")).read() if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "problems.md")) else "(see the summary)"
t = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "README_template.md")).read()
fill = {"BUILT": S["built_utc"], "FROM_BLOCK": f"{W['from_block']:,}", "FROM_UTC": utc(W["from_ts"]), "HEAD": f"{W['head']:,}", "HEAD_UTC": utc(W["head_ts"]),
        "NBLOCKS": f"{W['head'] - W['from_block'] + 1:,}", "EV_HEAD": f"{ev_head:,}", "EV_COMPLETE": f"{S['ev_complete']:,}", "POOLS": f"{S['pools']:,}",
        "V4_INITS": f"{inits:,}", "V4_OUT": f"{inits - v4:,}", "DEX_TABLE": DEX_MD, "N_CREATES": sum(1 for _ in jl_iter("rcpt.jsonl")),
        "N_SWAPTX": f"{nsw:,}", "N_FBLOCKS": f"{nfb:,}", "RPC": RPC, "TOKX_FAMS": f"{S['families']['tokx']['all']:,}",
        "POOLS_NQ": f"{S['pools'] - S['quote_pairs']:,}", "FAM_TABLE": FAM_MD, "OV_TABLE": OV_MD, "FUND_TEXT": FU_MD, "TOP_TABLE": TOP_MD,
        "BONDING": BOND, "PROBLEMS": PROB}
for k, v in PFILL.items(): PROB = PROB.replace("{" + k + "}", str(v))
fill["PROBLEMS"] = PROB
for k, v in fill.items(): t = t.replace("{" + k + "}", str(v))
open(os.path.join(CEN, "README.md"), "w").write(t)
print("README", len(t), "rpc", dict(tot))
