#!/usr/bin/env python3
"""pumpswapcensus.py DAYS OUT.json: PumpSwap (pAMMBay6...) pools created directly by a wallet, in census.py's format, so linescan.py
and linereport.py run on them unchanged (read-only; HELIUS_API_KEY).

PumpSwap has no account that only pool creations touch: ammprobe.py found that create_pool's static accounts (global config, event
authority, system / token / token-2022 / associated-token programs, WSOL) are in 89-100% of sampled swaps. Instead, the pools are
listed from the program's accounts: Helius getProgramAccountsV2 (Pool discriminator, paged), with changedSinceSlot = the window's
start (a swap does not write the Pool account, so this returns the pools created, deposited into or withdrawn from since then).
Kept: quote mint WSOL, and a creator that is a wallet (an ed25519 point); pump.fun's migrations create pools under a per-mint PDA
(off the curve), so they drop out here. Each kept pool's first transaction (getTransactionsForAddress ascending, one call) must be
its create_pool, inside the window; it gives the creator (fee payer), amounts, vaults and LP mint. Then census.py's checks: the SOL
vault now, the LP mint's later signatures (a deposit or withdraw: 'lp_later'), and creator profiles (signature count, funder) for
creators of pulled pools and of 2+ pools."""
import json, os, sys, time, base64, hashlib, collections, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pumplib as P
import census as C
C.rpc = P.rpc

DISC = base64.b64encode(hashlib.sha256(b"account:Pool").digest()[:8]).decode()
CREATE = hashlib.sha256(b"global:create_pool").digest()[:8]
PP = 2 ** 255 - 19
DD = (-121665 * pow(121666, PP - 2, PP)) % PP


