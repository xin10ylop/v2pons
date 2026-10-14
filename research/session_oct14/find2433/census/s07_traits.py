"""Step 7: score the 2.433 traits per family (s04 rows, s05 events, s06 txs).
Per family: launches, rate per day, fresh launcher (distinct senders, sender nonce), the repeat buyers (actor = tx.to + selector of a buy in
[L+1, L+EARLY]) with coverage, first-buy offset p10/p50/p90, size, wallet set, minOut tolerance (largest calldata word in (0.5, 1] x tokens
out), outsiders before the repeat buyer and what happened to those pools, pull timing. Writes s07_traits.json and prints s07_traits.out."""
import sys, collections, statistics
from common import *
EARLY = 80
ETHUSD = 2570.0
rows = {r["pid"]: r for r in jload("s04_launches.json")}
tg = {t["pid"]: t for t in jload("s05_targets.json")}
EV = {p["pid"]: p for p in jl_load("s05_events_cache.jsonl")}
TX = {r["h"]: r for r in jl_load("s06_tx_cache.jsonl") if "miss" not in r}
DEC = {"ETH": 18, "WETH": 18, "USDG": 6}
def q(xs, f):
    xs = sorted(xs); return xs[min(len(xs) - 1, int(f * len(xs)))] if xs else None
def pct(xs): return "%s/%s/%s" % (q(xs, .1), q(xs, .5), q(xs, .9)) if xs else "-"
def eth_of(amt, quote):
    if quote in ("ETH", "WETH"): return amt / 1e18
    if quote == "USDG": return amt / 1e6 / ETHUSD
    return None
def swaps(p, r):
    """[(bn, ti, li, h, router, buy?, eth_in_or_out, tok_amt, sqrt_after)] for the pool, quote-aware."""
    out = []
    quote_is_0 = r["c0"] in (E, WETH, USDG)
    for s in p["sw"]:
        d = s[5]; a0, a1 = sgn(W(d, 0)), sgn(W(d, 1)); sq = W(d, 2)
        if p["ven"] == "v4":
            qd, td = (a0, a1) if quote_is_0 else (a1, a0)       # swapper deltas: negative = paid in
            buy = qd < 0; qa = -qd if buy else qd; ta = td if buy else -td
        else:
            qd, td = (a0, a1) if quote_is_0 else (a1, a0)       # pool deltas: positive = pool received
            buy = qd > 0; qa = qd if buy else -qd; ta = -td if buy else td
        out.append(dict(bn=s[0], ti=s[1], li=s[2], h=s[3], rt=s[4], buy=buy, q=qa, eth=eth_of(qa, r["q"]), tok=ta, sq=sq))
    return out
def pulls(p):
    """first liquidity removal block and its tx (v4 ModifyLiquidity < 0, V3 Burn amount > 0)"""
    if p["ven"] == "v4":
        neg = [m for m in p["ml"] if sgn(W(m[5], 2)) < 0]
        pos = [m for m in p["ml"] if sgn(W(m[5], 2)) > 0]
    else:
        neg = [m for m in p["ml"] if m[5][0] == T_V3BURN and W(m[6], 0) > 0]
        pos = [m for m in p["ml"] if m[5][0] == T_V3MINT]
    return (neg[0] if neg else None), pos
def actor(h):
    t = TX.get(h)
    return (t["to"][:10] + ":" + t["s"]) if t else "?"
