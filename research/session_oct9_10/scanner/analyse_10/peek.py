import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
F = load_families()
KEYS = ["0x258dd351af960bc487532c0108d3f90e8d115369|7fde822e|804|10000|200|true",
"0x2a53386daf0bf3eedd9e715d162649764358c7b5|3d9ab7c9|292|0|200|false",
"0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2020|200000|2000|true",
"0x78ba8b21e8adbbc84f2e11f0e92c6f2299b78281|7fde822e|804|10000|200|true"]
for k in KEYS:
    r = F[k]
    print("=====", k)
    print(json.dumps({a: b for a, b in r.items() if a != "pids"}, default=str)[:3000])
