#!/usr/bin/env python3
"""seatprofile.py CHAIN CPDUMP ENTRIES DAY...: how the dust seat executes and what the line does around it, from the tapes plus a sample of
transactions. Same inputs as seatlab.py (ENTRIES is the seat wallet's entries.py file).

  entry      the seat's buy block against the pool's add block, its place in its block
  exit       the multiple it sells at (sold/paid) by pool size, and the pool's price path after its entry (multiple of its entry price at
             t seconds, over the pools still alive), the peak before the pull, the price at the pull
  tx         to-address, selector, gas price, gas limit, value and Universal Router calldata shape (commands, deadline) of the seat, of a
             second wallet (TWIN env) and of newcomers that were pulled on
  timing     outside dust first buys under 200 s: pulled within 5 s, residents (RESIDENTS env) against newcomers, by whether the machine
             had already bought and by age
  history    token transfers received by TWIN before the first tape day (was it on the chain before?)
Read-only, public RPCs (a few hundred transaction lookups)."""
import os, sys, json, gzip, random, bisect, collections, statistics as st, datetime as dt
import hlib as H
from seatlab import q

TWIN = os.environ.get("TWIN", "0x68936d46d0aaee21930d1f0039c1ce1b3431931d")
RESIDENTS = set(os.environ.get("RESIDENTS", "0x7ae81404e32aef363eb63bc4befba78fb5b636de,0x68936d46d0aaee21930d1f0039c1ce1b3431931d,"
                               "0x24919ef805725a0b368b5e36d49aabe7dccc5cc2,0x2be87ad70cf11ea294d7c42044b5b8277a3e4874").split(","))
T = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def ur_shape(t, url):
    inp = t["input"]
    if not (t.get("to") or "").lower().startswith("0x8876789976") or len(inp) < 202:
        return ((t.get("to") or "")[:10], inp[:10])
    off = int(inp[10:74], 16) * 2 + 10; clen = int(inp[off:off + 64], 16); cmds = inp[off + 64:off + 64 + clen * 2]
    dl = int(inp[138:202], 16); dls = "max" if dl > 2 ** 40 else f"+{round((dl - H.ts(url, int(t['blockNumber'], 16))) / 10) * 10}s"
    return ("UR", f"bytes {(len(inp) - 2) // 2}", f"cmd {cmds}", f"deadline {dls}", f"gas {int(t['gas'], 16)}")


