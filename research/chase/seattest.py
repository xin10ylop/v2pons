#!/usr/bin/env python3
"""seattest.py RUGS.json CHAIN OUT.json [MIN_POOLS] [SAMPLE]: the seat test on every line of a rugcensus.py dataset, the property that made the
2.433 line pay: an outside buy right after the launch, BEFORE the operator's fleet buys, and the fleet still comes and the pull still waits
for its timer.

A line: pulled pools of one venue/fee/tick spacing/hook shape and one native launch size (3 significant figures), MIN_POOLS (8) or more from
5+ distinct launch wallets. SAMPLE (16) pools per line, spread over the window; every swap on each from the launch to the pull, with the
buyer (V2/V3: the Swap's recipient topic; v4: the transaction's sender). Fleet: buyers on at least a quarter of the sampled pools (3 at
least), not a launch wallet. Per line:
  pump      the fleet's buys before its last buy, net of its sells, as a price multiple (constant product, from the launch's native side)
  pre-fleet outside buys before the fleet's first buy (dust under 0.2% of the pool apart), and what followed each: the fleet still came
            and the pull waited (OPEN), the fleet never came (SKIP), the pull came within ~10 s (PULL)
  post      outside buys after the fleet's first buy of 0.2%+ of the pool: pulled within ~10 s, or not
  seat      the paper trade: buy 1% of the pool's native in the first block after the launch, sell after the fleet's last buy, 0.3% a leg"""
import json, sys, collections, statistics as st, concurrent.futures as cf
import v4census as V
import rugcensus as R
from rugline import T_SWAP2, T_SWAP3, T_SWAP3P, T_SWAP4

R.EP["rh"] = [("https://rpc.mainnet.chain.robinhood.com", 25000)]           # it caps eth_getLogs at 30,000 blocks now
R.EP["bsc"] = [("https://rpc-bsc.48.club", 5000), ("https://bsc-rpc.publicnode.com", 5000)]
TXURL = {"base": "https://base.gateway.tenderly.co", "eth": "https://ethereum-rpc.publicnode.com", "bsc": "https://bsc-rpc.publicnode.com",
         "rh": "https://rpc.mainnet.chain.robinhood.com"}


def swaps(ch, p, cap=150):
    lo, hi = p["bn"], p["rem_bn"] + 2
    if p["venue"] == "v4":
        L = R.logs(ch, lo, hi, [[T_SWAP4], p["id"][3:]], p["pm"])
    else:
        L = R.logs(ch, lo, hi, [[T_SWAP2, T_SWAP3, T_SWAP3P]], p["id"][3:])
    L = sorted(L, key=lambda x: (int(x["blockNumber"], 16), int(x["logIndex"], 16)))[:cap]
    ev = []
    for x in L:
        d = x["data"][2:]; off = int(x["blockNumber"], 16) - p.get("add_bn", p["bn"])
        t0 = x["topics"][0]
        if t0 == T_SWAP2:
            a0i, a1i, a0o, a1o = (int(d[i:i + 64], 16) for i in (0, 64, 128, 192))
            nat = ((a0i - a0o) if p["nat"] == 0 else (a1i - a1o)) / 1e18; who = "0x" + x["topics"][2][26:]
        elif t0 == T_SWAP4:
            nat = (-R.i256(d[0:64]) if p["nat"] == 0 else -R.i256(d[64:128])) / 1e18; who = None
        else:
            nat = (R.i256(d[0:64]) if p["nat"] == 0 else R.i256(d[64:128])) / 1e18; who = "0x" + x["topics"][2][26:]
        ev.append({"off": off, "nat": nat, "who": who, "tx": x["transactionHash"]})
    if p["venue"] == "v4":
        url = TXURL.get(ch, V.CH[ch][0] if ch in V.CH else R.EP[ch][0][0])
        for e in ev:
            try:
                e["who"] = V.rpc(url, "eth_getTransactionByHash", [e["tx"]], tries=3)["from"].lower()
            except Exception:
                e["who"] = None
    p["sw"] = ev
    return p


def cp_after(N, buys):
    """constant product, native reserve N and token reserve 1: the native reserve and price after native flows (+ in, - out)"""
    x, y = N, 1.0
    for b in buys:
        if b > 0:
            nx = x + b; y = x * y / nx; x = nx
        elif b < 0 and x + b > 0:
            nx = x + b; y = x * y / nx; x = nx
    return x, y


def seat(N, fleet_flows, s=None, fee=0.003):
    s = s if s is not None else 0.01 * N
    x, y = N, 1.0
    nx = x + s * (1 - fee); got = y - x * y / nx; x, y = nx, x * y / nx          # our buy
    for b in fleet_flows:
        if b == 0:
            continue
        nx = x + b
        if nx <= 0:
            continue
        y = x * y / nx; x = nx
    ny = y + got; out = x - x * y / ny                                            # our sell
    return out * (1 - fee) - s, s


