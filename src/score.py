#!/usr/bin/env python3
"""Price the engine's decisions from the chain. For every would_fire (dry run) or trade_done (live) in the log: the pool's swaps and
liquidity changes after the launch, the paper trade at the planned landing (the trigger block + 2) and the planned sell (+ HOLD),
the crowd's buys inside the hold, the operator's pull relative to the trigger, and, live, the actual fill against the paper. Also
the supply reading: armed launches by fee tier and the crowd's first-buy offsets.

    python3 src/score.py /var/log/flip/engine.jsonl [hours=24]
"""
import json, os, sys, time, collections, statistics as st, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v4math
from eth_utils import keccak
RPC = os.environ.get("RPC_URL", "https://rpc.mainnet.chain.robinhood.com"); H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"}
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"; ETH_USD = float(os.environ.get("ETH_USD", "2570")); GAS = 0.02
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex(); T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
W = lambda d, i: int(d[2 + 64*i: 2 + 64*(i+1)], 16); sgn = lambda x: x - (1 << 256) if x >= (1 << 255) else x
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x


def rpc(m, p):
    for i in range(6):
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(RPC, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(), H), timeout=60))
            if "result" in d: return d["result"]
        except Exception:
            pass
        time.sleep(2 * (i + 1))
    raise RuntimeError(m)


def pool_events(pid, b0, span=600):
    ls = rpc("eth_getLogs", [{"fromBlock": hex(b0), "toBlock": hex(b0 + span), "address": PM, "topics": [[T_SWAP, T_ML], pid]}])
    sw = []; rem = []
    for l in ls:
        d = l["data"]; bn = int(l["blockNumber"], 16)
        if l["topics"][0] == T_SWAP: sw.append((bn, int(l["logIndex"], 16), s128(W(d, 0)), s128(W(d, 1)), W(d, 2), W(d, 3), l["transactionHash"]))
        elif sgn(W(d, 2)) < 0: rem.append(bn)
    return sorted(sw), (min(rem) if rem else None)


def state_after(sw, bn, sqrt_p0, liq0):
    prev = [x for x in sw if x[0] <= bn]
    return (prev[-1][4], prev[-1][5]) if prev else (sqrt_p0, liq0)


def price(sw, pull, sqrt_p0, liq0, fee, entry_after, exit_bn, stake_wei):
    f = fee / 1e6; sp, L = state_after(sw, entry_after, sqrt_p0, liq0)
    tok = v4math.buy_out(sp, L, stake_wei * (1 - f))
    if tok <= 0: return None
    if pull is not None and pull <= exit_bn: return -1.0 - GAS / (stake_wei / 1e18 * ETH_USD)
    sp2, L2 = state_after(sw, exit_bn, sqrt_p0, liq0)
    return (v4math.sell_out(sp2, L2, tok) * (1 - f) - stake_wei) / stake_wei - GAS / (stake_wei / 1e18 * ETH_USD)


