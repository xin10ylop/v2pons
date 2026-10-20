"""Forward test of analyst C's rule on the V3 crowd line's recent launches (from w05_recent_<h>.json): buy 0.0058 ETH at the head of
launch + 2, sell 20 blocks after the first real buy (>= 0.005 ETH) at or after ours, or at launch + 80; a Burn (liquidity > 0) at or before
the sell block = -100%. Simulated with analyst C's V3Sim (replay.py: our buy put in the pool, every later swap re-simulated by amount).
Also: the gross price move (token price in ETH after our entry -> at the exit, from the Swap events' sqrtPriceX96, no impact/fees), the
first real buy's offset, size and sender contract, the wave's ETH in [frb, frb + 20], the first pull's offset."""
import json, sys, os, statistics as st, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/C")
from replay import replay, V3Sim
from v3dec import decode_launch_v3, WETH
from eth_utils import keccak
D = json.load(open(sys.argv[1])); Q = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0058
A_ENTRY, K, CAP = int(os.environ.get("ENTRY", "2")), 20, int(os.environ.get("CAP", "80"))
tp = lambda s: "0x" + keccak(text=s).hex()
T_SW = tp("Swap(address,address,int256,int256,uint160,uint128,int24)"); T_MI = tp("Mint(address,address,int24,int24,uint128,uint256,uint256)")
T_BU = tp("Burn(address,int24,int24,uint128,uint256,uint256)")
CROWD_SHAPES = {("3593564c", 484), ("a0193551", 452), ("49f74a5d", 452)}
UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
def S(x): x = int(x, 16); return x - (1 << 256) if x >> 255 else x
def W(d, i): return d[2 + 64 * i: 2 + 64 * (i + 1)]
def compact(l):
    t = l["topics"]; d = l["data"]; bn = int(l["blockNumber"], 16); ti = int(l["transactionIndex"], 16); li = int(l["logIndex"], 16); tx = l["transactionHash"]; a = l["address"].lower()
    if t[0] == T_SW: return ["s", bn, ti, li, a, "0x" + t[1][-40:], "0x" + t[2][-40:], S(W(d, 0)), S(W(d, 1)), int(W(d, 2), 16), int(W(d, 3), 16), S(W(d, 4)), tx]
    if t[0] == T_MI: return ["mi", bn, ti, li, a, "0x" + t[1][-40:], S(t[2]), S(t[3]), int(W(d, 1), 16), int(W(d, 2), 16), int(W(d, 3), 16), tx]
    if t[0] == T_BU: return ["b", bn, ti, li, a, "0x" + t[1][-40:], S(t[2]), S(t[3]), int(W(d, 0), 16), int(W(d, 1), 16), int(W(d, 2), 16), tx]
BT = D["buy_txs"]; head = D["head"]; rows = []
for x in D["line"]:
    d = decode_launch_v3(bytes.fromhex(x["tx"]["input"][2:])); qs = d["qs"]; lb = x["lb"]
    ev = [c for c in (compact(l) for l in x["logs"]) if c]
    o = {"lb": lb, "ev": ev, "ev_to": head - 3}
    row = {"dex": "v3", "quote_side": qs, "fee": d["fee"]}
    buys = [(e[1] - lb, (e[7] if qs == 0 else e[8]), e) for e in ev if e[0] == "s" and (e[7] if qs == 0 else e[8]) > 0]
    real = [(off, dq, e) for off, dq, e in buys if dq >= 5 * 10 ** 15]
    frb = real[0] if real else None
    trig = [off for off, dq, e in real if off >= A_ENTRY]
    b = trig[0] + K if trig and trig[0] + K <= CAP else CAP
    pulls = [e[1] - lb for e in ev if e[0] == "b" and e[8] > 0]
    r = replay(row, o, A_ENTRY, b, Q)
    # gross: the pool's own sqrtP path (no impact): price after the events of blocks < lb+2 vs after the events of blocks < lb+b
    def sp_before(blk):
        s = d["sqrt_p"]
        for e in ev:
            if e[0] == "s" and e[1] < blk: s = e[9]
        return s
    s0, s1 = sp_before(lb + A_ENTRY), sp_before(lb + b)
    gross = (s0 / s1) ** 2 - 1 if qs == 0 else (s1 / s0) ** 2 - 1
    ft = BT.get(frb[2][12]) if frb else None
    via = None
    if ft:
        sel = ft["input"][2:10]; ln = (len(ft["input"]) - 2) // 2
        via = ("crowd" if (sel, ln) in CROWD_SHAPES and (ft["to"] or "").lower() != UR else "other") + f":{(ft['to'] or '')[:10]}:{sel}:{ln}"
    wave = sum(dq for off, dq, e in real if frb and frb[0] <= off <= frb[0] + 20) / 1e18
    rows.append({"lb": lb, "age": head - lb, "pool": x["pool"], "qs": qs, "frb_off": frb[0] if frb else None, "frb_eth": frb[1] / 1e18 if frb else None, "via": via,
                 "wave20_eth": wave, "exit": b, "trig": trig[0] if trig else None, "pull": pulls[0] if pulls else None, "ret": r.get("ret"), "ok": r["ok"], "pulled": r.get("pulled"),
                 "gross": gross, "n_swaps_hold": sum(1 for e in ev if e[0] == "s" and lb + A_ENTRY <= e[1] < lb + b), "hi": d["hi"], "L": d["liq"],
                 "utc": None})
