"""Helpers over the shared block cache (lch/bc.py): sent/received txs of an address in a block range."""
import sys, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/lch")
import bc
def R(bn, ts, t): return {"bn": bn, "utc": time.strftime("%m-%d %H:%M:%S", time.gmtime(ts)), "hash": t[0], "from": t[1], "to": t[2], "eth": int(t[3]) / 1e18, "nonce": t[4], "sel": t[5], "len": t[6]}
def touching(addrs, lo, hi, desc=False, stop=None):
    A = {a.lower() for a in addrs}; out = []
    it = bc.txs_desc(lo, hi) if desc else bc.txs(lo, hi)
    for bn, ts, t in it:
        if t[1] in A or t[2] in A:
            out.append(R(bn, ts, t))
            if stop and stop(out): break
    return out
def show(rows, lab=None):
    for r in rows: print("   ", r["bn"], r["utc"], r["from"], "->", r["to"], round(r["eth"], 6), "n", r["nonce"], r["sel"], r["hash"][:16], (lab or {}).get(r["from"], ""), (lab or {}).get(r["to"], ""), flush=True)
