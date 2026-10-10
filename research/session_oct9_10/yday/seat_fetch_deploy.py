"""For each copy launch: the launcher copy's creation (a tx with to=null in L-40..L-1 whose receipt's contractAddress is the copy),
and the copy's code at 'latest' (the public RPC keeps no historical state, so eth_getCode at the launch block errors)."""
import pickle, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chain import batch, rpc
HERE = os.path.dirname(os.path.abspath(__file__)); CACHE = os.path.join(HERE, "cache_seat.pkl")
d = pickle.load(open(CACHE, "rb"))
if "code_latest" not in d:
    d["code_latest"] = batch([("eth_getCode", [p["to"], "latest"]) for p in d["copies"]])
    pickle.dump(d, open(CACHE, "wb"))
d.setdefault("deploy", {})
for p in d["copies"]:
    if p["pid"] in d["deploy"]: continue
    L = p["block"]; found = None
    blks = batch([("eth_getBlockByNumber", [hex(L - k), True]) for k in range(1, 41)])
    cands = [(int(b["number"], 16), t) for b in blks for t in b["transactions"] if t["to"] is None and t["from"].lower() == p["from"].lower()]
    if not cands:
        cands = [(int(b["number"], 16), t) for b in blks for t in b["transactions"] if t["to"] is None]
    recs = batch([("eth_getTransactionReceipt", [t["hash"]]) for _, t in cands]) if cands else []
    for (bn, t), r in zip(cands, recs):
        if r and (r.get("contractAddress") or "").lower() == p["to"].lower():
            found = {"block": bn, "tx": t["hash"], "from": t["from"], "status": r["status"], "init_len": len(t["input"]) // 2 - 1}
    d["deploy"][p["pid"]] = found
    print(L, found and (found["block"] - L), file=sys.stderr)
pickle.dump(d, open(CACHE, "wb"))
