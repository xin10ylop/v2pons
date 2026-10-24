#!/usr/bin/env python3
"""dammchain.py CENSUS.json OUT.json [MIN_POOLS] [MIN_SOL]: links DAMM v2 creators into operator chains through their SOL (public RPC,
paced; read-only).

The big creators (MIN_POOLS+ pools of MIN_SOL+ SOL; defaults 10 and 50) have 5000+ signatures, so their first funder cannot be walked
back on the public RPC. Their end is cheap to read instead: a creator ends by sending its SOL (100+ SOL) to a single-use relay wallet
whose one transaction forwards all of it to the next creator. Per creator: its newest transactions' outgoing System transfers of
10+ SOL; a destination that is a creator links directly, one with at most 3 signatures (a relay) is followed one hop. Linked
creators are one chain (one operator: the funder line of linescan.py, via relays). Writes the links and the chains."""
import json, sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dammstate import rpc


def outgoing(addr, limit=5, min_sol=10.0):
    out = []
    for q in rpc("getSignaturesForAddress", [addr, {"limit": limit}]):
        if q["err"]:
            continue
        tx = rpc("getTransaction", [q["signature"], {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])
        for ins in tx["transaction"]["message"]["instructions"] + [i for g in tx["meta"].get("innerInstructions") or [] for i in g["instructions"]]:
            pi = ins.get("parsed") if isinstance(ins.get("parsed"), dict) else None
            if pi and pi.get("type") == "transfer" and pi["info"].get("source") == addr and pi["info"].get("lamports", 0) >= min_sol * 1e9:
                out.append((pi["info"]["destination"], pi["info"]["lamports"] / 1e9, q["blockTime"]))
        if out:
            break
    return out


def main(census, out, min_pools, min_sol):
    pools = json.load(open(census))["pools"]
    allc = collections.defaultdict(list)
    for p in pools:
        if p["sol"] >= min_sol:
            allc[p["creator"]].append(p)
    big = [c for c, v in sorted(allc.items(), key=lambda kv: -len(kv[1])) if len(v) >= min_pools]
    res = json.load(open(out)).get("links", {}) if os.path.exists(out) else {}
    print(f"{len(big)} creators with {min_pools}+ pools of {min_sol}+ SOL", flush=True)
    for c in big:
        if c in res:
            continue
        link = {"next": None, "via": None, "sol": None}
        try:
            for dst, sol, t in outgoing(c):
                if dst in allc:
                    link.update(next=dst, sol=sol, t=t); break
                n = rpc("getSignaturesForAddress", [dst, {"limit": 4}])
                if len(n) <= 3:
                    for d2, s2, t2 in outgoing(dst, limit=3):
                        link.update(via=dst, sol=sol, t=t, next=d2 if d2 in allc else None, next_any=d2)
                        break
                    break
                link.update(sink=dst, sol=sol, t=t); break
        except Exception as e:
            link["error"] = str(e)[:80]
        res[c] = link
        json.dump({"links": res}, open(out, "w"))
        print(f"  {c[:10]} ({len(allc[c])} pools) -> {(link.get('via') or '')[:8]} -> {(link.get('next') or link.get('next_any') or link.get('sink') or '-')[:10]} "
              f"{link.get('sol')}", flush=True)
    parent = {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for c, l in res.items():
        if l.get("next"):
            parent[find(l["next"])] = find(c)
    chains = collections.defaultdict(list)
    for c in set(res) | {l["next"] for l in res.values() if l.get("next")}:
        chains[find(c)].append(c)
    ch = sorted(([sorted(v, key=lambda c: min(p["t"] for p in allc[c])) for v in chains.values() if len(v) >= 2]), key=lambda v: -sum(len(allc[c]) for c in v))
    json.dump({"links": res, "chains": ch}, open(out, "w"))
    for v in ch:
        print(f"chain of {len(v)} creators, {sum(len(allc[c]) for c in v)} pools: " + " -> ".join(f"{c[:8]}({len(allc[c])})" for c in v), flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 10, float(sys.argv[4]) if len(sys.argv) > 4 else 50)
