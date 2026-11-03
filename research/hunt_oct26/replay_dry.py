#!/usr/bin/env python3
"""replay_dry.py SINCE_UNIX [UNTIL_UNIX]: the box's two dry lines replayed on the chain's recorded prices (every swap, the crowd's sells
included, which the engine's price copy leaves out), with the engine's rules, for every pool launched in the window:

  c1      v4 PositionManager multicall of 2,276 B, value 0, native ETH, fee 100, tick spacing 1, no hook; the trigger = the first buy of
          0.005+ ETH through C-1's router within 600 blocks of the launch; our buy at the head of trigger + 2; the sell when the feed shows
          50 blocks with no router buy (the trigger counts), at the latest our buy + 200 (quiet_blocks 50, hold_blocks 200)
  v3wave  V3 PositionManager 0x73991a25 multicall of 836 B, value 0, WETH as token0; the trigger = the first buy of 0.001+ ETH through
          one of its 4 routers within 600 blocks; our buy at trigger + 2; the sell at the first block whose price pays +9% after gas
          (take_profit 0.09), at the latest our buy + 100

A pull (v4 ModifyLiquidity below 0; V3 Burn above 0) at or before the sell is -100%. STAKE (env, 0.002 ETH, the box's dry stake), our
buy kept in the pool until we sell. The engine holds one position at a time, so it trades a subset of these. Read-only, public RPC."""
import os, sys, time, json, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../src"))
import hlib as H, v4math
from eth_utils import keccak

SINCE = int(sys.argv[1]); UNTIL = int(sys.argv[2]) if len(sys.argv) > 2 else None
STAKE = int(float(os.environ.get("STAKE", "0.002")) * 1e18); GAS = int(0.000006e18)
url = H.CH["rh"]["rpc"]; PM = H.CH["rh"]["pm"]
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"; V3PM = "0x73991a25c818bf1f1128deaab1492d45638de0d3"; V3F = "0x1f7d7550b1b028f7571e69a784071f0205fd2efa"
C1R = {"0xd6d35b56237a05afd4cd7e441226fefc3f78c4e6"}
V3R = {"0x7feb3ecbacbd0cc23ec46659d541636d58749a97", "0x80e49ed118b932d9538ec817ef8b29fbac31e080", "0xaf9d6fa019328d8cf8598d0d5be22cc6622b09f1", "0xfc7241d4356564e32b16e8e4838c648efceb8144"}
WETH = "0x0bd7d308f8e1639fab988df18a8011f41eacad73"
T = lambda s: "0x" + keccak(text=s).hex()
T_INIT4 = T("Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)"); T_SWAP4 = T("Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)")
T_ML = T("ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)"); T_PC = T("PoolCreated(address,address,uint24,int24,address)")
T_SW3 = T("Swap(address,address,int256,int256,uint160,uint128,int24)"); T_BURN3 = T("Burn(address,int24,int24,uint128,uint256,uint256)")
sg = lambda h: (lambda x: x - (1 << 256) if x >= 1 << 255 else x)(int(h, 16))


def block_at(ts, head, head_ts):
    """the first block at or after unix time ts (10 blocks a second, then corrected on the chain)"""
    b = max(1, head - int((head_ts - ts) * 10))
    for _ in range(6):
        bt = int(H.rpc(url, "eth_getBlockByNumber", [hex(b), False])["timestamp"], 16)
        if abs(bt - ts) <= 1:
            break
        b += int((ts - bt) * 10)
    return b


