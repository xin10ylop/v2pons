"""Skeptic 1, stage 4: the operator's reaction lag to a non-dust (>= 0.00003 ETH) outside buy that lands BEFORE the bot's first buy T on the
3.0 line, measured from chain data: (a) the precursor angle's cached pools (10-11 09:38-21:45 UTC: every swap to L+90 with its tx, every
liquidity call to L+400; ../precursor/parsed.pkl, read only), (b) this angle's two slices (swaps to L+150 with txs, liquidity to L+250).
Outside = not the bot's buy (0x1cbaf24d c1120e3d), not the sentinel 0xe71a69f4. Lag = first pull block - the buy's block.
Also the same for outside buys after T (lag after T), for reference."""
import pickle, collections, statistics as st, sys
from lib import *
NEW30 = 1791692539
src = []
F = pickle.load(open("../precursor/parsed.pkl", "rb"))["pools"]
src += [("finder 09:38-21:45", p, 90) for p in F if p["line"] == "3.0"]
for f, lab in (("parsed.pkl", "oldest slice"), ("parsed_late.pkl", "newest slice")):
    for p in pickle.load(open(f, "rb"))["pools"]:
        if f == "parsed.pkl" and p["L"] >= 85728798: continue
        src.append((lab + (" (pre-04:22 regime)" if p.get("ts", NEW30) < NEW30 else ""), p, 150))
pre = collections.defaultdict(list); post = collections.defaultdict(list); cases = []
for lab, p, cover in src:
    pulls = sorted(m["bn"] for m in p["ml"] if m["dL"] < 0)
    Tbn = p["Tbn"]
    seen = set()
    for s in p["sw"]:
        if not s["buy"] or s.get("bot") or s["eoa"] == SENTINEL or s["q"] < 3e13 or not s["have_tx"]: continue
        if s["off"] > cover: continue
        if pulls and s["bn"] > pulls[0]: continue
        nxt = next((b for b in pulls if b >= s["bn"]), None)
        lag = nxt - s["bn"] if nxt is not None else None
        before = Tbn is None or s["bn"] < Tbn or (s["bn"] == Tbn and s["ti"] < p["Tti"])
        key = (p["pid"], s["eoa"])
        if key in seen: continue   # the first buy of a wallet in a pool
        seen.add(key)
        (pre if before else post)[lab].append(lag)
        cases.append((lab, "pre-T" if before else "post-T", utc(p.get("ts") or 0) if p.get("ts") else "", p["pid"][:12], p["T"], s["off"], s["eoa"][:10], s["to"][:10] + ":" + s["sel"], round(s["q"] / 1e18, 6), lag,
                      "ours" if s["eoa"] in (OURS,) else ""))
for lab in sorted(set(list(pre) + list(post))):
    for nm, d in (("BEFORE T", pre), ("after T", post)):
        v = d.get(lab, [])
        if not v: continue
        got = sorted(x for x in v if x is not None)
        print(f"{lab:38s} {nm:8s} buys {len(v):3d}  pulled after {len(got):3d}  lags {got}  min {min(got) if got else None} median {st.median(got) if got else None}")
allpre = sorted(x for lab, v in pre.items() if "pre-04:22" not in lab for x in v if x is not None)
print(f"\ncurrent regime, every outside non-dust buy BEFORE T with a pull after it: n {len(allpre)}, lags {allpre}")
print(f"  min {allpre[0]}, p10 {pct(allpre,.1)}, p25 {pct(allpre,.25)}, median {st.median(allpre)}, p75 {pct(allpre,.75)}, max {allpre[-1]}; share pulled within 3/4/5/6/9 blocks: " +
      " ".join(f"{sum(1 for x in allpre if x <= k)}/{len(allpre)}" for k in (3, 4, 5, 6, 9)))
nopull = sum(1 for lab, v in pre.items() if "pre-04:22" not in lab for x in v if x is None)
print(f"  pre-T outside buys never followed by a pull in the window: {nopull}")
print("\ncases (slice, before/after T, launch UTC, pool, T, buy offset, wallet, to:selector, ETH, pull lag):")
for c in cases:
    if "pre-04:22" in c[0]: continue
    print("  ", c)
