"""Step 14: where the launcher's ETH goes after the pull (its next transaction) and where its funder got the ETH (the funder's
previous incoming transfer), for the launches sampled in s13. Full-block scans, read-only."""
import sys
from common import *
pools = {p["L"]: p for p in load_pools()}
launchers = {p["launcher"]: p["L"] for p in pools.values()}
d = jload("s13_launcher.json")
def scan(a, b, pred, stop_first=True, step=200, reverse=False):
    rng = list(range(a, b + 1, step))
    if reverse: rng = rng[::-1]
    hits = []
    for s in rng:
        e = min(b, s + step - 1)
        blocks = rpc.batch("eth_getBlockByNumber", [[hex(x), True] for x in range(s, e + 1)], n=25)
        for blk in blocks:
            for t in blk["transactions"]:
                if pred(t): hits.append(dict(bn=int(t["blockNumber"], 16), h=t["hash"], f=t["from"].lower(), to=(t.get("to") or "").lower(),
                                            n=int(t["nonce"], 16), v=int(t["value"], 16), sel=t["input"][:10]))
        if hits and stop_first: return hits
    return hits
out = []
for x in d[:8]:
    w = x["launcher"]; p = pools[x["L"]]
    fund = [t for t in x["txs"] if t["to"] == w and t["v"] > 0][0]
    funder = fund["f"]
    nf = int(rpc.call("eth_getTransactionCount", [funder, "latest"]), 16); bf = int(rpc.call("eth_getBalance", [funder, "latest"]), 16) / 1e18
    print(f"=== L {x['L']} launcher {w[:10]} funded {fund['v']/1e18:.4f} by {funder} (nonce now {nf}, balance {bf:.4f}); funding tx nonce {fund['n']}")
    # the funder's previous incoming transfer (up to 3,000 blocks back)
    prev = scan(fund["bn"] - 3000, fund["bn"], lambda t: (t.get("to") or "").lower() == funder and int(t["value"], 16) > 0, stop_first=False, reverse=True)
    for t in sorted(prev, key=lambda t: t["bn"])[-3:]:
        lab = "launcher of L %d" % launchers[t["f"]] if t["f"] in launchers else ""
        print(f"   funder got {t['v']/1e18:.4f} at L{t['bn']-x['L']:+d} from {t['f']} (nonce {t['n']}) {lab}")
    # the launcher's transaction after the pull
    nxt = scan(p["pull_bn"] + 1, p["pull_bn"] + 4000, lambda t: t["from"].lower() == w) if "pull_bn" in p else []
    for t in nxt[:2]:
        lab = "launcher of L %d" % launchers[t["to"]] if t["to"] in launchers else ""
        print(f"   after the pull: L{t['bn']-x['L']:+d} (pull+{t['bn']-p['pull_bn']}) nonce {t['n']} to {t['to']} value {t['v']/1e18:.4f} sel {t['sel']} {lab}")
    out.append(dict(L=x["L"], launcher=w, funder=funder, funder_nonce=nf, funder_prev=prev[-3:], after_pull=nxt[:2]))
    sys.stdout.flush()
jdump(out, "s14_chain.json")
print(rpc.STATS)
