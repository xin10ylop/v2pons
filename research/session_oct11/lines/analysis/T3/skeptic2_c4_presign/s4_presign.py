"""Stage 4: does anything visible precede the bot's first buy T (block Tbn) by 1-4 blocks? (candidate 4: a presigned or failed copy of the
bot's buy). On the slice L > 86158232 (pools the finder never saw).
 (a) signing time: word 6 of the c1120e3d calldata is a deadline; deadline - ts(T block); j = blocks before T that share T's timestamp
     (if the deadline is clock + 1,200, 1199 means it was signed in the previous second, i.e. at least j+1 blocks before T; 1200 means at
     most about j blocks before T). -> bounds on the sign-to-land lag in blocks.
 (b) every transaction in blocks [T-12, T+3]; flags: to the bot router (any selector), from T's buyer, from any bot wallet (any wallet that
     sent a c1120e3d buy in our data), calldata containing the pool's token or pool id, to the token, to the PositionManager / Permit2,
     from the sentinel, from the pool's launcher or any 3.0 launcher; and every failed (status 0) transaction in [T-12, T+1].
 (c) logs in [T-4, T-1] emitted by the token or carrying the pool id / token / buyer in a topic.
 (d) the rule 'a flagged pool-specific tx (same token/pool id, or the buyer, or a failed bot-router tx) in [T-4, T-1]': hits, and the
     generic 'any bot-router / bot-wallet tx' as a precursor: share of T windows with one in [T-4, T-1] vs the control windows [T-12, T-5]
     (per-block rates), lead distribution."""
import pickle, collections
from lib import *
D = pickle.load(open("parsed.pkl", "rb")); P = sorted([p for p in D["pools"] if p["T"] is not None], key=lambda p: p["L"])
kb = KV("blk"); kr = KV("rcp")
botw = {s["eoa"] for p in D["pools"] for s in p["sw"] if s["bot"]}
launchers = {p["launcher"] for p in D["pools"]}
print(f"pools with T: {len(P)}; bot wallets seen in this slice: {len(botw)}; launchers {len(launchers)}")
# (a)
lag = collections.Counter(); byj = collections.defaultdict(collections.Counter); rows = []
for p in P:
    dl = p["Tw"][6]; T = p["Tbn"]; ts = kb.d[str(T)]["ts"]
    j = 0
    while str(T - j - 1) in kb.d and kb.d[str(T - j - 1)]["ts"] == ts and j < 12: j += 1
    d = dl - ts; lag[d] += 1; byj[min(j, 8)][d] += 1
    rows.append((p["L"], p["T"], d, j, utc(ts), round(p["Tq"], 4)))
print("\n(a) deadline - ts(T block), seconds:", sorted(lag.items()), f"(n {len(P)})")
print("    by j = blocks before T in T's own second (8 = 8 or more):")
for j in sorted(byj): print(f"      j {j}: n {sum(byj[j].values()):3d} {dict(sorted(byj[j].items()))}")
# sign-to-land lag bounds: 1199 -> lag >= j+1; 1200 -> lag <= j. Find the smallest k consistent with most pools
for k in range(0, 9):
    ok = sum(1 for r in rows if (r[2] == 1199 and k >= r[3] + 1) or (r[2] == 1200 and k <= r[3]))
    print(f"    a constant sign-to-land lag of {k} blocks is consistent with {ok}/{len(rows)} pools")
# (b)
def flags(t, p, buyer):
    f = []; inp = (t.get("input") or "").lower(); to = (t.get("to") or "").lower(); fr = (t.get("from") or "").lower()
    tok = p["token"][2:].lower(); pid = p["pid"][2:].lower()
    if to == BOT: f.append("to bot router:" + inp[2:10])
    if fr == buyer: f.append("from T's buyer:" + inp[2:10])
    elif fr in botw: f.append("from a bot wallet:" + to[:10] + ":" + inp[2:10])
    if tok in inp: f.append("calldata has the token:" + to[:10] + ":" + inp[2:10])
    if pid in inp: f.append("calldata has the pool id:" + to[:10] + ":" + inp[2:10])
    if to == p["token"].lower(): f.append("to the token:" + inp[2:10])
    if to == POSM: f.append("to PositionManager:" + inp[2:10])
    if to == PERMIT2: f.append("to Permit2:" + inp[2:10])
    if fr == SENTINEL: f.append("from the sentinel")
    if fr == p["launcher"]: f.append("from the launcher")
    elif fr in launchers: f.append("from another 3.0 launcher")
    return f
