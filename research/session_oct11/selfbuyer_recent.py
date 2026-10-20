"""The V3 self-buying launcher (lc:0a493d1a|13ead562, REPORT_C candidate 2): its launches in the last N hours and the size of its own first
buy per pool (public RPC, read-only). The go signal for that line is its buy back at 0.05 ETH."""
import sys
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc, logs, batch, W, sgn
from eth_utils import keccak
FACTORY = "0x1f7d7550b1b028f7571e69a784071f0205fd2efa"; POSM3 = "0x73991a25c818bf1f1128deaab1492d45638de0d3"; WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"
T_PC = "0x" + keccak(text="PoolCreated(address,address,uint24,int24,address)").hex()
T_SW3 = "0x" + keccak(text="Swap(address,address,int256,int256,uint160,uint128,int24)").hex()
hours = float(sys.argv[1]) if len(sys.argv) > 1 else 6
head = int(rpc("eth_blockNumber", []), 16); start = head - int(hours * 3600 * 9.8)
ls = []
for a in range(start, head + 1, 4000):
    ls += logs({"address": FACTORY, "topics": [T_PC]}, a, min(a + 3999, head))
txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in ls])
rows = []
for l, t in zip(ls, txs):
    if not t or (t.get("to") or "").lower() != POSM3 or t["input"][2:10] != "13ead562": continue
    pool = "0x" + l["data"][-40:]; t0 = "0x" + l["topics"][1][-40:]; t1 = "0x" + l["topics"][2][-40:]; L = int(l["blockNumber"], 16)
    wside = 0 if t0 == WETH else 1 if t1 == WETH else None
    if wside is None: continue
    sw = sorted(logs({"address": pool, "topics": [T_SW3]}, L, min(L + 150, head - 5)), key=lambda s: (int(s["blockNumber"], 16), int(s["logIndex"], 16)))
    stx = batch([("eth_getTransactionByHash", [s["transactionHash"]]) for s in sw[:6]])
    first = None
    for s, tx in zip(sw, stx):
        dq = sgn(W(s["data"], 0 if wside == 0 else 1))                                      # the pool's WETH delta: positive = a buy
        if dq > 0:
            first = (int(s["blockNumber"], 16) - L, dq / 1e18, (tx.get("to") or "")[:10] if tx else "?", bool(tx) and (tx.get("from") or "").lower() == t["from"].lower()); break
    rows.append((L, t["from"][:10], first))
print(f"head {head}: {len(rows)} launches of the 13ead562 self-buyer in the last {hours:g} h (of {len(ls)} V3 pools created)")
for L, frm, f in rows:
    print(f"  {L} launcher {frm}: first buy " + (f"+{f[0]} {f[1]:.4f} ETH via {f[2]}, by the launcher: {f[3]}" if f else "none within 150 blocks"))
sizes = sorted(f[1] for L, frm, f in rows if f and f[3])
if sizes: print(f"the launcher's own first buy: n {len(sizes)}, median {sizes[len(sizes) // 2]:.4f} ETH, at 0.045 or more: {sum(x >= 0.045 for x in sizes)}")
