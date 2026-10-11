"""Stream pools.jsonl once; keep every V2/V3 row and the v4 rows of the mixed families named in the task. -> C/v23.pkl"""
import json, pickle, os, sys
CEN = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/census"
OUT = os.path.dirname(os.path.abspath(__file__))
MIXED_TOK = ("0f34e3b5", "97c7ba1b", "d4e7eae4", "70adce63", "203caacb")
rows = {}
with open(os.path.join(CEN, "pools.jsonl")) as f:
    for line in f:
        r = json.loads(line)
        if r["dex"] in ("v2a", "v2b", "v3") or (r["fam"]["tok"] or "")[:8] in MIXED_TOK:
            rows[r["pool"]] = r
pickle.dump(rows, open(os.path.join(OUT, "v23.pkl"), "wb"))
from collections import Counter
print(len(rows), Counter(r["dex"] for r in rows.values()))
