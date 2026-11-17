#!/usr/bin/env python3
"""watchfee0.py [MINUTES]: a live DRY-RUN watcher for the operator's fee-0, no-hook pools (the lead in REPORT_NOV16B). No trades, ever.

Every ~15 s it reads new Robinhood blocks, finds each new v4 pool with fee 0 and no hook (Initialize), and follows it: when the operator's
demand first buys (a swap whose native goes IN, i.e. a buy, of >= TRIG_ETH, through the decoy router 0x65050a9b, the Universal Router, or any
sender), it records a paper entry of STAKE at the next block's price, then watches for the exit -- the first block whose price pays >= TP after
gas (sell into the pump), at the latest HOLD blocks after entry, or -100% if the liquidity is pulled first. It logs, per pool: launch block,
launcher, token, the demand that arrived, the entry and exit offsets, and the paper return. Reserves come from each Swap's own sqrtP/liquidity;
our stake is kept in the pool until the sell. Read-only (public RPC); writes watchfee0.log. This measures the ride live and grows the sample;
it does not and cannot place an order."""
import os, sys, time, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../src"))
import hlib as H, v4math
from eth_utils import keccak

MINUTES = float(sys.argv[1]) if len(sys.argv) > 1 else 180
STAKE = int(float(os.environ.get("STAKE", "0.005")) * 1e18); GAS = int(0.000006e18)
TP = float(os.environ.get("TP", "0.08")); HOLD = int(os.environ.get("HOLD", "2000")); TRIG_ETH = float(os.environ.get("TRIG_ETH", "0.02"))
WIN = int(os.environ.get("WIN", "6000"))                              # blocks to follow each pool
LAG = int(os.environ.get("LAG", "0")); ENTRY_LAG = int(os.environ.get("ENTRY_LAG", "0"))                                 # blocks between seeing the take-profit and our sell landing (0 = the same block, optimistic)
url = H.CH["rh"]["rpc"]; PM = H.CH["rh"]["pm"]
DECOY = "0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc"; UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
T = lambda s: "0x" + keccak(text=s).hex()
T_INIT4 = T("Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)")
T_SWAP4 = T("Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)")
T_ML = T("ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)")
sg = lambda h: (lambda x: x - (1 << 256) if x >= 1 << 255 else x)(int(h, 16))
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchfee0.log")


def say(m):
    line = f"{time.strftime('%m-%d %H:%M:%S', time.gmtime())} {m}"
    print(line, flush=True)
    open(LOG, "a").write(line + "\n")


def getlogs(lo, hi, topics, address=None):
    out = []
    for a in range(lo, hi + 1, 30000):
        q = {"fromBlock": hex(a), "toBlock": hex(min(hi, a + 29999)), "topics": topics}
        if address:
            q["address"] = address
        out += H.rpc(url, "eth_getLogs", [q]) or []
    return out


