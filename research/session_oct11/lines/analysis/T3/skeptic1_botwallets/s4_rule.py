"""Stage 4: candidate 2 re-measured on pools the finder did not use.
Rule (finder): any transaction from one of the bot's buyer wallets (buys via the bot router c1120e3d in another pool, sells to the Universal
Router 24856bc3, anything else they send), seen in the window before T, precedes T by a stable 1-4 blocks.
Bot wallet set W = wallets that sent c1120e3d to the bot router 0x1cbaf24d in any block fetched here or in any pool parsed here (union with the
finder's 110 for a second variant). Per pool with a bot buy: every full block L+1..T (block T only ahead of the bot's tx) -> per block offset the
classes present. Outputs:
  A. profile: share of pools with a class at d = T - b blocks, d = 0..30, and the background (blocks with d >= 13);
  B. the rule as a trigger: arm at L+a, fire on the first block b >= L+a holding the class; lead = T - b (distribution, hit rate lead 1..4);
  C. precision: of all (pool, block) firing in [L+a, T-1], the share with T-b in 1..4 vs the share of all blocks in that range (lift);
  D. a $5 front following the trigger with the operator's reaction modelled (see s5_front.py).
Regimes: 'old' = L < 85,553,521 (10-11 01:27-04:30 UTC, T at L+8/9 and the pool pulled at T+3 after 0x8cf143dd's buy at L+1..3);
         'cur' = L >= 85,553,521 to 85,728,763 (04:30-09:37 UTC, T at L+20..55, the current regime); 'late' = after the finder's last pool."""
import pickle, json, collections, sys, os
from lib import *
CUR0 = 85553521; FINDER_START = 85728764; FINDER_LAST = 86150251
D = pickle.load(open("parsed.pkl", "rb")); P = D["pools"]
kv = KV("blk"); B = kv.d
def regime(p): return "old" if p["L"] < CUR0 else ("cur" if p["L"] < FINDER_START else ("late" if p["L"] > FINDER_LAST else "FINDER"))
for p in P: p["reg"] = regime(p)
assert not any(p["reg"] == "FINDER" for p in P)
# bot wallet sets
W_pools = {s["eoa"] for p in P for s in p["sw"] if s["bot"]}
W_blk = {t[1] for b in B.values() for t in b["tx"] if t[2] == BOT and t[3] == "c1120e3d"}
fe = pickle.load(open("../precursor/events.pkl", "rb")); W_finder = set(fe["botw"])
W = W_pools | W_blk
print(f"bot wallets: in my pools' bot buys {len(W_pools)}, senders of c1120e3d in my blocks {len(W_blk)}, union {len(W)}; the finder's 110: {len(W_finder)}, "
      f"overlap with my union {len(W & W_finder)}")
pullers = collections.Counter(t[1] for b in B.values() for t in b["tx"] if t[2] == BOT and t[3] != "c1120e3d")
print("other senders to the bot router (selector):", collections.Counter((t[1][:10], t[3]) for b in B.values() for t in b["tx"] if t[2] == BOT and t[3] != "c1120e3d").most_common(6))
def classes(t, Wset, buyer):
    frm, to, sel = t[1], t[2], t[3]; out = []
    if frm in Wset:
        out.append("ANY bot-wallet tx")
        if to == BOT and sel == "c1120e3d": out.append("bot buy (another pool)")
        elif to == UR and sel == "24856bc3": out.append("bot-wallet sell via UR 24856bc3")
        else: out.append("bot-wallet other tx")
        if frm == buyer: out.append("T's buyer wallet")
    if to == BOT and sel != "c1120e3d": out.append("tx to bot router, not a buy")
    return out
def per_pool(p, Wset):
    """{off: set(classes)} for blocks L+1..T (T's block only ahead of the bot's tx); None if a block is missing"""
    ev = {}
    for off in range(1, p["T"] + 1):
        b = B.get(str(p["L"] + off))
        if b is None: return None
        cl = set()
        for t in b["tx"]:
            if off == p["T"] and t[7] >= p["Tti"]: continue
            cl.update(classes(t, Wset, p["buyer"]))
        ev[off] = cl
    return ev
