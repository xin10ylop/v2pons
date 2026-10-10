import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
F = load_families()
K1 = "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|100|1|true"
K2 = "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|500|10|true"
for k in (K1, K2):
    r = dict(F[k]); 
    print(k, json.dumps({x: r[x] for x in r if x != 'pids'})[:3000])
    print(r['pids'])
