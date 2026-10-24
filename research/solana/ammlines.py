#!/usr/bin/env python3
"""ammlines.py CENSUS.json OUTDIR [K]: prepares linescan.py for a DAMM v2 or PumpSwap census (dammcensus.py / pumpswapcensus.py)
(read-only; HELIUS_API_KEY).

Lines are built with linescan.py's own rules (a funder with 4+ pools, a creator with 3+, hub-funded fresh creators by exact SOL
amount; only lines with a pull; hub funders out). A line with more than K pools (default 12) keeps K of them, spread evenly in time,
so the trade reads stay affordable on a ~5 calls/s key; the reduced census is written to OUTDIR/census_lines.json (every line still
has its 3 or 4 pools). Each kept pool's trades are read with getTransactionsForAddress (full transactions, ascending, the window
linescan.py uses: to the last position/LP move + 10 min, or 24 h) and written in linescan.py's cache format (OUTDIR/trades/<pool>.json:
per transaction the fee payer and the two vaults' balance changes), and OUTDIR/meta.json gets the pool's open time and base fee:
DAMM v2: the pool account's activation point and fee (base fee numerator / 1e9 at activation, read from the Pool account: cliff fee at
byte 8); PumpSwap: open at creation, the fee from the global config (lp + protocol + creator bps). Then run linescan.py fetch (it
finds the trades cached and reads the funders' outflows and hub checks) and linescan.py scan with the reduced census."""
import json, os, sys, time, base64, collections, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pumplib as P
import census as C
C.rpc = P.rpc
os.environ.setdefault("HELIUS_API_KEY", "")
import linescan as LS


def sample(ps, k):
    ps = sorted(ps, key=lambda p: p["t"])
    if len(ps) <= k:
        return ps
    return [ps[round(i * (len(ps) - 1) / (k - 1))] for i in range(k)]


def trades(p):
    t_end = (max(p["lp_later"]) + 600) if p.get("lp_later") else p["t"] + 86400
    t_end = min(t_end, p["t"] + 3 * 86400)
    txs, complete = P.gtfa(p["pool"], gte=p["t"] - 5, lte=t_end, asc=True, max_pages=40 if p.get("lp_later") else 10)
    tok_vault = p["v1"] if p["sol_vault"] == p["v0"] else p["v0"]
    rows = []
    for i, tx in enumerate(txs):
        ks = P.keys(tx); m = tx["meta"]
        pre = {b["accountIndex"]: float(b["uiTokenAmount"]["uiAmount"] or 0) for b in m.get("preTokenBalances") or []}
        post = {b["accountIndex"]: float(b["uiTokenAmount"]["uiAmount"] or 0) for b in m.get("postTokenBalances") or []}
        d = {}
        for v in (p["sol_vault"], tok_vault):
            j = ks.index(v) if v in ks else None
            d[v] = (post.get(j, 0.0) - pre.get(j, 0.0)) if j is not None else 0.0
        rows.append({"i": i, "t": tx["blockTime"], "slot": tx["slot"], "sig": tx["transaction"]["signatures"][0], "payer": ks[0], "type": None,
                     "source": None, "sol_d": d[p["sol_vault"]], "tok_d": d[tok_vault], "err": False})
    return {"rows": rows, "n_sigs": len(txs), "truncated": not complete or len(txs) >= 4000, "missing": 0, "t_end": t_end, "fetched": int(time.time())}


def damm_meta(pools):
    out = {}
    for k in range(0, len(pools), 100):
        r = P.rpc("getMultipleAccounts", [[p["pool"] for p in pools[k:k + 100]], {"encoding": "base64"}])
        for p, v in zip(pools[k:k + 100], r["value"]):
            if not v:
                continue
            b = base64.b64decode(v["data"][0])
            cliff = int.from_bytes(b[8:16], "little"); mode = b[16]; nper = int.from_bytes(b[22:24], "little")
            freq = int.from_bytes(b[24:32], "little"); red = int.from_bytes(b[32:40], "little")
            act = int.from_bytes(b[472:480], "little"); atype = b[480]
            a_mint = P.b58e(b[168:200])
            open_t = (p["t"] + max(0, act - p["slot"]) * 0.4) if atype == 0 else act
            out[p["pool"]] = {"open_time": int(open_t), "fee": cliff / 1e9, "fee_sched": [mode, nper, freq, red], "activation": [atype, act],
                              "layout_ok": a_mint in (p.get("m0"), p.get("v0_mint"))}
    return out


def main(census, outdir, k):
    os.makedirs(outdir + "/trades", exist_ok=True)
    pools = [p for p in json.load(open(census))["pools"] if p.get("sol")]
    lines = [L for L in LS.build_lines(pools) if L["selected"]]
    hubs = P.jload(outdir + "/hubs.json", {})
    for L in lines:
        if L["kind"] == "funder" and L["id"] not in hubs:
            try:
                hubs[L["id"]] = LS.hub_check(L["id"])
            except Exception:
                pass
    P.jsave(outdir + "/hubs.json", hubs)
    lines = [L for L in LS.build_lines(pools, hubs) if L["selected"] and not (L["kind"] == "funder" and hubs.get(L["id"], {}).get("hub"))]
    keep = {}
    for L in lines:
        for p in sample(L["pools"], k):
            keep[p["sig"]] = p
    print(f"{len(lines)} lines with a pull ({collections.Counter(L['kind'] for L in lines)}), {sum(len(L['pools']) for L in lines)} pool slots; "
          f"{len(keep)} pools kept (at most {k} a line)", flush=True)
    for L in sorted(lines, key=lambda L: -len(L["pools"]))[:30]:
        print(f"  {L['key'][:60]:60s} pools {len(L['pools'])} pulled {L['n_census_pulled']} SOL {sorted({round(p['sol'], 2) for p in L['pools']})[:5]}", flush=True)
    red = dict(json.load(open(census))); red["pools"] = list(keep.values())
    json.dump(red, open(outdir + "/census_lines.json", "w"))
    meta = P.jload(outdir + "/meta.json", {})
    kinds = {p["kind"] for p in keep.values()}
    if "damm2" in kinds:
        meta.update(damm_meta([p for p in keep.values() if p["pool"] not in meta]))
    P.jsave(outdir + "/meta.json", meta)
    need = [p for p in keep.values() if not os.path.exists(f"{outdir}/trades/{p['pool']}.json")]
    print(f"trades to read: {len(need)} pools", flush=True)

    def one(p):
        try:
            P.jsave(f"{outdir}/trades/{p['pool']}.json", trades(p))
        except Exception as e:
            print(f"  trades failed {p['pool'][:10]}: {str(e)[:80]}", flush=True)
    with cf.ThreadPoolExecutor(8) as ex:
        for n, _ in enumerate(ex.map(one, need)):
            if n % 100 == 0:
                print(f"  trades {n}/{len(need)} {dict(P.STATS)}", flush=True)
    print("done", dict(P.STATS), flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 12)