def main():
    path = sys.argv[1]; hours = float(sys.argv[2]) if len(sys.argv) > 2 else 24; t_lo = time.time() - hours * 3600
    ev = [json.loads(l) for l in open(path) if l.strip()]; ev = [e for e in ev if e.get("t", 0) >= t_lo]
    start = [e for e in ev if e["ev"] == "start"]; hold = start[-1]["hold_blocks"] if start else 7; stake = int(start[-1]["stake_eth"] * 1e18) if start else int(0.0012e18)
    armed = {e["pid"]: e for e in ev if e["ev"] == "armed"}; first = {e["pid"]: e for e in ev if e["ev"] == "first_buy"}
    print(f"{path}: last {hours:g} h; {len(armed)} launches armed, {sum(1 for a in armed.values() if a['eligible'])} eligible; first real buy seen on {len(first)}")
    tiers = collections.Counter(("sub-1%" if a["fee"] < 10000 else ("1%" if a["fee"] == 10000 else "over 1%")) for a in armed.values())
    print("  by fee tier:", dict(tiers))
    offs = [f["offset"] for f in first.values()]
    if offs: print(f"  the crowd's first buy: offset blocks p10/50/90 {[sorted(offs)[int(q * (len(offs) - 1))] for q in (.1, .5, .9)]} (backtest 22/44/64); value median {st.median(f['value'] for f in first.values()) / 1e18:.4f} ETH")
    fires = [e for e in ev if e["ev"] in ("would_fire", "fire")]; done = {e["pid"]: e for e in ev if e["ev"] == "trade_done" and not e.get("dry")}
    rows = []
    for e in fires:
        a = armed.get(e["pid"])
        if not a: continue
        sw, pull = pool_events(e["pid"], a["seq"]); trig = e["trig_seq"]
        paper = {land: price(sw, pull, a["sqrt_p"], a["liq"], a["fee"], trig + land - 1, trig + land + hold, stake) for land in (1, 2, 3)}
        behind = [x for x in sw if trig + 2 <= x[0] <= trig + 2 + hold and x[2] < 0]
        d = done.get(e["pid"]); row = {"pid": e["pid"][:12], "t": time.strftime("%m-%d %H:%M:%S", time.gmtime(e["t"])), "fee": a["fee"], "trig": trig - a["seq"], "paper": paper, "buys_behind": len(behind),
                                       "eth_behind": sum(-x[2] for x in behind) / 1e18, "pull_after_trig": (pull - trig) if pull is not None else None, "live": None}
        if d and d.get("buy") and isinstance(d["buy"], dict):
            row["live"] = {"ret": d.get("ret"), "pnl_usd": d.get("pnl_usd"), "buy_offset": d.get("buy_offset"), "hold": d.get("hold_blocks"), "pull_after_buy": d.get("pull_after_buy_blocks"), "buy": d["buy"].get("status"), "sell": d.get("sell", {}).get("status") if isinstance(d.get("sell"), dict) else d.get("sell")}
        rows.append(row)
    print(f"\n{len(rows)} decisions (paper = $3 at the trigger block + land, sold {hold} blocks after; a pull before the sell = -100%)")
    for r in rows:
        pp = " ".join(f"land{l}:{'n/a' if v is None else f'{v:+.1%}'}" for l, v in r["paper"].items())
        live = "" if r["live"] is None else f" | LIVE ret {r['live']['ret']} ${r['live']['pnl_usd']} landed +{r['live']['buy_offset']} held {r['live']['hold']} pull after buy {r['live']['pull_after_buy']} buy {r['live']['buy']} sell {r['live']['sell']}"
        print(f"  {r['t']} {r['pid']} fee {r['fee']/1e4:g}% trigger +{r['trig']}: {pp}; {r['buys_behind']} buys ({r['eth_behind']:.3f} ETH) behind in the hold; pull {r['pull_after_trig']} blocks after the trigger{live}")
    v = [r["paper"][2] for r in rows if r["paper"].get(2) is not None]
    if v: print(f"\n  paper, land 2: n {len(v)}, mean {st.mean(v):+.1%}, median {st.median(v):+.1%}, win {sum(1 for x in v if x > 0) / len(v):.0%} (backtest at hold {hold}: about +6% mean, 94% win)")
    lv = [r["live"]["ret"] for r in rows if r["live"] and r["live"]["ret"] is not None]
    if lv: print(f"  live: n {len(lv)}, mean {st.mean(lv):+.1%}, win {sum(1 for x in lv if x > 0) / len(lv):.0%}, total ${sum(r['live']['pnl_usd'] for r in rows if r['live'] and r['live']['pnl_usd'] is not None):+.2f}; pulls within the hold: {sum(1 for r in rows if r['live'] and r['live']['pull_after_buy'] is not None and r['live']['hold'] is not None and r['live']['pull_after_buy'] <= r['live']['hold'])}")


if __name__ == "__main__":
    main()
