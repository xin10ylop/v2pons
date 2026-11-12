#!/usr/bin/env python3
"""lineprobe.py CHAIN DAY[,DAY...] TO SELECTOR LEN [TOKEN_LEN] [WIN]: one launch line, pool by pool, to judge a scheduled buyer's seat.

The line: every pool the census saw created on the days whose launch transaction called TO (an 8-hex prefix) with SELECTOR and LEN bytes of
input (and, when given, a token of TOKEN_LEN bytes of code). For each pool, its first WIN blocks: every swap with its block offset, side,
native size, the transaction's sender and target; the liquidity pulls; for v4 the pool's hook and fee.

Then the line's actors: every sender that buys in 20%+ of the pools (the crew, the scheduled buyers among them), with its offset and size
spread; and the pools where someone else (an outsider) bought before the crew's first scheduled buy: what the crew did then (bought anyway,
skipped, pulled, sold into it). Read-only, public RPCs."""
import os, sys, json, collections, statistics as st
import hlib as H

CH = sys.argv[1]; DAYS = sys.argv[2].split(","); TO = sys.argv[3].lower(); SEL = sys.argv[4].lower(); LEN = int(sys.argv[5])
TLEN = int(sys.argv[6]) if len(sys.argv) > 6 and sys.argv[6] != "-" else None
WIN = int(sys.argv[7]) if len(sys.argv) > 7 else {"rh": 900, "base": 300, "bnb": 1300, "eth": 120}[CH]
HERE = os.path.dirname(os.path.abspath(__file__)); url = H.CH[CH]["rpc"]; PM = H.CH[CH]["pm"]; WN = H.CH[CH]["weth"].lower()
T_SYNC = "0x1c411e9a96e071241c2f21f7726b17ae89e3cab4c78be50e062b03a9fffbbad1"
Q96 = 2 ** 96


def load(name, default):
    try:
        return json.load(open(os.path.join(HERE, "out", name)))
    except (OSError, ValueError):
        return default


