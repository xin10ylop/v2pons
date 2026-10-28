#!/usr/bin/env python3
"""bnb2433_seat.py [--hours 6]: is the 2.433 operator's BNB line still closed to outside buyers? Its pools in the last HOURS, found the way
watch2433.py finds them (PancakeSwap V2 pairs whose token has the operator's byte-identical code), then every Swap of each pair until it
was pulled (its own liquidity burnt) or the window ended. Buyers are the pair Swap's `to` (the receiving wallet, or a router).

  fleet      a receiver buying in a quarter of the pools or more (3 at least)
  outsider   every other receiver
Per outsider buy (BNB in): its size, whether the pull followed within 10 / 30 blocks, and whether that receiver sold before the pull.
Prints the totals and the size bands (dust under 0.001 BNB, real 0.001+). Read-only, public RPCs."""
import sys, collections, statistics as st, concurrent.futures as cf
import watch2433 as W

BOT_NONCE = 2000
HOURS = float(sys.argv[sys.argv.index("--hours") + 1]) if "--hours" in sys.argv else 6.0
WBNB = "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"
T_SWAP2 = "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"
T_BURN = "0xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496"
T_MINT = "0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f"


def main():
    from Crypto.Hash import keccak
    kec = lambda b: keccak.new(digest_bits=256, data=b).hexdigest()
    urls = W.EP["bsc_logs"]; head = int(W.call(urls, "eth_blockNumber", []), 16); a0 = head - int(HOURS * 3600 / W.BLOCK_S["bsc"])
    pairs = []
    for a in range(a0, head + 1, 2000):
        for l in W.call(urls, "eth_getLogs", [{"address": W.PCS_V2_FACTORY, "topics": [W.T_PAIR], "fromBlock": hex(a), "toBlock": hex(min(a + 1999, head))}]):
            t0, t1 = "0x" + l["topics"][1][26:], "0x" + l["topics"][2][26:]
            tok = t1 if t0 == WBNB else t0 if t1 == WBNB else None
            if tok and tok.endswith(("7777", "ffff", "8888")):
                pairs.append((tok, "0x" + l["data"][26:66], int(l["blockNumber"], 16), t0 == WBNB))

    def is_op(p):
        try:
            c = W.call(W.EP["bsc"], "eth_getCode", [p[0], "latest"], tries=3)
            return len(c) > 2 and kec(bytes.fromhex(c[2:])) == W.OP_TOKEN_CODEHASH
        except Exception:
            return False
    with cf.ThreadPoolExecutor(10) as ex:
        ops = [p for p, ok in zip(pairs, ex.map(is_op, pairs)) if ok]
    print(f"bsc, last {HOURS:g} h (blocks {a0}-{head}): {len(pairs)} vanity WBNB pairs, {len(ops)} with the operator's token")

    def read(p):
        tok, pair, b0, wbnb0 = p
        L = []
        for a in range(b0, head + 1, 2000):
            L += W.call(urls, "eth_getLogs", [{"address": pair, "fromBlock": hex(a), "toBlock": hex(min(a + 1999, head))}])
            if any(x["topics"][0] == T_BURN for x in L):
                break
        burns = [int(x["blockNumber"], 16) for x in L if x["topics"][0] == T_BURN]
        mint = next((x for x in L if x["topics"][0] == T_MINT), None)
        liq = int(mint["data"][2:66] if wbnb0 else mint["data"][66:130], 16) / 1e18 if mint else None
        sw = []
        for x in L:
            if x["topics"][0] != T_SWAP2:
                continue
            d = x["data"][2:]; a0i, a1i, a0o, a1o = (int(d[i:i + 64], 16) for i in range(0, 256, 64))
            bnb_in = (a0i - a0o) if wbnb0 else (a1i - a1o)
            sw.append((int(x["blockNumber"], 16), bnb_in / 1e18, "0x" + x["topics"][2][26:]))
        return {"pair": pair, "b0": b0, "pull": min(burns) if burns else None, "liq": liq, "sw": sw}
    with cf.ThreadPoolExecutor(6) as ex:
        P = list(ex.map(read, ops))
    pulled = [p for p in P if p["pull"]]
    life = [(p["pull"] - p["b0"]) * W.BLOCK_S["bsc"] for p in pulled]
    print(f"  pulled {len(pulled)} of {len(P)}; launch BNB median {st.median([p['liq'] for p in P if p['liq']] or [0]):.3f}; life median {st.median(life) if life else 0:.0f} s")
    seen = collections.Counter()
    for p in P:
        for r in {s[2] for s in p["sw"] if s[1] > 0}:
            seen[r] += 1
    fleet = {r for r, c in seen.items() if c >= max(3, len(P) / 4)}
    print(f"  fleet receivers {len(fleet)}; swaps {sum(len(p['sw']) for p in P)}")
    cand = sorted({s[2] for p in pulled for s in p["sw"] if s[1] > 0 and s[2] not in fleet})
    with cf.ThreadPoolExecutor(10) as ex:
        nonce = dict(zip(cand, ex.map(lambda a: int(W.call(W.EP["bsc"], "eth_getTransactionCount", [a, "latest"], tries=3), 16), cand)))
    bots = {a for a, n in nonce.items() if n >= BOT_NONCE}
    print(f"  buyers outside the fleet {len(cand)}: {len(bots)} with {BOT_NONCE}+ transactions (the operator's rotating bots), {len(cand) - len(bots)} genuine")
    fleet |= bots
    rows = []
    for p in pulled:
        sold = collections.defaultdict(bool)
        for b, v, r in p["sw"]:
            if v < 0 and b < p["pull"]:
                sold[r] = True
        firsts = {}
        for b, v, r in p["sw"]:
            if v > 0 and r not in fleet and r not in firsts and b < p["pull"]:
                firsts[r] = (b, v)
        for r, (b, v) in firsts.items():
            rows.append({"size": v, "dt": p["pull"] - b, "out": sold[r], "in_s": (b - p["b0"]) * W.BLOCK_S["bsc"], "who": r})
    for name, sel in (("dust < 0.001 BNB", lambda r: r["size"] < 0.001), ("real >= 0.001 BNB", lambda r: r["size"] >= 0.001)):
        rs = [r for r in rows if sel(r)]
        if not rs:
            print(f"  outsiders, {name}: none"); continue
        print(f"  outsiders, {name}: {len(rs)} buys | pull within 10 blocks {sum(r['dt'] <= 10 for r in rs) / len(rs):.0%}, 30 blocks {sum(r['dt'] <= 30 for r in rs) / len(rs):.0%}"
              f" | median {st.median(r['dt'] for r in rs):.0f} blocks after | size median {st.median(r['size'] for r in rs):.4f}"
              f" | in at median {st.median(r['in_s'] for r in rs):.0f} s")


if __name__ == "__main__":
    main()
