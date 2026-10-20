"""analyse_25 dumper_link: does each 7fde822e launch name the dump wallet 0x94dddbb5 in its calldata (the 25% supply recipient), per launch
contract and deployer; and the F4 launches' calldata for the deployer (the 20% recipient). Census data only. Writes dumper_link.json."""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common25 import *  # noqa
P = load_pools(); T = load_txs()
K = json.load(open(os.path.join(HERE, "keys.json")))
F = load_families()
D = "94dddbb54535ee3515b3b9e10be5a6569c586324"
out = {}
c = collections.Counter()
for p in P.values():
    if p["selector"] != "7fde822e": continue
    t = T[p["launch_tx"]]; inp = t.get("input") or t["input512"]
    c[(p["launch_from"][:10], D in inp)] += 1
out["7fde822e_calldata_names_0x94dddbb5 (deployer, yes/no)"] = {"%s %s" % k: v for k, v in c.items()}
for i, k in enumerate(K):
    t = T[P[F[k]["pids"][0]]["launch_tx"]]; inp = t.get("input") or t["input512"]
    words = [inp[10 + 64 * j: 10 + 64 * (j + 1)] for j in range((len(inp) - 10) // 64)]
    txt = bytes.fromhex("".join(w for w in words if not w.startswith("0000"))).decode("latin1")
    out["F%d" % (i + 1)] = {"names_0x94dddbb5": D in inp, "head_words": words[:8], "ascii": "".join(ch if 32 <= ord(ch) < 127 else "." for ch in txt)[:300]}
json.dump(out, open(os.path.join(HERE, "dumper_link.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