def minout_ratio(h, tok_out):
    t = TX.get(h)
    if not t or "in" not in t or tok_out <= 0: return None
    inp = t["in"]; ws = []
    for i in range((len(inp) - 10) // 64):
        try: ws.append(int(inp[10 + 64 * i: 10 + 64 * (i + 1)], 16))
        except ValueError: pass
    c = [w for w in ws if tok_out * 0.5 < w <= tok_out]
    return max(c) / tok_out if c else None
def analyse(pids, label):
    P = []
    for pid in pids:
        r = rows[pid]; p = EV.get(pid)
        if not p: continue
        L = r["b"]; sw = swaps(p, r); pl, adds = pulls(p)
        launcher = r["frm"]
        P.append(dict(pid=pid, r=r, L=L, sw=sw, pull=(pl[0] - L if pl else None), pull_tx=(pl[3] if pl else None), adds=adds, launcher=launcher))
    n = len(P)
    if not n: return None
    res = dict(label=label, n=n)
    span_h = max(1e-9, (max(x["r"]["t"] for x in P) - min(x["r"]["t"] for x in P)) / 3600)
    res["first"] = hm(min(x["r"]["t"] for x in P)); res["last"] = hm(max(x["r"]["t"] for x in P))
    res["per_day"] = round(n / max(span_h, 1) * 24, 1)
    snd = collections.Counter(x["launcher"] for x in P)
    res["senders"] = len(snd); res["max_per_sender"] = snd.most_common(1)[0][1]
    res["sender_nonce"] = pct([x["r"]["n"] for x in P])
    # buys by actor in [L+1, L+EARLY], excluding the launch tx and the launcher's own txs
    act = collections.defaultdict(list)
    for x in P:
        seen = set()
        for s in x["sw"]:
            if not s["buy"] or s["bn"] > x["L"] + EARLY or s["h"] == x["r"]["h"]: continue
            t = TX.get(s["h"])
            if t and t["f"] == x["launcher"]: continue
            a = actor(s["h"])
            if a in seen: continue
            seen.add(a)
            act[a].append(dict(pid=x["pid"], off=s["bn"] - x["L"], eth=s["eth"], tok=s["tok"], h=s["h"], f=(t["f"] if t else "?"), rt=s["rt"], n=(t["n"] if t else None)))
    reps = []
    for a, xs in act.items():
        cov = len(xs) / n
        if cov < 0.3: continue
        eths = [y["eth"] for y in xs if y["eth"] is not None]
        offs = [y["off"] for y in xs]
        wal = collections.Counter(y["f"] for y in xs)
        mr = [m for m in (minout_ratio(y["h"], y["tok"]) for y in xs) if m]
        reps.append(dict(actor=a, cov=round(cov, 2), npools=len(xs), off=pct(offs), off_spread=(q(offs, .9) - q(offs, .1)), eth=pct([round(e, 5) for e in eths]),
                         eth_med=q(eths, .5), wallets=len(wal), top_wallet_share=round(wal.most_common(1)[0][1] / len(xs), 2),
                         wallet_nonce=pct([y["n"] for y in xs if y["n"] is not None]), router=collections.Counter(y["rt"][:10] for y in xs).most_common(2),
                         minout_ratio=pct([round(m, 4) for m in mr]), n_minout=len(mr)))
    reps.sort(key=lambda z: (-(z["eth_med"] or 0) * z["cov"]))
    res["repeat"] = reps
    # pick the main repeat buyer: coverage >= 0.5, median eth >= 0.001, earliest median offset
    main = [z for z in reps if z["cov"] >= 0.5 and (z["eth_med"] or 0) >= 0.001]
    main.sort(key=lambda z: q([y["off"] for y in act[z["actor"]]], .5))
    res["main"] = main[0]["actor"] if main else None
    pl = [x["pull"] for x in P if x["pull"] is not None]
    res["pulled"] = "%d/%d" % (len(pl), n); res["pull_off"] = pct(pl)
    if res["main"]:
        T = {y["pid"]: y["off"] for y in act[res["main"]]}
        # outsiders before T: buys >= 0.0002 ETH by others (not launcher, not the main actor) in [L+1, T-1]
        oc = []
        for x in P:
            t0 = T.get(x["pid"])
            lim = t0 if t0 is not None else EARLY
            outs = []
            for s in x["sw"]:
                if not s["buy"] or s["h"] == x["r"]["h"] or s["bn"] - x["L"] >= lim: continue
                tt = TX.get(s["h"]); a = actor(s["h"])
                if a == res["main"] or (tt and tt["f"] == x["launcher"]): continue
                if (s["eth"] or 0) >= 0.0002: outs.append((s["bn"] - x["L"], round(s["eth"], 5), a))
            oc.append(dict(pid=x["pid"], T=t0, outs=outs, pull=x["pull"]))
        w = [o for o in oc if o["outs"]]; wo = [o for o in oc if not o["outs"]]
        res["outsider_pools"] = len(w)
        res["main_came_if_outsider"] = "%d/%d" % (sum(o["T"] is not None for o in w), len(w))
        res["main_came_if_clean"] = "%d/%d" % (sum(o["T"] is not None for o in wo), len(wo))
        res["pull_if_outsider"] = pct([o["pull"] for o in w if o["pull"] is not None])
        res["pull_if_clean"] = pct([o["pull"] for o in wo if o["pull"] is not None])
        res["pulled_before_T_or_200"] = "%d/%d outsider vs %d/%d clean" % (
            sum(1 for o in w if o["pull"] is not None and o["pull"] < (o["T"] or 10**9) + 0 and o["pull"] <= 200), len(w),
            sum(1 for o in wo if o["pull"] is not None and o["pull"] < (o["T"] or 10**9) and o["pull"] <= 200), len(wo))
        res["outsider_examples"] = [o for o in w][:6]
    return res
if __name__ == "__main__":
    fams = collections.defaultdict(list)
    for pid, t in tg.items(): fams[t["fam"]].append(pid)
    out = []
    for f, pids in sorted(fams.items(), key=lambda kv: -len(kv[1])):
        r = analyse(pids, f)
        if r: out.append(r)
    jdump(out, "s07_traits.json")
    for r in out:
        print("\n== %s  n=%d  %s..%s  %.1f/day  senders %d (max %d/sender) nonce %s  pulled %s at %s" % (r["label"], r["n"], r["first"], r["last"], r["per_day"], r["senders"], r["max_per_sender"], r["sender_nonce"], r["pulled"], r["pull_off"]))
        for z in r["repeat"][:6]:
            print("   actor %-22s cov %.2f off %-10s spread %-3s eth %-24s wallets %d (top %.2f) nonce %s router %s minOut/got %s (n %d)" % (z["actor"], z["cov"], z["off"], z["off_spread"], z["eth"], z["wallets"], z["top_wallet_share"], z["wallet_nonce"], z["router"], z["minout_ratio"], z["n_minout"]))
        if r.get("main"):
            print("   main %s | outsider-before-T pools %d: main came %s (clean %s); pull p10/50/90 outsider %s clean %s; pulled<=200 & before T: %s" % (r["main"], r["outsider_pools"], r["main_came_if_outsider"], r["main_came_if_clean"], r["pull_if_outsider"], r["pull_if_clean"], r["pulled_before_T_or_200"]))
