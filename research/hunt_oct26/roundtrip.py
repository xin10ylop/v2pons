#!/usr/bin/env python3
"""roundtrip.py CHAIN DAY[,DAY...] TO SELECTOR LEN [TOKEN_LEN] [WIN]: does a line let its outsiders OUT? The exit test at scale, by
tracking real wallets' token balances on the chain -- the one property that made the 2.433 seat tradeable and that every defended line fails.

The line is every pool whose launch called TO (8-hex prefix) with SELECTOR and LEN bytes (and token code TOKEN_LEN if given), as lineprobe.
For each pool it reads every swap (buy and sell) with its EOA, over WIN blocks. crew = a wallet buying in 10%+ of the line's pools (3+): the
operator's own fleet. Then, for every NON-crew, non-launcher wallet that buys:

  round trip   it sold 80%+ of the tokens it bought before the pool's liquidity pull -> return = native out / native in - 1
  cut off      the pool was pulled and it never sold 80%+ -> counted as -100%

Reports, for the line: outsiders who bought, the share that completed a round trip, their median and mean return, and the share cut off by
the pull. A 2.433-type line: most outsiders round-trip at a profit, few cut off. A honeypot or rug: the opposite. Read-only, public RPCs."""
import os, sys, json, collections, statistics as st
import hlib as H
from tape import fetch, events

CH = sys.argv[1]; DAYS = sys.argv[2].split(","); TO = sys.argv[3].lower(); SEL = sys.argv[4].lower(); LEN = int(sys.argv[5])
TLEN = int(sys.argv[6]) if len(sys.argv) > 6 and sys.argv[6] != "-" else None
WIN = int(sys.argv[7]) if len(sys.argv) > 7 else {"rh": 6000, "base": 300, "bnb": 1300, "eth": 120}[CH]
HERE = os.path.dirname(os.path.abspath(__file__)); url = H.CH[CH]["rpc"]; WN = H.CH[CH]["weth"].lower()
PUBLIC = {"rh": {"0x8876789976decbfcbbbe364623c63652db8c0904", "0xcaf681a66d020601342297493863e78c959e5cb2", "0x89e5db8b5aa49aa85ac63f691524311aeb64ed43"},
          "base": {"0x6ff5693b99212da76ad316178a184ab56d299b43", "0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24", "0x2626664c2603336e57b271c5c0b26f421741e481", "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad", "0x8cfe327cec66d1c090dd72bd0ff11d690c33a2eb"},
          "bnb": {"0x10ed43c718714eb63d5aa57b78b54704e256024e", "0x13f4ea83d0bd40e75c8222255bc855a974568dd4", "0x1906c1d672b88cd1b9ac7593301ca990f94eae07", "0xd9c500dff816a1da21a48a732d3498bf09dc9aeb", "0x111111125421ca6dc452d289314280a0f8842a65", "0x1b81d678ffb9c0263b24a97847620c99d213eb14"},
          "eth": {"0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad", "0x66a9893cc07d91d95644aedd05d03f95e1dba8af", "0x7a250d5630b4cf539739df2c5dacb4c659f2488d", "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45", "0x111111125421ca6dc452d289314280a0f8842a65", "0x3328f7f4a1d1c57c35df56bbf0c9dcafca309c49", "0x80a64c6d7f12c47b7c66c5b4e20e72bc1fcd5d9e", "0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f"}}[CH]


def load(name, default):
    try:
        return json.load(open(os.path.join(HERE, "out", name)))
    except (OSError, ValueError):
        return default