def logs(lo, hi, topics, address):
    out = []
    for a in range(lo, hi + 1, 20000):
        out += H.rpc(url, "eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(min(hi, a + 19999)), "address": address, "topics": topics}]) or []
    return out


def ride(ev, routers, trig_min, fee, pull, rule, head):
    """ev: [(block, eth_in (+ buy), sqrtP after, L after, tx to)]; returns (trigger offset, held, why, ret) or None (no trigger)"""
    trig = next((e[0] for e in ev if e[4] in routers and e[1] >= trig_min), None)
    if trig is None:
        return None
    entry = trig + 2; rb = sorted({e[0] for e in ev if e[4] in routers and e[1] > 0})
    pre = [e for e in ev if e[0] < entry]
    sp, L = pre[-1][2], pre[-1][3]
    q = v4math.buy_out_int(sp, L, STAKE, fee)

    def ret(b):
        if pull is not None and pull <= b:
            return -1.0
        post = [e for e in ev if e[0] <= b]
        sp2 = int(v4math.sqrt_after_buy(post[-1][2] if post[-1][0] >= entry else sp, L, STAKE * (10 ** 6 - fee) // 10 ** 6))
        return (v4math.sell_out_int(sp2, L, q, fee) - STAKE - GAS) / STAKE
    kind, a, cap = rule
    if entry + cap > head:
        return "open"
    last = trig; swap_blocks = {e[0] for e in ev}
    for b in range(entry, entry + cap + 1):
        last = max([x for x in rb if x <= b] or [last])
        if pull is not None and pull <= b:
            return trig, b - entry, "pull", -1.0
        if kind == "quiet" and b - last >= a:
            return trig, b - entry, "quiet", ret(b + 1)                 # sent at the end of b, lands in b + 1
        if kind == "tp" and b in swap_blocks and ret(b) >= a:
            return trig, b - entry, "take profit", ret(b + 1)
    return trig, cap, "cap", ret(entry + cap + 1)


def main():
    head = int(H.rpc(url, "eth_blockNumber", []), 16); head_ts = int(H.rpc(url, "eth_getBlockByNumber", [hex(head), False])["timestamp"], 16)
    lo = block_at(SINCE, head, head_ts); hi = block_at(UNTIL, head, head_ts) if UNTIL else head
    print(f"window: blocks {lo}..{hi} ({time.strftime('%m-%d %H:%M', time.gmtime(SINCE))} - {time.strftime('%m-%d %H:%M', time.gmtime(UNTIL or head_ts))} UTC), stake {STAKE / 1e18:g} ETH", flush=True)
    res = {"c1": [], "v3wave": []}
    # C-1
    il = [l for l in logs(lo, hi, [T_INIT4], PM) if l["topics"][2] == "0x" + "0" * 64]
    tx = H.batch(url, [("eth_getTransactionByHash", [l["transactionHash"]]) for l in il], size=50, workers=4, tries=8)
    for l, t in zip(il, tx):
        d = l["data"][2:]
        if not (t and (t.get("to") or "").lower() == POSM and (len(t["input"]) - 2) // 2 == 2276 and int(t["value"], 16) == 0
                and int(d[0:64], 16) == 100 and int(d[64:128], 16) == 1 and int(d[128:192], 16) == 0):
            continue
        pid = l["topics"][1]; bn = int(l["blockNumber"], 16); top = min(head, bn + 900)
        sw = logs(bn, top, [T_SWAP4, pid], PM); ml = logs(bn + 1, top, [T_ML, pid], PM)
        pull = min((int(m["blockNumber"], 16) for m in ml if sg(m["data"][2 + 128:2 + 192]) < 0), default=None)
        st_ = H.batch(url, [("eth_getTransactionByHash", [s["transactionHash"]]) for s in sw], size=50, workers=4, tries=8) if sw else []
        ev = [(int(s["blockNumber"], 16), -sg(s["data"][2:66]), int(s["data"][2:][128:192], 16), int(s["data"][2:][192:256], 16), (x.get("to") or "").lower() if x else "")
              for s, x in zip(sw, st_) if int(s["blockNumber"], 16) <= bn + 900]
        r = ride(ev, C1R, int(0.005e18), 100, pull, ("quiet", 50, 200), head)
        if r and r != "open" and r[0] - bn <= 600:
            res["c1"].append((bn, *r))
    # the V3 crowd
    pc = logs(lo, hi, [T_PC], V3F)
    tx = H.batch(url, [("eth_getTransactionByHash", [l["transactionHash"]]) for l in pc], size=50, workers=4, tries=8)
    for l, t in zip(pc, tx):
        if not (t and (t.get("to") or "").lower() == V3PM and (len(t["input"]) - 2) // 2 == 836 and int(t["value"], 16) == 0
                and "0x" + l["topics"][1][26:] == WETH):
            continue
        pool = "0x" + l["data"][2:][64 + 24:128]; bn = int(l["blockNumber"], 16); top = min(head, bn + 800)
        sw = logs(bn, top, [T_SW3], pool); bu = logs(bn + 1, top, [T_BURN3], pool)
        pull = min((int(b["blockNumber"], 16) for b in bu if int(b["data"][2:66], 16) > 0), default=None)
        st_ = H.batch(url, [("eth_getTransactionByHash", [s["transactionHash"]]) for s in sw], size=50, workers=4, tries=8) if sw else []
        ev = [(int(s["blockNumber"], 16), sg(s["data"][2:66]), int(s["data"][2:][128:192], 16), int(s["data"][2:][192:256], 16), (x.get("to") or "").lower() if x else "")
              for s, x in zip(sw, st_)]
        r = ride(ev, V3R, int(0.001e18), 100, pull, ("tp", 0.09, 100), head)
        if r and r != "open" and r[0] - bn <= 600:
            res["v3wave"].append((bn, *r))
    for fam, rows in res.items():
        rs = [r[4] for r in rows]
        print(f"\n== {fam}: {len(rows)} triggered pools on the chain" + (f", mean {st.mean(rs):+.1%}, median {st.median(rs):+.1%}, won {sum(x > 0 for x in rs)}/{len(rs)}, pulled {sum(x <= -1 for x in rs)}" if rs else ""))
        for bn, trig, held, why, r in rows:
            print(f"   launch {time.strftime('%H:%M', time.gmtime(head_ts - (head - bn) / 10))} UTC  trigger +{trig - bn:3d}  held {held:3d} blocks  {why:11s} {r:+.1%}")
    json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "replay_dry.json"), "w"))


if __name__ == "__main__":
    main()
