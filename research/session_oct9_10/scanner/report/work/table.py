# One row per analysed family: the analyst, the family key (strict or regrouped), its count, the analyst's own verdict where it gave one,
# its front and follow numbers (n, mean) as it reported them, and the census's own counts (pools with a buy of 0.0002 ETH or more,
# pulled within 3,000 blocks). Output: report/work/table.json.
import json, glob, os, re, sys, collections, statistics as st
S = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner"
sys.path.insert(0, S + "/census")
from load import load_families, load_pools, load_events
KRE = re.compile(r"((?:0x[0-9a-f]{40}|create)\|[0-9a-f]{8}\|\d+\|\d+\|-?\d+\|(?:true|false))")
GRE = re.compile(r"^(?:F\d\S*|G\d)\s+(.*)$")
def num(x):
    try: return float(x)
    except Exception: return None
def fr(v):
    """(n, mean) from a front/follow field: a dict with n/mean, or a string 'n 9, mean -2.06%'"""
    if isinstance(v, dict):
        if "mean" in v: return (v.get("n"), v.get("mean"))
        for k in ("all", "main", "sched", "bot_sched"):
            if isinstance(v.get(k), dict) and "mean" in v[k]: return (v[k].get("n"), v[k]["mean"])
        return (v.get("n"), None)
    if isinstance(v, str):
        m = re.search(r"n\s*=?\s*(\d+)[^0-9-+]*?mean\s*([-+]?[0-9.]+)\s*%", v)
        if m: return (int(m.group(1)), float(m.group(2)) / 100)
        m = re.search(r"n\s*=?\s*(\d+)", v)
        if m: return (int(m.group(1)), None)
    return (None, None)
def entries(r):
    if isinstance(r, list):
        for x in r:
            if isinstance(x, dict): yield (str(x.get("key") or x.get("label")), x)
        return
    for k, v in r.items():
        if k == "families":
            if isinstance(v, list):
                for x in v:
                    if isinstance(x, dict): yield (str(x.get("key")), x)
            elif isinstance(v, dict):
                for kk, x in v.items():
                    if isinstance(x, dict): yield (kk, x)
        elif k == "main" and isinstance(v, dict):
            for kk, x in v.items():
                if isinstance(x, dict) and kk not in ("controls",): yield (kk, x)
        elif isinstance(v, dict) and k not in ("controls", "controls_extra", "calibration", "calibration_live", "method", "method_calibration", "numbers", "stats", "extra",
                                               "wider", "wider_groups", "variants", "hazard_trap", "postwindow", "related", "extra_buyers_reach", "loose_7fde822e",
                                               "fam4_hold_within_window", "fam4_long_hold", "fam4_crowd", "pricer_check_assigned", "fam2_capacity_decoded", "fam4_capacity_decoded",
                                               "trap_v2433", "F1-WIDE_detail", "F1_operator_rule"):
            yield (k, v)
rows = []
for d in sorted(glob.glob(S + "/analyse_*"), key=lambda x: int(x.rsplit("_", 1)[1])):
    n = int(d.rsplit("_", 1)[1]); p = None
    for fn in ("results_final.json", "results.json"):
        if os.path.exists(os.path.join(d, fn)): p = os.path.join(d, fn); break
    if not p: continue
    r = json.load(open(p))
    for label, x in entries(r):
        low = label.lower()
        if "control" in low or "operator-a" in low or "operator a" in low or label.startswith("0x3194e326") or "(operator a" in low or label in ("v2433_relay_trap",): continue
        if label.startswith("vbot-v2.433") or label == "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|2500|50|true": continue
        m = KRE.search(label); key = m.group(1) if m else label
        front = fr(x.get("front_rule", x.get("front", x.get("front_bot_sched"))))
        follow = fr(x.get("follow_rule", x.get("follow")))
        rows.append({"a": n, "label": label[:140], "key": key, "strict": bool(m and (m.group(1) == label or label.startswith(("F", "G")) and not any(w in label for w in ("WIDE", "LAUNCHER", "DEPLOYER", "DEP-", "SELECTOR", "CODEHASH")))),
                     "count": x.get("count"), "verdict": x.get("verdict"), "score": x.get("candidate_score"),
                     "front_n": front[0], "front_mean": front[1], "follow_n": follow[0], "follow_mean": follow[1],
                     "notes": str(x.get("notes", x.get("verdict_reason", x.get("why", ""))))[:400]})
# census numbers for strict keys
F = load_families(); P = load_pools()
keys = sorted({r["key"] for r in rows if r["key"] in F})
E = load_events(set(pid for k in keys for pid in F[k]["pids"]))
cen = {}
for k in keys:
    pids = F[k]["pids"]; real = 0; pulled = 0; offs = []
    for pid in pids:
        e = E.get(pid) or {}
        b0 = P[pid]["launch_block"]
        rb = [s for s in e.get("swaps", []) if s["a0"] <= -int(0.0002e18)]
        if rb: real += 1; offs.append(rb[0]["bn"] - b0)
        if e.get("pulls"): pulled += 1
    cen[k] = {"census_count": len(pids), "real_buy_pools": real, "real_buy_off_p50": st.median(offs) if offs else None, "pulled_3000": pulled,
              "per_day": round(len(pids) / 1.99938, 1)}
for r in rows:
    r.update(cen.get(r["key"], {}))
json.dump(rows, open(S + "/report/work/table.json", "w"), indent=1)
print(len(rows), "rows;", len({r['key'] for r in rows}), "distinct keys;", sum(1 for r in rows if r["key"] in F), "rows with strict census key;", len(keys), "distinct strict keys")
for r in rows:
    print(r["a"], "|", r["key"][:96], "|", r["count"], "|", r["verdict"], "|", r["front_n"], r["front_mean"] if r["front_mean"] is None else round(r["front_mean"], 4), "|", r["follow_n"], r["follow_mean"] if r["follow_mean"] is None else round(r["follow_mean"], 4), "|", r.get("real_buy_pools"), r.get("pulled_3000"))
