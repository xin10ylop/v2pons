"""Per-venue launch census + first-swap sampling (read-only RPC).
usage: sample.py --chain C --url U --venue NAME --kind {v4,pcsinf,v3,v2,solidly,fourmeme,kumbaya} --address A
                 [--creations FILE] [--span 10000] [--depth N] [--W N] [--hours 24] [--n 20] [--cap 40]
Counts creations over min(24h, depth) and samples the n most recent launches whose W-block swap window is complete."""
import argparse, json, os, sys, time, collections, statistics
sys.path.insert(0, os.path.dirname(__file__))
import rpc
OUT = os.path.join(os.path.dirname(__file__), "..", "out")
CREATE = {
 "v4": ["0xdd466e674ea557f56295e2d0218a125ea4b4f0f6f3307b95f85e6110838d6438"],
 "pcsinf": ["0x426cc62fe6a33a40ba2788c2c87a9c34ee4582b95bc9fa5a7bb7ae70b750b99c"],
 "v3": ["0x783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118",
        "0xab0d57f0df537bb25e80245ef7748fa62353808c54d6e528a9dd20887aed9ac2",
        "0x91ccaa7a278130b65168c3a0c8d3bcae84cf5e43704342bd3ec0b59e59c036db"],
 "v2": ["0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9"],
 "solidly": ["0x2128d88d14c80cb081c1252a5acff7a264671bf199ce226b53788fb26065005e"],
 "fourmeme": ["0x396d5e902b675b032348d3d2e9517ee8f0c4a926603fbc075d3d282ff00cad20",
              "0xc60523754e4c8d044ae75f841c3a7f27fefeed24c086155510c2ae0edf538fa0"],
 "kumbaya": None,  # TokenIgnited, computed below
}
from eth_hash.auto import keccak
def topic(sig): return "0x" + keccak(sig.encode()).hex()
CREATE["kumbaya"] = [topic("TokenIgnited(address,address,address,uint256,uint16,int24,int24)")]
CREATE["nadfun"] = [topic("CurveCreate(address,address,address,string,string,string,uint256,uint256,uint256)")]
SWAP = {
 "v4": [topic("Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)")],
 "pcsinf": [topic("Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24,uint16)")],
 "v3": [topic("Swap(address,address,int256,int256,uint160,uint128,int24)"),
        topic("Swap(address,address,int256,int256,uint160,uint128,int24,uint128,uint128)")],
 "v2": [topic("Swap(address,uint256,uint256,uint256,uint256,address)")],
 "solidly": [topic("Swap(address,address,uint256,uint256,uint256,uint256)")],
 "fourmeme": [topic("TokenPurchase(address,address,uint256,uint256,uint256,uint256,uint256,uint256)"),
              topic("TokenSale(address,address,uint256,uint256,uint256,uint256,uint256,uint256)")],
}
SWAP["kumbaya"] = SWAP["v3"]
SWAP["nadfun"] = [topic("CurveBuy(address,address,uint256,uint256)"), topic("CurveSell(address,address,uint256,uint256)")]
def word(data, i): return "0x" + data[2 + 64 * i: 2 + 64 * (i + 1)]
def addr_of(w): return "0x" + w[-40:]

def parse_creation(kind, l):
    t = l["topics"]; d = l["data"]
    c = {"block": int(l["blockNumber"], 16), "tx": l["transactionHash"]}
    if kind in ("v4",):
        c.update(key=t[1], c0=addr_of(t[2]), c1=addr_of(t[3]), fee=int(word(d, 0), 16), hooks=addr_of(word(d, 2)))
    elif kind == "pcsinf":
        c.update(key=t[1], c0=addr_of(t[2]), c1=addr_of(t[3]), hooks=addr_of(word(d, 0)))
    elif kind == "v3":
        idx = 1 if t[0] == CREATE["v3"][0] else 0
        c.update(key=addr_of(word(d, idx)), c0=addr_of(t[1]), c1=addr_of(t[2]))
    elif kind in ("v2", "solidly"):
        c.update(key=addr_of(word(d, 0)), c0=addr_of(t[1]), c1=addr_of(t[2]))
    elif kind == "fourmeme":
        c.update(key=addr_of(word(d, 1)), creator=addr_of(word(d, 0)))
    elif kind == "nadfun":
        c.update(key=addr_of(t[2]), creator=addr_of(t[1]), pool=addr_of(t[3]))
    elif kind == "kumbaya":
        c.update(key=addr_of(t[3]), token=addr_of(t[1]), creator=addr_of(t[2]))
    return c

