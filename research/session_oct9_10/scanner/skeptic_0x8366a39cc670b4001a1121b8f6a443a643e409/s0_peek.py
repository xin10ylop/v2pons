import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
KEY = "0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|500|1|true"
F = load_families(); f = F[KEY]
print({k: v for k, v in f.items() if k != "pids"})
P = load_pools()
pids = f["pids"]
p = P[pids[0]]
print(json.dumps(p, indent=0)[:3000])
E = load_events(set(pids[:2]))
e = E[pids[0]]
print("adds", e["adds"][:3]); print("pulls", e["pulls"][:2]); print("nswaps", len(e["swaps"]))
for s in e["swaps"][:12]: print(s)
