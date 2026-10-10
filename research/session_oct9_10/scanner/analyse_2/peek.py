import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
F = load_families()
keys = ["0x58daec3116aae6d93017baaea7749052e8a04fa7|f7020405|196|10000|200|false",
"0xfcd182416ca91a9e88e9fe44e4f78ea3cb2c15c7|6fe958d8|68|30000|200|false",
"0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|790000|60|true",
"0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|836798|9303|true"]
for k in keys:
    f = dict(F[k]); f["pids"] = f["pids"][:3]
    print(k); print(json.dumps(f, indent=None)[:3000]); print()
