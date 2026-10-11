"""For a launch shape seen in recent_launches (launcher address suffix, calldata length): the last N pools' swaps in 300 blocks (public RPC)."""
import sys, time, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc, logs, batch, PM, T_INIT, T_SWAP, T_ML, W, sgn
suffix, clen, n = sys.argv[1].lower(), int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 3
minutes = float(sys.argv[4]) if len(sys.argv) > 4 else 180
head = int(rpc("eth_blockNumber", []), 16); start = head - int(minutes * 60 * 9.7)
ls = []
for a in range(start, head + 1, 4000):
    ls += logs({"address": PM, "topics": [T_INIT]}, a, min(a + 3999, head))
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in ls])
pools = [(l, t) for l, t in zip(ls, txs) if t and (t.get("to") or "create").lower().endswith(suffix) and (len(t["input"]) - 2) // 2 == clen]
pools = [p for p in pools if int(p[0]["blockNumber"], 16) < head - 300][-n:]
print(f"shape to..{suffix} len {clen}: {len(pools)} pools shown (launched {minutes:g} min window)")
for l, t in pools:
    pid = l["topics"][1]; L = int(l["blockNumber"], 16); c0 = l["topics"][2][-40:]; c1 = l["topics"][3][-40:]
    quote_is0 = c0 == "0" * 40 or c0.startswith("5fc5") or c0.startswith("0bd7") or c0.startswith("4a0e")
    sw = sorted(logs({"address": PM, "topics": [T_SWAP, pid]}, L, min(L + 300, head)), key=lambda s: (int(s["blockNumber"], 16), int(s["logIndex"], 16)))
    ml = logs({"address": PM, "topics": [T_ML, pid]}, L, min(L + 300, head))
    stx = batch([("eth_getTransactionByHash", [s["transactionHash"]]) for s in sw[:12]])
    print(f"\n launch {L} from {t['from'][:10]} quote {'ETH' if c0 == '0' * 40 else c0[:8]} fee {W(l['data'], 0)} ts {sgn(W(l['data'], 1))} hook {'yes' if int(l['data'][130:194], 16) else 'no'}: {len(sw)} swaps, pulls at {[int(m['blockNumber'], 16) - L for m in ml if sgn(W(m['data'], 2)) < 0][:4]}")
    for s, x in zip(sw[:12], stx):
        amt = sgn(W(s["data"], 0 if quote_is0 else 1)); who = (x.get("to") or "")[:10] if x else "?"; frm = (x.get("from") or "")[:10] if x else "?"
        print(f"   +{int(s['blockNumber'], 16) - L:<4} {'buy ' if amt < 0 else 'sell'} {abs(amt) / 1e18 if c0 == '0' * 40 or c0.startswith('0bd7') else abs(amt) / 1e6:10.4f} via {who} from {frm}{'  (launcher)' if frm == t['from'][:10] else ''}")
