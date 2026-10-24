#!/usr/bin/env python3
"""dammcensus.py DAYS OUT.json: Meteora DAMM v2 (cpamdpZC...) pool creations with a SOL side, in census.py's format, so linescan.py
and linereport.py run on them unchanged (read-only; HELIUS_API_KEY).

The creation marker: 8dnhmayAP3LA957YgSdP3Nw48ZJM6C4248qfFeyfnxTP, an account that does not exist and that only pool creations pass
(a trailing remaining account of initialize_customizable_pool / initialize_pool; most likely the token-badge PDA of the WSOL mint).
Checked by ammprobe.py and by hand: 500 of 500 transactions touching it were DAMM v2 creations (339 initialize_customizable_pool,
4 initialize_pool, 157 Meteora DBC migrations), and it is in none of 300 sampled swaps. Coverage caveat: a creation whose client does
not pass the badge account is missed.
Listed with getTransactionsForAddress (full transactions, 6-hour chunks). Per creation: the caller (direct = DAMM v2 called at top
level; Meteora DBC's migration and other launchpads are kept but marked, and only direct creations are followed up), the creator
(fee payer), pool, position, mints, vaults and their amounts after the creation (the SOL side's), the time.
Per direct SOL pool: the SOL vault's balance now and whether the creator's position still exists (getMultipleAccounts, 100 a call);
a pool whose SOL vault is under 5% of its deposit, or whose position is closed, is looked at further: the position's later
signatures ('lp_later': its removals and close; census.py's LP-mint moves), read only for pools that can form a line in
linescan.py (a funder with 4+ pools, a creator with 3+, or 3+ pools of one exact SOL amount from fresh creators). Creator profiles
(signature count, funder: census.creator_profile) for creators of such pulled pools and creators with 2+ direct SOL pools."""
import json, os, sys, time, hashlib, collections, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pumplib as P
import census as C
C.rpc = P.rpc

MARKER = "8dnhmayAP3LA957YgSdP3Nw48ZJM6C4248qfFeyfnxTP"
G = lambda n: hashlib.sha256(f"global:{n}".encode()).digest()[:8]
LAYOUT = {G("initialize_customizable_pool"): ("customizable", {"creator": 0, "payer": 3, "pool": 5, "position": 6, "m0": 7, "m1": 8, "v0": 9, "v1": 10}),
          G("initialize_pool"): ("config", {"creator": 0, "payer": 3, "config": 4, "pool": 6, "position": 7, "m0": 8, "m1": 9, "v0": 10, "v1": 11}),
          G("initialize_pool_with_dynamic_config"): ("dynamic", {"creator": 0, "payer": 3, "config": 5, "pool": 7, "position": 8, "m0": 9, "m1": 10,
                                                                  "v0": 11, "v1": 12})}
CALLERS = {"dbcij3LWUppWqq96dh6gJWwBifmcGfLSB5D4DuSMaqN": "dbc"}
CHUNK = 6 * 3600


def parse(tx):
    ks = P.keys(tx); m = tx["transaction"]["message"]; tops = [ks[i["programIdIndex"]] for i in m["instructions"]]
    for top, depth, prog, accs, data in P.ixs(tx, ks):
        if prog != P.DAMM2:
            continue
        lay = LAYOUT.get(P.b58d(data)[:8])
        if not lay:
            continue
        kind, pos = lay
        if len(accs) <= max(pos.values()):
            continue
        caller = "direct" if tops[top] == P.DAMM2 else CALLERS.get(tops[top], tops[top])
        rec = {"kind": "damm2", "ix": kind, "caller": caller, "sig": tx["transaction"]["signatures"][0], "t": tx["blockTime"], "slot": tx["slot"],
               "creator": ks[0], "pos_creator": accs[pos["creator"]], **{k: accs[v] for k, v in pos.items() if k not in ("creator", "payer")}}
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
        rec["lp"] = rec["position"]
        return rec
    return None


def chunk(outdir, a, b):
    path = f"{outdir}/chunks/{a}.json"
    d = P.jload(path)
    if d:
        return d
    txs, complete = P.gtfa(MARKER, gte=a, lt=b, asc=True, max_pages=200)
    recs = [r for r in (parse(tx) for tx in txs) if r]
    d = {"a": a, "b": b, "n_tx": len(txs), "complete": complete, "recs": recs}
    P.jsave(path, d)
    return d


def multi(addrs):
    out = {}
    for k in range(0, len(addrs), 100):
        r = P.rpc("getMultipleAccounts", [addrs[k:k + 100], {"encoding": "jsonParsed"}])
        for a, v in zip(addrs[k:k + 100], r["value"]):
            out[a] = v
    return out


