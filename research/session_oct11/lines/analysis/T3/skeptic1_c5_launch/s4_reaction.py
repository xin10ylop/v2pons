"""Stage 4: the operator's reaction re-measured on this slice (pools the finder and REPORT_R's 'today' figures did not use).
Outside buy = a buy swap whose tx is not the bot router's c1120e3d, not from the sentinel 0xe71a69f4, not from a bot buyer wallet (any wallet
seen sending c1120e3d to the bot router in the slice); non-dust = >= 0.00003 ETH. For each pool, the first non-dust outside buy before T (or
before L+90 in pools with no bot buy) and the lag to the first pull after it. Baseline: pools with no such buy, pulled before T."""
import pickle, collections, statistics as st
from lib import *
D = pickle.load(open("parsed.pkl", "rb")); from common_reg import regime
P = D["pools"]
botw = {s["eoa"] for p in P for s in p["sw"] if s["bot"]}
print("pools", len(P), "bot buyer wallets", len(botw))
pre = []; post = []; nobuy_pre = []; dust = collections.Counter()
for p in P:
    Tbn = p["Tbn"]; lim = Tbn if Tbn is not None else p["L"] + 90
    outs = [s for s in p["sw"] if s["buy"] and s["have_tx"] and not s["bot"] and s["eoa"] != SENTINEL and s["eoa"] not in botw and s["eoa"] != OURS]
    ob = [s for s in outs if s["q"] >= 3 * 10 ** 13 and (s["bn"] < lim or (s["bn"] == lim and Tbn is not None and s["ti"] < p["Tti"]))]
    for s in outs:
        if s["q"] < 3 * 10 ** 13 and s["bn"] < lim: dust[s["eoa"][:10]] += 1
    pulls = [m for m in p["ml"] if m["dL"] < 0]
    if ob:
        s = ob[0]; pl = [m for m in pulls if m["bn"] >= s["bn"]]
        pre.append(dict(pid=p["pid"][:10], L=p["L"], off=s["off"], q=s["q"] / 1e18, eoa=s["eoa"][:10], to=s["to"][:10], T=p["T"],
                        lag=pl[0]["bn"] - s["bn"] if pl else None, botbought=p["T"] is not None and (not pl or p["Tbn"] < pl[0]["bn"])))
    else:
        nobuy_pre.append(p)
    if Tbn is not None:
        oa = [s for s in outs if s["q"] >= 3 * 10 ** 13 and s["bn"] > Tbn and s["bn"] <= p["L"] + 90]
        if oa:
            s = oa[0]; pl = [m for m in pulls if m["bn"] >= s["bn"]]
            post.append(dict(off=s["off"], T=p["T"], q=s["q"] / 1e18, eoa=s["eoa"][:10], lag=pl[0]["bn"] - s["bn"] if pl else None))
print("\nnon-dust outside buys BEFORE T (first per pool):", len(pre))
for r in pre: print("  ", r)
lags = [r["lag"] for r in pre if r["lag"] is not None]
if lags:
    print(f"  pulled after it: {len(lags)} of {len(pre)}; lag min {min(lags)} p25 {pct(lags,.25)} median {st.median(lags)} p75 {pct(lags,.75)} max {max(lags)}; "
          f"within 14 blocks {sum(1 for x in lags if x <= 14)}; the bot still bought before the pull in {sum(1 for r in pre if r['botbought'])}")
    print("  lag histogram:", sorted(collections.Counter(lags).items()))
base_pulled = [p for p in nobuy_pre if p["pull"] is not None and (p["T"] is None or p["pull"] < p["T"])]
print(f"\nbaseline: pools with no non-dust outside buy before T: {len(nobuy_pre)}, pulled before T (or with no bot buy and pulled): {len(base_pulled)}; "
      f"pools with no bot buy at all: {sum(1 for p in nobuy_pre if p['T'] is None)}")
print("\nnon-dust outside buys AFTER T to L+90 (first per pool):", len(post))
pl2 = [r["lag"] for r in post if r["lag"] is not None]
for r in post: print("  ", r)
if pl2: print(f"  pulled after it {len(pl2)} of {len(post)}; lag min {min(pl2)} median {st.median(pl2)} max {max(pl2)}")
print("\ndust buyers before T (count of buys):", dust.most_common(8))

print("\n== by regime; a wallet is 'recurring' when it buys (non-dust, outside) in >= 3 pools of the slice (the operator's own decoys are spared)")
wc = collections.Counter()
for p in P:
    for s_ in p["sw"]:
        if s_["buy"] and s_["have_tx"] and not s_["bot"] and s_["eoa"] not in botw and s_["eoa"] != SENTINEL and s_["q"] >= 3 * 10 ** 13: wc[s_["eoa"][:10]] += 1
for reg in ("old", "new"):
    R = [r for r in pre if regime(D, r["L"]) == reg]
    for kind, sel in (("one-off", lambda r: wc[r["eoa"]] < 3), ("recurring", lambda r: wc[r["eoa"]] >= 3)):
        X = [r for r in R if sel(r)]; lg = [r["lag"] for r in X if r["lag"] is not None]
        print(f"  {reg} regime, {kind} wallets: first pre-T buys {len(X)}, pulled after {len(lg)}; lag min {min(lg) if lg else None} median {st.median(lg) if lg else None} "
              f"max {max(lg) if lg else None}; hist {sorted(collections.Counter(lg).items())}; wallets {collections.Counter(r['eoa'] for r in X).most_common(6)}")
    NP = [p for p in nobuy_pre if regime(D, p["L"]) == reg]
    print(f"  {reg} regime baseline: pools with no non-dust outside buy before T {len(NP)}, pulled at all to L+400: {sum(1 for p in NP if p['pull'] is not None)}, "
          f"pull offset from T: {sorted(collections.Counter(p['pull'] - p['T'] for p in NP if p['pull'] is not None and p['T'] is not None).items())[:20]}")
for reg in ("new",):
    print(f"\n  {reg} regime, every pool with a non-dust outside buy before T:")
    for r in pre:
        if regime(D, r["L"]) == reg: print("    ", r, "wallet pools", wc[r["eoa"]])
