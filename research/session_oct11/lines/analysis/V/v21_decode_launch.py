"""Run the engine's own decode_launch (src/flip_engine.py, imported read-only) on every C-1 core launch whose full calldata the census
cached; check the decoded pool id against the census pool; tabulate the shape constants. Also the multicall's inner calls."""
import os
os.environ.setdefault("LOG_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "engine_import.jsonl"))
from common import *
import flip_engine as fe
rows = [r for r in jl(os.path.join(V, "c1_rows.jsonl")) if r["quote"] == "ETH"]
T = json.load(open(os.path.join(V, "c1_txs.json")))
ok = bad = nofull = 0; shapes = C.Counter(); inner = C.Counter(); tick_off = C.Counter()
for r in rows:
    t = T.get(r["launch_tx"])
    if not t or "input" not in t: nofull += 1; continue
    b = bytes.fromhex(t["input"][2:])
    d = fe.decode_launch(b)
    if d is None or d["pid"] != r["pool"]: bad += 1; continue
    ok += 1
    shapes[(d["c0"] == "0" * 40, d["hooks"] == "0" * 40, d["fee"], d["tick_spacing"], d["sqrt_p"], d["lo"], d["hi"], d["mint_liq"])] += 1
    t0 = fe.tick_at(d["sqrt_p"]); tick_off[(d["lo"] - t0, d["hi"] - t0)] += 1
    arr = 4 + fe._u(b, 4); n = fe._u(b, arr)
    inner[tuple(b[fe._dyn(b, arr + 32, arr + 32 + 32 * i)[0]:][:4].hex() for i in range(n))] += 1
print(f"C-1 core launches {len(rows)}: full calldata cached {len(rows) - nofull}; decode_launch ok (pid = census pool) {ok}; failed/mismatch {bad}")
print("multicall inner calls:", inner.most_common(3))
print("decoded shapes (ETH c0, no hook, fee, tick spacing, sqrtP, tickLower, tickUpper, mint liquidity): count")
for k, v in shapes.most_common(10): print("  ", v, k)
print("tick range relative to tick_at(sqrtP):", tick_off.most_common(5))
