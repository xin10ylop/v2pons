import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); F = load_families(); LF = load_loose_families(); CF = load_code_families()
keys = ["SELECTOR:ec64ddcf|196|0|60|false", "CODEHASH:8ce82419af8f18d1be64b864a92a7313a543947b187c6c0a1c94a6feac23c407|bc9d39fd|*|0|200|false"]
print(list(LF.keys())[:5]); print(list(CF.keys())[:5])
for k in ["ec64ddcf|196|0|60|false"]:
    r = LF.get(k); print(k, {a: b for a, b in r.items() if a != "pids"} if r else None)
for k in CF:
    if k.startswith("8ce82419"):
        r = CF[k]; print(k, {a: b for a, b in r.items() if a != "pids"})
