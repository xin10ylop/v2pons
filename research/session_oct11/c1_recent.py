"""C-1's launches in the last N minutes and what its bot did in each (public RPC, read-only)."""
import sys, time, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10"); sys.path.insert(0, "/home/user/v2pons/src")
from chain import rpc, logs, batch, PM, T_INIT, T_SWAP, T_ML, W, sgn
minutes = float(sys.argv[1]) if len(sys.argv) > 1 else 120
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"; ROUTER = "0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6"
head = int(rpc("eth_blockNumber", []), 16); t_head = int(rpc("eth_getBlockByNumber", [hex(head), False])["timestamp"], 16)
lo = head - 1000; tb = int(rpc("eth_getBlockByNumber", [hex(lo), False])["timestamp"], 16); bps = 1000 / max(1, t_head - tb)
start = head - int(minutes * 60 * bps)
ls = []
for a in range(start, head + 1, 2000):
    ls += logs({"address": PM, "topics": [T_INIT]}, a, min(a + 1999, head))
cand = [l for l in ls if W(l["data"], 0) == 100 and W(l["data"], 1) == 1 and l["topics"][2][-40:] == "0" * 40]
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in cand])
c1 = [(l, tx) for l, tx in zip(cand, txs) if tx and (tx.get("to") or "").lower() == POSM and (len(tx["input"]) - 2) // 2 == 2276 and int(tx["value"], 16) == 0]
print(f"head {head} {time.strftime('%H:%M:%S', time.gmtime(t_head))} UTC; {len(c1)} C-1 launches in the last {minutes:g} min (of {len(cand)} fee-100/ts-1 ETH pools)")
rows = []
for l, tx in c1:
    pid = l["topics"][1]; L = int(l["blockNumber"], 16); to = min(L + 400, head - 5)
    sw = logs({"address": PM, "topics": [T_SWAP, pid]}, L, to); ml = logs({"address": PM, "topics": [T_ML, pid]}, L, to)
    stx = batch([("eth_getTransactionByHash", [s["transactionHash"]]) for s in sw[:40]])
    bot_buys = []; others = []
    for s, t in zip(sw, stx):
        a0 = sgn(W(s["data"], 0)); bn = int(s["blockNumber"], 16) - L
        if a0 >= 0: continue
        via = (t.get("to") or "").lower() if t else ""
        (bot_buys if via == ROUTER else others).append((bn, -a0 / 1e18))
    pulls = sorted(int(m["blockNumber"], 16) - L for m in ml if sgn(W(m["data"], 2)) < 0)
    T = bot_buys[0][0] if bot_buys else None
    by60 = sum(e for b, e in bot_buys if T is not None and b <= T + 60)
    age = head - L
    rows.append((L, age, T, bot_buys[0][1] if bot_buys else None, len(bot_buys), round(by60, 3), pulls[0] if pulls else None, len(others), round(sum(e for _, e in others), 4)))
print(f"{'launch':>9} {'age':>5} {'botT':>5} {'first':>7} {'nbot':>4} {'ETH by T+60':>11} {'pull':>5} {'others':>6} {'othETH':>7}")
for r in rows:
    print(f"{r[0]:>9} {r[1]:>5} {str(r[2]):>5} {str(r[3])[:7]:>7} {r[4]:>4} {r[5]:>11} {str(r[6]):>5} {r[7]:>6} {r[8]:>7}")
done = [r for r in rows if r[1] > 400]
print(f"\nlaunches older than 400 blocks: {len(done)}; with a bot buy: {sum(1 for r in done if r[2] is not None)}; median ETH by T+60 among those: "
      f"{sorted(r[5] for r in done if r[2] is not None)[len([r for r in done if r[2] is not None]) // 2] if any(r[2] is not None for r in done) else None}")

# a quick forward test of the rule on these pools: enter at the state after the bot's first buy (our buy lands T + 2; the price copy after T),
# exit at the last swap at or before T + 62; the token's ETH price is (2^96 / sqrtP)^2, so our gross return is (sqrtP_entry / sqrtP_exit)^2 - 1
print("\nforward test (gross, before ~0.3% of fees and our own impact): return from the price after the bot's first buy to the last swap <= T+62")
rets = []
for l, tx in c1:
    pid = l["topics"][1]; L = int(l["blockNumber"], 16); to = min(L + 400, head - 5)
    sw = logs({"address": PM, "topics": [T_SWAP, pid]}, L, to)
    sw = sorted(sw, key=lambda s: (int(s["blockNumber"], 16), int(s["logIndex"], 16)))
    stx = batch([("eth_getTransactionByHash", [s["transactionHash"]]) for s in sw[:40]])
    T = None
    for s, t in zip(sw, stx):
        if t and (t.get("to") or "").lower() == ROUTER and sgn(W(s["data"], 0)) < 0:
            T = int(s["blockNumber"], 16) - L; sp_entry = W(s["data"], 2); break
    if T is None:
        print(f"  {L}: no bot buy"); continue
    ml = logs({"address": PM, "topics": [T_ML, pid]}, L, to); pulls = sorted(int(m["blockNumber"], 16) - L for m in ml if sgn(W(m["data"], 2)) < 0)
    if pulls and pulls[0] <= T + 62:
        rets.append(-1.0); print(f"  {L}: T +{T}, PULLED at +{pulls[0]} before the sell: -100%"); continue
    inwin = [s for s in sw if int(s["blockNumber"], 16) - L <= T + 62]
    sp_exit = W(inwin[-1]["data"], 2) if inwin else sp_entry
    r = (sp_entry / sp_exit) ** 2 - 1; rets.append(r)
    print(f"  {L}: T +{T}, {len(inwin) - 1} swaps in the hold, gross {r:+.1%}")
if rets:
    rs = sorted(rets); print(f"\n{len(rets)} pools: mean {sum(rets) / len(rets):+.1%}, median {rs[len(rs) // 2]:+.1%}, win {sum(r > 0.003 for r in rets)}/{len(rets)}, worst {rs[0]:+.1%}")
