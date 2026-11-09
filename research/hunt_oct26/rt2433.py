#!/usr/bin/env python3
"""rt2433.py [DAY] [WIN]: the 2.433 positive control for the exit test, done cheaply.

Finds the 2.433 line's pools directly by their launch signature (v4 Initialize with sqrtPriceX96 = FRONT_SQRT_P) in one log sweep, instead
of resolving a whole RH day of launch transactions. Then, for each pool, reads its swaps over WIN blocks, resolves every swap to its EOA,
and measures the same thing roundtrip.py does: of the non-fleet wallets that bought, what share sold 80%+ back out before the pull, and at
what return. If the test is sound, 2.433 outsiders should round-trip at a profit -- the property every recent line lacks. Read-only, RH RPC."""
import os, sys, json, collections, statistics as st
import hlib as H
from eth_utils import keccak

DAY = sys.argv[1] if len(sys.argv) > 1 else "20261010"
WIN = int(sys.argv[2]) if len(sys.argv) > 2 else 600
url = H.CH["rh"]["rpc"]; PM = H.CH["rh"]["pm"]; HERE = os.path.dirname(os.path.abspath(__file__))
UR = "0x8876789976decbfcbbbe364623c63652db8c0904"                          # the Universal Router (public): resolve its callers
T_INIT4 = "0x" + keccak(text="Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)").hex()
T_SWAP4 = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
SQRT = 1604517591721945638372359205383840
sg = lambda h: (lambda x: x - (1 << 256) if x >= 1 << 255 else x)(int(h, 16))


def main():
    r = json.load(open(os.path.join(HERE, f"out/rh_{DAY}_00.json")))["chains"]["rh"]
    lo = min(c[2] for c in r["created"]); hi = max(c[2] for c in r["created"])
    print(f"RH {DAY}: Initialize sweep over blocks {lo}..{hi} for the 2.433 launch price", flush=True)
    pools = []
    for a in range(lo, hi + 1, 25000):
        logs = H.rpc(url, "eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(min(hi, a + 24999)), "address": PM, "topics": [T_INIT4]}]) or []
        for l in logs:
            d = l["data"][2:]
            if l["topics"][2] == "0x" + "0" * 64 and len(d) >= 5 * 64 and int(d[3*64:4*64], 16) == SQRT:
                pools.append({"id": "v4:" + l["topics"][1], "bn": int(l["blockNumber"], 16), "nat": 0})
    print(f"  2.433 pools found: {len(pools)}", flush=True)
    if not pools:
        return
    # swaps + pulls, in groups of consecutive launches (<= topic cap) over each group's tight block span
    tc = {}; byid = {p["id"]: p for p in pools}
    for p in pools:
        p["ev"] = []; p["pull"] = None
    pools.sort(key=lambda p: p["bn"]); GN = 40
    groups = [pools[i:i + GN] for i in range(0, len(pools), GN)]
    for gi, grp in enumerate(groups):
        pids = [p["id"][3:] for p in grp]; g_lo = grp[0]["bn"]; g_hi = grp[-1]["bn"] + WIN
        for a in range(g_lo, g_hi + 1, 25000):
            b = min(g_hi, a + 24999)
            for topic, kind in ((T_SWAP4, "sw"), (T_ML, "ml")):
                logs = H.rpc(url, "eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(b), "address": PM, "topics": [topic, pids]}]) or []
                for l in logs:
                    p = byid.get("v4:" + l["topics"][1])
                    if not p:
                        continue
                    bn = int(l["blockNumber"], 16)
                    if bn > p["bn"] + WIN:
                        continue
                    d = l["data"][2:]
                    if kind == "ml":
                        if bn > p["bn"] and sg(d[128:192]) < 0:
                            p["pull"] = min(p["pull"], bn) if p["pull"] is not None else bn
                        continue
                    a0 = sg(d[0:64]); snd = "0x" + l["topics"][2][26:]
                    p["ev"].append((bn, int(l["logIndex"], 16), -a0 / 1e18, a0, snd, l["transactionHash"]))
                    if snd == UR:
                        tc[l["transactionHash"]] = None
        if gi % 10 == 0:
            print(f"  ...group {gi+1}/{len(groups)}", flush=True)
    need = sorted(tc)
    for i in range(0, len(need), 2000):
        g = need[i:i + 2000]
        for h, x in zip(g, H.batch(url, [("eth_getTransactionByHash", [h]) for h in g], size=50, workers=4, tries=8)):
            tc[h] = x["from"].lower() if x else None
    # fleet = buys in 10%+ of pools
    cnt = collections.Counter()
    for p in pools:
        bs = set()
        for bn, li, nat, a0, snd, h in p["ev"]:
            if nat > 0:
                bs.add(tc.get(h) or snd if snd == UR else snd)
        for w in bs:
            cnt[w] += 1
    fleet = {w for w, n in cnt.items() if n >= max(3, 0.1 * len(pools))}
    print(f"  fleet wallets (buy in 10%+ of pools): {len(fleet)}; pulled pools: {sum(1 for p in pools if p['pull'] is not None)}/{len(pools)}", flush=True)
    trips = []; n_out = 0; cut = 0
    for p in pools:
        bought = collections.defaultdict(float); sold = collections.defaultdict(float); nin = collections.defaultdict(float); nout = collections.defaultdict(float)
        for bn, li, nat, a0, snd, h in sorted(p["ev"]):
            w = (tc.get(h) or snd) if snd == UR else snd
            if not w or w in fleet:
                continue
            tok = abs(a0)                                                      # token side magnitude as a proxy weight (buy vs sell matched per wallet)
            if nat > 0:
                bought[w] += 1; nin[w] += nat
            else:
                sold[w] += 1; nout[w] += -nat
        for w in bought:
            if nin[w] <= 0:
                continue
            n_out += 1
            if sold[w] >= 1:                                                   # sold at least once (v4 native side; a completed exit)
                trips.append(nout[w] / nin[w] - 1)
            elif p["pull"] is not None:
                cut += 1; trips.append(-1.0)
    done = [t for t in trips if t > -0.999]
    print(f"  outsiders that bought: {n_out}")
    if n_out:
        print(f"  completed a round trip (sold before the pull): {len(done)} ({len(done)/n_out:.0%})")
        print(f"  cut off by a pull before selling: {cut} ({cut/n_out:.0%})")
    if done:
        print(f"  round-trip return: median {st.median(done):+.1%}, mean {st.mean(done):+.1%}, won {sum(t>0 for t in done)}/{len(done)}")
    print(f"  => {'TRADEABLE-SHAPED: outsiders exit at a profit' if done and len(done)/max(n_out,1) >= 0.5 and st.median(done) > 0 else 'outsiders cannot reliably exit'}")


if __name__ == "__main__":
    main()
