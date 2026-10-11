# The engine's own decode_launch / front_mismatch / front_fingerprint on the 889 census v3.0 launches, with the v3.0 FRONT_* settings,
# under FEE_MAX_PPM unset (default 9999) or 10000 (argv[1]). Read-only: imports src/flip_engine.py with a scratch LOG_PATH.
import sys, os, collections
M = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/report/merge"
os.environ["LOG_PATH"] = M + "/fee_check.jsonl"
os.environ.pop("FEE_MAX_PPM", None)
if len(sys.argv) > 1: os.environ["FEE_MAX_PPM"] = sys.argv[1]
os.environ.update({"FRONT_VALUE_WEI": "3000000000000000000", "FRONT_FEE": "10000", "FRONT_TICK_SPACING": "200",
                   "FRONT_SQRT_P": "679394651928963067279918579724198", "FRONT_LIQ": "25725498245903809899643", "FRONT_PIN": "1"})
sys.path.insert(0, "/home/user/v2pons/src")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
import flip_engine as E
from load import load_pools, load_txs, load_families
P = load_pools(); T = load_txs(); F = load_families()
k = "0x58daec3116aae6d93017baaea7749052e8a04fa7|ac9650d8|1444|10000|200|true"
out = collections.Counter()
for pid in F[k]["pids"]:
    p = P[pid]
    if p["launch_value_wei"] != E.FRONT_VALUE_WEI: continue
    d = E.decode_launch(bytes.fromhex(T[p["launch_tx"]]["input"][2:]))
    if d is None: out["undecoded"] += 1; continue
    t0 = E.tick_at(d["sqrt_p"]); liq = d["mint_liq"] if d["lo"] <= t0 < d["hi"] else 0
    out[(E.front_mismatch(d, liq), tuple(E.front_fingerprint(d)))] += 1
print("FEE_MAX_PPM", E.FEE_MAX_PPM, dict(out))
