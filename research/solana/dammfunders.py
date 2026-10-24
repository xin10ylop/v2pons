#!/usr/bin/env python3
"""dammfunders.py CENSUS.json OUT.json [MIN_POOLS] [MIN_SOL]: the funder of each DAMM v2 creator with MIN_POOLS+ pools of MIN_SOL+
SOL (default 20 pools, 50 SOL), on the public RPC (paced; read-only). These creators have 1000+ signatures, so the walk pages
getSignaturesForAddress back to the wallet's first transaction (at most 5 pages: 5000 signatures) and takes the sender of the first SOL into it
(census.py's rule). Creators sharing a funder are one operator."""
import json, sys, collections, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dammstate import rpc


def first_funder(c, max_pages=5):
    before, last, n = None, None, 0
    for _ in range(max_pages):
        p = {"limit": 1000}
        if before:
            p["before"] = before
        s = rpc("getSignaturesForAddress", [c, p])
        n += len(s)
        if s:
            last = s[-1]; before = last["signature"]
        if len(s) < 1000:
            break
    else:
        return {"n": n, "complete": False, "funder": None}
    out = {"n": n, "complete": True, "funder": None, "first_t": last.get("blockTime") if last else None}
    if last:
        tx = rpc("getTransaction", [last["signature"], {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])
        for ins in tx["transaction"]["message"]["instructions"] + [i for g in tx["meta"].get("innerInstructions") or [] for i in g["instructions"]]:
            pi = ins.get("parsed") if isinstance(ins.get("parsed"), dict) else None
            if pi and pi.get("type") == "transfer" and pi.get("info", {}).get("destination") == c and "lamports" in pi["info"]:
                out.update(funder=pi["info"]["source"], funded_sol=pi["info"]["lamports"] / 1e9); break
    return out


def main(census, out, min_pools, min_sol):
    pools = json.load(open(census))["pools"]
    cnt = collections.Counter(p["creator"] for p in pools if p["sol"] >= min_sol)
    cs = [c for c, k in cnt.most_common() if k >= min_pools]
    res = json.load(open(out)) if os.path.exists(out) else {}
    print(f"{len(cs)} creators with {min_pools}+ pools of {min_sol}+ SOL", flush=True)
    for c in cs:
        if c in res:
            continue
        try:
            res[c] = first_funder(c)
        except Exception as e:
            print(f"  {c[:8]}: {str(e)[:60]}", flush=True); continue
        json.dump(res, open(out, "w"))
        print(f"  {c[:10]} pools {cnt[c]} sigs {res[c]['n']} funder {res[c].get('funder')}", flush=True)
    by = collections.defaultdict(list)
    for c, v in res.items():
        if v.get("funder"):
            by[v["funder"]].append(c)
    print("funders shared:", {f[:10]: len(v) for f, v in by.items() if len(v) >= 2})


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 20, float(sys.argv[4]) if len(sys.argv) > 4 else 50)
