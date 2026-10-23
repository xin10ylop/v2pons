#!/usr/bin/env python3
"""rugline.py RUGS.json CHAIN SHAPE SIZE OUT.json [N]: one line from rugcensus.py (its pulled pools of one shape, e.g. "v2 fee - ts -",
and one native size to 3 significant figures), every trade on N of them (default all) from creation to the pull: the block offset, the
trader (the transaction's sender), the native side (+ a buy). The fleet is the traders in at least a quarter of the pools; an outsider is
anyone else. Prints, per pool, the fleet's buys and the pull, and for pools with an outsider: when the outsider bought against the
fleet's first buy, and how many blocks later the pull came (a pull right after an outsider = a detector; none = a seat)."""
import json, sys, collections, statistics as st, concurrent.futures as cf
import v4census as V
import rugcensus as R

T_SWAP2 = "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"   # Swap(address,uint256,uint256,uint256,uint256,address)
T_SWAP3 = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"   # Swap(address,address,int256,int256,uint160,uint128,int24)
T_SWAP3P = "0x19b47279256b2a23a1665c810c8d55a1758940ee09377d4f8d26497a3577dc83"  # PancakeSwap V3 Swap (with protocol fees)
T_SWAP4 = "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f"


def life(ch, p, url):
    lo, hi = p["bn"], p["rem_bn"] + 2
    if p["venue"] == "v4":
        L = R.logs(ch, lo, hi, [[T_SWAP4], p["id"][3:]], p["pm"])
    else:
        L = R.logs(ch, lo, hi, [[T_SWAP2, T_SWAP3, T_SWAP3P]], p["id"][3:])
    ev = []
    for x in L:
        d = x["data"][2:]; off = int(x["blockNumber"], 16) - p.get("add_bn", p["bn"])
        if x["topics"][0] == T_SWAP2:
            a0i, a1i, a0o, a1o = (int(d[i:i + 64], 16) for i in (0, 64, 128, 192))
            nat = (a0i - a0o) if p["nat"] == 0 else (a1i - a1o)                   # native into the pair: a buy
        elif x["topics"][0] == T_SWAP4:
            nat = -R.i256(d[0:64]) if p["nat"] == 0 else -R.i256(d[64:128])       # the swapper's delta; minus = paid in
        else:
            nat = R.i256(d[0:64]) if p["nat"] == 0 else R.i256(d[64:128])         # the pool's delta; plus = received
        ev.append({"off": off, "eth": nat / 1e18, "tx": x["transactionHash"], "li": int(x["logIndex"], 16)})
    for e in ev:
        try:
            t = V.rpc(url, "eth_getTransactionByHash", [e["tx"]], tries=4); e["frm"] = t["from"].lower(); e["to"] = (t.get("to") or "").lower()
        except Exception:
            e["frm"] = e["to"] = None
    p["swaps"] = sorted(ev, key=lambda e: (e["off"], e["li"]))
    p["pull_off"] = p["rem_bn"] - p.get("add_bn", p["bn"])
    return p


def main(rugs, ch, shape, size, out, n=None):
    r = json.load(open(rugs))["chains"][ch]
    url = V.CH[ch][0] if ch in V.CH else R.EP[ch][0][0]
    if ch in ("base", "eth"):
        url = R.EP[ch][0][0]
    ps = [p for p in r["rugs"] if f"{p['venue']} fee {p.get('fee', '-')} ts {p.get('ts', '-')}" + (" hook" if p.get("hooks", R.ZERO) != R.ZERO else "") == shape
          and R.sig3(p.get("nat_in") or 0) == float(size)]
    ps = sorted(ps, key=lambda p: p["bn"])[: int(n) if n else None]
    print(f"{len(ps)} pools of {shape} x {size} on {ch}; block time {r['bt']:.2f} s", flush=True)
    with cf.ThreadPoolExecutor(3) as ex:
        ps = list(ex.map(lambda p: life(ch, p, url), ps))
    cnt = collections.Counter(f for p in ps for f in {e["frm"] for e in p["swaps"]})
    fleet = {f for f, c in cnt.items() if f and c >= max(3, len(ps) // 4) and f not in {p.get("frm") for p in ps}}
    print("fleet:", [(f[:10], cnt[f]) for f in sorted(fleet, key=lambda f: -cnt[f])], flush=True)
    clean, dirty = [], []
    for p in ps:
        fb = [e for e in p["swaps"] if e["frm"] in fleet and e["eth"] > 0]
        outs = [e for e in p["swaps"] if e["frm"] not in fleet and e["frm"] != p.get("frm")]
        p["fleet_buys"] = [(e["off"], round(e["eth"], 4)) for e in fb]; p["outs"] = [(e["off"], round(e["eth"], 5), e["frm"]) for e in outs]
        (dirty if outs else clean).append(p)
        print(f"  {p['bn']} {(p.get('frm') or '?')[:10]} in {p.get('nat_in', 0):.4g} | fleet buys {len(fb)} = {sum(e['eth'] for e in fb):.3f} first +{fb[0]['off'] if fb else '-'}"
              f" | outsiders {len(outs)} first +{outs[0]['off'] if outs else '-'} ({outs[0]['eth']:+.4f})" if outs else
              f"  {p['bn']} {(p.get('frm') or '?')[:10]} in {p.get('nat_in', 0):.4g} | fleet buys {len(fb)} = {sum(e['eth'] for e in fb):.3f} first +{fb[0]['off'] if fb else '-'} | outsiders 0",
              f"| pull +{p['pull_off']}", flush=True)
    pc = [p["pull_off"] for p in clean]
    print(f"no outsider: {len(clean)} pools, pull median +{st.median(pc) if pc else '-'} blocks", flush=True)
    print(f"with an outsider: {len(dirty)} pools", flush=True)
    for p in dirty:
        o = next(e for e in p["swaps"] if e["frm"] not in fleet and e["frm"] != p.get("frm"))
        fb = next((e["off"] for e in p["swaps"] if e["frm"] in fleet and e["eth"] > 0), None)
        print(f"    outsider {o['frm'][:10]} {o['eth']:+.5f} at +{o['off']} (fleet's first buy +{fb}) -> pull +{p['pull_off']} ({p['pull_off'] - o['off']} blocks after it)", flush=True)
    json.dump({"chain": ch, "shape": shape, "size": size, "fleet": sorted(fleet), "pools": ps}, open(out, "w"))


if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[2], a[3], a[4], a[5], a[6] if len(a) > 6 else None)
