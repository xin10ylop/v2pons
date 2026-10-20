"""Pick out of the census tx caches every transaction of the C-1 rows (launch txs and every swap/pull tx in their events) -> c1_txs.json."""
import pickle, re
from common import *
rows = [r for r in jl(os.path.join(V, "c1_rows.jsonl"))]
E = pickle.load(open(os.path.join(V, "ev.pkl"), "rb"))
want = set()
for r in rows:
    want.add(r["launch_tx"])
    for e in E[r["pool"]]["ev"]: want.add(e[12] if e[0] == "s" else e[10])
out = {}
for n in ("tx_launch.jsonl", "tx_swap.jsonl", "tx_swap_b.jsonl"):
    with open(os.path.join(CEN, "cache", n)) as f:
        for line in f:
            m = re.match(r'\{"hash": ?"(0x[0-9a-f]{64})"', line)
            if m and m.group(1) not in want: continue
            try: x = json.loads(line)
            except Exception: continue
            if x["hash"] not in want: continue
            old = out.get(x["hash"])
            if old is not None and "input" in old and "input" not in x: old.update({k: v for k, v in x.items() if k not in old}); continue
            out[x["hash"]] = x
json.dump(out, open(os.path.join(V, "c1_txs.json"), "w"))
print("wanted", len(want), "found", len(out))
k = next(iter(out)); print({a: (b if not isinstance(b, str) or len(b) < 80 else b[:80] + "...") for a, b in out[k].items()})