def on_curve(addr):
    b = P.b58d(addr)
    if len(b) != 32:
        return False
    y = int.from_bytes(b, "little") & ((1 << 255) - 1)
    if y >= PP:
        return False
    u = (y * y - 1) % PP; v = (DD * y * y + 1) % PP
    x2 = u * pow(v, PP - 2, PP) % PP
    return x2 == 0 or pow(x2, (PP - 1) // 2, PP) == 1


def pools_changed(since_slot):
    out, key = [], None
    while True:
        p = {"encoding": "base64", "filters": [{"memcmp": {"offset": 0, "bytes": DISC, "encoding": "base64"}}],
             "dataSlice": {"offset": 11, "length": 96}, "limit": 5000, "changedSinceSlot": since_slot}
        if key:
            p["paginationKey"] = key
        r = P.rpc("getProgramAccountsV2", [P.PUMPSWAP, p])
        for a in r["accounts"]:
            b = base64.b64decode(a["account"]["data"][0])
            out.append({"pool": a["pubkey"], "pcreator": P.b58e(b[0:32]), "base": P.b58e(b[32:64]), "quote": P.b58e(b[64:96])})
        key = r.get("paginationKey")
        if not key:
            return out


def creation(c):
    txs, _ = P.gtfa(c["pool"], asc=True, limit=1, max_pages=1)
    if not txs:
        return None
    tx = txs[0]; ks = P.keys(tx)
    for top, depth, prog, accs, data in P.ixs(tx, ks):
        if prog != P.PUMPSWAP or P.b58d(data)[:8] != CREATE or accs[0] != c["pool"]:
            continue
        m = tx["transaction"]["message"]; tops = [ks[i["programIdIndex"]] for i in m["instructions"]]
        rec = {"kind": "pumpswap", "sig": tx["transaction"]["signatures"][0], "t": tx["blockTime"], "slot": tx["slot"], "creator": ks[0],
               "pool_creator": accs[2], "caller": "direct" if tops[top] == P.PUMPSWAP else tops[top], "pool": c["pool"],
               "m0": accs[3], "m1": accs[4], "lp": accs[5], "v0": accs[9], "v1": accs[10]}
        post = {b["accountIndex"]: b for b in tx["meta"].get("postTokenBalances") or []}
        for side in ("v0", "v1"):
            idx = ks.index(rec[side]) if rec[side] in ks else None
            b = post.get(idx)
            if b:
                rec[side + "_mint"] = b["mint"]; rec[side + "_amt"] = float(b["uiTokenAmount"]["uiAmount"] or 0)
        sol_side = "v0" if rec.get("v0_mint") == P.WSOL else "v1" if rec.get("v1_mint") == P.WSOL else None
        rec["sol"] = rec.get(sol_side + "_amt") if sol_side else None
        rec["sol_vault"] = rec.get(sol_side) if sol_side else None
        rec["token"] = (rec.get("v1_mint") if sol_side == "v0" else rec.get("v0_mint")) if sol_side else None
        return rec
    return {"not_create": True, "pool": c["pool"], "t": tx["blockTime"]}


def main(days, out):
    slot = P.rpc("getSlot", []); t_now = int(time.time()); t0 = t_now - int(days * 86400)
    since = slot - int(days * 86400 / 0.4)
    allp = pools_changed(since)
    sol = [c for c in allp if c["quote"] == P.WSOL]
    wal = [c for c in sol if on_curve(c["pcreator"])]
    print(f"pools changed since slot {since} (~{days:g} days): {len(allp)}; WSOL-quoted {len(sol)}; creator a wallet (not a PDA) {len(wal)}", flush=True)
    recs = []
    with cf.ThreadPoolExecutor(8) as ex:
        for n, r in enumerate(ex.map(C.safe(creation, "creation"), wal)):
            if r and not r.get("not_create") and r["t"] >= t0:
                recs.append(r)
            if n % 500 == 0:
                print(f"  creations {n}/{len(wal)}: {len(recs)} in the window {dict(P.STATS)}", flush=True)
    print(f"direct creations in the window: {len(recs)} (callers {dict(collections.Counter(r['caller'] if r['caller'] == 'direct' else 'other' for r in recs))})", flush=True)
    pools = [r for r in recs if r.get("sol")]
    vaults = {}
    for k in range(0, len(pools), 100):
        res = P.rpc("getMultipleAccounts", [[r["sol_vault"] for r in pools[k:k + 100]], {"encoding": "jsonParsed"}])
        for r, v in zip(pools[k:k + 100], res["value"]):
            try:
                vaults[r["sig"]] = float(v["data"]["parsed"]["info"]["tokenAmount"]["uiAmount"] or 0) if v else 0.0
            except Exception:
                vaults[r["sig"]] = None

    def later(r):
        s = P.rpc("getSignaturesForAddress", [r["lp"], {"limit": 50}])
        return r["sig"], sorted(x["blockTime"] for x in s if not x["err"] and (x.get("blockTime") or 0) > r["t"])[:10]
    lat = {}
    with cf.ThreadPoolExecutor(6) as ex:
        for res in ex.map(C.safe(later, "later"), pools):
            if res:
                lat[res[0]] = res[1]
    for r in pools:
        r["sol_now"] = vaults.get(r["sig"]); r["lp_later"] = lat.get(r["sig"], [])
    pulled = [r for r in pools if r["lp_later"] and r["sol_now"] is not None and r["sol_now"] < 0.05 * r["sol"]]
    cnt = collections.Counter(r["creator"] for r in pools)
    creators = sorted({r["creator"] for r in pulled} | {c for c, k in cnt.items() if k >= 2})
    print(f"SOL pools {len(pools)}, pulled {len(pulled)}; creator profiles {len(creators)}", flush=True)
    prof = {}
    with cf.ThreadPoolExecutor(6) as ex:
        for cp in ex.map(C.safe(C.creator_profile, "creator"), creators):
            if cp:
                prof[cp[0]] = cp[1]
    for r in pools:
        r.update(prof.get(r["creator"], {}))
    json.dump({"t0": t0, "days": days, "n_changed": len(allp), "n_wsol": len(sol), "n_wallet_creator": len(wal), "pools": pools,
               "failed": dict(C.FAILED)}, open(out, "w"))
    print("done ->", out, dict(P.STATS), flush=True)


if __name__ == "__main__":
    main(float(sys.argv[1]), sys.argv[2])
