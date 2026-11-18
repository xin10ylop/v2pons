#!/usr/bin/env python3
"""ponsclean.py: are these Pons (Robinhood bonding-curve launchpad) copy-trade wallets clean, i.e. trading coins they have no hand in?

For each wallet, over its window (FROM_DAYS_AGO .. TO_DAYS_AGO): its CurveBuy / CurveSell logs (as sender or recipient), the coin each
belongs to and that coin's launch (TokenLaunched on the factory: token, curve, creator, block, tx). It prints:
  who signs     the transactions behind its trades (tx.from) and where they go (tx.to): a contract wallet's controller
  creators      whether it, its signer, or another of the checked wallets launched the coins it bought; how concentrated the creators are
  timing        blocks from launch to its first buy; buys inside the launch transaction or launch block (bundled with the creator)
  gifts         ERC-20 tokens it received or sent other than through a curve (an insider allocation, or moving coins between wallets)
  overlap       coins two checked wallets both bought, and how close together
Read-only (public RPC logs and transactions). Output: ponsclean.out."""
import os, sys, pickle, collections, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hlib as H
from eth_utils import keccak

url = H.CH["rh"]["rpc"]
K = lambda s: "0x" + keccak(text=s).hex()
CB = K("CurveBuy(address,address,uint256,uint256,uint256,uint256)"); CS = K("CurveSell(address,address,uint256,uint256,uint256,uint256)")
TL = "0x8d4aad4953d0ca700d468f3753aa14432d1b35b43ec6409f051fb6aa43a89607"; TR = K("Transfer(address,address,uint256)")
FACTORY = "0x7ed598bcef8bd9edd8c97a195c6d13f40801ec7e"
BPS = 9.75                                                            # blocks a second
WALLETS = {"9a3955a1": ("0x9a3955a122ab8a649a8511df2dce169471fd0ec1", 4, 0), "5bc235ac": ("0x5bc235acecff3dde394f4bfc696f7c35efd502f0", 4, 0),
           "9e0771d4": ("0x9e0771d4a5fe0c5dbd03e6175807b8290c2e40b0", 18, 9), "c54d3914": ("0xc54d3914f91f984d61b63d491f38934c4e706b79", 4, 0)}
head = int(H.rpc(url, "eth_blockNumber", []), 16)
pad = lambda a: "0x" + "0" * 24 + a[2:]
ad = lambda t: "0x" + t[-40:]


def logs(lo, hi, topics, address=None):
    out = []
    step = 100000 if address else 30000                              # the RPC allows 30k blocks for a topic-only query
    for a in range(lo, hi + 1, step):
        q = {"fromBlock": hex(a), "toBlock": hex(min(hi, a + step - 1)), "topics": topics}
        if address:
            q["address"] = address
        out += H.rpc(url, "eth_getLogs", [q]) or []
    return out


rng = {k: (head - int(f * 86400 * BPS), head - int(t * 86400 * BPS)) for k, (_, f, t) in WALLETS.items()}
lo_all = min(r[0] for r in rng.values()) - int(2 * 86400 * BPS); hi_all = head
print(f"head {head}; launches from block {lo_all}", flush=True)
CACHE = os.environ.get("CACHE", "/tmp/claude-0/-home-user-v2pons/48f7dd16-3073-5667-9085-af9d544164ac/scratchpad/ponslaunch.pkl")
launch = pickle.load(open(CACHE, "rb")) if os.path.exists(CACHE) else {}      # curve -> dict
done = max((v["block"] for v in launch.values()), default=lo_all - 1)
for l in logs(max(lo_all, done + 1), hi_all, [TL], FACTORY):
    launch[ad(l["topics"][2])] = dict(token=ad(l["topics"][1]), creator=ad(l["topics"][3]), block=int(l["blockNumber"], 16), tx=l["transactionHash"])
pickle.dump(launch, open(CACHE, "wb"))
print(f"{len(launch)} Pons launches in the scan", flush=True)
creators_all = collections.Counter(v["creator"] for v in launch.values())
trades = {}
for k, (w, _, _) in WALLETS.items():
    lo, hi = rng[k]
    a = logs(lo, hi, [[CB, CS], pad(w)]); b = logs(lo, hi, [[CB, CS], None, pad(w)])
    seen = set(); ev = []
    for l in a + b:
        key = (l["transactionHash"], l["logIndex"])
        if key in seen:
            continue
        seen.add(key)
        d = l["data"][2:]; x = [int(d[i:i + 64], 16) for i in range(0, len(d), 64)]
        ev.append(dict(buy=l["topics"][0] == CB, curve=l["address"].lower(), block=int(l["blockNumber"], 16), tx=l["transactionHash"],
                       t1=ad(l["topics"][1]), t2=ad(l["topics"][2]), eth=(x[0] if l["topics"][0] == CB else x[1]) / 1e18))
    ev.sort(key=lambda e: e["block"])
    gin = logs(lo, hi, [TR, None, pad(w)]); gout = logs(lo, hi, [TR, pad(w)])
    trades[k] = dict(ev=ev, gin=gin, gout=gout)
    print(f"  {k}: {sum(e['buy'] for e in ev)} buys, {sum(not e['buy'] for e in ev)} sells, {len(gin)} token transfers in, {len(gout)} out", flush=True)

