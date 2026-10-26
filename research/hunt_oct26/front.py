#!/usr/bin/env python3
"""front.py CENSUS.json OUT.json [MIN_POOLS] [SAMPLE]: the front seat on every pump-and-pull line of a census.py window, measured by outcome.

research/chase/seattest.py calls a seat closed when the pull comes within ~10 s of an outside buy. On the 2.433 line that was every pool:
the bot bought within those seconds, we sold into it, and the pull came after (T+3). This test asks instead what made the 2.433 line pay:

  fleet     wallets (the transaction's sender) buying in a quarter of the sampled pools or more (3 at least), not a launch wallet
  pre       the first outside buy before the fleet's first buy (dust under 0.2% of the pool apart), and what followed it:
              CAME   the fleet still bought, and the pull came at least 2 blocks after the fleet's first buy (an exit existed)
              NONE   the fleet never bought before the pull (skipped or pulled on the outsider)
  early     outsiders whose first buy came before the fleet's first buy (or, with no fleet, in the first 20 blocks) and who sold before the
            pull: their realised native profit in the pool (sells minus buys), per pool and per wallet. Money taken out at the front seat.
  seat      paper: buy 1% of the pool's native at launch+1, sell in the block after the fleet's 1st / 3rd buy (-100% if the pull is first),
            the pool's own fee each leg (V2 0.3%; v4/V3 the pool's fee)

A line: pulled pools of one shape and one launch size (3 significant figures), or, for the rest, one shape and one launch target (launcher
contract or router) with any size; MIN_POOLS (8) pools and 3+ launch wallets. SAMPLE (14) pools a line, spread over the window.
Verdict: OPEN (outsiders came in ahead of the fleet and the fleet still came in most pools), CLOSED (it did not), UNTESTED (nobody tried).
Read-only, public RPCs."""
import os, sys, json, collections, statistics as st, concurrent.futures as cf
import hlib as H

MIN_POOLS = int(sys.argv[3]) if len(sys.argv) > 3 else 8
SAMPLE = int(sys.argv[4]) if len(sys.argv) > 4 else 14
# routers anyone can call: never the operator's own contract, even when its pull goes through one
PUBLIC = {"rh": {"0x8876789976decbfcbbbe364623c63652db8c0904"},
          "base": {"0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24", "0x6ff5693b99212da76ad316178a184ab56d299b43", "0x8cfe327cec66d1c090dd72bd0ff11d690c33a2eb",
                   "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad", "0x2626664c2603336e57b271c5c0b26f421741e481"}}
# routers and wallets proven independent by summarize.py (profits on two or more operators' pools), plus ours and the D65 crew's
INDEP = {"0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc", "0xfd1b271f235e5230eaee9d914ccb1af495bfb758", "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957",
         "0x0e24493c662e62b33d371376e0ac181eb193a31d", "0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8", "0x492a40b43ce221ec2c952cda473f441e365dea62"}
for _f in ("out/indep_rh.json", "out/indep_base.json"):
    try:
        INDEP |= set(json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), _f))))
    except (OSError, ValueError):
        pass


def swaps(ch, p, cap=400):
    lo, hi = p["bn"], p["rem_bn"] + 2
    if p["venue"] == "v4":
        L = H.logs(ch, lo, hi, [H.T_SWAP4, p["id"][3:]], p["pm"], workers=1)
    else:
        L = H.logs(ch, lo, hi, [H.T_SWAP2 if p["venue"] == "v2" else H.T_SWAP3], p["id"][3:], workers=1)
    L = sorted(L, key=lambda x: (int(x["blockNumber"], 16), int(x["logIndex"], 16)))[:cap]
    ev = []
    for x in L:
        d = x["data"][2:]; bn = int(x["blockNumber"], 16)
        if p["venue"] == "v2":
            a0i, a1i, a0o, a1o = (int(d[i:i + 64], 16) for i in (0, 64, 128, 192))
            nat = ((a0i - a0o) if p["nat"] == 0 else (a1i - a1o)) / 1e18
        elif p["venue"] == "v4":
            nat = -H.i256(d[0:64] if p["nat"] == 0 else d[64:128]) / 1e18
        else:
            nat = H.i256(d[0:64] if p["nat"] == 0 else d[64:128]) / 1e18
        ev.append({"bn": bn, "nat": nat, "tx": x["transactionHash"]})
    txs = H.batch(H.CH[ch]["rpc"], [("eth_getTransactionByHash", [e["tx"]]) for e in ev], workers=2)
    for e, t in zip(ev, txs):
        e["who"] = t["from"].lower() if t else None; e["via"] = (t.get("to") or "").lower() if t else None
    p["sw"] = ev
    return p