def main():
    lc = load(f"struct_launch_{CH}.json", {}); cc = load(f"token_code_{CH}.json", {})
    P = []
    for d in DAYS:
        r = json.load(open(os.path.join(HERE, f"out/{CH}_{d}_00.json")))["chains"][CH]
        rug = {p["id"]: p for p in r["rugs"]}
        miss = sorted({c[3] for c in r["created"] if c[3] not in lc})
        for i in range(0, len(miss), 2000):
            g = miss[i:i + 2000]
            for h, x in zip(g, H.batch(url, [("eth_getTransactionByHash", [h]) for h in g], size=50, workers=4, tries=10)):
                if x:
                    lc[h] = [x["from"].lower(), (x.get("to") or "").lower(), x["input"][:10], (len(x["input"]) - 2) // 2, int(x["value"], 16) / 1e18]
        json.dump(lc, open(os.path.join(HERE, "out", f"struct_launch_{CH}.json"), "w"))
        for k, tok, bn, tx, nin in r["created"]:
            t = lc.get(tx)
            if not t or not t[1].startswith(TO) or t[2] != SEL or t[3] != LEN:
                continue
            venue = k.split(":")[0]
            P.append({"id": k, "venue": venue, "tok": tok.lower(), "bn": bn, "tx": tx, "launcher": t[0], "nat": 0 if venue == "v4" or WN < tok.lower() else 1,
                      "rem_bn": bn + WIN, "pull": rug[k]["rem_bn"] if k in rug else None})
    if TLEN is not None:
        tk = sorted({p["tok"] for p in P if p["tok"] not in cc})
        from eth_utils import keccak
        for t, c in zip(tk, H.batch(url, [("eth_getCode", [t, "latest"]) for t in tk], size=50, workers=4, tries=10) if tk else []):
            cc[t] = [keccak(bytes.fromhex(c[2:])).hex()[:12], (len(c) - 2) // 2] if c and len(c) > 2 else ["nocode", 0]
        json.dump(cc, open(os.path.join(HERE, "out", f"token_code_{CH}.json"), "w"))
        P = [p for p in P if cc.get(p["tok"], ["?", 0])[1] == TLEN]
    print(f"{CH} {','.join(DAYS)}: {len(P)} pools of the line (to {TO}.. {SEL} {LEN} B{', token ' + str(TLEN) + ' B' if TLEN else ''}), window {WIN} blocks", flush=True)
    if not P:
        return
    L = fetch(CH, P)
    per = collections.defaultdict(list)
    for x in L:
        k = ("v4:" + x["topics"][1]) if x["topics"][0] == H.T_SWAP4 else (("v3:" if x["topics"][0] in (H.T_SWAP3, H.T_SWAP3_PCS) else "v2:") + x["address"].lower())
        per[k].append(x)
    # resolve every swap's EOA
    who = {}; need = set()
    for p in P:
        for x in per.get(p["id"], []):
            if x["topics"][0] not in (H.T_SWAP4, H.T_SWAP3, H.T_SWAP3_PCS, H.T_SWAP2):
                continue
            snd = "0x" + x["topics"][2][26:] if x["topics"][0] == H.T_SWAP4 else "0x" + x["topics"][1][26:]
            who[(int(x["blockNumber"], 16), int(x["logIndex"], 16))] = (snd, x["transactionHash"])
            if snd in PUBLIC:
                need.add(x["transactionHash"])
    tc = load(f"buyer_tx_{CH}.json", {})
    todo = sorted(h for h in need if h not in tc)
    for i in range(0, len(todo), 2000):
        g = todo[i:i + 2000]
        for h, x in zip(g, H.batch(url, [("eth_getTransactionByHash", [h]) for h in g], size=50, workers=4, tries=10)):
            tc[h] = x["from"].lower() if x else None
    json.dump(tc, open(os.path.join(HERE, "out", f"buyer_tx_{CH}.json"), "w"))
    eoa = lambda bn, li, snd, h: (tc.get(h) or snd) if snd in PUBLIC else snd
    # events per pool, with token amounts
    for p in P:
        p["ev"] = [(e[0], e[2], e[7], eoa(e[0], e[1], *who.get((e[0], e[1]), (None, None)))) for e in events(p, per.get(p["id"], [])) if e[0] <= p["bn"] + WIN]
    # crew: a wallet that buys in 10%+ of the pools
    c = collections.Counter()
    for p in P:
        for w in {w for _, nat, _, w in p["ev"] if nat > 0 and w}:
            c[w] += 1
    crew = {w for w, n in c.items() if n and n >= max(3, 0.1 * len(P))}
    print(f"  crew (buys in 10%+ of pools): {len(crew)}; pulled pools: {sum(1 for p in P if p['pull'] is not None)}/{len(P)}")
    trips = []; n_out = 0; cut = 0
    for p in P:
        bought = collections.defaultdict(float); sold = collections.defaultdict(float); nin = collections.defaultdict(float); nout = collections.defaultdict(float)
        for blk, nat, tok, w in sorted(p["ev"]):
            if not w or w in crew or w == p["launcher"]:
                continue
            if nat > 0:
                bought[w] += tok; nin[w] += nat
            else:
                sold[w] += -tok; nout[w] += -nat
        for w in bought:
            if bought[w] <= 0 or nin[w] <= 0:
                continue
            n_out += 1
            if sold[w] >= 0.8 * bought[w]:
                trips.append(nout[w] / nin[w] - 1)
            elif p["pull"] is not None:
                cut += 1; trips.append(-1.0)
    done = [t for t in trips if t > -0.999]
    print(f"  outsiders that bought: {n_out}")
    if n_out:
        print(f"  completed a round trip (sold 80%+ before the pull): {len(done)} ({len(done)/n_out:.0%})")
        print(f"  cut off by a pull before they could sell: {cut} ({cut/n_out:.0%})")
    if done:
        print(f"  round-trip return: median {st.median(done):+.1%}, mean {st.mean(done):+.1%}, won {sum(t>0 for t in done)}/{len(done)}")
    verdict = "TRADEABLE-SHAPED: outsiders exit at a profit" if done and len(done) / max(n_out, 1) >= 0.5 and st.median(done) > 0 else "defended: outsiders cannot reliably exit"
    print(f"  => {verdict}")


if __name__ == "__main__":
    main()