def main(ch, cpf, entf, days):
    here = os.path.dirname(os.path.abspath(__file__)); url = H.CH[ch]["rpc"]; random.seed(1)
    CP = json.load(gzip.open(os.path.join(here, cpf), "rt"))
    E = json.load(open(os.path.join(here, entf))); seat = None
    tapes = {day: json.load(gzip.open(os.path.join(here, f"out/tape_{ch}_{day}.json.gz"), "rt")) for day in days}
    per = collections.defaultdict(list)
    for day in days:
        for pid, cps in CP[day].items():
            seen = {}
            for e, cp in zip(tapes[day]["pools"][pid]["ev"], cps):
                if cp and e[2] > 0 and cp not in seen:
                    seen[cp] = e[2]
            for cp, s in seen.items():
                per[cp].append(s)
    machine = {cp for cp, v in per.items() if len(v) >= 3 and st.median(v) >= 0.001}
    # --- entry and exit
    dblk = collections.Counter(); firstin = [0, 0]; mult = collections.defaultdict(list); path = collections.defaultdict(lambda: collections.defaultdict(list))
    peak = collections.defaultdict(list); atpull = collections.defaultdict(list); txs = []
    for x in E:
        d = tapes.get(x["day"])
        if not d:
            continue
        p = d["pools"][x["pool"]]; ev = p["ev"]; b = ev[x["b"]]; bt = d["bt"]; n = round(p["nin"]); bns = [e[0] for e in ev]
        dblk[b[0] - p["add"]] += 1; firstin[0] += not any(e[0] == b[0] and e[1] < b[1] for e in ev); firstin[1] += 1
        if seat is None:
            seat = CP[x["day"]][x["pool"]][x["b"]]
        price0 = b[4] / b[5]
        for t in (10, 30, 60, 120, 180, 240, 300, 360):
            k = bisect.bisect_right(bns, b[0] + round(t / bt)) - 1
            if k >= x["b"] and ev[k][0] < p["pull"] and ev[k][4]:
                path[n][t].append((ev[k][4] / ev[k][5]) / price0)
        alive = [(e[4] / e[5]) / price0 for e in ev[x["b"]:] if e[0] < p["pull"] and e[4]]
        if alive:
            peak[n].append(max(alive)); atpull[n].append(alive[-1])
        if x["s"] is not None:
            mult[n].append(-ev[x["s"]][2] / b[2])
        txs.append(b[6])
    print(f"== entry: seat {seat}; buy block - add block {sorted(dblk.items())[:8]} | first swap of the pool in its block {firstin[0]} of {firstin[1]}")
    for n in sorted(mult):
        print(f"== exit, x{n} pools ({len(peak[n])} entries): sells at {q(mult[n])} x its entry price | peak before the pull {q(peak[n])} | at the pull {q(atpull[n])}")
        print("   price path after its entry (median multiple): " + " ".join(f"{t}s:{st.median(v):.2f}" for t, v in sorted(path[n].items()) if v))
    # --- transactions
    F = json.load(open(os.path.join(here, "out/tolmodel_first.json")))

    def tx_of(r):
        p = tapes[r["day"]]["pools"][r["pool"]]; cps = CP[r["day"]][r["pool"]]
        return next((e[6] for e, cp in zip(p["ev"], cps) if cp == r["who"] and e[2] > 0), None)

    groups = {"seat": random.sample(txs, min(50, len(txs))),
              "twin": [h for h in (tx_of(r) for r in random.sample([r for r in F if r["who"] == TWIN] or [None], 1) if r) if h]}
    groups["twin"] = [h for h in (tx_of(r) for r in random.sample([r for r in F if r["who"] == TWIN], min(50, sum(r["who"] == TWIN for r in F)))) if h]
    new = [r for r in F if r["who"] not in RESIDENTS and r["size"] < 0.0001 and r["age"] < 200 and r["to_pull"] <= 5]
    groups["newcomer dust, pulled"] = [h for h in (tx_of(r) for r in random.sample(new, min(50, len(new)))) if h]
    print("== transactions (sample): to, selector, gas price, value, calldata shape")
    for name, hs in groups.items():
        got = [t for t in H.batch(url, [("eth_getTransactionByHash", [h]) for h in hs], size=25, workers=2) if t]
        if not got:
            print(f"   {name}: none"); continue
        to = collections.Counter((t.get("to") or "")[:10] for t in got); sel = collections.Counter(t["input"][:10] for t in got)
        gp = [int(t["gasPrice"], 16) / 1e9 for t in got]; val = [int(t["value"], 16) / 1e18 for t in got]
        shapes = collections.Counter(ur_shape(t, url) for t in got[:20])
        print(f"   {name:22s} n {len(got):2d} | to {to.most_common(2)} | selector {sel.most_common(2)} | gas price gwei median {st.median(gp):.4f} max {max(gp):.4f}"
              f" | value {q(val) if len(val) >= 20 else st.median(val)} | senders {len({t['from'] for t in got})}")
        for k, c in shapes.most_common(3):
            print(f"      {c:2d} x {k}")
    # --- timing against the machine
    mfirst = {}
    for day in days:
        bt = tapes[day]["bt"]
        for pid, cps in CP[day].items():
            p = tapes[day]["pools"][pid]
            mfirst[(day, pid)] = next(((e[0] - p["add"]) * bt for e, cp in zip(p["ev"], cps) if e[2] >= 0.01 and (cp in machine or cp == p["frm"])), 1e9)
    rows = [r for r in F if r["size"] < 0.0001 and r["age"] < 200]
    print("== outside dust first buys under 200 s: pulled within 5 s, by wallet kind, whether the machine had bought yet, and age")
    for name, sel in (("resident", lambda r: r["who"] in RESIDENTS), ("newcomer", lambda r: r["who"] not in RESIDENTS)):
        for pre in (True, False):
            for lo, hi in ((0, 0.35), (0.35, 0.6), (0.6, 1), (1, 2), (2, 5), (5, 20), (20, 200)):
                v = [r for r in rows if sel(r) and ((r["age"] < mfirst[(r["day"], r["pool"])]) == pre) and lo <= r["age"] < hi]
                if len(v) >= 3:
                    print(f"   {name:8s} {'before' if pre else 'after '} the first machine buy, age {lo:4g}-{hi:<4g}s: {len(v):5d} buys by {len({r['who'] for r in v}):3d} wallets"
                          f" | pulled within 5 s {sum(r['to_pull'] <= 5 for r in v) / len(v):4.0%}")
    v = [r for r in rows if r["who"] not in RESIDENTS and r["age"] < mfirst[(r["day"], r["pool"])]]
    print(f"   newcomers in the residents' slot (before the first machine buy): {len(v)}, pulled within 5 s {sum(r['to_pull'] <= 5 for r in v)} | by wallet and day: "
          + str(collections.Counter((r["who"][:10], r["day"][4:]) for r in v).most_common(8)))
    # --- the twin's history
    y, m, dd = int(days[0][:4]), int(days[0][4:6]), int(days[0][6:])
    lo = H.block_at(ch, dt.datetime(y, m, dd, tzinfo=dt.timezone.utc).timestamp() - 13 * 86400); hi = H.block_at(ch, dt.datetime(y, m, dd, tzinfo=dt.timezone.utc).timestamp())
    L = H.logs(ch, lo, hi, [T, None, "0x" + "0" * 24 + TWIN[2:]])
    print(f"== {TWIN[:10]}: token transfers received in the 13 days before {days[0]}: {len(L)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
