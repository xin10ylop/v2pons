"""Skeptic f2276/100: where the creators' pulled ETH goes (self-loop to the app router = the operator's own crowd, or away = a rug of the
app's users). For the 8 pulled census pools with the most ETH at the pull: the launcher's balance and nonce now; the blocks pull..pull+N
with full transactions, every tx from the launcher after its pull (to, value, selector)."""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc, batch
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "data")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "census"))
from load import load_pools, load_events, load_txs
a6 = json.load(open(os.path.join(HERE, "a6_trap.json")))
P = load_pools(); T = load_txs()
top = sorted([r for r in a6["rows"] if r.get("pull") is not None], key=lambda r: -r["eth_at_pull"])[:8]
E = load_events(set(r["pid"] for r in top))
st = batch([(m, [P[r["pid"]]["launch_from"], "latest"]) for r in top for m in ("eth_getBalance", "eth_getTransactionCount")])
out = []
for i, r in enumerate(top):
    lf = P[r["pid"]]["launch_from"]; pull = E[r["pid"]]["pulls"][0]; pt = T[pull["tx"]]
    row = {"pid": r["pid"][:10], "launcher": lf, "eth_at_pull": r["eth_at_pull"], "pull_bn": pull["bn"], "pull_nonce": pt["nonce"],
           "bal_now": int(st[2 * i], 16) / 1e18, "nonce_now": int(st[2 * i + 1], 16)}
    out.append(row); print(row, flush=True)
cp = os.path.join(D, "after_pull_blocks.json")
C = json.load(open(cp)) if os.path.exists(cp) else {}
for row in out:
    if row["nonce_now"] <= row["pull_nonce"] + 1: row["after"] = "no tx after the pull"; continue
    found = []
    a = row["pull_bn"]
    for chunk in range(0, 6):                      # up to 3,000 blocks after the pull, 500 at a time
        lo = a + chunk * 500; hi = lo + 500
        need = [b for b in range(lo, hi) if str(b) not in C]
        for j in range(0, len(need), 50):
            res = batch([("eth_getBlockByNumber", [hex(b), True]) for b in need[j:j + 50]])
            for b, blk in zip(need[j:j + 50], res):
                C[str(b)] = [[t["from"], t["to"], int(t["value"], 16), t["input"][:10], t["hash"], int(t["nonce"], 16)] for t in (blk or {}).get("transactions", [])
                             if t["from"] in [o["launcher"] for o in out]]
            time.sleep(0.2)
        for b in range(lo, hi):
            for tx in C.get(str(b), []):
                if tx[0] == row["launcher"]: found.append([b - a] + tx[1:])
        if found and len(found) >= row["nonce_now"] - row["pull_nonce"] - 1: break
    json.dump(C, open(cp, "w"))
    row["after"] = found; print(row["pid"], "after the pull:", found, flush=True)
json.dump(out, open(os.path.join(HERE, "f3_money.json"), "w"), indent=1)
