# List every family entry each analyst reports on (by key), whether it is a control, and the raw front/follow/verdict fields (truncated).
import json, os, glob, re
S = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner"
KEYRE = re.compile(r"(0x[0-9a-f]{40}|create|LAUNCHER:|CODEHASH:|SELECTOR:)")
rows = []
def entries(r):
    # yield (label, dict)
    if isinstance(r, list):
        for x in r:
            if isinstance(x, dict): yield (x.get("key") or x.get("label") or "?", x)
        return
    fam = r.get("families")
    if isinstance(fam, list):
        for x in fam:
            if isinstance(x, dict): yield (x.get("key") or "?", x)
    elif isinstance(fam, dict):
        for k, x in fam.items():
            if isinstance(x, dict): yield (k, x)
    for k, x in r.items():
        if k == "families": continue
        if isinstance(x, dict) and ("|" in k or k.lower().startswith(("control", "f1", "f2", "f3", "f4", "g1", "g2", "g3", "g4", "opc", "06cb", "dep-", "wide", "f1f2", "f234", "f34", "f1-", "f2-", "f3-", "f4-"))):
            yield (k, x)
for d in sorted(glob.glob(S + "/analyse_*"), key=lambda x: int(x.rsplit("_", 1)[1])):
    n = int(d.rsplit("_", 1)[1])
    p = None
    for fn in ["results_final.json", "results.json"]:
        if os.path.exists(os.path.join(d, fn)): p = os.path.join(d, fn); break
    if not p: rows.append({"a": n, "key": None, "note": "no results file"}); continue
    r = json.load(open(p))
    for k, x in entries(r):
        rows.append({"a": n, "file": os.path.basename(p), "key": k, "count": x.get("count"),
                     "verdict": x.get("verdict"), "score": x.get("candidate_score"),
                     "front": str(x.get("front_rule", x.get("front")))[:600], "follow": str(x.get("follow_rule", x.get("follow")))[:400],
                     "notes": str(x.get("notes", x.get("front_why", "")))[:600]})
json.dump(rows, open(S + "/report/work/assigned.json", "w"), indent=1)
for r in rows: print(r["a"], "|", str(r["key"])[:110], "|", r.get("count"), "|", r.get("verdict"))
print(len(rows))
