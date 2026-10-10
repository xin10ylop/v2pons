"""where else do these launchers / deployers appear in the census (other strict keys, the loose 7fde822e family)"""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from px import *  # noqa
P = load_pools(); LF = load_loose_families(); TF = load_to_families(); F = load_families()
FAMS = ["0x575b952fd3c079b3e72f4cd45f546edd2486d8fa|7fde822e|804|10000|200|true",
        "0x5bd1fbe78a78fe8236fa00cf48fbeba74ae34661|a80ac0c2|1156|0|200|false",
        "0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|3000|60|true",
        "0xa0ce0291c181f800e7a5096b433685c37cfbf4df|617ac5de|676|8388608|200|false"]
out = {}
for k in FAMS:
    f = F[k]; to = f["launch_to"]; deps = set(P[x]["launch_from"] for x in f["pids"])
    same_to = [p for p in P.values() if p["launch_to"] == to and p["family"] != k]
    same_dep = [p for p in P.values() if p["launch_from"] in deps and p["family"] != k]
    sel_only = [p for p in P.values() if p["selector"] == f["selector"] and p["family"] != k]
    def agg(ps):
        fams = collections.Counter(p["family"] for p in ps)
        return {"pools": len(ps), "families": fams.most_common(6), "known": collections.Counter(p["known"] for p in ps).most_common(),
                "with_real_first_buy": sum(1 for p in ps if p["first_buy_eth"] and p["first_buy_eth"] >= 0.0002),
                "pulled": sum(1 for p in ps if p["first_pull_rel"] is not None),
                "first_buy_rel_p50": q([p["first_buy_rel"] for p in ps if p["first_buy_rel"] is not None]),
                "first_pull_rel": q([p["first_pull_rel"] for p in ps if p["first_pull_rel"] is not None])}
    out[k] = {"deployers": sorted(deps), "same_launch_to_other_keys": agg(same_to), "same_deployers_other_keys": agg(same_dep),
              "same_selector_other_keys": agg(sel_only)}
    print("=====", k)
    for a, b in out[k].items(): print(" ", a, json.dumps(b)[:900])
for lk, v in LF.items():
    if lk.startswith("7fde822e"): print("loose", lk, json.dumps(v)[:400])
json.dump(out, open(os.path.join(HERE, "related.json"), "w"), indent=1)