tally = collections.Counter(); specific = []; generic_pre = collections.Counter(); generic_ctl = 0; ctl_blocks = 0; pre_blocks = 0
failed = []; nearest = []
for p in P:
    T = p["Tbn"]; buyer = p["buyer"]; st = {}
    for b in range(T - 12, T + 2):
        for r in kr.d.get(str(b), []): st[r["tx"]] = r["status"]
    gen_lead = None
    for b in range(T - 12, T + 4):
        d = T - b
        for t in kb.d[str(b)]["txs"]:
            if t["hash"] == p["Ttx"]: continue
            fl = flags(t, p, buyer)
            s = st.get(t["hash"])
            if s == "0x0": failed.append((p["L"], p["T"], d, (t["from"] or "")[:10], (t["to"] or "")[:10], (t["input"] or "")[:10], fl))
            for x in fl: tally[(x.split(":")[0], d)] += 1
            spec = [x for x in fl if x.startswith(("calldata has", "from T's buyer", "to the token"))] + \
                   ([x for x in fl if x.startswith("to bot router")] if s == "0x0" else [])
            if spec and d >= 0: specific.append((p["L"], p["T"], d, (t["from"] or "")[:10], (t["to"] or "")[:10], (t["input"] or "")[:10], s, spec))
            gen = any(x.startswith(("to bot router", "from a bot wallet", "from T's buyer")) for x in fl)
            if gen and 1 <= d <= 4 and gen_lead is None: gen_lead = d
            if gen and 1 <= d <= 4: generic_pre[d] += 1
            if gen and 5 <= d <= 12: generic_ctl += 1
    nearest.append(gen_lead)
    pre_blocks += 4; ctl_blocks += 8
print("\n(b) flag counts by (kind, blocks before T; negative = after):")
for k in sorted({k[0] for k in tally}):
    print(f"    {k:28s}", {d: tally[(k, d)] for d in range(12, -4, -1) if tally[(k, d)]})
print(f"\n    failed (status 0) transactions in [T-12, T+1]: {len(failed)}")
for x in failed[:30]: print("      ", x)
print(f"\n    pool-specific precursors (the token or pool id in calldata, a tx from T's buyer, to the token, or a failed bot-router tx; a Permit2 call counts only with the token in its calldata), at or before T:")
for x in specific: print("      ", x)
print(f"    pools with one in [T-4, T-1]: {len({x[0] for x in specific if 1 <= x[2] <= 4})} of {len(P)}")
print(f"\n(d) generic: any bot-router / bot-wallet tx (other pools) per block: in [T-4, T-1] {sum(generic_pre.values())}/{pre_blocks} = {sum(generic_pre.values())/pre_blocks:.3f}; "
      f"control [T-12, T-5] {generic_ctl}/{ctl_blocks} = {generic_ctl/ctl_blocks:.3f}; by lead {dict(sorted(generic_pre.items()))}")
print(f"    pools with one in [T-4, T-1]: {sum(1 for x in nearest if x)} of {len(P)}; nearest lead {collections.Counter(nearest)}")
# (c) logs in [T-4, T-1]
lg = collections.Counter(); lgx = []
for p in P:
    T = p["Tbn"]; keys = {p["pid"].lower(), "0x" + "0" * 24 + p["token"][2:].lower(), "0x" + "0" * 24 + p["buyer"][2:]}
    for b in range(T - 4, T):
        for r in kr.d[str(b)]:
            for l in r["logs"]:
                if l["a"] == p["token"].lower() or keys & {x.lower() for x in l["t"]}:
                    lg[T - b] += 1; lgx.append((p["L"], p["T"], T - b, l["a"][:10], l["t"][0][:10], r["to"][:10] if r["to"] else None))
print(f"\n(c) logs in [T-4, T-1] emitted by the token or with the pool id / token / buyer in a topic: {sum(lg.values())} {dict(lg)}")
for x in lgx[:20]: print("      ", x)
print("\nper pool (L, T, deadline - ts, j, T time, size):")
for r in rows: print("   ", r)