def main(days, out):
    outdir = os.path.splitext(out)[0] + "_work"; os.makedirs(outdir + "/chunks", exist_ok=True)
    win = P.jload(outdir + "/window.json")
    if not win:
        t1 = int(time.time()) // 3600 * 3600; win = {"t0": t1 - int(days * 86400), "t1": t1}; P.jsave(outdir + "/window.json", win)
    t0, t1 = win["t0"], win["t1"]
    starts = list(range(t0, t1, CHUNK))
    recs, ntx = [], 0
    with cf.ThreadPoolExecutor(4) as ex:
        for n, d in enumerate(ex.map(lambda a: chunk(outdir, a, a + CHUNK), starts)):
            recs += d["recs"]; ntx += d["n_tx"]
            if n % 8 == 0:
                print(f"  chunks {n + 1}/{len(starts)}: {len(recs)} creations {dict(P.STATS)}", flush=True)
    by = collections.Counter((r["caller"] if r["caller"] in ("direct", "dbc") else "other", r["ix"]) for r in recs)
    print(f"{ntx} marker transactions, {len(recs)} creations in {days:g} days: {dict(by)}", flush=True)
    direct = [r for r in recs if r["caller"] == "direct" and r.get("sol")]
    print(f"direct with a SOL side: {len(direct)} (SOL: median {sorted(r['sol'] for r in direct)[len(direct) // 2] if direct else 0:.3f})", flush=True)
    # pulls: the SOL vault now, the position's existence
    vaults = multi([r["sol_vault"] for r in direct]); poss = multi([r["position"] for r in direct])
    for r in direct:
        v = vaults.get(r["sol_vault"])
        try:
            r["sol_now"] = float(v["data"]["parsed"]["info"]["tokenAmount"]["uiAmount"] or 0) if v else 0.0
        except Exception:
            r["sol_now"] = None
        r["position_alive"] = poss.get(r["position"]) is not None
    cand = [r for r in direct if (r["sol_now"] is not None and r["sol_now"] < 0.05 * r["sol"]) or not r["position_alive"]]
    print(f"pulled candidates (SOL vault < 5% of the deposit, or the position closed): {len(cand)}", flush=True)

    cnt = collections.Counter(r["creator"] for r in direct)
    creators = sorted({r["creator"] for r in cand} | {c for c, k in cnt.items() if k >= 2})
    ppath = outdir + "/profiles.json"; prof = P.jload(ppath, {})
    need = [c for c in creators if c not in prof]
    print(f"creator profiles: {len(creators)} ({len(need)} new)", flush=True)
    with cf.ThreadPoolExecutor(6) as ex:
        for n, cp in enumerate(ex.map(C.safe(C.creator_profile, "creator"), need)):
            if cp:
                prof[cp[0]] = cp[1]
            if n % 500 == 0:
                print(f"  creators {n}/{len(need)} {dict(P.STATS)}", flush=True); P.jsave(ppath, prof)
    P.jsave(ppath, prof)
    for r in direct:
        r.update(prof.get(r["creator"], {}))
    # the pull's timing ('lp_later': the position's later signatures) only for pools that can form a line in linescan.py:
    # a funder with 4+ pools, a creator with 3+, or 3+ pools of one exact SOL amount from fresh creators
    byf = collections.Counter(r.get("funder") for r in direct if r.get("funder"))
    bys = collections.Counter(round(r["sol"], 3) for r in direct if (r.get("n") or 99) < 20 and r["sol"] >= 1)
    grp = [r for r in cand if byf.get(r.get("funder"), 0) >= 4 or cnt[r["creator"]] >= 3 or ((r.get("n") or 99) < 20 and r["sol"] >= 1 and bys[round(r["sol"], 3)] >= 3)]
    print(f"position histories for {len(grp)} pulled pools in candidate groups", flush=True)

    def later(r):
        s = P.rpc("getSignaturesForAddress", [r["position"], {"limit": 50}])
        return r["sig"], sorted(x["blockTime"] for x in s if not x["err"] and (x.get("blockTime") or 0) > r["t"])[:10]
    lpath = outdir + "/later.json"; lat = P.jload(lpath, {})
    need = [r for r in grp if r["sig"] not in lat]
    with cf.ThreadPoolExecutor(6) as ex:
        for n, res in enumerate(ex.map(C.safe(later, "later"), need)):
            if res:
                lat[res[0]] = res[1]
            if n % 500 == 0:
                print(f"  position histories {n}/{len(need)} {dict(P.STATS)}", flush=True); P.jsave(lpath, lat)
    P.jsave(lpath, lat)
    for r in direct:
        r["lp_later"] = lat.get(r["sig"], [])
    json.dump({"t0": t0, "days": days, "marker": MARKER, "by_caller": {f"{a}/{b}": v for (a, b), v in by.items()},
               "pools": direct, "other": [r for r in recs if r["caller"] != "direct" or not r.get("sol")][:0], "failed": dict(C.FAILED)}, open(out, "w"))
    print("done ->", out, dict(P.STATS), flush=True)


if __name__ == "__main__":
    main(float(sys.argv[1]), sys.argv[2])
