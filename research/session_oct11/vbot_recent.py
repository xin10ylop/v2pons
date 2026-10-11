"""The volume bot's 2.4333 and 3.0 lines in the last N minutes, from the chain: per pool the buys ahead of the bot (decoys/fronters), the bot's
first buy, its later buys/sells, pulls; summaries per line (public RPC, read-only)."""
import sys, time, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc, logs, batch, PM, T_INIT, T_SWAP, T_ML, W, sgn
minutes = float(sys.argv[1]) if len(sys.argv) > 1 else 120
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"; BOT = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"; DECOY = "0x65050a9b"
head = int(rpc("eth_blockNumber", []), 16); t_head = int(rpc("eth_getBlockByNumber", [hex(head), False])["timestamp"], 16)
lo = head - 1000; tb = int(rpc("eth_getBlockByNumber", [hex(lo), False])["timestamp"], 16); bps = 1000 / max(1, t_head - tb)
start = head - int(minutes * 60 * bps)
ls = []
for a in range(start, head + 1, 2000):
    ls += logs({"address": PM, "topics": [T_INIT]}, a, min(a + 1999, head))
cand = [l for l in ls if l["topics"][2][-40:] == "0" * 40]
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in cand])
lines = {2433328500000000000: "2.433", 3 * 10 ** 18: "3.0"}
pools = [(lines[int(tx["value"], 16)], l, tx) for l, tx in zip(cand, txs) if tx and (tx.get("to") or "").lower() == POSM and int(tx["value"], 16) in lines and (len(tx["input"]) - 2) // 2 == 1444]
print(f"head {head} {time.strftime('%H:%M:%S', time.gmtime(t_head))} UTC, last {minutes:g} min: " + ", ".join(f"{n} {k} launches" for k, n in collections.Counter(p[0] for p in pools).items()))
out = collections.defaultdict(list)
for line, l, tx in pools:
    pid = l["topics"][1]; L = int(l["blockNumber"], 16); to = min(L + 200, head - 5)
    if to - L < 120: continue
    sw = sorted(logs({"address": PM, "topics": [T_SWAP, pid]}, L, to), key=lambda s: (int(s["blockNumber"], 16), int(s["logIndex"], 16)))
    ml = logs({"address": PM, "topics": [T_ML, pid]}, L, to)
    stx = batch([("eth_getTransactionByHash", [s["transactionHash"]]) for s in sw[:30]])
    ev = []
    for s, t in zip(sw, stx):
        a0 = sgn(W(s["data"], 0)); bn = int(s["blockNumber"], 16) - L
        who = (t.get("to") or "")[:10].lower() if t else "?"; frm = (t.get("from") or "")[:10].lower() if t else "?"
        ev.append((bn, "buy" if a0 < 0 else "sell", abs(a0) / 1e18, "bot" if who == BOT[:10] else "decoy" if frm == DECOY else frm))
    pulls = sorted(int(m["blockNumber"], 16) - L for m in ml if sgn(W(m["data"], 2)) < 0)
    bot = [e for e in ev if e[3] == "bot" and e[1] == "buy"]
    T = bot[0][0] if bot else None
    ahead = [e for e in ev if e[1] == "buy" and e[3] != "bot" and (T is None or e[0] <= T)]
    decoy_eth = sum(e[2] for e in ahead if e[3] == "decoy"); stranger = [e for e in ahead if e[3] != "decoy"]
    bot2 = bot[1][0] if len(bot) > 1 else None; bot_sells = [e[0] for e in ev if e[3] == "bot" and e[1] == "sell"]
    out[line].append(dict(L=L, T=T, bot_eth=bot[0][2] if bot else None, n_bot=len(bot), bot2=bot2, bot_sell1=bot_sells[0] if bot_sells else None, decoy=round(decoy_eth, 5),
                          decoy_offs=[e[0] for e in ahead if e[3] == "decoy"], strangers=[(e[0], round(e[2], 5), e[3]) for e in stranger], pull=pulls[0] if pulls else None, span=to - L))
for line, rows in out.items():
    print(f"\n=== {line}: {len(rows)} pools with at least 120 blocks of history")
    print(f"{'launch':>9} {'botT':>5} {'botETH':>7} {'nbot':>4} {'bot2':>5} {'botSell':>7} {'decoyETH':>8} {'decoy@':>10} {'pull':>5}  strangers before the bot")
    for r in rows:
        print(f"{r['L']:>9} {str(r['T']):>5} {str(r['bot_eth'])[:7]:>7} {r['n_bot']:>4} {str(r['bot2']):>5} {str(r['bot_sell1']):>7} {r['decoy']:>8} {str(r['decoy_offs'])[:10]:>10} {str(r['pull']):>5}  {r['strangers'][:3]}")
    withT = [r for r in rows if r["T"] is not None]
    if withT:
        Ts = sorted(r["T"] for r in withT); dec = sorted(r["decoy"] for r in rows)
        print(f"  bot first buy offset p10/50/90: {Ts[len(Ts)//10]}/{Ts[len(Ts)//2]}/{Ts[9*len(Ts)//10]}; no bot buy: {len(rows)-len(withT)}; "
              f"decoy ETH ahead p50/p90/max: {dec[len(dec)//2]}/{dec[9*len(dec)//10]}/{dec[-1]}; pools with a stranger ahead: {sum(1 for r in rows if r['strangers'])}; "
              f"pulled within span: {sum(1 for r in rows if r['pull'] is not None)} (offsets {sorted(r['pull'] for r in rows if r['pull'] is not None)[:12]})")
        b2 = [r['bot2'] - r['T'] for r in withT if r['bot2']]; bs = [r['bot_sell1'] - r['T'] for r in withT if r['bot_sell1']]
        if b2: print(f"  the bot's second buy, blocks after its first (p50): {sorted(b2)[len(b2)//2]} (n {len(b2)}); its first sell after its first buy (p50): {sorted(bs)[len(bs)//2] if bs else None} (n {len(bs)})")
