#!/usr/bin/env python3
"""v3burn.py HOURS: can the V3 crowd's operator take a holder's tokens, as C-1's can? For every V3 crowd token (the 836 B launches through
the V3 PositionManager 0x73991a25) of the last HOURS hours: its transfers to 0xdead / 0x0 and the Approvals that a third party's
transaction made on a holder's behalf (C-1's pattern: Approval(holder, its router) in a transaction the holder did not send), counted per
token in small queries. Read-only, public RPC."""
import sys, collections
import hlib as H
from eth_utils import keccak
HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 48
url = H.CH["rh"]["rpc"]
T_TR = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"; T_AP = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925"
DEAD = "0x" + "0" * 24 + "000000000000000000000000000000000000dead"; ZERO = "0x" + "0" * 64
T_PC = "0x" + keccak(text="PoolCreated(address,address,uint24,int24,address)").hex()
V3R = {"0x7feb3ecbacbd0cc23ec46659d541636d58749a97", "0x80e49ed118b932d9538ec817ef8b29fbac31e080", "0xaf9d6fa019328d8cf8598d0d5be22cc6622b09f1", "0xfc7241d4356564e32b16e8e4838c648efceb8144"}
PUBLIC = {"0x8876789976decbfcbbbe364623c63652db8c0904", "0xcaf681a66d020601342297493863e78c959e5cb2", "0x000000000022d473030f116ddee9f6b43ac78ba3"}   # UR, SwapRouter02, Permit2
head = int(H.rpc(url, "eth_blockNumber", []), 16); lo = head - int(HOURS * 36000)
pc = []
for a in range(lo, head + 1, 20000):
    pc += H.rpc(url, "eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(min(head, a + 19999)), "address": "0x1f7d7550b1b028f7571e69a784071f0205fd2efa", "topics": [T_PC]}]) or []
tx = H.batch(url, [("eth_getTransactionByHash", [l["transactionHash"]]) for l in pc], size=50, workers=4, tries=8)
WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"
toks = [(next(x for x in ("0x" + l["topics"][1][26:], "0x" + l["topics"][2][26:]) if x != WETH), int(l["blockNumber"], 16), "0x" + l["data"][2:][64 + 24:128]) for l, t in zip(pc, tx)
        if t and (t.get("to") or "").lower() == "0x73991a25c818bf1f1128deaab1492d45638de0d3" and (len(t["input"]) - 2) // 2 == 836]   # the token, never WETH
print(f"V3 crowd tokens, last {HOURS:g} h: {len(toks)}", flush=True)
tot = collections.Counter(); third_ap = []; heavy = []; burn_logs = []
for tok, bn, pool in toks:
    hi = min(head, bn + 30000); n_burn = 0; aps = []
    for a in range(bn, hi + 1, 5000):
        b = min(hi, a + 4999)
        bl = H.rpc(url, "eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(b), "address": tok, "topics": [T_TR, None, [DEAD, ZERO]]}]) or []
        n_burn += len(bl); burn_logs.extend((tok, pool, x) for x in bl)
        aps += [x for x in (H.rpc(url, "eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(b), "address": tok, "topics": [T_AP]}]) or [])
                if "0x" + x["topics"][2][26:] not in PUBLIC and "0x" + x["topics"][1][26:] != pool]
    tot["burn logs"] += n_burn
    if n_burn > 50:
        heavy.append((tok, n_burn))
    if aps:
        ts = H.batch(url, [("eth_getTransactionByHash", [x["transactionHash"]]) for x in aps], size=50, workers=4)
        for x, t in zip(aps, ts):
            if t and t["from"].lower() != "0x" + x["topics"][1][26:]:
                third_ap.append((tok, "0x" + x["topics"][1][26:], "0x" + x["topics"][2][26:], (t.get("to") or "").lower(), t["from"].lower()))
print(dict(tot), "| tokens with 50+ transfers to 0xdead/0x0:", len(heavy), heavy[:5])
print(f"Approvals made for a holder by someone else's transaction: {len(third_ap)} in {len({x[0] for x in third_ap})} tokens")
for x in third_ap[:8]:
    print("   token", x[0][:10], "holder", x[1][:10], "spender", x[2][:10], "tx to", x[3][:10], ("(a crowd router)" if x[3] in V3R else ""), "from", x[4][:10])

EP = "0x0000000071727de22e5e9d8baf0edac6f37da032"; EP6 = "0x5ff137d4b0fdcd49dca30c7cf57e578a026d2789"
bts = H.batch(url, [("eth_getTransactionByHash", [x["transactionHash"]]) for _, _, x in burn_logs], size=50, workers=4, tries=8) if burn_logs else []
taken = [(tok, "0x" + x["topics"][1][26:], (t.get("to") or "").lower(), t["from"].lower()) for (tok, pool, x), t in zip(burn_logs, bts)
         if t and t["from"].lower() != "0x" + x["topics"][1][26:] and "0x" + x["topics"][1][26:] not in (pool, "0x" + "0" * 40) and (t.get("to") or "").lower() not in (EP, EP6)]
print(f"\nTHE C-1 PATTERN (a holder's tokens to 0xdead/0x0 by someone else's transaction, ERC-4337 apart): {len(taken)} in {len({x[0] for x in taken})} of {len(toks)} tokens")
print("   by the transaction's target:", collections.Counter(x[2][:10] for x in taken).most_common(6), "| holders:", collections.Counter(x[1][:10] for x in taken).most_common(6))