def swap_query(kind, venue_addr, c):
    if kind in ("v4", "pcsinf"):
        return venue_addr, [SWAP[kind], c["key"]]
    if kind == "fourmeme":
        return venue_addr, [SWAP[kind]]
    if kind == "nadfun":
        return venue_addr, [SWAP[kind], None, "0x" + "0" * 24 + c["key"][2:]]
    return c["key"], [SWAP[kind]]

def swap_sender(kind, l):
    t = l["topics"]
    if kind in ("v4", "pcsinf"): return addr_of(t[2])
    if kind == "nadfun": return addr_of(t[1])
    if kind == "fourmeme": return addr_of(word(l["data"], 1))  # account
    return addr_of(t[1]) if len(t) > 1 else None

def main():
    ap = argparse.ArgumentParser()
    for a in ("chain", "url", "venue", "kind", "address", "creations"):
        ap.add_argument("--" + a)
    ap.add_argument("--span", type=int, default=10000)
    ap.add_argument("--depth", type=int, default=0)
    ap.add_argument("--W", type=int, default=1800)
    ap.add_argument("--hours", type=float, default=24)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--cap", type=int, default=40)
    ap.add_argument("--bt", type=float, default=0)
    ap.add_argument("--hooks", default=None)
    ap.add_argument("--traded_only", type=int, default=0, help="if >0: scan up to this many recent launches, keep the first n with >=1 external swap in W")
    A = ap.parse_args()
    url, kind, vaddr = A.url, A.kind, A.address.lower()
    head = rpc.block_number(url)
    head -= 3  # load-balanced RPCs can lag a block or two
    hb = rpc.get_block(url, head); head_ts = int(hb["timestamp"], 16)
    if not A.bt:
        ob = rpc.get_block(url, head - 2000); A.bt = (head_ts - int(ob["timestamp"], 16)) / 2000
    day_blocks = int(A.hours * 3600 / A.bt)
    lookback = min(day_blocks, A.depth - 50) if A.depth else day_blocks
    frm = head - lookback
    errlog = []
    if A.creations:
        logs = [json.loads(x) for x in open(A.creations)]
        logs = [l for l in logs if l["address"].lower() == vaddr and l["topics"][0] in CREATE[kind]]
        frm = min([int(l["blockNumber"], 16) for l in logs] + [frm])
        meta = json.load(open(A.creations.replace("creations_", "discover_").replace(".jsonl", ".json")))
        frm, cov_to = meta["from"], meta["to"]
    else:
        logs, _ = rpc.get_logs_range(url, vaddr, [CREATE[kind]], frm, head, chunk=A.span, max_chunk=A.span, log=errlog)
        cov_to = head
    covered_hours = (cov_to - frm) * A.bt / 3600
    creations = [parse_creation(kind, l) for l in logs]
    if A.hooks:
        creations = [c for c in creations if c.get("hooks") == A.hooks.lower()]
    creations.sort(key=lambda c: c["block"])
    per_day = len(creations) * 24 / covered_hours if covered_hours else None
    hooks = collections.Counter(c.get("hooks") for c in creations if c.get("hooks"))
    # sample
    lo_ok = head - A.depth + 10 if A.depth else 0
    cands = [c for c in creations if c["block"] + A.W + 3 <= head and c["block"] >= lo_ok]
    sample = cands[-A.n:] if not A.traded_only else list(reversed(cands[-A.traded_only:]))
    scanned = 0; scanned_with_ext = 0
    txcache = {}
    def gtx(h):
        if h not in txcache:
            try:
                tx = rpc.get_tx(url, h)
                txcache[h] = {"from": tx["from"].lower(), "to": (tx.get("to") or "").lower(),
                              "gasPrice": int(tx.get("gasPrice") or "0x0", 16), "gas": int(tx["gas"], 16)} if tx else None
            except Exception as e:
                txcache[h] = None; errlog.append(f"tx {h}: {str(e)[:80]}")
        return txcache[h]
    rows = []
    for c in sample:
        if A.traded_only and len(rows) >= A.n: break
        qa, qt = swap_query(kind, vaddr, c)
        try:
            sw, _ = rpc.get_logs_range(url, qa, qt, c["block"], c["block"] + A.W, chunk=A.span, max_chunk=A.span, log=errlog)
        except Exception as e:
            errlog.append(f"swaps {c['key']}: {str(e)[:100]}"); continue
        if kind == "fourmeme":
            sw = [l for l in sw if addr_of(word(l["data"], 0)) == c["key"]]
        sw.sort(key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
        scanned += 1
        has_ext = any(l["transactionHash"] != c["tx"] for l in sw)
        scanned_with_ext += has_ext
        if A.traded_only:
            if not has_ext: continue
        first3 = []
        for l in sw[:3]:
            tx = gtx(l["transactionHash"]) or {}
            first3.append({"offset": int(l["blockNumber"], 16) - c["block"], "tx": l["transactionHash"],
                           "same_tx_as_launch": l["transactionHash"] == c["tx"], "to": tx.get("to"), "from": tx.get("from"),
                           "swap_sender": swap_sender(kind, l)})
        early = [l for l in sw if int(l["blockNumber"], 16) <= c["block"] + 2]
        hashes = list(dict.fromkeys(l["transactionHash"] for l in early))
        truncated = len(hashes) > A.cap
        wallets, wallets_ex = set(), set()
        for h in hashes[:A.cap]:
            tx = gtx(h)
            if tx:
                wallets.add(tx["from"])
                if h != c["tx"]: wallets_ex.add(tx["from"])
        launch_tx = gtx(c["tx"])
        rows.append({**c, "launch_from": (launch_tx or {}).get("from"), "launch_to": (launch_tx or {}).get("to"),
                     "n_swaps_W": len(sw), "first3": first3, "n_swaps_first3blocks": len(early),
                     "n_tx_first3blocks": len(hashes), "wallets_first3blocks": len(wallets),
                     "wallets_first3blocks_excl_launch_tx": len(wallets_ex), "truncated": truncated})
    # tallies (exclude swaps inside the launch tx itself)
    to_ct, from_ct, snd_ct = collections.Counter(), collections.Counter(), collections.Counter()
    for r in rows:
        tos = {f["to"] for f in r["first3"] if not f["same_tx_as_launch"] and f["to"]}
        frs = {f["from"] for f in r["first3"] if not f["same_tx_as_launch"] and f["from"]}
        sns = {f["swap_sender"] for f in r["first3"] if not f["same_tx_as_launch"] and f["swap_sender"]}
        to_ct.update(tos); from_ct.update(frs); snd_ct.update(sns)
    traded = [r for r in rows if r["n_swaps_W"] > 0]
    offs = [f["offset"] for r in rows for f in r["first3"] if not f["same_tx_as_launch"]]
    gp = [t["gasPrice"] for t in txcache.values() if t and t["gasPrice"]]
    res = {"chain": A.chain, "venue": A.venue, "kind": kind, "address": vaddr, "hooks_filter": A.hooks, "url": url, "head": head, "head_ts": head_ts,
           "block_time": A.bt, "from_block": frm, "covered_hours": round(covered_hours, 2), "n_creations": len(creations),
           "per_day": round(per_day, 1) if per_day is not None else None, "W_blocks": A.W,
           "top_hooks": hooks.most_common(8), "n_sampled": len(rows), "traded_only_scan": A.traded_only, "n_scanned": scanned, "n_scanned_with_external_swap_in_W": scanned_with_ext, "n_traded_in_W": len(traded),
           "launch_tx_contains_swap": sum(1 for r in rows if any(f["same_tx_as_launch"] for f in r["first3"])),
           "first3_offsets_excl_launch_tx": sorted(offs),
           "median_offset_first_external_swap": statistics.median([min([f["offset"] for f in r["first3"] if not f["same_tx_as_launch"]]) for r in rows if any(not f["same_tx_as_launch"] for f in r["first3"])]) if any(any(not f["same_tx_as_launch"] for f in r["first3"]) for r in rows) else None,
           "first3_tx_to_by_launches": to_ct.most_common(10), "first3_tx_from_by_launches": from_ct.most_common(10),
           "first3_swap_sender_by_launches": snd_ct.most_common(10),
           "wallets_first3blocks": [r["wallets_first3blocks"] for r in rows],
           "wallets_first3blocks_excl_launch_tx": [r["wallets_first3blocks_excl_launch_tx"] for r in rows],
           "median_wallets_first3blocks_excl_launch_tx": statistics.median([r["wallets_first3blocks_excl_launch_tx"] for r in rows]) if rows else None,
           "median_wallets_first3blocks_traded_only": statistics.median([r["wallets_first3blocks_excl_launch_tx"] for r in traded]) if traded else None,
           "launch_tx_to_counts": collections.Counter(r["launch_to"] for r in rows).most_common(5),
           "gasPrice_gwei_median": statistics.median(gp) / 1e9 if gp else None, "n_tx_lookups": len(txcache),
           "rows": rows, "errlog": errlog[:30], "rpc_stats": rpc.STATS}
    fn = os.path.join(OUT, f"sample_{A.chain}_{A.venue}.json")
    json.dump(res, open(fn, "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k not in ("rows", "rpc_stats")})[:3000])
    print("rpc", json.dumps(rpc.STATS))
if __name__ == "__main__":
    main()
