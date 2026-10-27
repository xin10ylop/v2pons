#!/usr/bin/env python3
"""entries.py CHAIN WALLET DAY...: every entry a wallet made in the pulled pools of the tapes, sold or not (the round-trip match only sees the
ones it sold whole). Its token Transfer logs (topic filter on the wallet, both directions) over each day's blocks, matched to the pool's
swap in the same transaction: a transfer from the pool's holder to it is a buy, from it to the holder a sell.

out/entries_CHAIN_WALLET.json: [{day, pool, b (its first buy's index in the tape), s (its first sell's index after it, or null), paid}].
Read-only, public RPCs."""
import os, sys, json, gzip, collections
import hlib as H

T = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def main(ch, wallet, days):
    here = os.path.dirname(os.path.abspath(__file__))
    wallet = wallet.lower(); pad = "0x" + "0" * 24 + wallet[2:]
    out = []
    for day in days:
        d = json.load(gzip.open(os.path.join(here, f"out/tape_{ch}_{day}.json.gz"), "rt"))
        cen = {p["id"]: p for p in json.load(open(os.path.join(here, f"out/{ch}_{day}_00.json")))["chains"][ch]["rugs"]}
        pools = {pid: p for pid, p in d["pools"].items() if pid in cen}
        by_tx = collections.defaultdict(list)
        for pid, p in pools.items():
            for i, e in enumerate(p["ev"]):
                by_tx[e[6]].append((pid, i))
        lo = min(p["bn"] for p in pools.values()); hi = max(p["pull"] for p in pools.values()) + 2
        L = H.logs(ch, lo, hi, [T, None, pad]) + H.logs(ch, lo, hi, [T, pad, None])
        per = collections.defaultdict(lambda: {"b": None, "s": [], "paid": 0.0})
        for x in L:
            for pid, i in by_tx.get(x["transactionHash"], []):
                if x["address"].lower() != cen[pid]["tok"].lower():
                    continue
                e = pools[pid]["ev"][i]
                if e[2] > 0 and H.a_of(x["topics"][2]) == wallet:
                    r = per[pid]; r["paid"] += e[2]
                    if r["b"] is None or i < r["b"]:
                        r["b"] = i
                elif e[2] < 0 and H.a_of(x["topics"][1]) == wallet:
                    per[pid]["s"].append(i)
        for pid, r in per.items():
            if r["b"] is None:
                continue
            s = min((i for i in r["s"] if i > r["b"]), default=None)
            out.append({"day": day, "pool": pid, "b": r["b"], "s": s, "paid": r["paid"]})
        print(f"  {ch} {day}: {sum(1 for o in out if o['day'] == day)} entries, {sum(1 for o in out if o['day'] == day and o['s'] is None)} never sold", flush=True)
    json.dump(out, open(os.path.join(here, f"out/entries_{ch}_{wallet[:10]}.json"), "w"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
