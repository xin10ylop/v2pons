#!/usr/bin/env python3
"""v4line.py CHAIN FEE TS SQRTP HOURS OUT.json [SPAN_BLOCKS]: one scripted v4 line, every pool of it in the last HOURS (native/token, no
hook, the given fee, tick spacing and opening sqrtPriceX96), and each pool's life for SPAN_BLOCKS: the swaps (sender, native side, block
offset) and the liquidity add and pull. The fleet is the wallets that swap in most pools; an outsider is any other swapper. Prints the
pull's offset with and without outsiders, and what the outsiders did (the block of their first buy against the fleet's first buy)."""
import json, sys, time, collections, statistics as st
import v4census as V
from v4life import T_ML, T_SWAP, s


def main(ch, fee, ts, sqrtp, hours, out, span=400):
    url, bt, _ = V.CH[ch]; lurl = V.LOGS.get(ch, url); pm = V.PM.get(ch)
    head = int(V.rpc(url, "eth_blockNumber", []), 16); a = head - int(hours * 3600 / bt)
    pools = []
    for lo in range(a, head + 1, 1000):
        q = {"fromBlock": hex(lo), "toBlock": hex(min(lo + 999, head)), "topics": [V.T_INIT, None, "0x" + "0" * 64]}
        if pm:
            q["address"] = pm
        for x in V.rpc(lurl, "eth_getLogs", [q]):
            d = x["data"][2:]
            if (int(d[0:64], 16), int(d[64:128], 16), int(d[128:192], 16), int(d[192:256], 16)) == (fee, ts, 0, sqrtp):
                pools.append({"bn": int(x["blockNumber"], 16), "pid": x["topics"][1], "pm": x["address"], "tx": x["transactionHash"]})
    print(f"{len(pools)} pools of the line in {hours} h (first block {pools[0]['bn'] if pools else '-'})", flush=True)
    for n, p in enumerate(pools):
        if p["bn"] + span > head:
            p["young"] = True; continue
        L = []
        for lo in range(p["bn"], p["bn"] + span + 1, 1000):
            L += V.rpc(lurl, "eth_getLogs", [{"fromBlock": hex(lo), "toBlock": hex(min(lo + 999, p["bn"] + span)), "address": p["pm"], "topics": [[T_ML, T_SWAP], p["pid"]]}])
        ev = []
        for x in L:
            dd = x["data"][2:]; off = int(x["blockNumber"], 16) - p["bn"]
            if x["topics"][0] == T_ML:
                ev.append({"k": "ml", "off": off, "liq": s(dd[128:192])})
            else:
                t = V.rpc(url, "eth_getTransactionByHash", [x["transactionHash"]], tries=4)
                ev.append({"k": "swap", "off": off, "eth": -s(dd[0:64]) / 1e18, "frm": t["from"].lower(), "to": (t.get("to") or "").lower(), "tx": x["transactionHash"]})
        p["ev"] = ev
        p["pull"] = next((e["off"] for e in ev if e["k"] == "ml" and e["liq"] < 0), None)
        if n % 20 == 0:
            print(f"  {n}/{len(pools)}", flush=True)
    done = [p for p in pools if not p.get("young")]
    cnt = collections.Counter(f for p in done for f in {e["frm"] for e in p["ev"] if e["k"] == "swap"})
    fleet = {f for f, c in cnt.items() if c >= max(3, len(done) // 4)}
    print("fleet:", sorted(fleet), flush=True)
    clean, dirty = [], []
    for p in done:
        outs = [e for e in p["ev"] if e["k"] == "swap" and e["frm"] not in fleet]
        fb = next((e["off"] for e in p["ev"] if e["k"] == "swap" and e["frm"] in fleet and e["eth"] > 0), None)
        p["outsiders"] = outs; p["fleet_first"] = fb
        (dirty if outs else clean).append(p)
    pc = [p["pull"] for p in clean if p["pull"] is not None]
    print(f"no outsider: {len(clean)} pools, pull +{min(pc) if pc else '-'}..+{max(pc) if pc else '-'} (median {st.median(pc) if pc else '-'}); "
          f"fleet skipped {sum(1 for p in clean if p['fleet_first'] is None)}", flush=True)
    print(f"with an outsider: {len(dirty)} pools", flush=True)
    for p in dirty:
        o = p["outsiders"][0]
        print(f"  {p['bn']} outsider {o['frm'][:10]} {o['eth']:+.5f} at +{o['off']} (fleet's first buy +{p['fleet_first']}) -> pull +{p['pull']}; "
              f"fleet swaps {sum(1 for e in p['ev'] if e['k'] == 'swap' and e['frm'] in fleet)}; outsiders {[(e['frm'][:8], round(e['eth'], 5), e['off']) for e in p['outsiders'][:4]]}", flush=True)
    json.dump({"chain": ch, "fee": fee, "ts": ts, "sqrtp": sqrtp, "head": head, "fleet": sorted(fleet), "pools": pools}, open(out, "w"))


if __name__ == "__main__":
    a = sys.argv
    main(a[1], int(a[2]), int(a[3]), int(a[4]), float(a[5]), a[6], int(a[7]) if len(a) > 7 else 400)
