#!/usr/bin/env python3
"""slot30.py DAY...: the 2.433 operator's 3.0 ETH line (v4 POSM 1,444 B, 3 ETH, fee 1%): does an outside buy behind its bot's first buy
(env SLOT blocks after it, 5 by default: our behind-ride's slot; MIN_OUT the least size, 0.0005) bring the pull? Its pools from the census days given; the bot = calls to 0x1cbaf24d; its fleet =
senders buying in 10%+ of the sampled pools; outsiders = everyone else (not the launch wallet). Per pool: the bot's first buy, outside buys
in the slot, the pull (ModifyLiquidity < 0) and its offset from that buy; pools with an outside slot buy against pools without. Read-only."""
import sys, os, json, collections, statistics as st
import hlib as H
from eth_utils import keccak
SLOT = int(os.environ.get("SLOT", "5")); MIN_OUT = float(os.environ.get("MIN_OUT", "0.0005"))   # the slot after the bot's buy (blocks); an outside buy's least size
url = H.CH["rh"]["rpc"]; PM = H.CH["rh"]["pm"]; BOT = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
sg = lambda h: (lambda x: x - (1 << 256) if x >= 1 << 255 else x)(int(h, 16))
lc = json.load(open("out/struct_launch_rh.json")); P = []
for d in sys.argv[1:]:
    r = json.load(open(f"out/rh_{d}_00.json"))["chains"]["rh"]
    for k, tok, bn, tx, nin in r["created"]:
        t = lc.get(tx)
        if t and k.startswith("v4:") and t[2] == "0xac9650d8" and t[3] == 1444 and abs(t[4] - 3.0) < 1e-9:
            P.append({"pid": k[3:], "bn": bn, "launcher": t[0]})
P = P[::max(1, len(P) // 400)]
print(f"{len(P)} pools of the 3.0 line sampled", flush=True)
tc = {}
for p in P:
    sw = H.rpc(url, "eth_getLogs", [{"fromBlock": hex(p["bn"]), "toBlock": hex(p["bn"] + 600), "address": PM, "topics": [H.T_SWAP4, "0x" + p["pid"][2:] if not p["pid"].startswith("0x") else p["pid"]]}]) or []
    ml = H.rpc(url, "eth_getLogs", [{"fromBlock": hex(p["bn"] + 1), "toBlock": hex(p["bn"] + 3000), "address": PM, "topics": [T_ML, p["pid"]]}]) or []
    p["pull"] = min((int(m["blockNumber"], 16) for m in ml if sg(m["data"][2 + 128:2 + 192]) < 0), default=None)
    p["sw"] = [(int(s["blockNumber"], 16), -sg(s["data"][2:66]) / 1e18, s["transactionHash"]) for s in sw]
need = sorted({h for p in P for b, e, h in p["sw"] if e > 0})
for h, x in zip(need, H.batch(url, [("eth_getTransactionByHash", [h]) for h in need], size=50, workers=4, tries=8)):
    tc[h] = (x["from"].lower(), (x.get("to") or "").lower()) if x else (None, None)
cnt = collections.Counter()
for p in P:
    for w in {tc[h][0] for b, e, h in p["sw"] if e > 0 and h in tc}:
        cnt[w] += 1
fleet = {w for w, n in cnt.items() if n >= 0.1 * len(P)}
print(f"fleet: {len(fleet)} wallets buying in 10%+ of the pools", flush=True)
rows = []
for p in P:
    bot = next((b for b, e, h in p["sw"] if e > 0 and tc.get(h, (None, None))[1] == BOT), None)
    if bot is None:
        continue
    slot = [(b, e, tc[h][0]) for b, e, h in p["sw"] if bot + 1 <= b <= bot + SLOT and e >= MIN_OUT and tc.get(h, (None,))[0] not in fleet | {p["launcher"], None} and tc[h][1] != BOT]
    rows.append({"bot": bot - p["bn"], "slot": slot, "pull_after_bot": (p["pull"] - bot) if p["pull"] else None, "pull_after_out": (p["pull"] - min(b for b, e, w in slot)) if p["pull"] and slot else None})
with_s = [r for r in rows if r["slot"]]; without = [r for r in rows if not r["slot"]]
def pulled(rs, n):
    return sum(1 for r in rs if r["pull_after_bot"] is not None and r["pull_after_bot"] <= n) / len(rs) if rs else None
print(f"pools with the bot's first buy: {len(rows)}; with an outside buy 1-{SLOT} blocks after it: {len(with_s)} (sizes {sorted(round(e, 4) for r in with_s for b, e, w in r['slot'])[:20]})")
for n in (20, 50, 100, 200):
    print(f"  pulled within {n:3d} blocks of the bot's buy: with an outside slot buy {pulled(with_s, n) if with_s else float('nan'):.0%}  without {pulled(without, n):.0%}")
pa = sorted(r["pull_after_bot"] for r in without if r["pull_after_bot"] is not None)
print(f"  without: the pull's offset from the bot's buy, median {st.median(pa) if pa else '-'} (p10 {pa[len(pa) // 10] if pa else '-'}, p90 {pa[9 * len(pa) // 10] if pa else '-'})")
for r in with_s[:15]:
    print("   slot", [(b - (r['bot']), round(e, 4), w[:10]) for b, e, w in r["slot"]][:3], "pull after the bot's buy", r["pull_after_bot"])
po = sorted(r["pull_after_out"] for r in with_s if r["pull_after_out"] is not None)
print(f"  the pull after the outsider's buy (blocks): {po[:40]}")
print("  outsiders:", collections.Counter(w for r in with_s for b, e, w in r["slot"]).most_common(8))