t_head = D["t_head"]; bps = D["bps"]
print(f"{len(rows)} launches of the V3 crowd line in the {D['hours']:g} h to {time.strftime('%H:%M', time.gmtime(t_head))} UTC (stake {Q} ETH; rule: buy +{A_ENTRY}, sell first real buy at/after ours +{K}, cap +{CAP})")
print(f"{'launch':>9} {'UTC':>5} {'qs':>2} {'frb':>4} {'frbETH':>7} {'via':<34} {'wave20':>6} {'exit':>4} {'pull':>5} {'gross':>7} {'net':>7}")
for z in rows:
    z["utc"] = time.strftime("%H:%M", time.gmtime(t_head - (head - z["lb"]) / bps))
    print(f"{z['lb']:>9} {z['utc']:>5} {z['qs']:>2} {str(z['frb_off']):>4} {('%.4f' % z['frb_eth']) if z['frb_eth'] else '-':>7} {str(z['via'])[:34]:<34} {z['wave20_eth']:>6.3f} {z['exit']:>4} {str(z['pull']):>5} "
          f"{z['gross']*100:>+6.2f}% {(z['ret']*100 if z['ok'] else float('nan')):>+6.2f}%")
ok = [z for z in rows if z["ok"]]
def summ(lab, zs):
    if not zs: print(f"{lab}: none"); return
    rs = [z["ret"] for z in zs]; gs = [z["gross"] for z in zs]
    print(f"{lab}: n {len(zs)} net mean {st.mean(rs)*100:+.2f}% median {st.median(rs)*100:+.2f}% win {sum(r > 0 for r in rs)}/{len(rs)} pulled<=sell {sum(1 for z in zs if z['pulled'])} "
          f"gross mean {st.mean(gs)*100:+.2f}% median {st.median(gs)*100:+.2f}%; frb by +60: {sum(1 for z in zs if z['frb_off'] is not None and z['frb_off'] <= 60)}, by +80: {sum(1 for z in zs if z['frb_off'] is not None and z['frb_off'] <= 80)}, "
          f"any frb: {sum(1 for z in zs if z['frb_off'] is not None)}; $/trade at {Q} ETH {st.mean(rs)*Q*2570 - 0.02:+.3f}")
summ("all", ok)
last3 = [z for z in ok if z["age"] <= 3 * 3600 * bps]
summ("last 3 h", last3)
summ("before the last 3 h", [z for z in ok if z["age"] > 3 * 3600 * bps])
json.dump(rows, open(os.path.splitext(sys.argv[1])[0] + ("_forward.json" if CAP == 80 and A_ENTRY == 2 and Q == 0.0058 else f"_forward_e{A_ENTRY}_c{CAP}_q{Q:g}.json"), "w"), indent=0)
fr = [z["frb_off"] for z in rows if z["frb_off"] is not None]
print("frb offsets", sorted(fr)); print("frb ETH", sorted(round(z["frb_eth"], 4) for z in rows if z["frb_eth"]))
print("pull offsets", sorted(z["pull"] for z in rows if z["pull"] is not None), "never pulled (to head)", sum(1 for z in rows if z["pull"] is None))
print("mint top tick / L variants", sorted({(z["hi"], z["L"]) for z in rows}))
