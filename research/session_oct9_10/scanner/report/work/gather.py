# Walk every analyst's results file and collect each dict that carries a verdict, with the path it came from.
import json, os, glob, sys
S = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner"
out = []
def walk(o, path, fn):
    if isinstance(o, dict):
        if "verdict" in o:
            out.append({"file": fn, "path": path, "obj": o})
        for k, v in o.items():
            if k.startswith("_"): continue
            walk(v, path + [str(k)], fn)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            walk(v, path + [i], fn)
for d in sorted(glob.glob(S + "/analyse_*"), key=lambda x: int(x.rsplit("_", 1)[1])):
    for fn in ["results_final.json", "results.json"]:
        p = os.path.join(d, fn)
        if os.path.exists(p):
            try: r = json.load(open(p))
            except Exception as e: print("ERR", p, e); continue
            walk(r, [], p.replace(S + "/", ""))
            break
    else:
        print("NO RESULTS", d, os.listdir(d))
json.dump(out, open(S + "/report/work/verdicts_raw.json", "w"), indent=0, default=str)
for x in out:
    o = x["obj"]
    key = o.get("key") or (x["path"][-1] if x["path"] else "")
    print(x["file"], "|", "/".join(map(str, x["path"]))[:90], "|", str(key)[:90], "|", o.get("count"), "|", o.get("verdict"), "|", o.get("candidate_score", o.get("score")))
