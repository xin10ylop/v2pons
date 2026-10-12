"""Robustness of r06's mean: bootstrap 90% interval, the mean without the top 1/5/10 trades and without Oct 12 03:00-03:30 UTC (the
0x7feb3ecb cluster); the sell at the END of its landing block (after the block's other swaps) against the head; the cap at 76 / 70 / 60.
Writes r12_robust.out (stdout) and r12_launches.tsv (one line per launch)."""
from common import *
import statistics as stt, random, calendar, importlib.util
spec = importlib.util.spec_from_file_location("r6", J("r06_replay.py"))
D = json.load(open(J("r06_rows.json"))); R = D["rows"]
for key in ("0.0012|2|2", "0.002|2|2", "0.0036|2|2", "0.004|2|2", "0.0058|2|2"):
    v = [r["r"][key]["ret"] for r in R]; random.seed(7)
    bs = sorted(stt.mean(random.choices(v, k=len(v))) for _ in range(20000))
    s = sorted(v)
    c0, c1 = calendar.timegm((2026, 10, 12, 3, 0, 0)), calendar.timegm((2026, 10, 12, 3, 30, 0))
    print(f"{key}: mean {stt.mean(v)*100:+.2f}%  bootstrap 90% [{bs[1000]*100:+.2f}%, {bs[19000]*100:+.2f}%]  without top 1 {stt.mean(s[:-1])*100:+.2f}%  top 5 {stt.mean(s[:-5])*100:+.2f}%  "
          f"top 10 {stt.mean(s[:-10])*100:+.2f}%  top 28 (10%) {stt.mean(s[:-28])*100:+.2f}%  without Oct 12 03:00-03:30 {stt.mean(r['r'][key]['ret'] for r in R if not c0 <= r['ts'] < c1)*100:+.2f}%")
# variants that need the event stream again: import r06's functions without re-running its main loop
src = open(J("r06_replay.py")).read().split("STAKES = [")[0]
g = {"__name__": "r6v", "__file__": J("r06_replay.py")}; exec(compile(src, "r06_replay_head", "exec"), g)
X = {x["pool"]: x for x in g["X"]}
def replay_v(x, es, e, q, d, cap, sell_tail=False):
    Pool = g["Pool"]; apply = g["apply"]; lb = x["lb"]; buy_blk = lb + e; pool = Pool(x["sqrt_p"]); i = 0
    while i < len(es) and es[i]["bn"] < buy_blk: apply(pool, es[i]); i += 1
    a0, a1 = pool.swap(True, q); tok = -a1
    trig = next((r for r in es if r["k"] == "s" and r.get("eng") is not None and r["eng"] >= g["MIN"] and r["a0"] > 0 and r["bn"] >= buy_blk), None)
    send = min(trig["bn"] + 18, lb + cap) if trig else lb + cap; land = send + d
    pull = next((r["bn"] for r in es if r["k"] == "b" and r["amt"] > 0), None); pulled = pull is not None and pull <= land
    while i < len(es) and (es[i]["bn"] <= land if sell_tail else es[i]["bn"] < land): g["apply"](pool, es[i]); i += 1
    out = -pool.swap(False, tok)[0]; gas = (g["GAS_BUY"] + (g["GAS_SELL_PULLED"] if pulled else g["GAS_SELL"])) * g["BASE_FEE"]
    return (-1.0 if pulled else (out - q) / q) - gas / q, pulled
rows_es = [(X[r["pool"]], g["parse"](X[r["pool"]])) for r in R]
q = int(0.0058e18)
for lab, kw in (("sell at the END of its landing block (+2)", dict(e=2, d=2, cap=78, sell_tail=True)), ("cap 76 (lands +78)", dict(e=2, d=2, cap=76)),
                ("cap 70 (lands +72)", dict(e=2, d=2, cap=70)), ("cap 60 (lands +62)", dict(e=2, d=2, cap=60)), ("cap 88 (lands +90)", dict(e=2, d=2, cap=88)),
                ("cap 98 (lands +100)", dict(e=2, d=2, cap=98))):
    res = [replay_v(x, es, q=q, **kw) for x, es in rows_es]; v = [a for a, b in res]
    print(f"0.0058, entry +2, {lab}: mean {stt.mean(v)*100:+.2f}% median {stt.median(v)*100:+.3f}% pulled {sum(b for a, b in res)}")
with open(J("r12_launches.tsv"), "w") as f:
    hdr = ["launch_utc", "block", "pool", "token", "weth_side", "launch_wallet", "crowd1_off", "crowd1_eth", "crowd1_contract", "engine_trigger_off", "engine_trigger_eth",
           "n_before", "eth_before", "before (offset:sender:to:size ETH)", "first_burn_off", "burn_by_launch_wallet", "exit_send_off(e2)", "exit(e2)", "price_move(e2,l2)"]
    for qq in ("0.0012", "0.0036", "0.0058"):
        for e in (1, 2, 3): hdr += [f"gross_{qq}_e{e}", f"net_{qq}_e{e}"]
    hdr += ["net_0.0058_e2_lands+1", "engine_dry_0.0058"]
    f.write("\t".join(hdr) + "\n")
    for r in R:
        m = r["r"]["0.0058|2|2"]
        bef = " ".join(f"{b[0]}:{(b[1] or '?')[:8]}:{(b[2] or '?')[:8]}:{b[4]:.5f}" for b in r["before"])
        row = [r["utc"], r["lb"], r["pool"], r["token"], "token0", r["launch_from"], r["crowd1_off"], f"{r['crowd1_eth']:.4f}" if r["crowd1_eth"] else "", r["crowd1_to"] or "",
               r["eng1_off"], f"{r['eng1_eth']:.4f}" if r["eng1_eth"] else "", len(r["before"]), f"{sum(b[4] for b in r['before']):.5f}", bef, r["burn_off"], r["burn_by_launcher"],
               m["send_off"], "cap" if m["cap"] else "crowd+18", f"{m['move']*100:+.3f}%"]
        for qq in ("0.0012", "0.0036", "0.0058"):
            for e in (1, 2, 3):
                z = r["r"][f"{qq}|{e}|2"]; row += [f"{z['gross']*100:+.3f}%", f"{z['ret']*100:+.3f}%"]
        row += [f"{r['r']['0.0058|2|1']['ret']*100:+.3f}%", f"{r['dry']['0.0058']['dry']*100:+.3f}%"]
        f.write("\t".join(str(c) if c is not None else "" for c in row) + "\n")
print("wrote r12_launches.tsv", len(R), "rows")