CL = ["ANY bot-wallet tx", "bot buy (another pool)", "bot-wallet sell via UR 24856bc3", "bot-wallet other tx", "T's buyer wallet", "tx to bot router, not a buy"]
res = {}
for wname, Wset in (("W=my union", W), ("W=the finder's 110 only", W_finder)):
    print(f"\n######## wallet set {wname} ({len(Wset)})")
    for reg in ("cur", "late", "cur+late", "old"):
        G = [p for p in P if p["T"] is not None and (p["reg"] == reg or (reg == "cur+late" and p["reg"] in ("cur", "late")))]
        EV = {}
        for p in G:
            e = per_pool(p, Wset)
            if e is not None: EV[p["pid"]] = e
        G = [p for p in G if p["pid"] in EV]
        if not G: print(f"\n== {reg}: no pools with blocks"); continue
        Ts = [p["T"] for p in G]
        print(f"\n== regime {reg}: {len(G)} pools with every block L+1..T; T p10/50/90 {pct(Ts,.1)}/{pct(Ts,.5)}/{pct(Ts,.9)} min {min(Ts)} max {max(Ts)}; "
              f"no bot buy (not in this table): {sum(1 for p in P if p['reg'] == reg and p['T'] is None)}")
        maxd = 30 if reg != "old" else 8
        print("  A. pools with the class at d = T - b (d=0: T's block ahead of the bot's tx); n = pools whose window reaches that d; bg = share of blocks with d >= 13 (or d >= 5 for 'old')")
        print("     " + " " * 34 + " ".join(f"{d:>4}" for d in range(0, min(maxd, 16) + 1)))
        for c in CL:
            row = []; bgh = bgn = 0
            for d in range(0, maxd + 1):
                S = [p for p in G if p["T"] - d >= 1]
                h = sum(1 for p in S if c in EV[p["pid"]][p["T"] - d])
                row.append((h, len(S)))
            for p in G:
                for off, cl in EV[p["pid"]].items():
                    d = p["T"] - off
                    if d >= (13 if reg != "old" else 5) and off >= 4: bgn += 1; bgh += c in cl
            bg = bgh / bgn if bgn else 0
            w14 = sum(1 for p in G if any(c in EV[p["pid"]].get(p["T"] - d, ()) for d in range(1, 5)))
            exp14 = len(G) * (1 - (1 - bg) ** 4)
            print(f"     {c[:34]:34s}" + " ".join(f"{100*h/n if n else 0:4.0f}" for h, n in row[:17]) + f"  (% of pools) | bg/blk {100*bg:4.1f}% | any in d1-4 {w14}/{len(G)} ({100*w14/len(G):.0f}%) vs {exp14:.1f} expected at bg")
        # B. trigger
        print("  B. trigger = first block b >= L+a with the class; lead = T - b. hit = lead 1..4; early = lead >= 5; d0 = in T's block ahead of the bot; none = nothing before the bot's buy")
        for c in CL[:4]:
            for a in ((1, 4, 10, 15, 20, 25, 30) if reg != "old" else (1, 3, 5)):
                leads = []
                for p in G:
                    f = next((off for off in range(a, p["T"] + 1) if c in EV[p["pid"]][off]), None)
                    leads.append(None if f is None else p["T"] - f)
                n = len(leads); hit = sum(1 for x in leads if x is not None and 1 <= x <= 4); early = sum(1 for x in leads if x is not None and x >= 5)
                d0 = sum(1 for x in leads if x == 0); none = sum(1 for x in leads if x is None)
                ll = sorted(x for x in leads if x is not None)
                hist = collections.Counter(min(x, 31) for x in ll)
                print(f"     {c[:31]:31s} a={a:2d}: hit {hit:3d}/{n} ({100*hit/n:3.0f}%) early {early:3d} d0 {d0:2d} none {none:3d} | lead p10/50/90 {pct(ll,.1)}/{pct(ll,.5)}/{pct(ll,.9)} "
                      f"| lead 1..8: " + " ".join(f"{hist.get(x,0)}" for x in range(1, 9)))
                res[(wname, reg, c, a)] = leads
        # C. precision
        print("  C. precision: share of firing blocks in [L+a, T-1] that lie 1..4 before T, vs the share of all blocks there (lift = ratio)")
        for c in CL[:4]:
            for a in ((4, 15, 20) if reg != "old" else (1, 3)):
                fh = fn = bh = bn = 0
                for p in G:
                    for off in range(a, p["T"]):
                        d = p["T"] - off; bn += 1; bh += 1 <= d <= 4
                        if c in EV[p["pid"]][off]: fn += 1; fh += 1 <= d <= 4
                print(f"     {c[:31]:31s} a={a:2d}: firing blocks {fn:4d}, of them 1..4 before T {fh:3d} ({100*fh/fn if fn else 0:4.1f}%) | all blocks {bn:5d}, 1..4 before T {100*bh/bn:4.1f}% | lift {((fh/fn)/(bh/bn)) if fn and bn and bh else 0:.2f}")
pickle.dump({"res": res, "W": sorted(W), "W_finder": sorted(W_finder)}, open("s4_rule.pkl", "wb"))
