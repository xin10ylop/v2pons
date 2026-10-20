"""Synthesizer step 1: the 27 skeptic verdicts (9 candidates x replay/reaction/execution), read from the workflow journal (the task text
carried a truncated copy). Writes verdicts_all.json and the tally (s01_verdicts.out). Read-only on the journal."""
import json, os, collections as C
HERE = os.path.dirname(os.path.abspath(__file__))
J = "/root/.claude/projects/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/subagents/workflows/wf_891776dc-e3d/journal.jsonl"
lab = {}; out = []
for l in open(J):
    d = json.loads(l)
    if d["type"] == "started": lab[d["key"]] = d["label"]
    if d["type"] == "result" and isinstance(d.get("result"), dict) and "lens" in d["result"]:
        out.append({"label": lab[d["key"]], **d["result"]})
json.dump(out, open(os.path.join(HERE, "verdicts_all.json"), "w"), indent=1)
T = C.OrderedDict()
for o in out:
    _, lens, cand = o["label"].split(":", 2)
    T.setdefault(cand, {})[lens] = o["refuted"]
L = [f"{len(out)} verdicts, {len(T)} candidates"]
for cand, v in T.items():
    nref = sum(v.values())
    L.append(f"{'SURVIVES' if nref <= 1 else 'REFUTED '} refuted-by {nref}/3  replay {'R' if v.get('replay') else '-'} reaction {'R' if v.get('reaction') else '-'} "
             f"execution {'R' if v.get('execution') else '-'}  | {cand[:95]}")
L.append(f"lens refutation counts: " + str(C.Counter(l for v in T.values() for l, x in v.items() if x)))
open(os.path.join(HERE, "s01_verdicts.out"), "w").write("\n".join(L) + "\n"); print("\n".join(L))