def cp(N, flows, s=0.0, fee=0.003):
    """constant product from (N native, 1 token): our buy s first (after fee), then the flows; returns (x, y, our tokens)"""
    x, y, got = N, 1.0, 0.0
    if s:
        nx = x + s * (1 - fee); got = y - x * y / nx; y = x * y / nx; x = nx
    for b in flows:
        if b and x + b > 0:
            nx = x + b; y = x * y / nx; x = nx
    return x, y, got


def sell(x, y, got, fee):
    ny = y + got
    return (x - x * y / ny) * (1 - fee)


def test_line(ch, ps, bt):
    ps = sorted(ps, key=lambda p: p["bn"])
    take = ps[:: max(1, len(ps) // SAMPLE)][:SAMPLE]
    with cf.ThreadPoolExecutor(4) as ex:
        take = [p for p in ex.map(lambda p: _safe(ch, p), take) if p.get("sw") is not None]
    if not take:
        return None
    launchers = {p.get("frm") for p in ps}
    # the operator's own contract: the pull transaction's target, when it is not a public router; buys through it are the fleet's
    pt = H.batch(H.CH[ch]["rpc"], [("eth_getTransactionByHash", [p["rem_tx"]]) for p in take if p.get("rem_tx")])
    pull_to = collections.Counter((t.get("to") or "").lower() for t in pt if t)
    op_routers = {a for a, c in pull_to.items() if c >= len(pt) / 2 and a not in PUBLIC.get(ch, ())}
    cnt = collections.Counter(w for p in take for w in {e["who"] for e in p["sw"] if e["who"] and e["nat"] > 0})
    recurring = {w for w, c in cnt.items() if c >= max(3, len(take) // 4) and w not in launchers}
    # a recurring wallet that sells most of what it bought before the pull, in most of its pools, is a fronter, not the fleet
    rt = collections.Counter(); seen = collections.Counter()
    for p in take:
        for w in recurring:
            es = [e for e in p["sw"] if e["who"] == w and e["bn"] <= p["rem_bn"]]
            b = sum(e["nat"] for e in es if e["nat"] > 0)
            if b > 0:
                seen[w] += 1
                rt[w] += -sum(e["nat"] for e in es if e["nat"] < 0) >= 0.5 * b
    # a recurring wallet that sells what it bought before the pull is an outside fronter only when it is proven independent (summarize.py:
    # profits on two or more operators' pools, or ours / the D65 crew's); otherwise it is the line's own round-tripping fleet (operator A's
    # 98 recurring wallets buy at 2 s and sell at 5-8 s, whitelisted)
    indep_via = {e["who"] for p in take for e in p["sw"] if e["via"] in INDEP}
    fronters = {w for w in recurring if rt[w] >= 0.5 * seen[w] and (w in INDEP or w in indep_via)}
    # a private router that 10+ wallets of this line call (or 5+, each in about one pool) is the line's own machinery (its fleet), unless
    # summarize.py found it profiting on several pool types (an independent bot: D65's routers also ran a fresh wallet per pool)
    via_w = collections.defaultdict(collections.Counter)
    for p in take:
        for w, v in {(e["who"], e["via"]) for e in p["sw"] if e["nat"] > 0 and e["via"]}:
            via_w[v][w] += 1
    for v, ws in via_w.items():
        if v not in PUBLIC.get(ch, ()) and v not in INDEP and (len(ws) >= 10 or (len(ws) >= 5 and st.median(ws.values()) <= 1.5)):
            op_routers.add(v)
    fleet = (recurring - fronters) | {e["who"] for p in take for e in p["sw"] if e["via"] in op_routers and e["nat"] > 0}
    r = {"n": len(ps), "sampled": len(take), "launchers": len(launchers), "fleet": len(fleet), "fronters": sorted(fronters), "op_routers": sorted(op_routers),
         "pull_to": pull_to.most_common(3), "size_med": st.median(p.get("nat_in") or 0 for p in ps),
         "pull_med_min": st.median(p["pull_min"] for p in ps), "first": [], "nbuys": [], "fleet_in": [], "pump": [], "seat1": [], "seat3": [],
         "pre": collections.Counter(), "pre_ex": [], "early": collections.defaultdict(lambda: [0, 0, 0.0, 0.0]), "early_pools": 0,
         "via": collections.Counter(), "first_bn": [], "pools": [], "real": collections.Counter(), "real_ex": [], "real_exit": 0,
         "rule": "exit-window"}
    for p in take:
        N = p.get("nat_in") or 0
        if N <= 0:
            continue
        a0 = p.get("add_bn", p["bn"]); pull = p["rem_bn"]
        fee = 0.003 if p["venue"] == "v2" else (p.get("fee", 3000) if p.get("fee", 3000) < 1 << 23 else 3000) / 1e6
        sw = [e for e in p["sw"] if e["bn"] <= pull]
        fb = [e for e in sw if e["who"] in fleet and e["nat"] >= 0.005 * N]      # the fleet's real-size buys (its dust and decoys apart)
        T = fb[0]["bn"] if fb else None
        r["pools"].append({"id": p["id"], "bn": p["bn"], "N": N, "T": (T - a0) if T else None, "pull": pull - a0, "nb": len(fb)})
        if fb:
            r["first"].append(T - a0); r["nbuys"].append(len(fb)); r["fleet_in"].append(sum(e["nat"] for e in fb) / N)
            for e in fb:
                r["via"][e["via"]] += 1
            flows_all = [e["nat"] for e in sw if e["who"] in fleet]
            x, y, _ = cp(N, flows_all); r["pump"].append((x / y) / N)
            s = 0.01 * N
            for k, key in ((1, "seat1"), (3, "seat3")):
                if len(fb) < k:
                    r[key].append(-1.0 if pull <= T + 1 else 0.0); continue
                ex_bn = fb[k - 1]["bn"] + 1
                if ex_bn >= pull:
                    r[key].append(-1.0); continue
                flows = [e["nat"] for e in sw if e["who"] in fleet and e["bn"] < ex_bn]
                x, y, got = cp(N, flows, s, fee); r[key].append(sell(x, y, got, fee) / s - 1)
        dust = 0.0005 * N
        outs = [e for e in sw if e["who"] and e["who"] not in fleet and e["who"] not in launchers]
        for e in outs:
            if e["nat"] >= dust and (T is None or e["bn"] < T):
                tag = "CAME" if T is not None and pull >= T + 2 else "NONE"
                r["pre"][tag] += 1; r["pre_ex"].append([round(e["nat"], 5), e["bn"] - a0, (T - a0) if T else None, pull - a0, tag, e["who"]])
                break
        per = collections.defaultdict(list)
        for e in outs:
            per[e["who"]].append(e)
        hit = False
        for w, es in per.items():
            buys = [e for e in es if e["nat"] > 0]; sells = [e for e in es if e["nat"] < 0]
            if not buys or not sells:
                continue
            fbuy = buys[0]["bn"]
            if (T is not None and fbuy < T) or (T is None and fbuy - a0 <= 20):
                pnl = -sum(e["nat"] for e in es); paid = sum(e["nat"] for e in buys)
                if paid < dust / 4:
                    continue
                d = r["early"][w]; d[0] += 1; d[1] += pnl > 0; d[2] += pnl; d[3] += paid; hit = True
        r["early_pools"] += hit
        # every real-size outside buy, the losers included: did its buyer get out, or was it pulled on within ~10 s while still holding
        # with no fleet buy to sell into first (the trap the owner described: left holding a token it cannot sell)
        real = max(0.001, 0.0005 * N); react = max(2, int(10 / bt))
        for e in outs:
            if e["nat"] < real:
                continue
            later = [x for x in sw if x["bn"] > e["bn"] or (x["bn"] == e["bn"] and x is not e and sw.index(x) > sw.index(e))]
            sold = any(x["who"] == e["who"] and x["nat"] < 0 for x in later)
            # the exit the 2.433 line gave us: a real-size fleet buy after ours with a block left to sell into it before the pull
            win = [x for x in later if x["who"] in fleet and x["nat"] >= 0.005 * N and x["bn"] <= pull - 2]
            if sold:
                tag = "SOLD"
            elif pull - e["bn"] <= react and not win:          # pulled within ~10 s, still holding, and no exit ever existed
                tag = "RUGGED"
            else:
                tag = "HELD"                                  # an exit window existed (or the pull came late); the buyer kept it
            r["real"][tag] += 1
            if win:
                r["real_exit"] += 1
            if len(r["real_ex"]) < 40:
                r["real_ex"].append([round(e["nat"], 5), e["bn"] - a0, pull - a0, tag, e["who"], len(win), round(sum(x["nat"] for x in win), 4)])
    r["early"] = {w: v for w, v in sorted(r["early"].items(), key=lambda kv: -kv[1][2])}
    top = list(r["early"])[:5]
    nn = H.batch(H.CH[ch]["rpc"], [("eth_getTransactionCount", [w, "latest"]) for w in top])
    for w, n in zip(top, nn):
        r["early"][w] = r["early"][w] + [int(n, 16) if n else None]
    return r


def _safe(ch, p):
    try:
        return swaps(ch, p)
    except Exception as e:
        p["sw"] = None; p["err"] = str(e)[:80]
        return p


def lines(rugs):
    g = collections.defaultdict(list); used = set()
    shp = lambda p: f"{p['venue']} fee {p.get('fee', '-')} ts {p.get('ts', '-')}" + (" hook" if p.get("hooks", H.ZERO) != H.ZERO else "")
    for p in rugs:
        if (p.get("nat_in") or 0) > 0:
            g[(shp(p), f"{float(f'{p["nat_in"]:.3g}'):g}")].append(p)
    out = {}
    for k, v in g.items():
        if len(v) >= MIN_POOLS and len({p.get("frm") for p in v}) >= 3:
            out[f"{k[0]} x {k[1]}"] = v; used.update(p["id"] for p in v)
    g2 = collections.defaultdict(list)
    for p in rugs:
        if p["id"] not in used and (p.get("nat_in") or 0) > 0 and p.get("to"):
            g2[(shp(p), p["to"])].append(p)
    for k, v in g2.items():
        if len(v) >= MIN_POOLS and len({p.get("frm") for p in v}) >= 3:
            out[f"{k[0]} via {k[1]}"] = v
    return out


def verdict(t):
    """TRAP when real-size outside buys get pulled on before their buyer can sell (half or more); TOLERANT when 3+ were made and at most a
    fifth were; otherwise the pre-fleet test (OPEN / CLOSED) or UNTESTED"""
    rl = t["real"]; n = rl["SOLD"] + rl["RUGGED"] + rl["HELD"]
    if n >= 2 and rl["RUGGED"] >= 0.5 * n:
        return "TRAP"
    pre = t["pre"]
    if n >= 3 and rl["RUGGED"] <= 0.2 * n and rl["SOLD"] >= 2:
        return "TOLERANT" + ("+OPEN" if pre["CAME"] >= 2 and pre["CAME"] >= 2 * pre["NONE"] else "")
    if pre["CAME"] >= 2 and pre["CAME"] >= 2 * pre["NONE"]:
        return "OPEN"
    if pre["CAME"] + pre["NONE"] >= 2:
        return "CLOSED"
    return "UNTESTED"


def summary(name, t):
    m = lambda xs: st.median(xs) if xs else float("nan")
    win = sum(v[1] for v in t["early"].values()); n_e = sum(v[0] for v in t["early"].values()); pnl = sum(v[2] for v in t["early"].values())
    top = list(t["early"].items())[:3]
    return (f"  {t['n']:4d} {name[:58]:58s} fleet {t['fleet']:3d} T+{m(t['first']):<5g} buys {m(t['nbuys']):<4g} in x{m(t['fleet_in']):.2f} pump x{m(t['pump']):.2f}"
            f" pull {t['pull_med_min']:.1f}m | seat1 {m(t['seat1']):+.1%} seat3 {m(t['seat3']):+.1%} | pre CAME {t['pre']['CAME']} NONE {t['pre']['NONE']}"
            f" | real outside buys SOLD {t['real']['SOLD']} RUGGED {t['real']['RUGGED']} HELD {t['real']['HELD']}"
            f" | early {t['early_pools']}/{t['sampled']} pools, {win}/{n_e} won, {pnl:+.4f} | {verdict(t)}"
            + (f"\n        fronters (recurring round-trippers) {t['fronters'][:6]} op routers {t['op_routers']}" if t["fronters"] or t["op_routers"] else "")
            + "".join(f"\n        early {w} pools {v[0]} won {v[1]} pnl {v[2]:+.5f} paid {v[3]:.5f} nonce {v[4] if len(v) > 4 else '?'}" for w, v in top))


def main(path, out):
    d = json.load(open(path)); ch = next(iter(d["chains"])); r = d["chains"][ch]
    L = lines(r["rugs"])
    if os.environ.get("SKIP_KNOWN"):                       # lines the earlier reports already settled as traps: not re-tested (the 2.433 line kept as the control)
        import verdicts
        L = {k: v for k, v in L.items() if not verdicts.label(ch, k, [p.get("to") for p in v]) or "2.433" in verdicts.label(ch, k, [p.get("to") for p in v])}
    print(f"{ch} {r.get('window')}: {len(r['rugs'])} pulled pools, {len(L)} lines", flush=True)
    res = {}
    for name, ps in sorted(L.items(), key=lambda kv: -len(kv[1])):
        t = test_line(ch, ps, r["bt"])
        if not t:
            print(f"  {name}: unreadable", flush=True); continue
        t["verdict"] = verdict(t); t["targets"] = [p.get("to") for p in ps]; res[name] = t
        print(summary(name, t), flush=True)
        json.dump({"chain": ch, "window": r.get("window"), "lines": res}, open(out, "w"), default=lambda o: dict(o) if isinstance(o, collections.Counter) else list(o))
    json.dump({"chain": ch, "window": r.get("window"), "lines": res}, open(out, "w"), default=lambda o: dict(o) if isinstance(o, collections.Counter) else list(o))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
