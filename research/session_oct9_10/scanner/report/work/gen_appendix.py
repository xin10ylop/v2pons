# The appendix tables of REPORT_owner.md: every analysed strict family that was not flagged (from table.json, the analysts' own numbers,
# and the census counts), the eight families of analysts 2 and 3 (no result file: census counts), and the regroupings. Prints markdown.
import json
W = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/report/work"
T = json.load(open(W + "/table.json")); M = json.load(open(W + "/a23_missing.txt"))
JUDGED = {"0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|10000|200|true", "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2276|100|1|true",
          "0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|500|1|true", "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|100|1|true",
          "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|500|10|true", "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|2500|50|true"}
NOTES = {'0x16cf6788b762ee8969744586ed16fc5705140dd7|4101659e|388|0|200|false': 'no liquidity at the launch price in 32 of 32; a real buy in 1', '0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2020|3000|60|false': "inside analyse_27's G1 (all POSM 2,020-byte launches): front -55.4% (n 234), follow +4.9% mean, -0.7% median, 23% win (n 52)", '0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2020|600000|6000|true': "fee-farm pool, fee 60%; inside analyse_23's high-fee class (front -75.3%, n 167)", '0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|500|1|false': "= analyse_26's F4b (operator C-2's hooked sibling, same crowd routers): follow +13.3% mean, +0.8% median, 62% win (n 21), 0 pulled by +3,000; the relay's sell reverted in an eth_call on 3 of 3 hooked pools, and on 1 hookless one, so the sellability test is inconclusive (analyse_26/honeypot_sim.json)", '0x58daec3116aae6d93017baaea7749052e8a04fa7|f7020405|196|10000|200|false': 'per-pool hooks; buyers are 18 recurring wallets through the Universal Router; my ride replay -1.0% to -2.1% at holds 5-100, 0 pulled (report/work/f702_ride.json)', '0xfcd182416ca91a9e88e9fe44e4f78ea3cb2c15c7|6fe958d8|68|30000|200|false': 'no liquidity at the launch price; no real buy', '0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|790000|60|true': 'fee-farm pool, fee 79%; no real buy', '0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|836798|9303|true': "fee 83.7%; no real buy; inside analyse_26's F4c (front -66.5%)"}
def short(k):
    p = k.split("|")
    if len(p) != 6: return k
    to = "PM" if p[0].startswith("0x8366a39c") else "POSM" if p[0].startswith("0x58daec31") else p[0][:10]
    return f"{to} {p[1]} {p[2]}B fee {p[3]} ts {p[4]} {'no hook' if p[5] == 'true' else 'hooked'}"
def pct(x): return "" if x is None else f"{100 * x:+.1f}%"
def why(r):
    k = r["key"]; fee = int(k.split("|")[3]) if k.count("|") == 5 else 0
    v = r.get("verdict")
    if "|7fde822e|" in k: return "launchpad pool (selector 7fde822e): token-only range, no pull, a real buy in at most 1 pool"
    if k.startswith("0x05d55239"): return "no rule priced by the analyst; my ride replay -0.2% to -1.9% at holds 5-100 (report/work/ride_0x05d55239.json)"
    if k.startswith("0x0000ffff"): return "public token launchpad: no pull, organic first buys (analyse_19 notes)"
    if fee >= 100000 and fee != 8388608: return f"fee-farm pool, fee {fee / 10000:g}% a swap: two fees exceed any move"
    if r.get("front_n") == 0 and (r.get("real_buy_pools") or 0) == 0: return "no ETH at the launch price and no real buy"
    if r.get("front_n") == 0: return "no ETH liquidity at the launch price"
    if (r.get("real_buy_pools") or 0) == 0: return "no buy of 0.0002 ETH or more in any pool"
    return "buys exist but both rules lose after two fees" if (r.get("front_mean") or 0) < 0 and (r.get("follow_mean") is None or r["follow_mean"] < 0.01) else "small positive follow on a tiny sample"
rows = [r for r in T if r["key"] not in JUDGED and r.get("census_count")]
rows.sort(key=lambda r: -(r["census_count"] or 0))
print("| family (launch target, selector, calldata, fee, tick spacing, hook) | analyst dir | launches in 48 h | pools with a buy >= 0.0002 ETH | pulled by +3,000 | front mean (n) | follow mean (n) | analyst verdict | why not |")
print("|---|---|---|---|---|---|---|---|---|")
for r in rows:
    fr = f"{pct(r['front_mean'])} ({r['front_n']})" if r.get("front_mean") is not None else ("none" if r.get("front_n") in (0, None) else f"n {r['front_n']}")
    fo = "none in family" if (r.get("follow_n") or 0) > (r.get("census_count") or 0) else (f"{pct(r['follow_mean'])} ({r['follow_n']})" if r.get("follow_mean") is not None else "none")
    print(f"| {short(r['key'])} | analyse_{r['a']} | {r['census_count']} | {r['real_buy_pools']} | {r['pulled_3000']} | {fr} | {fo} | {r.get('verdict') or 'not stated'} | {why(r)} |")
print()
print("| family | analyst dir | launches in 48 h | pools with a buy >= 0.0002 ETH | first such buy, median offset | pulled by +3,000 | note |")
print("|---|---|---|---|---|---|---|")
for k, v in M.items():
    a = "analyse_3" if k in json.load(open(W + "/../../analyse_3/keys.json")) else "analyse_2"
    print(f"| {short(k)} | {a} (no result file) | {v['count']} | {v['real_buy_pools']} | {v['real_off_p50'] if v['real_off_p50'] is not None else 'none'} | {v['pulled_3000']} | {NOTES.get(k, '')} |")
print()
for r in T:
    if not r.get("census_count") and r["key"] not in ("inputs", "raw", "calib_v2433", "pricer_validation_on_F1_operator", "crowd_minout", "postwindow_launcher", "pricer_check_assigned", "verdicts"):
        print("REGROUP", r["a"], "|", r["label"][:120], "|", r["count"], "|", pct(r["front_mean"]), r["front_n"], "|", pct(r["follow_mean"]), r["follow_n"])
