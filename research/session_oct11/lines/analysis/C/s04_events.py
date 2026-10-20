"""Load raw events (one pass over cache/ev.jsonl) for every pool of the studied families (V2/V3 and the v4 rows of the mixed
token families) -> C/ev.pkl {pool: {"kind","lb","ev_to","ev"}}"""
import sys, os, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/census")
from load import load_events
from fams import *
R = load_rows(); FP = fam_pools(R, v23_only=False)
ids = set(r["pool"] for rs in FP.values() for r in rs)
print("pools", len(ids))
E = load_events(ids)
print("loaded", len(E), sum(len(o["ev"]) for o in E.values()))
pickle.dump(E, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ev.pkl"), "wb"))