signers = {}
for k, (w, _, _) in WALLETS.items():
    ev = trades[k]["ev"]
    print(f"\n===== {k} {w}  window {rng[k][0]}..{rng[k][1]}")
    if not ev:
        print("   no Pons trades in the window"); continue
    txs = sorted({e["tx"] for e in ev})
    sample = txs[:: max(1, len(txs) // 300)]
    got = H.batch(url, [("eth_getTransactionByHash", [h]) for h in sample], size=50, workers=4, tries=8)
    frm = collections.Counter(x["from"].lower() for x in got if x); to = collections.Counter((x["to"] or "").lower() for x in got if x)
    signers[k] = set(frm)
    print(f"   signers of its trade transactions (sample {len(sample)} of {len(txs)}): {[(a, n) for a, n in frm.most_common(4)]}")
    print(f"   sent to: {[(a, n) for a, n in to.most_common(4)]}")
    buys = [e for e in ev if e["buy"]]
    firsts = {}
    for e in buys:
        firsts.setdefault(e["curve"], e)
    known = [c for c in firsts if c in launch]
    print(f"   coins bought: {len(firsts)}, launch found for {len(known)}")
    if not known:
        continue
    cr = collections.Counter(launch[c]["creator"] for c in known)
    me = {w} | signers[k]
    own = sum(n for a, n in cr.items() if a in me)
    print(f"   coins launched by this wallet or its signer: {own}; distinct creators {len(cr)}; top creators "
          f"{[(a[:10], n, creators_all[a]) for a, n in cr.most_common(5)]}  (bought / that creator's launches in the scan)")
    delay = [firsts[c]["block"] - launch[c]["block"] for c in known]
    same_tx = sum(firsts[c]["tx"] == launch[c]["tx"] for c in known); same_blk = sum(d == 0 for d in delay)
    print(f"   first buy after launch: median {st.median(delay):.0f} blocks ({st.median(delay) / BPS:.1f} s); within 10 blocks {sum(d <= 10 for d in delay)}; "
          f"in the launch block {same_blk}; inside the launch transaction {same_tx}")
    sz = [e["eth"] for e in buys]
    print(f"   buy size: median {st.median(sz):.4f} ETH, max {max(sz):.3f}; total bought {sum(sz):.2f} ETH, sold {sum(e['eth'] for e in ev if not e['buy']):.2f} ETH")
    curves = set(launch) | {e["curve"] for e in ev}
    gin = [l for l in trades[k]["gin"] if ad(l["topics"][1]) not in curves and ad(l["topics"][1]) != "0x" + "0" * 40]
    gout = [l for l in trades[k]["gout"] if ad(l["topics"][2]) not in curves and ad(l["topics"][2]) != "0x" + "0" * 40]
    print(f"   tokens received NOT from a curve: {len(gin)} from {collections.Counter(ad(l['topics'][1]) for l in gin).most_common(4)}")
    print(f"   tokens sent NOT to a curve:       {len(gout)} to {collections.Counter(ad(l['topics'][2]) for l in gout).most_common(4)}")

print("\n===== between the wallets")
allsig = {k: v | {WALLETS[k][0]} for k, v in signers.items()}
ks = list(trades)
for i in range(len(ks)):
    for j in range(i + 1, len(ks)):
        a, b = ks[i], ks[j]
        sa = allsig.get(a, set()); sb = allsig.get(b, set())
        fa = {}; fb = {}
        for e in trades[a]["ev"]:
            if e["buy"]: fa.setdefault(e["curve"], e["block"])
        for e in trades[b]["ev"]:
            if e["buy"]: fb.setdefault(e["curve"], e["block"])
        both = set(fa) & set(fb)
        close = [abs(fa[c] - fb[c]) for c in both]
        print(f"   {a} / {b}: shared signers {len(sa & sb)}; coins both bought {len(both)}"
              + (f", median {st.median(close):.0f} blocks apart, {sum(x <= 2 for x in close)} within 2 blocks" if close else ""))
        made = sum(1 for c in fa if c in launch and launch[c]["creator"] in sb) + sum(1 for c in fb if c in launch and launch[c]["creator"] in sa)
        if made:
            print(f"      ! one bought coins the other (or its signer) launched: {made}")
