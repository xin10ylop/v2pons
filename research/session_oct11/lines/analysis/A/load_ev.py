"""Load the raw events of every non-vbot pool of the lc family (plus the vbot pools for reference baselines) once; pickle to A/ev.pkl."""
import json, os, sys, pickle
CEN = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/census"
sys.path.insert(0, CEN); from load import load_events
OUT = os.path.dirname(os.path.abspath(__file__))
VB = {"vbot-v2.433", "vbot-v3.0", "vbot-v5.0"}; VBV = {2433328500000000000, 2433300000000000000, 3 * 10**18, 5 * 10**18}
rows = [json.loads(l) for l in open(os.path.join(OUT, "lc_rows.jsonl"))]
keep = {r["pool"] for r in rows if not r["quote_pair"] and r["known_fp"] not in VB and r["launch"]["value_wei"] not in VBV}
print("non-vbot pools", len(keep))
E = load_events(keep)
print("with events", len(E))
pickle.dump(E, open(os.path.join(OUT, "ev.pkl"), "wb"), protocol=5)