def test_line(ch, ps, bt, sample):
    ps = sorted(ps, key=lambda p: p["bn"])
    take = ps[:: max(1, len(ps) // sample)][:sample]
    with cf.ThreadPoolExecutor(5) as ex:
        take = [p for p in ex.map(lambda p: _safe(ch, p), take) if p.get("sw") is not None]
    if not take:
        return None
    launchers = {p.get("frm") for p in ps}
    cnt = collections.Counter(w for p in take for w in {e["who"] for e in p["sw"] if e["who"] and e["nat"] > 0})
    fleet = {w for w, c in cnt.items() if c >= max(3, len(take) // 4) and w not in launchers}
    pulls = sorted(p["rem_bn"] - p.get("add_bn", p["bn"]) for p in ps)
    med_pull = st.median(pulls)
    react = max(2, int(10 / bt))                                                    # ~10 s in blocks
    res = {"n": len(ps), "sampled": len(take), "fleet": len(fleet), "launchers": len(launchers), "pull_med_min": round(med_pull * bt / 60, 1),
           "size": st.median(p.get("nat_in") or 0 for p in ps), "pre": collections.Counter(), "pre_ex": [], "post_real": 0, "post_pulled": 0,
           "pump": [], "seat": [], "fleet_first": [], "fleet_last": []}
    for p in take:
        N = p.get("nat_in") or 0
        if N <= 0:
            continue
        poff = p["rem_bn"] - p.get("add_bn", p["bn"])
        fb = [e for e in p["sw"] if e["who"] in fleet and e["nat"] > 0]
        first = fb[0]["off"] if fb else None; last = fb[-1]["off"] if fb else None
        flows = [e["nat"] for e in p["sw"] if e["who"] in fleet and (last is None or e["off"] <= last)]
        if fb:
            res["fleet_first"].append(first); res["fleet_last"].append(last)
            x, y = cp_after(N, flows); res["pump"].append((x / y) / N)              # price multiple: (x/y) / (N/1)
            g, s = seat(N, flows); res["seat"].append(g / s)
        dust = 0.002 * N
        for e in p["sw"]:
            if e["who"] in fleet or e["who"] in launchers or e["nat"] <= 0:
                continue
            if first is None or e["off"] < first:
                if e["nat"] < dust:
                    continue
                if not fb:
                    tag = "SKIP"
                elif poff - e["off"] <= react:
                    tag = "PULL"
                else:
                    tag = "OPEN"
                res["pre"][tag] += 1
                res["pre_ex"].append((round(e["nat"], 5), e["off"], first, poff, tag, e["who"]))
                break                                                                # the first one decides the pool
        for e in p["sw"]:
            if first is not None and e["off"] > first and e["who"] not in fleet and e["who"] not in launchers and e["nat"] >= dust:
                res["post_real"] += 1
                if poff - e["off"] <= react:
                    res["post_pulled"] += 1
    return res


def _safe(ch, p):
    try:
        return swaps(ch, p)
    except Exception as e:
        p["sw"] = None; p["err"] = str(e)[:80]
        return p


def main(rugs, ch, out, min_pools=8, sample=16):
    r = json.load(open(rugs))["chains"][ch]
    bt = r["bt"]
    g = collections.defaultdict(list)
    for p in r["rugs"]:
        if not (p.get("nat_in") or 0) > 0:
            continue
        shape = f"{p['venue']} fee {p.get('fee', '-')} ts {p.get('ts', '-')}" + (" hook" if p.get("hooks", R.ZERO) != R.ZERO else "")
        g[(shape, R.sig3(p["nat_in"]))].append(p)
    lines = {k: v for k, v in g.items() if len(v) >= min_pools and len({p.get("frm") for p in v}) >= 5}
    print(f"{ch}: {len(lines)} lines of {min_pools}+ pools (block {bt:.2f} s)", flush=True)
    results = {}
    for (shape, size), ps in sorted(lines.items(), key=lambda kv: -len(kv[1])):
        t = test_line(ch, ps, bt, sample)
        if not t:
            print(f"  {shape} x {size}: unreadable", flush=True); continue
        results[f"{shape} x {size}"] = t
        pre = t["pre"]; verdict = ("OPEN" if pre["OPEN"] >= 2 and pre["OPEN"] > pre["PULL"] + pre["SKIP"] else
                                   "CLOSED" if pre["PULL"] + pre["SKIP"] >= 2 and pre["OPEN"] == 0 else "UNKNOWN")
        t["verdict"] = verdict
        pump = st.median(t["pump"]) if t["pump"] else 0; seatm = st.median(t["seat"]) if t["seat"] else 0
        print(f"  {len(ps):4d} x {size:<8g} {shape:24s} fleet {t['fleet']:3d} | pump x{pump:4.2f} seat {seatm:+6.1%} | fleet +{st.median(t['fleet_first']) if t['fleet_first'] else '-'}"
              f"..+{st.median(t['fleet_last']) if t['fleet_last'] else '-'} pull {t['pull_med_min']} min | pre-fleet OPEN {pre['OPEN']} SKIP {pre['SKIP']} PULL {pre['PULL']}"
              f" | post {t['post_pulled']}/{t['post_real']} pulled | {verdict}", flush=True)
        json.dump(results, open(out, "w"), default=list)
    json.dump(results, open(out, "w"), default=list)


if __name__ == "__main__":
    a = sys.argv
    main(a[1], a[2], a[3], int(a[4]) if len(a) > 4 else 8, int(a[5]) if len(a) > 5 else 16)
