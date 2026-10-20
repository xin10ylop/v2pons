#!/usr/bin/env python3
"""analyze.py base.json [bnb.json ...]: launcher groups on each chain, with the operator fingerprint score."""
import json, sys, statistics as st, urllib.request, time, collections, datetime
H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"}
RPC = {"base": "https://mainnet.base.org", "bnb": "https://bsc-rpc.publicnode.com", "ethereum": "https://ethereum-rpc.publicnode.com", "robinhood": "https://rpc.mainnet.chain.robinhood.com"}
BT = {"base": 2.0, "bnb": 0.45, "ethereum": 12.0, "robinhood": 0.1}
def ts_of(chain, bn):
    for _ in range(5):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(RPC[chain], json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_getBlockByNumber", "params": [hex(bn), False]}).encode(), H), timeout=30))
            return datetime.datetime.utcfromtimestamp(int(r["result"]["timestamp"], 16)).strftime("%m-%d %H:%M")
        except Exception: time.sleep(2)
    return "?"
def med(xs): return round(st.median(xs), 3) if xs else None
for path in sys.argv[1:]:
    d = json.load(open(path)); chain = d["chain"]; pools = d["pools"]
    print(f"\n===== {chain}: {len(pools)} native-paired v4 pools since {d['from']} UTC (blocks {d['blocks'][0]}-{d['blocks'][1]})")
    groups = collections.defaultdict(list)
    for pid, p in pools.items(): groups[(p["to"], p["hook"], p["ts"])].append(p)
    rows = []
    for (to, hook, ts), ps in groups.items():
        if len(ps) < 3: continue
        ps.sort(key=lambda p: p["bn"]); n = len(ps)
        sampled = [p for p in ps if "liq" in p]
        eth0 = [p["eth0"] for p in sampled if p.get("eth0")]
        pulls = [p["pull"][0] for p in sampled if p.get("pull")]
        fresh = sum(1 for p in ps if p.get("nonce") == 0); distinct_from = len({p["from"] for p in ps})
        fees = collections.Counter(p["fee"] for p in ps).most_common(3); sels = collections.Counter(p["sel"] for p in ps).most_common(2)
        span_h = (ps[-1]["bn"] - ps[0]["bn"]) * BT[chain] / 3600
        score = (ts == 200) + (fresh / n > 0.8) + (bool(pulls) and len(pulls) / max(1, len(sampled)) > 0.6) + (bool(eth0) and 1.0 <= st.median(eth0) <= 5.0) + (fees[0][0] <= 10000)
        rows.append((score, n, to, hook, ts, fees, sels, fresh, distinct_from, eth0, pulls, sampled, ps, span_h))
    rows.sort(key=lambda r: (-r[0], -r[1]))
    for score, n, to, hook, ts, fees, sels, fresh, distinct_from, eth0, pulls, sampled, ps, span_h in rows[:14]:
        first, last = ts_of(chain, ps[0]["bn"]), ts_of(chain, ps[-1]["bn"])
        print(f"\n[{chain}] score {score}/5  launcher 0x{to}  hook {('0x'+hook) if hook.strip('0') else 'none'}  tick {ts}  pools {n}  ({first} -> {last} UTC, {n/max(span_h,0.1):.1f}/h)")
        print(f"    fees {fees}  selectors {sels}  fresh-wallet deployers {fresh}/{n} (distinct {distinct_from})")
        if sampled:
            print(f"    sampled {len(sampled)}: liquidity ETH median {med(eth0)} (min {min(eth0) if eth0 else None}, max {max(eth0) if eth0 else None});"
                  f" pulled inside {int(BT[chain]*0)}..{round(BT[chain]*max(1,(sampled[0].get('pull') or [0])[0]) if False else 0)}: {len(pulls)}/{len(sampled)}, pull median {med(pulls)} blocks = {round(med(pulls)*BT[chain]) if pulls else None} s")
            print(f"    last pools: " + "; ".join(f"blk {p['bn']} liq {round(p.get('eth0',0),2)} pull {p.get('pull')}" for p in sampled[-4:]))
