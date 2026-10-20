"""Pick the active families (lc#tok with >= 10 angle-B launches and a first real buy in >= 5% of them, plus the contract-creation
launches of tok 65daaea0), load their events once from cache/ev.jsonl and save them (events.pkl: pool -> {kind, lb, ev})."""
import sys, pickle, time
from common import *
sys.path.insert(0, CEN); from load import load_events
F = json.load(open(os.path.join(D, "famstats.json")))
act = {s["key"] for s in F if s["g"] == "lt" and s["frb_share"] >= 0.05}
rows = load_rows()
fam = {}
for r in rows:
    k = key_of(r, "lt")
    if k in act: fam[r["pool"]] = k
    elif r["launch"]["to"] is None and r["fam"]["tok"].startswith("65daaea0"): fam[r["pool"]] = "create#65daaea0"
print("families", len(act) + 1, "pools", len(fam))
t = time.time(); E = load_events(set(fam)); print("events loaded", len(E), round(time.time() - t), "s")
pickle.dump({"fam": fam, "ev": E}, open(os.path.join(D, "events.pkl"), "wb"))
