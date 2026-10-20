"""B08: did the line launch before the census window (Oct 4 13:52 UTC)? V3 factory PoolCreated from D days (default 4) before the census's first
block (79,985,203) to it; keep 13ead562 -> 0x73991a25 launches; fetch their events (b02.fetch) and report the line launches, their own buys and
any outside buy ahead of the own buy. Public RPC, read-only. -> b08_before.json, b08_before.out"""
import sys, os, json
from bc import *
import b02_events
D = float(sys.argv[1]) if len(sys.argv) > 1 else 4.0
END = 79985203
PC = Cache("b08_pc"); TX = Cache("b08_tx")
t_end = int(R.call("eth_getBlockByNumber", [hex(END), False])["timestamp"], 16)
lo, hi = max(1, END - int(D * 86400 * 11)), END
while lo < hi:
    m = (lo + hi) // 2
    if int(R.call("eth_getBlockByNumber", [hex(m), False])["timestamp"], 16) < t_end - D * 86400: lo = m + 1
    else: hi = m
start = lo
print(f"scan {start}..{END} ({ts(t_end - D * 86400)} .. {ts(t_end)} UTC)")
pc = []
for a in range(start, END, 50000):
    b = min(a + 49999, END - 1); k = f"{a}-{b}"
    if k not in PC: PC.put(k, R.logs({"address": FACT, "topics": [T_PC]}, a, b))
    pc += PC[k]
tx = txs(TX, [l["transactionHash"] for l in pc])
fam = []
for l in pc:
    t = tx[l["transactionHash"]]
    if not t or t["to"] != NPM or t["input"][2:10] != "13ead562": continue
    t0 = "0x" + l["topics"][1][-40:]; t1 = "0x" + l["topics"][2][-40:]
    fam.append({"pool": "0x" + l["data"][-40:], "token0": t0, "token1": t1, "fee": int(l["topics"][3], 16), "lb": int(l["blockNumber"], 16),
                "launch_from": t["from"], "launch_nonce": t["nonce"], "qs": 0 if t0 == WETH else 1 if t1 == WETH else None, "token": t1 if t0 == WETH else t0})
BT = Cache("b01_bt"); bt = block_ts(BT, [x["lb"] for x in fam])
for x in fam: x["ts"] = bt[x["lb"]]
L = [x for x in fam if x["qs"] is not None]
b02_events.fetch(L, END + 5000)
EV = b02_events.EV; TXd = b02_events.TX.d; TR = b02_events.TR
out = [f"PoolCreated {len(pc)} in {start}..{END - 1}; 13ead562->NPM launches {len(fam)} (WETH side {len(L)})"]
recs = [build(x, EV[x["pool"]]["ev"], EV[x["pool"]]["ev_to"], TXd, TR.get(x["pool"])) for x in L]
for r in recs:
    o = r["own1"]
    out.append(f"  {r['lb']} {ts(r['ts'])} {r['lw'][:10]} n{r['nonce']} fee {r['fee']} {'LINE' if r['line'] else 'not-line'} mint {[(m['off'], '%.4g' % m['L'], m['lo'], m['hi']) for m in r['mints']][:2]} "
               f"own1 {('+%d %.4f' % (o['off'], o['eth'])) if o else 'none'} ahead {[(s['off'], round(s['eth'], 5), (s['from'] or '?')[:10]) for s in r['pre'] if s['off'] <= 200]} "
               f"pull {r['pull1']['off'] if r['pull1'] else '-'}")
json.dump({"start": start, "end": END, "launches": fam}, open(p("b08_before.json"), "w"), indent=0)
open(p("b08_before.out"), "w").write("\n".join(out) + "\n"); print("\n".join(out)); print(R.STATS)
