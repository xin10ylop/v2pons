"""The V3 self-buyer's sell lock (docs/RELAY_V3.md section 3: 10 of its 28 own-buy tokens refused a transfer into their pool from an outside
address on Oct 12, and whether the lock is on from the launch or switched on later was not known: the public node keeps no old state).
For each self-buyer launch of the last H hours (13ead562 straight to the V3 PositionManager, a WETH pool): the launcher's own first buy, the
other swaps to +400, and an eth_call of token.transfer(pool, 0) from an outside address on Dwellir's archive node at the launch + 1, the own
buy - 1, the own buy, + 1, + 3, + 10, + 100 and now. A revert at any of them is a lock; "ok" at the own buy + 1 (when our sell would go) and
a lock later is a lock switched on after the line's window. Read-only.

Usage: python3 research/session_oct14/selfbuyer/lockcheck.py [hours, default 6]"""
import sys, os, time
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc, logs, batch, W, sgn
import dwellir as _dw
from eth_utils import keccak
FACTORY = "0x1f7d7550b1b028f7571e69a784071f0205fd2efa"; POSM3 = "0x73991a25c818bf1f1128deaab1492d45638de0d3"; WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"
OUTSIDE = "0x8f3b1c6a2d9e4f7051b6c3a8e2d4f6a1b3c5d7e9"                      # an address with no history here: an outsider
T_PC = "0x" + keccak(text="PoolCreated(address,address,uint24,int24,address)").hex()
T_SW3 = "0x" + keccak(text="Swap(address,address,int256,int256,uint160,uint128,int24)").hex()
word = lambda x: (x[2:] if isinstance(x, str) else "%x" % x).rjust(64, "0")


def lock_at(token, pool, block):
    """'ok', 'LOCK <reason>' (the call reverted) or '? <error>' (the node could not answer)"""
    r = _dw.post({"jsonrpc": "2.0", "id": 1, "method": "eth_call",
                  "params": [{"from": OUTSIDE, "to": token, "data": "0xa9059cbb" + word(pool) + word(0)}, hex(block) if isinstance(block, int) else block]})
    if r is None: return "? no answer"
    if "error" not in r: return "ok"
    e = r["error"]; msg = str(e.get("message", ""))
    if "revert" in msg.lower() or e.get("code") == 3:
        d = e.get("data") or ""
        reason = ""
        if isinstance(d, str) and d.startswith("0x08c379a0") and len(d) >= 138:
            n = int(d[74:138], 16); reason = bytes.fromhex(d[138:138 + 2 * n]).decode("utf-8", "replace")
        return "LOCK " + (reason or (d[:10] if isinstance(d, str) and d else msg[:40]))
    return "? " + msg[:60]


def main():
    if not _dw.URL: sys.exit("no Dwellir research key: the historical checks need the archive node")
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 6
    head = int(rpc("eth_blockNumber", []), 16); t_head = int(rpc("eth_getBlockByNumber", [hex(head), False])["timestamp"], 16)
    start = head - int(hours * 3600 * 10)
    ls = []
    for a in range(start, head + 1, 4000):
        ls += logs({"address": FACTORY, "topics": [T_PC]}, a, min(a + 3999, head))
    txs = batch([("eth_getTransactionByHash", [l["transactionHash"]]) for l in ls])
    print(f"head {head} ({time.strftime('%m-%d %H:%M', time.gmtime(t_head))} UTC): self-buyer launches of the last {hours:g} h, sell lock = "
          f"token.transfer(pool, 0) from an outside address (Dwellir archive eth_call)")
    n_lock = n_ok = 0
    for l, t in zip(ls, txs):
        if not t or (t.get("to") or "").lower() != POSM3 or t["input"][2:10] != "13ead562": continue
        pool = "0x" + l["data"][-40:]; t0 = "0x" + l["topics"][1][-40:]; t1 = "0x" + l["topics"][2][-40:]; L = int(l["blockNumber"], 16)
        if WETH not in (t0, t1): continue
        token = t1 if t0 == WETH else t0; wi = 0 if t0 == WETH else 1; me = t["from"].lower()
        sw = sorted(logs({"address": pool, "topics": [T_SW3]}, L, min(L + 400, head)), key=lambda s: (int(s["blockNumber"], 16), int(s["logIndex"], 16)))
        stx = batch([("eth_getTransactionByHash", [s["transactionHash"]]) for s in sw]) if sw else []
        own = None; before = []; after_buys = after_sells = 0; out_sellers = set(); buyers = set()
        for s, tx in zip(sw, stx):
            b = int(s["blockNumber"], 16); dq = sgn(W(s["data"], wi)); frm = ((tx or {}).get("from") or "").lower()
            if own is None:
                if dq > 0 and frm == me: own = (b, dq / 1e18)
                elif frm != me: before.append((b - L, round(dq / 1e18, 4)))
                continue
            if dq > 0: after_buys += 1; buyers.add(frm)
            else:
                after_sells += 1
                if frm != me: out_sellers.add(frm)
        pts = [("L+1", L + 1)]
        if own: pts += [("buy-1", own[0] - 1), ("buy", own[0]), ("buy+1", own[0] + 1), ("buy+3", own[0] + 3), ("buy+10", own[0] + 10), ("buy+100", own[0] + 100)]
        pts.append(("now", "latest"))
        res = [(k, lock_at(token, pool, b if b == "latest" or b <= head else "latest")) for k, b in pts]
        locked = any(r.startswith("LOCK") for _, r in res)
        n_lock += locked; n_ok += not locked
        print(f"  L {L} launcher {me[:10]} pool {pool[:10]} token {token[:10]}: own buy " +
              (f"+{own[0] - L} {own[1]:.4f} ETH" if own else "none by +400") +
              f"; swaps before it {before[:4]}; after it: {after_buys} buys, {after_sells} sells, {len(out_sellers)} outside sellers")
        print("      " + "  ".join(f"{k} {r}" for k, r in res) + ("   <- LOCKED" if locked else ""))
    print(f"locked {n_lock}, never locked at the checked blocks {n_ok}")


if __name__ == "__main__":
    main()
