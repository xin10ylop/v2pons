#!/usr/bin/env python3
"""Does a chain order transactions by tip? Over N blocks from a given time: the share of transactions that offer a priority fee,
and the share of adjacent pairs (unequal tips) that sit in descending tip order inside their block. Arrival ordering gives about
50% (tips are noise to it); tip ordering gives well above it (a chain sorting by tip in rounds, ties by arrival, stays under
100%). Also the receipts' effectiveGasPrice against the base fee on a sample: on a chain that does not collect tips it equals it.

    python3 src/analysis/chain_ordering_check.py https://arb1.arbitrum.io/rpc "2026-09-10 12:00" "2026-10-07 12:00"
    python3 src/analysis/chain_ordering_check.py https://rpc.mainnet.chain.robinhood.com now
"""
import json, sys, time, calendar, urllib.request
RPC = sys.argv[1]; H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128", "Accept": "application/json"}; N = 300
def rpc(m, p):
    for i in range(8):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(), H), timeout=30))
            return r["result"]
        except Exception as e:
            err = e; time.sleep(2 + 2 * i)
    raise err
head = int(rpc("eth_blockNumber", []), 16)
def block_at(ts):
    lo, hi = 1, head
    while lo < hi:
        mid = (lo + hi) // 2
        if int(rpc("eth_getBlockByNumber", [hex(mid), False])["timestamp"], 16) < ts: lo = mid + 1
        else: hi = mid
    return lo
for when in sys.argv[2:]:
    start = head - N * 10 if when == "now" else block_at(calendar.timegm(time.strptime(when, "%Y-%m-%d %H:%M")))
    step = 10 if when == "now" else 1                     # a fast chain: every tenth block over the last N*10
    desc = asc = tot = pos = blocks = paid = nrec = 0
    for bn in range(start, start + N * step, step):
        b = rpc("eth_getBlockByNumber", [hex(bn), True]); base = int(b.get("baseFeePerGas", "0x0"), 16); tips = []
        for t in b["transactions"]:
            if t["type"] == "0x2": tips.append(min(int(t["maxPriorityFeePerGas"], 16), int(t["maxFeePerGas"], 16) - base))
            elif t["type"] in ("0x0", "0x1"): tips.append(int(t["gasPrice"], 16) - base)
        if len(tips) < 4: continue
        blocks += 1; tot += len(tips); pos += sum(1 for x in tips if x > 0)
        for a, c in zip(tips, tips[1:]):
            desc += a > c; asc += a < c
        if nrec < 40:
            for x in rpc("eth_getBlockReceipts", [hex(bn)]) or []:
                if x.get("type") in ("0x0", "0x1", "0x2"): nrec += 1; paid += int(x["effectiveGasPrice"], 16) > base
    print(f"{RPC} {when} (from block {start}): {blocks} blocks with 4+ user transactions, {tot} transactions; {pos/tot:.0%} offer a tip; "
          f"adjacent pairs in descending tip order {desc/(desc+asc):.0%}; receipts charged above the base fee {paid} of {nrec}")
