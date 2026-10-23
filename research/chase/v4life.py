#!/usr/bin/env python3
"""v4life.py CHAIN CENSUS.json OUT.json VMIN VMAX FEE [N]: the life of a v4census.py family's pools (N sampled, at least 2 hours old): the
pool id from the creation receipt, then every ModifyLiquidity and Swap on it for 2 hours (the PoolManager's logs), each swap's sender (the
transaction's from) and its native side. Prints per pool: blocks to the first buy, the buys before the pull, the pull's block, and the
wallets buying across many pools (a fleet)."""
import json, sys, random, collections
import v4census as V

T_ML = "0xf208f4912782fd25c7f114ca3723a2d5dd6f3bcc3ac8db5af63baa85f711d5ec"
T_SWAP = "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f"


def s(h, bits=256):
    v = int(h, 16)
    return v - (1 << bits) if v >= 1 << (bits - 1) else v


def main(ch, census, out, vmin, vmax, fee, n=25):
    d = json.load(open(census))["chains"][ch]
    url, bt, _ = V.CH[ch]; lurl = V.LOGS.get(ch, url); pm = V.PM.get(ch)
    span = int(7200 / bt)
    fam = [p for p in d["native"] if p.get("value") and vmin <= p["value"] <= vmax and p["fee"] == fee and p["bn"] < d["head"] - span]
    fam = sorted(random.Random(1).sample(fam, min(n, len(fam))), key=lambda p: p["bn"])
    res, buyers = [], collections.Counter()
    for p in fam:
        rc = V.rpc(url, "eth_getTransactionReceipt", [p["tx"]])
        init = next(x for x in rc["logs"] if x["topics"][0] == V.T_INIT)
        pid, pmx = init["topics"][1], init["address"]
        L = []
        for lo in range(p["bn"], p["bn"] + span + 1, 1000):
            L += V.rpc(lurl, "eth_getLogs", [{"fromBlock": hex(lo), "toBlock": hex(min(lo + 999, p["bn"] + span)), "address": pmx, "topics": [[T_ML, T_SWAP], pid]}])
        ev = []
        for x in L:
            dd = x["data"][2:]; off = int(x["blockNumber"], 16) - p["bn"]
            if x["topics"][0] == T_ML:
                ev.append({"k": "ml", "off": off, "liq": s(dd[128:192]), "tx": x["transactionHash"]})
            else:
                ev.append({"k": "swap", "off": off, "eth": -s(dd[0:64]) / 1e18, "tx": x["transactionHash"]})
        for e in ev:
            if e["k"] == "swap":
                t = V.rpc(url, "eth_getTransactionByHash", [e["tx"]], tries=4); e["frm"] = t["from"].lower(); e["to"] = (t.get("to") or "").lower()
        pull = next((e["off"] for e in ev if e["k"] == "ml" and e["liq"] < 0), None)
        buys = [e for e in ev if e["k"] == "swap" and e["eth"] > 0 and (pull is None or e["off"] <= pull)]
        for b in buys:
            buyers[b["frm"]] += 1
        res.append({**p, "pid": pid, "ev": ev, "pull": pull})
        print(f"{p['bn']} {p['frm'][:10]} {p['value']} | buys before pull {len(buys)} ({sum(b['eth'] for b in buys):.3f}) first +{buys[0]['off'] if buys else '-'} "
              f"| pull +{pull} | swaps {sum(e['k'] == 'swap' for e in ev)}", flush=True)
    print("buyers in 3+ pools:", [(a[:10], c) for a, c in buyers.most_common(15) if c >= 3], flush=True)
    json.dump(res, open(out, "w"))


if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[2], a[3], float(a[4]), float(a[5]), int(a[6]), int(a[7]) if len(a) > 7 else 25)
