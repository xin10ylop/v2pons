"""Per-pool hook tax of family 0x5bd1fbe7 (hook 0x75a54357): the launch receipt's hook event 0xcf68bf26 carries the tax rate (word 2, ppm),
checked against the 0x3c150631 events of the swaps (hookfee.json). Writes hooktax.json pid -> ppm."""
import sys, json, os
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from load import *
from chain import batch
HERE = os.path.dirname(os.path.abspath(__file__))
K = json.load(open(os.path.join(HERE, "keys.json")))
P = load_pools(); F = load_families()
HOOK = "0x75a54357d9c78a2db19004a5fdc76c50f9242aec"
pids = F[K[2]]["pids"]
CACHE = os.path.join(HERE, "launch_rcpts.json")
R = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
want = [P[p]["launch_tx"] for p in pids if P[p]["launch_tx"] not in R]
if want: R.update(zip(want, batch([("eth_getTransactionReceipt", [h]) for h in want]))); json.dump(R, open(CACHE, "w"))
W = lambda d, i: int(d[2 + 64*i: 2 + 64*(i+1)], 16)
out = {}
for p in pids:
    r = R[P[p]["launch_tx"]]
    ev = [l for l in r["logs"] if l["address"].lower() == HOOK and l["topics"][0][:10] == "0xcf68bf26"]
    words = [W(ev[0]["data"], i) for i in range((len(ev[0]["data"]) - 2) // 64)] if ev else None
    out[p] = {"tax_ppm": words[2] if words else None, "word1": words[1] if words else None, "topics": ev[0]["topics"] if ev else None,
              "status": r["status"], "gasUsed": int(r["gasUsed"], 16), "n_logs": len(r["logs"])}
    print(p[:12], out[p]["tax_ppm"], out[p]["word1"], [t[:20] for t in (out[p]["topics"] or [])], r["status"])
json.dump(out, open(os.path.join(HERE, "hooktax.json"), "w"), indent=1)
