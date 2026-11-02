#!/usr/bin/env python3
"""earlybuyers.py CHAIN CENSUS.json...: the 2.433 operator under any wallet, found by its bot's contract instead of its token or wallets.

Its bot bought every pool a few blocks after launch through its own contract (Robinhood 0x1cbaf24d, 20,443 B, buy selector c1120e3d;
Base 0x987d5db8, 22,816 B, buy selector 27f7e6ee); the Swap event's sender is the Universal Router, so the contract shows only as the
transaction's `to`. For every pulled pool of the census files (launch 0.5+ native): its swaps in the first WINDOW blocks (env, default 40
on Robinhood, 10 on Base: ~4 s / 20 s), each one's transaction (`to`, selector, value, sender). Then, per `to` contract that buys early in
MINPOOLS (default 5) or more pools: pools, wallets, selectors, code size and hash, and whether the code or a selector matches the
operator's; for a match, the shapes (venue, fee, tick spacing, launch size) of every pool it bought early. Also any early transaction anywhere with selector c1120e3d or 27f7e6ee. Read-only, public RPCs."""
import os, sys, json, collections
import hlib as H

WINDOW = int(os.environ.get("WINDOW", "0")) or None
MINPOOLS = int(os.environ.get("MINPOOLS", "5"))
SW4 = "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f"
SW2 = "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"
SW3 = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
REF = {"rh": "0x1cbaf24d53fe930fce8eff149fa797d2611da149", "base": "0x987d5db84d105c1f49391af409cc34c6050fb1d0"}
SELS = {"0xc1120e3d": "2.433 bot buy (Robinhood)", "0x27f7e6ee": "2.433 bot buy (Base)", "0xa0f7978d": "2.433 bot pull (Robinhood)"}


def kec(hexcode):
    from Crypto.Hash import keccak
    return keccak.new(digest_bits=256, data=bytes.fromhex(hexcode[2:])).hexdigest()


def main(ch, files):
    url = H.CH[ch]["rpc"]; win = WINDOW or (40 if ch == "rh" else 10)
    refhash = {k: kec(H.rpc(H.CH[k]["rpc"], "eth_getCode", [a, "latest"])) for k, a in REF.items()}
    pools = []
    for f in files:
        d = json.load(open(f))["chains"][ch]
        pools += [p for p in d["rugs"] if (p.get("nat_in") or 0) >= 0.5]
    shape = {p["id"]: f"{p['venue']} fee {p.get('fee', '-')} ts {p.get('ts', '-')} x {round(p.get('nat_in') or 0, 3):g}" for p in pools}
    calls = []
    for p in pools:
        bn = p["bn"]
        if p["venue"] == "v4":
            calls.append(("eth_getLogs", [{"address": p["pm"], "fromBlock": hex(bn), "toBlock": hex(bn + win), "topics": [SW4, p["id"].split(":")[1]]}]))
        else:
            calls.append(("eth_getLogs", [{"address": p["id"].split(":")[1], "fromBlock": hex(bn), "toBlock": hex(bn + win), "topics": [SW2 if p["venue"] == "v2" else SW3]}]))
    logs = H.batch(url, calls, size=10 if ch == "rh" else 5, workers=4 if ch == "rh" else 2, tries=10)
    for k in [i for i, x in enumerate(logs) if x is None]:                    # a refused batch comes back empty: ask again one by one
        try:
            logs[k] = H.rpc(url, *calls[k])
        except Exception:
            pass
    early = collections.defaultdict(set)                                       # tx hash -> pools
    for p, L in zip(pools, logs):
        for x in L or []:
            early[x["transactionHash"]].add(p["id"])
    hs = sorted(early)
    txs = H.batch(url, [("eth_getTransactionByHash", [h]) for h in hs], size=50 if ch == "rh" else 10, workers=4 if ch == "rh" else 2, tries=10)
    by_to = collections.defaultdict(lambda: {"pools": set(), "wallets": set(), "sels": collections.Counter(), "value": 0.0})
    hits = collections.Counter()
    for h, t in zip(hs, txs):
        if not t:
            continue
        to = (t.get("to") or "").lower(); sel = t["input"][:10]
        r = by_to[to]; r["pools"] |= early[h]; r["wallets"].add(t["from"].lower()); r["sels"][sel] += 1; r["value"] += int(t["value"], 16) / 1e18
        if sel in SELS:
            hits[(to, sel)] += 1
    print(f"{ch} {', '.join(os.path.basename(f) for f in files)}: {len(pools)} pulled pools ({sum(x is None for x in logs)} log queries failed), "
          f"{len(hs)} transactions swapping in the first {win} blocks ({sum(t is None for t in txs)} unread)")
    for (to, sel), n in hits.most_common():
        print(f"  SELECTOR MATCH {sel} ({SELS[sel]}) to {to}: {n} early transactions")
    rows = sorted(((to, r) for to, r in by_to.items() if len(r["pools"]) >= MINPOOLS), key=lambda kv: -len(kv[1]["pools"]))
    codes = H.batch(url, [("eth_getCode", [to, "latest"]) for to, _ in rows], size=20, workers=2)
    for (to, r), c in zip(rows, codes):
        c = c or "0x"; hh = kec(c) if len(c) > 2 else None
        tag = " ".join(f"CODE MATCH {k}" for k, v in refhash.items() if hh == v)
        print(f"  {to} pools {len(r['pools']):5d} wallets {len(r['wallets']):4d} | code {len(c) // 2 - 1:6d} B {hh[:12] if hh else '(wallet)':12s} | "
              f"selectors {r['sels'].most_common(3)} | value {r['value']:.3f} {tag}")
        if tag or any(sel in SELS for sel in r["sels"]):                         # the operator's contract: every pool shape it bought, by count
            print("      shapes: " + ", ".join(f"{k} ({n})" for k, n in collections.Counter(shape[i] for i in r["pools"]).most_common(12)))
    if not hits:
        print("  no early transaction with the 2.433 bot's selectors")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
