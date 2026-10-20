"""Case listings (offline): for 6 pools per shape, every Swap and ModifyLiquidity from the launch to +600 blocks (the launch tx summarized),
then what happened after +600 to the head (swap count, first and largest outside buy, any liquidity removal). Times are interpolated from
s01_meta (head/start timestamps; error about 1 s). Prints s08_cases.out."""
from common import *
M = json.load(open(J("s01_meta.json"))); D = json.load(open(J("s06_pools.json"))); A = json.load(open(J("s04_pools.json")))
mls = {p["pid"]: p["ml"] for p in A["pools"]}
bps = (M["head"] - M["start"]) / (M["t_head"] - M["t_start"])
tt = lambda bn: utc(M["t_head"] - (M["head"] - bn) / bps)
SENT = "0xe71a69f434a719cd5afa411568b69716aab3b84a"
def pick(pp):
    ext = lambda p: [w for w in p["sw"] if not w["inlaunch"] and w["from"] not in (SENT, p["launcher"])]
    act = [p for p in pp if ext(p)]
    rest = [p for p in pp if not ext(p)]
    out = act[:4] + rest[-2:] + rest[:max(0, 6 - len(act[:4]) - 2)]
    return out[:max(6, len(act[:4]) + 2)]
for s in ("S1", "S2", "S3", "S4"):
    pp = [p for p in D["pools"] if p["shape"] == s]
    print(f"\n######## {s} ({len(pp)} core pools in 12 h)")
    for p in pick(pp):
        ml = mls[p["pid"]]
        lt = [m for m in ml if m["inlaunch"]]
        dev = [w for w in p["sw"] if w["inlaunch"]]
        print(f"\n== pool {p['pid'][:18]} launched {tt(p['lb'])} UTC block {p['lb']} by {p['launcher']} via {p['target'][:10]} ({p['n']} B, value {p['value'] / 1e18:g}); "
              f"quote {p['qname']}, coin {p['coin'][:12]}; fee {p['fee']} ts {p['ts']} hook {p['hook'][:10]}")
        print(f"   launch tx: {len(lt)} ModifyLiquidity (owner {sorted({m['sender'][:10] for m in lt})}, range {min(m['lo'] for m in lt) if lt else None}..{max(m['hi'] for m in lt) if lt else None})"
              + (f"; launcher's own buy in the launch tx {dev[0]['eth']:.5f} ETH-eq (price x{dev[0]['mult']:.3f})" if dev else "; no swap in the launch tx"))
        for w in [w for w in p["sw"] if not w["inlaunch"] and w["off"] <= 600]:
            who = "sentinel" if w["from"] == SENT else ("LAUNCHER" if w["from"] == p["launcher"] else w["from"][:12])
            print(f"   +{w['off']:<4d} {'BUY ' if w['buy'] else 'SELL'} {w['eth'] if w['eth'] is not None else float('nan'):.6f} ETH-eq  {who:12s} via {(w['to'] or '')[:10]}:{w['sel']}  price x{w['mult']:.3f}")
        for m in [m for m in ml if not m["inlaunch"] and m["off"] <= 600]:
            print(f"   +{m['off']:<4d} ModifyLiquidity dL {m['dL']} by {m['sender'][:10]} (tx from {(m['from'] or '')[:10]})")
        late = [w for w in p["sw"] if w["off"] > 600 and w["from"] != SENT]
        rem = [m for m in ml if m["dL"] < 0]
        big = max(late, key=lambda w: w["eth"] or 0) if late else None
        print(f"   after +600 to the head (+{p['age']}): {len(late)} swaps" + (f", first at +{late[0]['off']} ({'buy' if late[0]['buy'] else 'sell'} {late[0]['eth']:.5f} by {'LAUNCHER' if late[0]['from'] == p['launcher'] else late[0]['from'][:10]})" if late else "")
              + (f", largest {big['eth']:.4f} at +{big['off']}" if big else "") + f"; price now x{p['last_mult']:.3f}, max x{p['max_mult']:.3f}; liquidity removals: {[(m['off'], m['dL']) for m in rem] or 'none'}")
