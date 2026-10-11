"""Synthesizer step 3: the V3 crowd line after the census (the repo's read-only forward-test captures: the 3 h to 19:10 UTC from git commit
c97463f, and the 3 h to 21:52 UTC at HEAD; copied here as fwd_1910utc.json / fwd_2152utc.json). For every launch: the first real buy
(>= 0.005 ETH) offset, the first pull, and the fixed rules K20 -> +80 and +2 -> +80 replayed with analyst C's V3 replay (imported read-only
from the repo, as analysis/W/w07_forward.py does), net of $0.02 gas. Compared with the census rate of a first real buy by +80 (s02).
-> s03_forward.out"""
import sys, os, json, time, statistics as S
from math import comb
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/W"); sys.path.insert(0, "/home/user/v2pons/research/session_oct11/lines/analysis/C")
from replay import replay
from v3dec import decode_launch_v3
from eth_utils import keccak
tp = lambda s: "0x" + keccak(text=s).hex()
T_SW = tp("Swap(address,address,int256,int256,uint160,uint128,int24)"); T_MI = tp("Mint(address,address,int24,int24,uint128,uint256,uint256)")
T_BU = tp("Burn(address,int24,int24,uint128,uint256,uint256)")
def Sg(x): x = int(x, 16); return x - (1 << 256) if x >> 255 else x
def W(d, i): return d[2 + 64 * i: 2 + 64 * (i + 1)]
def compact(l):    # same layout as w07_forward.py
    t = l["topics"]; d = l["data"]; bn = int(l["blockNumber"], 16); ti = int(l["transactionIndex"], 16); li = int(l["logIndex"], 16); tx = l["transactionHash"]; a = l["address"].lower()
    if t[0] == T_SW: return ["s", bn, ti, li, a, "0x" + t[1][-40:], "0x" + t[2][-40:], Sg(W(d, 0)), Sg(W(d, 1)), int(W(d, 2), 16), int(W(d, 3), 16), Sg(W(d, 4)), tx]
    if t[0] == T_MI: return ["mi", bn, ti, li, a, "0x" + t[1][-40:], Sg(t[2]), Sg(t[3]), int(W(d, 1), 16), int(W(d, 2), 16), int(W(d, 3), 16), tx]
    if t[0] == T_BU: return ["b", bn, ti, li, a, "0x" + t[1][-40:], Sg(t[2]), Sg(t[3]), int(W(d, 0), 16), int(W(d, 1), 16), int(W(d, 2), 16), tx]
Q = 0.0058; G = 0.02 / 2570 / Q
L = []; allz = []
def P(s=""): L.append(s); print(s)
for f in ("fwd_1910utc.json", "fwd_2152utc.json"):
    D = json.load(open(os.path.join(HERE, f))); head = D["head"]; bps = D["bps"]; th = D["t_head"]
    P(f"{f}: {len(D['line'])} crowd-line launches in the {D['hours']:g} h to {time.strftime('%H:%M', time.gmtime(th))} UTC (head {head})")
    for x in D["line"]:
        d = decode_launch_v3(bytes.fromhex(x["tx"]["input"][2:])); qs = d["qs"]; lb = x["lb"]
        ev = [c for c in (compact(l) for l in x["logs"]) if c]
        o = {"lb": lb, "ev": ev, "ev_to": head - 3}; row = {"dex": "v3", "quote_side": qs, "fee": d["fee"]}
        buys = [(e[1] - lb, (e[7] if qs == 0 else e[8])) for e in ev if e[0] == "s" and (e[7] if qs == 0 else e[8]) > 0]
        real = [b for b in buys if b[1] >= 5 * 10 ** 15]; frb = real[0] if real else None
        pulls = [e[1] - lb for e in ev if e[0] == "b" and e[8] > 0]
        z = {"utc": time.strftime("%H:%M", time.gmtime(th - (head - lb) / bps)), "frb": frb[0] if frb else None, "frb_eth": frb[1] / 1e18 if frb else None,
             "pull": min(pulls) if pulls else None, "real_by80": sum(1 for b in real if b[0] < 80)}
        for lab, a in (("k20", 20), ("k2", 2)):
            r = replay(row, o, a, 80, Q)
            z[lab] = None if not r["ok"] else ((-1.0 - G) if r["pulled"] else r["ret_nopull"] - G)
        allz.append(z)
        P(f"   {z['utc']} frb {str(z['frb']):>4} ({z['frb_eth'] or 0:.4f} ETH) real buys before +80 {z['real_by80']} first pull {str(z['pull']):>5} | K20/+80 "
          f"{'n/a' if z['k20'] is None else '%+.3f%%' % (z['k20']*100)} | +2/+80 {'n/a' if z['k2'] is None else '%+.3f%%' % (z['k2']*100)}")
P()
n = len(allz); by80 = sum(1 for z in allz if z["frb"] is not None and z["frb"] <= 80)
k20 = [z["k20"] for z in allz if z["k20"] is not None]; k2 = [z["k2"] for z in allz if z["k2"] is not None]
P(f"post-census: {n} launches; first real buy by +80 in {by80} ({by80/n*100:.0f}%); frb offsets {sorted(z['frb'] for z in allz if z['frb'] is not None)}")
P(f"   pulls at or before +80: {sum(1 for z in allz if z['pull'] is not None and z['pull'] <= 80)}; first pulls {sorted(z['pull'] for z in allz if z['pull'] is not None)}; never pulled to head {sum(1 for z in allz if z['pull'] is None)}")
P(f"   K20/+80 at $15 net: n {len(k20)} mean {S.mean(k20)*100:+.3f}% median {S.median(k20)*100:+.3f}% win {sum(1 for a in k20 if a > 0)}/{len(k20)} ${S.mean(k20)*Q*2570:+.3f}/trade")
P(f"   +2/+80  at $15 net: n {len(k2)} mean {S.mean(k2)*100:+.3f}% median {S.median(k2)*100:+.3f}% win {sum(1 for a in k2 if a > 0)}/{len(k2)} ${S.mean(k2)*Q*2570:+.3f}/trade")
s2 = json.load(open(os.path.join(HERE, "s02_lines.json")))
bd = s2["crowd_frb80_census"]["by_day"]; rates = {d: v[0] / v[1] for d, v in bd.items()}; pall = s2["crowd_frb80_census"]["all"][0] / s2["crowd_frb80_census"]["all"][1]
for lab, p in (("census all days", pall), ("census lowest day", min(rates.values()))):
    pr = sum(comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(by80 + 1))
    P(f"   P(<= {by80} of {n} with a first real buy by +80 | rate {p*100:.1f}%, {lab}) = {pr:.2e}")
open(os.path.join(HERE, "s03_forward.out"), "w").write("\n".join(L) + "\n")
