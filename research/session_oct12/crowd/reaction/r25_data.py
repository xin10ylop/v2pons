"""the data section: launches, days, pools pulled (and by whom), the crowd's first real buy, classes of the swaps, the RPC spent."""
from rlib import *
P = load(); M = json.load(open(J("r01_meta.json")))
days = collections.Counter(time.strftime("%m-%d", time.gmtime(p["ts"])) for p in P)
print(f"pools {len(P)}: launches {utc(P[0]['ts'])} .. {utc(min(p['ts'] for p in P[-5:]))}..{utc(P[-1]['ts'])} UTC; per day {sorted(days.items())}")
print(f"blocks {min(p['lb'] for p in P)} .. head {M['head']} ({utc(M['head_ts'])}); WETH token1 {sum(p['qs'] for p in P)}")
pl = [p for p in P if p["pull"] is not None]
print(f"pulled {len(pl)} (by the launch wallet {sum(1 for p in pl if p['pull_by_lw'])}); pull offset p10/50/90 {pct([p['pull'] for p in pl],.1)}/{pct([p['pull'] for p in pl],.5)}/{pct([p['pull'] for p in pl],.9)}")
fr = [p for p in P if p["frb"] is not None]
print(f"the crowd's first real buy before the pull (within + 3000): {len(fr)}; offset p10/25/50/75/90 " + "/".join(str(pct([p['frb'] for p in fr], q)) for q in (.1, .25, .5, .75, .9))
      + f"; by + 60 {sum(1 for p in fr if p['frb'] <= 60)}, by + 78 {sum(1 for p in fr if p['frb'] <= 78)}; first buy >= 0.005 not the crowd's: {sum(1 for p in P if p['trig'] is not None and (p['frb'] is None or p['trig'] < p['frb']))}")
cls = collections.Counter(s["k"] for p in P for s in p["sw"])
print(f"swaps up to the pull or + 3000: {sum(cls.values())}; classes {dict(cls)}")
print(f"outside wallets (bought >= 0.0005 ETH before the crowd): {len({o['w'] for p in P for o in p['outs']})} in {sum(1 for p in P if p['outs'])} pools")
n = 0; items = 0
for l in jl(J("rpc_log.jsonl")): n += 1; items += l["n"]
print(f"RPC (this directory's log): {n} POSTs, {items} items (plus r01's 213 POSTs logged under analysis/W)")
