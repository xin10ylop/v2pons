#!/usr/bin/env python3
"""dammpull.py CENSUS.json OUT.json: for the DAMM v2 pools whose position history dammstate.py read, the pull itself (public RPC,
paced; read-only): the position's newest signature (the close) and that transaction's SOL-vault balance before it (the SOL in the pool
when the creator pulled) and the SOL the creator's wallet gained in it, against the SOL deposited at creation. SOL at pull minus SOL
deposited = what buyers left in the pool (their net loss before fees, which is the creator's take)."""
import json, sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from dammstate import rpc


def main(census, out):
    pools = [p for p in json.load(open(census))["pools"] if p.get("lp_later")]
    res = {}
    for n, p in enumerate(pools):
        try:
            s = rpc("getSignaturesForAddress", [p["position"], {"limit": 20}])
            s = [x for x in s if not x["err"]]
            if not s:
                continue
            tx = rpc("getTransaction", [s[0]["signature"], {"encoding": "json", "maxSupportedTransactionVersion": 1}])
            m = tx["transaction"]["message"]; ks = list(m["accountKeys"]) + (tx["meta"].get("loadedAddresses") or {}).get("writable", []) + \
                (tx["meta"].get("loadedAddresses") or {}).get("readonly", [])
            pre = {b["accountIndex"]: float(b["uiTokenAmount"]["uiAmount"] or 0) for b in tx["meta"].get("preTokenBalances") or []}
            post = {b["accountIndex"]: float(b["uiTokenAmount"]["uiAmount"] or 0) for b in tx["meta"].get("postTokenBalances") or []}
            j = ks.index(p["sol_vault"]) if p["sol_vault"] in ks else None
            payer_gain = (tx["meta"]["postBalances"][0] - tx["meta"]["preBalances"][0]) / 1e9
            res[p["sig"]] = {"close_sig": s[0]["signature"], "close_t": tx["blockTime"], "close_payer": ks[0], "by_creator": ks[0] == p["creator"],
                             "sol_at_pull": pre.get(j) if j is not None else None, "sol_after": post.get(j) if j is not None else None,
                             "payer_sol_gain": payer_gain, "sol_deposit": p["sol"], "minutes": (tx["blockTime"] - p["t"]) / 60}
        except Exception as e:
            print(f"  {p['pool'][:8]}: {str(e)[:80]}", flush=True)
        if n % 10 == 0:
            print(f"  {n + 1}/{len(pools)}", flush=True); json.dump(res, open(out, "w"))
    json.dump(res, open(out, "w"))
    print(f"done: {len(res)} pulls -> {out}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
