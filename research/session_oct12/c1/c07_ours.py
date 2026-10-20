"""Our live C-1 trades in detail (offline, c04 + c05): every relay swap in a C-1 pool and every wallet transaction near the box-log times;
per pool: launch, T, our buy / sell offsets, the pull, the router's buying around us, every other buy after T (class, size, offset)."""
from common import *
D = json.load(open(J("c05_pools.json"))); P = {p["pid"]: p for p in D["pools"]}
O = json.load(open(J("c04_ours.json"))) if os.path.exists(J("c04_ours.json")) else []
print("== our wallet's transactions near the box-log C-1 times")
for f in O:
    p = P.get(f["c1"]) if f["c1"] else None
    sw = [l for l in f["logs"] if l["address"].lower() == PM and l["topics"][0] == T_SWAP]
    print(f"  nonce {f['nonce']} {utc(f['ts'])} block {f['block']} (idx {f['txindex']}) to {f['to'][:10]} sel {f['input'][2:10]} status {f['status']} gas {f['gasUsed']} swaps {len(sw)}"
          + (f" | C-1 pool {p['pid'][:12]} launch {p['lb']} {utc(p['ts'])} T +{p['T']} -> our tx at +{f['block'] - p['lb']} (T+{f['block'] - p['lb'] - p['T']}); pull +{p['pull']}" if p else ""))
ours = [p for p in P.values() if any(s["cls"] == "ours" for s in p["sw"])] + [P[f["c1"]] for f in O if f["c1"] and f["status"] == 0]
seen = set()
print("\n== our C-1 pools")
for p in sorted(ours, key=lambda p: p["lb"]):
    if p["pid"] in seen: continue
    seen.add(p["pid"])
    ob = [s for s in p["sw"] if s["cls"] == "ours" and s["buy"]]; os_ = [s for s in p["sw"] if s["cls"] == "ours" and not s["buy"]]
    rv = [f for f in O if f["c1"] == p["pid"] and f["status"] == 0]
    b = ob[0]["off"] if ob else (rv[0]["block"] - p["lb"] if rv else None)
    T = p["T"]
    rb = lambda a, z: [s for s in p["sw"] if s["buy"] and s["cls"] == "router" and a < s["off"] <= z]
    print(f"\n pool {p['pid']} token {p['token']} launch {p['lb']} {utc(p['ts'])} launcher {p['launcher'][:10]}")
    print(f"   T +{T} (router first buy {p['T_eth']:.4f} ETH); our buy {'+%d (T+%d) %.4f ETH' % (b, b - T, ob[0]['eth']) if ob else ('REVERTED at +%d (T+%d)' % (b, b - T) if rv else None)};"
          f" our sell {[('+%d' % s['off'], round(s['eth'], 6)) for s in os_]}; pull {p['pull']} ({'buy+%d' % (p['pull'] - b) if p['pull'] is not None and b is not None else '-'}) by {(p['pull_tx'] or {}).get('from', '')[:10]}")
    if b is not None:
        for nm, a, z in (("T..our buy", T - 1, b), ("our buy..+62", b, b + 62), ("+62..pull", b + 62, p["pull"] if p["pull"] is not None else b + 400)):
            g = rb(a, z); print(f"   router buys {nm:13s}: {len(g):3d}, {sum(s['eth'] for s in g):.4f} ETH")
        print(f"   router ETH by T+60 {sum(s['eth'] for s in rb(-1, T + 60)):.4f}; router sells before the pull {sum(1 for s in p['sw'] if not s['buy'] and s['cls'] == 'router' and (p['pull'] is None or s['off'] <= p['pull']))}")
    oth = [s for s in p["sw"] if s["buy"] and s["cls"] not in ("router", "ours") and (p["pull"] is None or s["off"] <= p["pull"]) and (b is None or s["off"] <= b + 200)]
    print(f"   other (non-router) buys from launch to min(pull, our buy + 200) [offset, class, from, ETH]: {[(s['off'], s['cls'], s.get('from', '?')[:10], round(s['eth'], 6)) for s in oth]}")
