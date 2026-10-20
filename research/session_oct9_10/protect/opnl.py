import sys, collections, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/protect")
from load_all import load_all
from classify import annotate
Q96 = 1 << 96; U = 2570
pools, head = load_all(); cw = annotate(pools)
B_ONLY = set()
# crowd B: fingerprinted wallets that never buy on a launch outside the 7 low-fee long launches
lowfee = {p["pid"] for p in pools if p["kind"] == "orig" and p["fee"] < 1000}
seen = collections.defaultdict(set)
for p in pools:
    for x in p["sw"]:
        if x.get("cls") == "crowd" and x["a0"] < 0: seen[x["from"]].add(p["pid"])
B_ONLY = {w for w, s in seen.items() if s and s <= lowfee}
rows = []; tot = collections.Counter(); n_pulled = 0; crowd_txs = 0
for p in pools:
    if p["pull"] is None: continue
    n_pulled += 1
    pre = [x for x in p["sw"] if (x["bn"], x["li"]) < (p["pull"]["bn"], p["pull"]["li"])]
    by = collections.Counter()
    for x in pre:
        c = x["cls"]
        if c == "crowd" and x["from"] in B_ONLY: c = "crowdB"
        by[c] += -x["a0"]                          # ETH the swapper put into the pool (negative: took out)
        if x["cls"] == "crowd": crowd_txs += 1
    for k, v in by.items(): tot[k] += v
    rows.append((p, by))
print(f"{n_pulled} pulled operator launches (Oct 8 00:00 -> Oct 9 ~12:06 UTC); net ETH each group left in the pools before the pull (+ = put in and lost to the operator):")
for k in ("crowd", "crowdB", "us", "dust", "outsider", "?"):
    print(f"  {k:9s} {tot[k]/1e18:+.5f} ETH  (${tot[k]/1e18*U:+.2f})")
gas_crowd = crowd_txs * 117_000 * 40_000_000 / 1e18
print(f"  crowd transactions {crowd_txs}, their gas about {gas_crowd:.5f} ETH (${gas_crowd*U:.2f}); launches+pulls+funding hops roughly {n_pulled} x ~0.0001 ETH = {n_pulled*1e-4:.4f} ETH")
# per kind
by_kind = collections.defaultdict(collections.Counter)
for p, by in rows:
    k = p["kind"] + ("/lowfee" if p["pid"] in lowfee else "")
    for c, v in by.items(): by_kind[k][c] += v
    by_kind[k]["n"] += 1
for k, c in by_kind.items():
    print(f"  {k:12s} n {c['n']:3d}: " + ", ".join(f"{g} {c[g]/1e18:+.4f}" for g in ("crowd", "crowdB", "us", "dust", "outsider") if c[g]))
# biggest outsider contributions
big = sorted(((by["outsider"], p) for p, by in rows), key=lambda t: -abs(t[0]))[:8]
print("largest outsider nets per launch:")
for v, p in big: print(f"   {time.strftime('%m-%d %H:%M', time.gmtime(p['ts']))} {p['kind']} fee {p['fee']} outsider net {v/1e18:+.5f} ETH")
