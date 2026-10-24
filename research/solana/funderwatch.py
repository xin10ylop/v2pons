#!/usr/bin/env python3
"""funderwatch.py FUNDER DAYS OUT.json: what a line's funder did in the last DAYS (read-only; HELIUS_API_KEY).

The funder's transactions (Helius address history), its incoming and outgoing SOL (>= 0.01), and for every recipient its own recent
transactions (one page of Helius history): the AMM programs it touched (Raydium CPMM / AMM v4 / LaunchLab, PumpSwap, Meteora DAMM v1/v2
and DLMM, pump.fun, Orca), Helius's type for each, and the Raydium pools it created (census.parse, creations only), written under 'pools' in census.py's format (funder set,
LP-mint moves and the SOL vault now) so linescan.py can take the file as an EXTRA. Recipients' PumpSwap, Meteora and pump.fun
transactions are listed under 'non_raydium', so a move off Raydium shows up."""
import json, os, sys, time, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import census as C
import census_fast as CF
import linescan as LS

C.rpc = CF.rpc
AMMS = {"CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C": "raydium-cpmm", "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8": "raydium-ammv4",
        "LanMV9sAd7wArD4vJFi2qDdfnVhFxYSUg6eADduJ3uj": "raydium-launchlab", "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA": "pumpswap",
        "cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG": "meteora-damm-v2", "Eo7WjKq67rjJQSZxS6z3YkapzY3eMj6Xy8X5EQVn5UaB": "meteora-damm-v1",
        "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo": "meteora-dlmm", "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P": "pump.fun",
        "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": "orca-whirlpool"}


def programs(t):
    ps = set()
    for ix in t.get("instructions") or []:
        ps.add(ix.get("programId"))
        for inner in ix.get("innerInstructions") or []:
            ps.add(inner.get("programId"))
    return sorted(AMMS[p] for p in ps if p in AMMS)


def main(funder, days, out):
    t0 = int(time.time() - float(days) * 86400)
    txs, complete = LS.addr_history(funder, t0, max_pages=40)
    txs = [t for t in txs if t.get("timestamp", 0) >= t0]
    sent, got = collections.defaultdict(list), collections.defaultdict(list)
    for t in txs:
        if t.get("transactionError"):
            continue
        for n in t.get("nativeTransfers") or []:
            if n["amount"] < 10 ** 7:
                continue
            if n.get("fromUserAccount") == funder and n.get("toUserAccount") != funder:
                sent[n["toUserAccount"]].append((t["timestamp"], n["amount"] / 1e9))
            elif n.get("toUserAccount") == funder:
                got[n.get("fromUserAccount")].append((t["timestamp"], n["amount"] / 1e9))
    print(f"funder {funder[:10]}: {len(txs)} transactions since {time.strftime('%Y-%m-%d %H:%M', time.gmtime(t0))} (complete {complete}); "
          f"{len(sent)} recipients, {len(got)} senders", flush=True)
    rec = {}
    for w, s in sorted(sent.items(), key=lambda kv: kv[1][0][0]):
        h, _ = LS.addr_history(w, t0 - 86400, max_pages=2)
        acts = []
        for t in h:
            pr = programs(t)
            if pr or t.get("type") in ("CREATE_POOL", "ADD_LIQUIDITY", "WITHDRAW_LIQUIDITY", "CREATE", "SWAP"):
                acts.append({"t": t.get("timestamp"), "type": t.get("type"), "source": t.get("source"), "programs": pr, "sig": t["signature"]})
        pools = []
        for a in acts:
            if "raydium-cpmm" in a["programs"] or "raydium-ammv4" in a["programs"]:
                for kind in ("cpmm", "ammv4"):
                    try:
                        r = C.parse(kind, a["sig"])
                    except Exception:
                        r = None
                    if r and r["creator"] == w and r.get("sol"):
                        m = LS.pool_meta(r)                      # a creation only (a withdraw's accounts would parse too)
                        if m.get("disc") in (LS.CPMM_INIT.hex(), "01"):
                            pools.append(r)
                        break
        rec[w] = {"sent": s, "n_tx": len(h), "amm_txs": acts, "raydium_pools": pools,
                  "non_raydium": [a for a in acts if any(p in ("pumpswap", "meteora-damm-v2", "meteora-damm-v1", "meteora-dlmm", "pump.fun", "raydium-launchlab")
                                                         for p in a["programs"])]}
        print(f"  {w[:10]} got {[round(a, 2) for _, a in s]} at {[time.strftime('%m-%d %H:%M', time.gmtime(t)) for t, _ in s][:4]} | {len(h)} txs, "
              f"AMM txs {collections.Counter(p for a in acts for p in a['programs'])}, Raydium pools {[(round(p['sol'], 2), p['pool'][:8]) for p in pools]}", flush=True)
    pools = []
    for w, x in rec.items():
        for p in x["raydium_pools"]:
            sigs = C.rpc("getSignaturesForAddress", [p["lp"], {"limit": 50}])
            p.update(funder=funder, funded=x["sent"], n=x["n_tx"],
                     lp_later=sorted(s["blockTime"] for s in sigs if not s["err"] and (s.get("blockTime") or 0) > p["t"])[:10])
            try:
                p["sol_now"] = float(C.rpc("getTokenAccountBalance", [p["sol_vault"]])["value"]["uiAmount"] or 0)
            except Exception:
                p["sol_now"] = None
            pools.append(p)
    json.dump({"funder": funder, "t0": t0, "days": float(days), "n_tx": len(txs), "complete": complete, "got": got, "recipients": rec,
               "pools": pools}, open(out, "w"))
    print(f"{len(pools)} Raydium pools (census format under 'pools')", flush=True)
    print("done ->", out, flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
