"""Step 16: the two pools the 3-hour watch counted as the same shape with 600+ swaps (launch blocks 88022489 and 88027196): their
Initialize (currencies, fee, hook), launcher, liquidity, and who swaps (routers, wallets) to +600."""
import collections
from common import *
out = []
for L in (88022489, 88027196):
    ls = rpc.logs({"address": PM, "topics": [T_INIT]}, L, L)
    for l in ls:
        t = rpc.call("eth_getTransactionByHash", [l["transactionHash"]])
        if (t.get("to") or "").lower() != PM: continue
        d = l["data"]; c0 = "0x" + l["topics"][2][-40:]; c1 = "0x" + l["topics"][3][-40:]
        pid = l["topics"][1]
        info = dict(L=L, pid=pid, c0=c0, c1=c1, fee=W(d, 0), ts=sgn(W(d, 1)), hook="0x" + d[2 + 128 + 24: 2 + 192], launcher=t["from"].lower(),
                    nonce=int(t["nonce"], 16), inlen=(len(t["input"]) - 2) // 2)
        print(info)
        names = []
        for c in (c0, c1):
            r = rpc.batch("eth_call", [[{"to": c, "data": "0x06fdde03"}, "latest"], [{"to": c, "data": "0x95d89b41"}, "latest"], [{"to": c, "data": "0x313ce567"}, "latest"]], n=3)
            def dstr(x):
                try:
                    b = bytes.fromhex(x[2:]); off = int.from_bytes(b[:32], "big"); ln = int.from_bytes(b[off:off+32], "big"); return b[off+32:off+32+ln].decode(errors="replace")
                except Exception: return None
            names.append((c, dstr(r[0]), dstr(r[1]), int(r[2], 16) if r[2] and r[2] != "0x" else None))
        print("  currencies:", names)
        ev = rpc.logs({"address": PM, "topics": [[T_SWAP, T_ML], [pid]]}, L, L + 600)
        ml = [e for e in ev if e["topics"][0] == T_ML]; sw = [e for e in ev if e["topics"][0] == T_SWAP]
        for e in ml:
            m = ml_fields(e); tt = rpc.call("eth_getTransactionByHash", [e["transactionHash"]])
            print(f"  ML +{int(e['blockNumber'],16)-L} {m['tl']}..{m['tu']} {m['dl']:.4e} from {tt['from'][:12]} to {tt['to'][:12]} value {int(tt['value'],16)/1e18:.4f} sel {tt['input'][:10]}")
        txs = rpc.batch("eth_getTransactionByHash", [[e["transactionHash"]] for e in sw], n=25)
        c = collections.Counter(); first = None; amt0_in = 0; nb = ns = 0
        for e, tt in zip(sw, txs):
            s = swap_fields(e); c[(tt["to"][:12], tt["input"][:10])] += 1
            if s["a0"] < 0: amt0_in += -s["a0"]; nb += 1
            else: ns += 1
            if first is None: first = (int(e["blockNumber"], 16) - L, tt["from"], tt["to"], -s["a0"] / 1e18)
        wallets = collections.Counter(tt["from"] for tt in txs)
        print(f"  swaps to +600 {len(sw)} (buys {nb}, sells {ns}), currency0 in {amt0_in/1e18:.3f}, first swap {first}")
        print("  routers:", c.most_common(6))
        print("  distinct wallets", len(wallets), "top", [(w[:10], n) for w, n in wallets.most_common(6)])
        out.append(dict(info=info, names=names, n_swaps=len(sw), routers=[[k[0], k[1], n] for k, n in c.most_common(10)], wallets=len(wallets), first=first))
jdump(out, "s16_big.json")
print(rpc.STATS)
