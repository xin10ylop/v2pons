import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
F = load_families()
KEYS = ["0x16cf6788b762ee8969744586ed16fc5705140dd7|4101659e|388|0|200|false",
"0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2020|3000|60|false",
"0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|2020|600000|6000|true",
"0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|500|1|false"]
for k in KEYS:
    r = dict(F[k]); r["pids"] = len(r["pids"])
    print(k); print(json.dumps(r, indent=None, default=str)[:3000]); print()
