#!/usr/bin/env python3
"""linehist.py FUNDER DAYS OUT.json: one line's history from its funder (HELIUS_API_KEY): the funder's outgoing SOL transfers in the last
DAYS (Helius's parsed history), each recipient's transactions, and the Raydium pools they created (census.parse), written in census.py's
format with the funder set, so trades.py can read every trade on them (trades.py OUT.json TRADES.json funder:FUNDER)."""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import census as C
from trades import history


def main(funder, days, out):
    t0 = int(time.time() - float(days) * 86400)
    txs = history(funder, t0)
    sent = {}
    for t in txs:
        if t.get("timestamp", 0) < t0:
            continue
        for n in t.get("nativeTransfers") or []:
            if n.get("fromUserAccount") == funder and n.get("toUserAccount") and n["amount"] >= 10 ** 9:
                sent.setdefault(n["toUserAccount"], []).append((t["timestamp"], n["amount"] / 1e9))
    print(f"funder {funder[:10]}: {len(txs)} transactions read, {len(sent)} recipients of >= 1 SOL in {days} days", flush=True)
    pools = []
    for n, (w, got) in enumerate(sorted(sent.items(), key=lambda kv: kv[1][0][0])):
        sigs = C.rpc("getSignaturesForAddress", [w, {"limit": 100}])
        for s in sigs:
            if s["err"]:
                continue
            for kind in ("cpmm", "ammv4"):
                try:
                    r = C.parse(kind, s["signature"])
                except Exception:
                    r = None
                if r and r["creator"] == w and r.get("sol"):
                    r.update(funder=funder, funded=got, n=len(sigs)); pools.append(r)
                    break
        print(f"  {n + 1}/{len(sent)} {w[:10]} funded {[round(a, 2) for _, a in got]} SOL: {sum(1 for p in pools if p['creator'] == w)} pool(s)", flush=True)
    for p in pools:
        sigs = C.rpc("getSignaturesForAddress", [p["lp"], {"limit": 50}])
        p["lp_later"] = sorted(s["blockTime"] for s in sigs if not s["err"] and (s.get("blockTime") or 0) > p["t"])[:10]
    json.dump({"t0": t0, "days": float(days), "pools": pools}, open(out, "w"))
    print(f"done -> {out}: {len(pools)} pools", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
