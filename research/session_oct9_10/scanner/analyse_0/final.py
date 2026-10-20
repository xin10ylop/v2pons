"""Assemble results_final.json (the per-family answer) from the outputs of analyse.py, deep_vbot.py, deep_crowd.py, slices_crowd.py,
fine_grid.py, cond_crowd.py, trap_extra.py, senders.py, calib_opA.py, calib_v2433_live.py and validate.py."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
L = lambda n: json.load(open(os.path.join(HERE, n)))
out = {"inputs": {k: L(k) for k in ("results.json", "deep_vbot.json", "deep_crowd.json", "slices_crowd.json", "fine_grid.json", "cond_crowd.json",
                                     "trap_extra.json", "senders.json", "calib_opA.json", "calib_v2433_live.json", "validate.json")}}
out["inputs"]["calib_opA.json"] = out["inputs"]["calib_opA.json"]["summary"]
out["families"] = L("families_out.json")
json.dump(out, open(os.path.join(HERE, "results_final.json"), "w"), indent=1)
print("written", os.path.join(HERE, "results_final.json"), len(out["families"]))
