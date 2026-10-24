#!/usr/bin/env python3
"""dammstate.py WORKDIR OUT.json [TOP_CREATORS] [PER_CREATOR]: finishes dammcensus.py's follow-up on the public RPC
(api.mainnet-beta.solana.com, paced: one call a second, backing off on 429/413), after the Helius key ran out of credits (read-only).

From dammcensus.py's cached creation chunks (WORKDIR/chunks): every direct DAMM v2 creation with a SOL side. Per pool (getMultipleAccounts,
100 a call, zero-length or 8-byte data slices): whether the creator's position still exists and the SOL vault's balance now
(SPL token account amount at byte 64). Pulled = the position closed or the SOL vault under 5% of the deposit.
For the TOP_CREATORS (default 30) creators with the most pools: PER_CREATOR (default 3) pools spread in time get their position's
signatures (the removal and close times: 'lp_later'), and the creator its funder (census.py's creator_profile: the sender of the
SOL in its oldest transaction; a wallet with 1000+ signatures is not walked back).
Writes OUT.json in census.py's format (kind 'damm2')."""
import json, os, sys, time, glob, base64, collections, urllib.request, urllib.error

URL = "https://api.mainnet-beta.solana.com"
WSOL = "So11111111111111111111111111111111111111112"
_last = [0.0]


def rpc(m, p):
    for k in range(12):
        w = _last[0] + 1.0 - time.time()
        if w > 0:
            time.sleep(w)
        _last[0] = time.time()
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(URL, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(),
                                                                        {"Content-Type": "application/json"}), timeout=60))
            if "result" in r:
                return r["result"]
            if (r.get("error") or {}).get("code") in (429, 413):
                time.sleep(5 * (k + 1)); continue
            raise RuntimeError(str(r.get("error"))[:120])
        except urllib.error.HTTPError as e:
            if e.code in (429, 413, 503):
                time.sleep(5 * (k + 1)); continue
            raise
    raise RuntimeError(f"{m}: gave up")


def profile(c):
    sigs = rpc("getSignaturesForAddress", [c, {"limit": 1000}])
    prof = {"n": len(sigs), "first_t": sigs[-1].get("blockTime") if sigs else None, "funder": None, "funded_sol": None}
    if sigs and len(sigs) < 1000:
        tx = rpc("getTransaction", [sigs[-1]["signature"], {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 1}])
        if tx:
            for ins in tx["transaction"]["message"]["instructions"] + [i for g in tx["meta"].get("innerInstructions") or [] for i in g["instructions"]]:
                pi = ins.get("parsed") if isinstance(ins.get("parsed"), dict) else None
                if pi and pi.get("type") == "transfer" and pi.get("info", {}).get("destination") == c and "lamports" in pi["info"]:
                    prof["funder"] = pi["info"]["source"]; prof["funded_sol"] = pi["info"]["lamports"] / 1e9; break
    return prof


def main(work, out, top, per):
    recs = [r for f in sorted(glob.glob(work + "/chunks/*.json")) for r in json.load(open(f))["recs"]]
    win = json.load(open(work + "/window.json"))
    direct = [r for r in recs if r["caller"] == "direct" and r.get("sol")]
    st = json.load(open(work + "/state.json")) if os.path.exists(work + "/state.json") else {}
    todo = [r for r in direct if r["sig"] not in st]
    print(f"{len(direct)} direct SOL pools; {len(todo)} need their state", flush=True)
    for k in range(0, len(todo), 100):
        ch = todo[k:k + 100]
        pv = rpc("getMultipleAccounts", [[r["position"] for r in ch], {"encoding": "base64", "dataSlice": {"offset": 0, "length": 0}}])["value"]
        vv = rpc("getMultipleAccounts", [[r["sol_vault"] for r in ch], {"encoding": "base64", "dataSlice": {"offset": 64, "length": 8}}])["value"]
        for r, p, v in zip(ch, pv, vv):
            amt = int.from_bytes(base64.b64decode(v["data"][0]), "little") / 1e9 if v else 0.0
            st[r["sig"]] = {"position_alive": p is not None, "sol_now": amt, "checked": int(time.time())}
        if k % 1000 == 0:
            print(f"  state {k + len(ch)}/{len(todo)}", flush=True); json.dump(st, open(work + "/state.json", "w"))
    json.dump(st, open(work + "/state.json", "w"))
    for r in direct:
        r.update(st.get(r["sig"], {}))
        r["pulled"] = (not r.get("position_alive", True)) or (r.get("sol_now") is not None and r["sol_now"] < 0.05 * r["sol"])
    cnt = collections.Counter(r["creator"] for r in direct)
    tops = [c for c, _ in cnt.most_common(top)]
    lat = json.load(open(work + "/later_pub.json")) if os.path.exists(work + "/later_pub.json") else {}
    prof = json.load(open(work + "/profiles_pub.json")) if os.path.exists(work + "/profiles_pub.json") else {}
    for c in tops:
        ps = sorted((r for r in direct if r["creator"] == c), key=lambda r: r["t"])
        pick = [ps[round(i * (len(ps) - 1) / max(1, per - 1))] for i in range(min(per, len(ps)))]
        for r in pick:
            if r["sig"] in lat:
                continue
            try:
                s = rpc("getSignaturesForAddress", [r["position"], {"limit": 20}])
                lat[r["sig"]] = sorted(x["blockTime"] for x in s if not x["err"] and (x.get("blockTime") or 0) > r["t"])[:10]
            except Exception as e:
                print(f"  position {r['position'][:8]}: {str(e)[:60]}", flush=True)
        if c not in prof:
            try:
                prof[c] = profile(c)
            except Exception as e:
                print(f"  profile {c[:8]}: {str(e)[:60]}", flush=True)
        json.dump(lat, open(work + "/later_pub.json", "w")); json.dump(prof, open(work + "/profiles_pub.json", "w"))
        print(f"  {c[:10]} pools {cnt[c]} funder {(prof.get(c) or {}).get('funder')} n {(prof.get(c) or {}).get('n')}", flush=True)
    for r in direct:
        r["lp_later"] = lat.get(r["sig"], [])
        r.update(prof.get(r["creator"], {}))
    json.dump({"t0": win["t0"], "days": (win["t1"] - win["t0"]) / 86400, "marker": "8dnhmayAP3LA957YgSdP3Nw48ZJM6C4248qfFeyfnxTP",
               "by_caller": dict(collections.Counter(f"{r['caller'] if r['caller'] in ('direct', 'dbc') else 'other'}/{r['ix']}" for r in recs)),
               "pools": direct}, open(out, "w"))
    print(f"pulled {sum(r['pulled'] for r in direct)} of {len(direct)} -> {out}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 30, int(sys.argv[4]) if len(sys.argv) > 4 else 3)