def ride(pid, bn, fee=0):
    """paper ride on one fee-0 pool from its launch block bn; returns a result dict or None if the demand never came"""
    hi = bn + WIN
    sw = getlogs(bn, hi, [T_SWAP4, pid], PM); ml = getlogs(bn + 1, hi, [T_ML, pid], PM)
    pull = min((int(m["blockNumber"], 16) for m in ml if sg(m["data"][2 + 128:2 + 192]) < 0), default=None)
    ev = []
    for s in sw:
        d = s["data"][2:]; a0 = sg(d[0:64]); sp = int(d[128:192], 16); L = int(d[192:256], 16)
        ev.append((int(s["blockNumber"], 16), int(s["logIndex"], 16), -a0, sp, L, "0x" + s["topics"][2][26:]))
    ev.sort()
    # the demand: first buy (native in, a0<0 -> -a0>0) of >= TRIG_ETH
    # never inside the launch block: a launcher's own buys there are part of its launch transaction (atomic, nobody can enter between them)
    trig = next((e for e in ev if e[0] > bn and e[2] >= TRIG_ETH * 1e18), None)
    if not trig:
        return None
    entry_blk = trig[0] + 1 + ENTRY_LAG                                  # ENTRY_LAG: extra blocks before our buy lands (feed + send latency)
    pre = [e for e in ev if e[0] < entry_blk]                         # our entry prices at the state after the trigger's whole block
    sp0, L0 = pre[-1][3], pre[-1][4]
    if not sp0 or not L0:
        return None
    q = v4math.buy_out_int(sp0, L0, STAKE, fee)                          # fee: the pool's own (hundredths of a bip), 0 for the fee-0 family
    demand_after = sum(e[2] for e in ev if e[0] >= entry_blk and e[2] > 0) / 1e18

    def ret_at(b):
        if pull is not None and pull <= b:
            return -1.0
        post = [e for e in ev if e[0] <= b and e[0] >= entry_blk]
        sp = post[-1][3] if post else sp0
        sp2 = int(v4math.sqrt_after_buy(sp, L0, STAKE * (10 ** 6 - fee) // 10 ** 6))
        return (v4math.sell_out_int(sp2, L0, q, fee) - STAKE - GAS) / STAKE
    exit_blk = entry_blk + HOLD; why = "hold"
    for b in sorted({e[0] for e in ev if e[0] >= entry_blk}):
        if b > entry_blk + HOLD:
            break
        if pull is not None and pull <= b:
            exit_blk, why = pull, "pull"; break
        if ret_at(b) >= TP:
            exit_blk, why = b + LAG, "take-profit"; break                  # the sell lands LAG blocks after the feed shows the take-profit
    r = ret_at(min(exit_blk, hi))
    return {"trig_off": trig[0] - bn, "trig_who": trig[5][:10], "trig_eth": trig[2] / 1e18, "entry_off": entry_blk - bn,
            "exit_off": exit_blk - bn, "why": why, "ret": r, "pull": None if pull is None else pull - bn, "demand_after": demand_after, "swaps": len(ev)}


def main():
    head = int(H.rpc(url, "eth_blockNumber", []), 16)
    say(f"watchfee0 start: head {head}; fee-0 no-hook pools; stake {STAKE/1e18:g} ETH, trigger {TRIG_ETH} ETH, take-profit {TP:.0%}, hold {HOLD}, follow {WIN} blocks; DRY RUN, no trades")
    seen = set(); pending = collections.deque(); done = []; cursor = head; t_end = time.time() + MINUTES * 60
    while time.time() < t_end:
        try:
            head = int(H.rpc(url, "eth_blockNumber", []), 16)
            if head > cursor:
                for l in getlogs(cursor + 1, head, [T_INIT4], PM):
                    d = l["data"][2:]; fee = int(d[0:64], 16); hooks = "0x" + d[128 + 24:192]; pid = l["topics"][1]
                    if fee == 0 and int(hooks, 16) == 0 and l["topics"][2] == "0x" + "0" * 64 and pid not in seen:
                        seen.add(pid); bn = int(l["blockNumber"], 16)
                        pending.append((pid, bn, l["transactionHash"])); say(f"new fee-0 pool {pid[:14]} at block {bn} (following for {WIN} blocks)")
                cursor = head
            # score pools whose window has closed
            ready = [x for x in pending if x[1] + WIN + 2 <= head]
            for pid, bn, tx in ready:
                pending.remove((pid, bn, tx))
                try:
                    r = ride(pid, bn)
                except RuntimeError as e:
                    say(f"  {pid[:14]}: read error {str(e)[:80]}"); continue
                if r is None:
                    say(f"  {pid[:14]}: no demand buy >= {TRIG_ETH} ETH in {WIN} blocks -> no trade"); continue
                done.append(r)
                say(f"  {pid[:14]}: demand {r['trig_eth']:.3f} ETH via {r['trig_who']} at +{r['trig_off']}, entry +{r['entry_off']}, exit +{r['exit_off']} ({r['why']}), "
                    f"demand after entry {r['demand_after']:.2f} ETH, pull {r['pull']} -> PAPER {r['ret']:+.1%}")
                rr = [x["ret"] for x in done]
                say(f"    running: {len(done)} rides, mean {sum(rr)/len(rr):+.1%}, won {sum(x>0 for x in rr)}/{len(rr)}, pulled-first {sum(1 for x in done if x['why']=='pull')}")
            time.sleep(15)
        except RuntimeError as e:
            say(f"rpc error: {str(e)[:100]}"); time.sleep(20)
    say(f"watchfee0 end: {len(done)} rides scored, {len(pending)} still open")


if __name__ == "__main__":
    main()