def main():
    lc = load(f"struct_launch_{CH}.json", {}); cc = load(f"token_code_{CH}.json", {}); tc = load(f"line_tx_{CH}.json", {})
    P = []
    for d in DAYS:
        r = json.load(open(os.path.join(HERE, f"out/{CH}_{d}_00.json")))["chains"][CH]
        rug = {p["id"]: p for p in r["rugs"]}
        cand = [c for c in r["created"]]
        miss = sorted({c[3] for c in cand if c[3] not in lc})
        for i in range(0, len(miss), 2000):
            g = miss[i:i + 2000]
            for h, x in zip(g, H.batch(url, [("eth_getTransactionByHash", [h]) for h in g], size=50, workers=4, tries=10)):
                if x:
                    lc[h] = [x["from"].lower(), (x.get("to") or "").lower(), x["input"][:10], (len(x["input"]) - 2) // 2, int(x["value"], 16) / 1e18]
            json.dump(lc, open(os.path.join(HERE, "out", f"struct_launch_{CH}.json"), "w"))
        for k, tok, bn, tx, nin in cand:
            t = lc.get(tx)
            if not t or not t[1].startswith(TO) or t[2] != SEL or t[3] != LEN:
                continue
            venue = k.split(":")[0]
            P.append({"id": k, "venue": venue, "tok": tok.lower(), "bn": bn, "tx": tx, "launcher": t[0], "nin": nin or 0, "day": d,
                      "nat": 0 if venue == "v4" or WN < tok.lower() else 1, "pull_census": rug[k]["rem_bn"] if k in rug else None,
                      "hooks": rug[k].get("hooks") if k in rug else None})
    tk = sorted({p["tok"] for p in P if p["tok"] not in cc})
    for t, c in zip(tk, H.batch(url, [("eth_getCode", [t, "latest"]) for t in tk], size=50, workers=4, tries=10) if tk else []):
        from eth_utils import keccak
        cc[t] = [keccak(bytes.fromhex(c[2:])).hex()[:12], (len(c) - 2) // 2] if c and len(c) > 2 else ["nocode", 0]
    if TLEN:
        P = [p for p in P if cc.get(p["tok"], ["?", 0])[1] == TLEN]
    P.sort(key=lambda p: p["bn"])
    print(f"{CH} {','.join(DAYS)}: {len(P)} pools of the line (to {TO}.. {SEL} {LEN} B{', token ' + str(TLEN) + ' B' if TLEN else ''}), window {WIN} blocks", flush=True)
    if not P:
        return
    print(f"  launchers: {collections.Counter(p['launcher'] for p in P).most_common(5)}")
    print(f"  token code: {collections.Counter(tuple(cc.get(p['tok'], ['?', 0])) for p in P).most_common(4)}")
    # logs
    for p in P:
        lo, hi = p["bn"], p["bn"] + WIN
        if p["venue"] == "v4":
            pid = p["id"][3:]
            p["logs"] = H.rpc(url, "eth_getLogs", [{"fromBlock": hex(lo), "toBlock": hex(hi), "address": PM, "topics": [[H.T_SWAP4, H.T_ML, H.T_INIT], pid]}]) or []
        else:
            a = p["id"][3:]
            tps = [[H.T_SWAP2, T_SYNC, H.T_BURN2, H.T_MINT2]] if p["venue"] == "v2" else [[H.T_SWAP3, H.T_SWAP3_PCS, H.T_BURN3, H.T_MINT3]]
            p["logs"] = H.rpc(url, "eth_getLogs", [{"fromBlock": hex(lo), "toBlock": hex(hi), "address": a, "topics": tps}]) or []
    need = sorted({x["transactionHash"] for p in P for x in p["logs"] if x["transactionHash"] not in tc})
    for i in range(0, len(need), 2000):
        g = need[i:i + 2000]
        for h, x in zip(g, H.batch(url, [("eth_getTransactionByHash", [h]) for h in g], size=50, workers=4, tries=10)):
            tc[h] = [x["from"].lower(), (x.get("to") or "").lower(), x["input"][:10], int(x.get("gasPrice") or "0x0", 16), int(x["transactionIndex"], 16)] if x else None
        json.dump(tc, open(os.path.join(HERE, "out", f"line_tx_{CH}.json"), "w"))
    # events
    for p in P:
        ev = []; sync = None; p["pulls"] = []
        for x in sorted(p["logs"], key=lambda x: (int(x["blockNumber"], 16), int(x["logIndex"], 16))):
            d = x["data"][2:]; bn = int(x["blockNumber"], 16); t0 = x["topics"][0]; who = tc.get(x["transactionHash"]) or ["?", "?", "?", 0, 0]
            if t0 == H.T_INIT:
                p["fee"] = int(d[0:64], 16); p["ts_"] = H.i256(d[64:128]); p["hooks"] = "0x" + d[128 + 24:192]
                continue
            if t0 == H.T_ML:
                if H.i256(d[128:192]) < 0 and bn > p["bn"]:
                    p["pulls"].append((bn - p["bn"], who[0]))
                continue
            if t0 in (H.T_BURN2, H.T_BURN3):
                if bn > p["bn"] and (t0 == H.T_BURN2 or int(d[0:64], 16) > 0):
                    p["pulls"].append((bn - p["bn"], who[0]))
                continue
            if t0 in (H.T_MINT2, H.T_MINT3):
                continue
            if t0 == T_SYNC:
                r0, r1 = int(d[0:64], 16), int(d[64:128], 16); sync = (r0, r1) if p["nat"] == 0 else (r1, r0)
                continue
            if t0 == H.T_SWAP2:
                a0i, a1i, a0o, a1o = (int(d[i:i + 64], 16) for i in (0, 64, 128, 192))
                nat = (a0i - a0o) if p["nat"] == 0 else (a1i - a1o); res = sync[0] / 1e18 if sync else None
            else:
                a0, a1 = H.i256(d[0:64]), H.i256(d[64:128])
                if t0 == H.T_SWAP4:
                    nat = -a0 if p["nat"] == 0 else -a1
                else:
                    nat = a0 if p["nat"] == 0 else a1
                s, liq = int(d[128:192], 16) / Q96, int(d[192:256], 16)
                res = ((liq / s) / 1e18 if p["nat"] == 0 else (liq * s) / 1e18) if s > 0 and liq > 0 else None
            ev.append((bn - p["bn"], nat / 1e18, who[0], who[1], who[2], who[4], res, x["transactionHash"]))
        p["ev"] = ev
    # the crew: senders buying in 20%+ of the pools
    n = len(P); seen = collections.defaultdict(list)
    for p in P:
        firsts = {}
        for e in p["ev"]:
            if e[1] > 0 and e[2] not in firsts and e[2] != p["launcher"]:
                firsts[e[2]] = e
        for w, e in firsts.items():
            seen[w].append((e[0], e[1], p["id"]))
    crew = {w: v for w, v in seen.items() if len(v) >= max(3, 0.2 * n)}
    print(f"\n  crew (buys in 20%+ of the {n} pools; the launcher excluded):")
    for w, v in sorted(crew.items(), key=lambda kv: st.median(x[0] for x in kv[1])):
        offs = sorted(x[0] for x in v); sz = sorted(x[1] for x in v); med = st.median(offs)
        print(f"    {w}  pools {len(v)} ({len(v)/n:.0%})  first buy +{med:g} (IQR {offs[len(offs)//4]}..{offs[3*len(offs)//4]}, {sum(abs(o-med)<=2 for o in offs)/len(offs):.0%} within 2)"
              f"  size {st.median(sz):.4g} ({sz[0]:.3g}..{sz[-1]:.3g})  via {collections.Counter((tc.get(next(e[7] for p in P if p['id']==x[2] for e in p['ev'] if e[2]==w)) or [0,'?'])[1][:10] for x in v[:20]).most_common(2)}")
    sells = collections.Counter(); pulls = collections.Counter()
    for p in P:
        for e in p["ev"]:
            if e[1] < 0:
                sells["launcher" if e[2] == p["launcher"] else ("crew" if e[2] in crew else "outsider")] += 1
        for o, w in p["pulls"]:
            pulls["launcher" if w == p["launcher"] else ("crew" if w in crew else "other")] += 1
    print(f"  sells in the window by: {dict(sells)}; pulls in the window: {sum(1 for p in P if p['pulls'])} pools, by {dict(pulls)}")
    hk = collections.Counter((p.get("hooks"), p.get("fee")) for p in P)
    print(f"  hooks/fee: {hk.most_common(4)}")
    # the scheduled anchor: the crew member with the biggest median size
    if not crew:
        return
    anchor = max(crew, key=lambda w: st.median(x[1] for x in crew[w]))
    a_med = st.median(x[0] for x in crew[anchor])
    print(f"\n  anchor (the crew's biggest scheduled buy): {anchor} at +{a_med:g}")
    out_first, clean = [], []
    for p in P:
        ab = next((e for e in p["ev"] if e[2] == anchor and e[1] > 0), None)
        lim = ab[0] if ab else a_med + 3
        ob = [e for e in p["ev"] if e[0] <= lim and e[1] >= 0.001 and e[2] not in crew and e[2] != p["launcher"] and (not ab or e is not ab)]
        ob = [e for e in ob if not ab or (e[0], e[5]) < (ab[0], ab[5])]
        (out_first if ob else clean).append((p, ab, ob))
    def fate(p, ab):
        pull = min((o for o, _ in p["pulls"]), default=None)
        return (f"anchor bought +{ab[0]} {ab[1]:.4g}" if ab else "anchor did NOT buy") + (f", pulled at +{pull}" if pull is not None else ", not pulled in window")
    print(f"  pools with an outsider buy before the anchor: {len(out_first)}; anchor bought in {sum(1 for _, ab, _ in out_first if ab)}"
          f" | clean pools: {len(clean)}; anchor bought in {sum(1 for _, ab, _ in clean if ab)}")
    print(f"  pulled in window: outsider-first {sum(1 for p, _, _ in out_first if p['pulls'])}/{len(out_first)}, clean {sum(1 for p, _, _ in clean if p['pulls'])}/{len(clean)}")
    for p, ab, ob in out_first[:40]:
        print(f"    {p['id'][:14]} launch {p['bn']}  outsiders: {[(e[0], round(e[1], 4), e[2][:10], e[3][:10]) for e in ob[:4]]}  -> {fate(p, ab)}")
    if os.environ.get("PER_POOL"):                       # a self-buy line: the launcher's own buys, everyone else's, the pulls, pool by pool
        print("\n  per pool: the launcher's buys (offset, ETH) | others' buys (offset, ETH, sender) | pulls (offset)")
        for p in P:
            lb = [(e[0], round(e[1], 3)) for e in p["ev"] if e[2] == p["launcher"] and e[1] > 0]
            ob = [(e[0], round(e[1], 4), e[2][:10]) for e in p["ev"] if e[2] != p["launcher"] and e[1] > 0]
            print(f"    {p['id'][:14]} {p['launcher'][:10]}  {lb} | {ob[:3]} | {[o for o, _ in p['pulls']][:2]}")
    if os.environ.get("SHOW"):
        for p in P[:int(os.environ["SHOW"])]:
            print(f"\n  {p['id']} launch {p['bn']} by {p['launcher'][:10]} tok {p['tok']} hooks {p.get('hooks')} fee {p.get('fee')} pulls {p['pulls']}")
            for e in p["ev"][:40]:
                tag = "L" if e[2] == p["launcher"] else ("C" if e[2] in crew else "o")
                print(f"     +{e[0]:4d} i{e[5]:3d} {'BUY ' if e[1] > 0 else 'SELL'} {abs(e[1]):9.5f} {tag} {e[2][:12]} -> {e[3][:12]} {e[4]}  pool native {e[6] if e[6] is None else round(e[6], 4)}")
    json.dump({"pools": [{k: v for k, v in p.items() if k != "logs"} for p in P], "crew": list(crew), "anchor": anchor},
              open(os.path.join(HERE, "out", f"line_{CH}_{TO}_{LEN}{'_' + str(TLEN) if TLEN else ''}.json"), "w"))


if __name__ == "__main__":
    main()
