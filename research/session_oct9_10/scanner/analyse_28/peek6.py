import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); ids = json.load(open("pids.json")); C = json.load(open("postwindow_logs.json"))
rows = json.load(open("hookfee.json"))
meas = collections.defaultdict(list)
RF = {"0x65050a9b": 0.01, "0x2fe63b82": 0.005, "0x6131b5fa": 0.0025, "0xe492912f": 0.01, "0xf2251d75": 0.01}
for r in rows:
    if r["fam"] == "F1" and r["side"] == "buy" and r["val"]:
        f = RF.get(r["to"]); 
        if f is not None: meas[r["pid"]].append(round(1 - (-r["a0"]) / (r["val"] * (1 - f)), 4))
for pid in ids["F1"]:
    p = P[pid]
    print(pid[:10], p["launch_block"], "age_at_head_h %.1f" % ((C["head"] - p["launch_block"]) * 0.1026 / 3600), "tick0", p["tick0"], "tax_now", C["f1_tax"][pid], "measured", sorted(set(meas.get(pid[:10], []))), "swaps", p["n_swaps"])
