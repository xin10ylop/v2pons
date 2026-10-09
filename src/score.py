#!/usr/bin/env python3
"""Price the engine's decisions from the chain. For every would_fire (dry run) or trade_done (live) in the log: the pool's swaps and
liquidity changes after the launch, the paper trade with the engine's exit (release 0.3: our buy at the trigger block + land, the
sell sent in the block of the first buy behind ours that prices it at TAKE_PROFIT, at the latest at our buy + HOLD - LEAD, landing
two blocks later), the crowd's buys inside the hold, the operator's pull relative to the trigger, and, live, the one line that
decided every live trade so far: the pull's block after our buy against our sell's, and which came first. Also the supply
reading: armed launches by fee tier and the crowd's first-buy offsets.

    python3 src/score.py /var/log/flip/engine.jsonl [hours=24]
"""
import json, os, sys, time, collections, statistics as st, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v4math
from eth_utils import keccak
RPC = os.environ.get("RPC_URL", "https://rpc.mainnet.chain.robinhood.com"); H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 Chrome/128"}; Q96 = 1 << 96
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


def price(sw, pull, sqrt_p0, liq0, fee, buy_bn, hold, lead, tp, stake_wei):
    """the engine's exit on paper: our buy at the head of buy_bn, the sell sent in the block of the first buy behind ours that
    prices it at tp (at the latest buy_bn + hold - lead) and landing two blocks later (the slow case); a pull at or before the
    landing is -100%. Our buy is put into the chain's later states by 1/sqrtP's additivity (one liquidity range). Returns
    (return, landing blocks after our buy)."""
    f = fee / 1e6; sp, L = state_after(sw, buy_bn - 1, sqrt_p0, liq0); x = stake_wei * (1 - f); gas = GAS / (stake_wei / 1e18 * ETH_USD)
    tok = v4math.buy_out(sp, L, x)
    if tok <= 0: return None, None
    def ret_at(sp_chain, L_):
        s_ours = Q96 / (Q96 / sp_chain + x / L_)
        return (v4math.sell_out(s_ours, L_, tok) * (1 - f) - stake_wei) / stake_wei - gas
    send = buy_bn + hold - lead
    for s in sw:
        if buy_bn <= s[0] <= buy_bn + hold - lead and s[2] < 0 and ret_at(s[4], s[5]) >= tp:
            send = s[0]; break
    land = send + 2
    if pull is not None and pull <= land: return -1.0 - gas, land - buy_bn
    sp2, L2 = state_after(sw, land - 1, sqrt_p0, liq0)
    return ret_at(sp2, L2), land - buy_bn


def main():
    path = sys.argv[1]; hours = float(sys.argv[2]) if len(sys.argv) > 2 else 24; t_lo = time.time() - hours * 3600
    ev = [json.loads(l) for l in open(path) if l.strip()]; ev = [e for e in ev if e.get("t", 0) >= t_lo]
    start = [e for e in ev if e["ev"] == "start"]; st0 = start[-1] if start else {}
    hold = st0.get("hold_blocks", 4); lead = st0.get("sell_lead_blocks", 2); tp = st0.get("take_profit", 0.01); stake = int(st0.get("stake_eth", 0.0012) * 1e18)
    ours = {"0x" + e["buy_hash"] for e in ev if e["ev"] == "fire" and e.get("buy_hash")} | {"0x" + e["hash"] for e in ev if e["ev"] == "sell_sent" and e.get("hash")}
    armed = {e["pid"]: e for e in ev if e["ev"] == "armed" and e.get("entry") != "front"}                # the front strategy (release 0.9) is priced by results.py, not here
    first = {e["pid"]: e for e in ev if e["ev"] == "first_buy" and e["pid"] in armed}
    print(f"{path}: last {hours:g} h; {len(armed)} launches armed, {sum(1 for a in armed.values() if a['eligible'])} eligible; first real buy seen on {len(first)}")
    tiers = collections.Counter(("sub-1%" if a["fee"] < 10000 else ("1%" if a["fee"] == 10000 else "over 1%")) for a in armed.values())
    print("  by fee tier:", dict(tiers))
    offs = [f["offset"] for f in first.values()]
    if offs: print(f"  the crowd's first buy: offset blocks p10/50/90 {[sorted(offs)[int(q * (len(offs) - 1))] for q in (.1, .5, .9)]} (backtest 22/44/64); value median {st.median(f['value'] for f in first.values()) / 1e18:.4f} ETH")
    fires = [e for e in ev if e["ev"] in ("would_fire", "fire") and e.get("entry") != "front"]; done = {e["pid"]: e for e in ev if e["ev"] == "trade_done" and not e.get("dry")}
    rows = []
    for e in fires:
        a = armed.get(e["pid"])
        if not a: continue
        sw, pull = pool_events(e["pid"], a["seq"]); trig = e["trig_seq"]; sw = [x for x in sw if x[6] not in ours]      # the paper is the pool without us
        paper = {land: price(sw, pull, a["sqrt_p"], a["liq"], a["fee"], trig + land, hold, lead, tp, stake)[0] for land in (1, 2, 3)}
        behind = [x for x in sw if trig + 2 <= x[0] <= trig + 2 + hold and x[2] < 0]
        d = done.get(e["pid"]); row = {"pid": e["pid"][:12], "t": time.strftime("%m-%d %H:%M:%S", time.gmtime(e["t"])), "fee": a["fee"], "trig": trig - a["seq"], "paper": paper, "buys_behind": len(behind),
                                       "eth_behind": sum(-x[2] for x in behind) / 1e18, "pull_after_trig": (pull - trig) if pull is not None else None, "live": None}
        if d and d.get("buy") and isinstance(d["buy"], dict):
            row["live"] = {"ret": d.get("ret"), "pnl_usd": d.get("pnl_usd"), "buy_offset": d.get("buy_offset"), "hold": d.get("hold_blocks"), "pull_after_buy": d.get("pull_after_buy_blocks"), "buy": d["buy"].get("status"),
                           "sell": d.get("sell", {}).get("status") if isinstance(d.get("sell"), dict) else d.get("sell"), "pulled_first": d.get("pulled_before_sell"), "why": (d.get("sell_why") or "").split(":")[0],
                           "amount_src": (d.get("sell_amount_src") or "").split(" ")[0], "tokens_left": d.get("tokens_left")}
        rows.append(row)
    print(f"\n{len(rows)} decisions (paper = ${stake / 1e18 * ETH_USD:.0f} landing at the trigger block + land; the sell on the first buy behind ours worth {tp:+.0%}, at the latest sent "
          f"at our buy + {hold - lead}, landing two blocks later; a pull at or before the landing = -100%)")
    for r in rows:
        pp = " ".join(f"land{l}:{'n/a' if v is None else f'{v:+.1%}'}" for l, v in r["paper"].items())
        L = r["live"]
        live = "" if L is None else (f" | LIVE ret {L['ret']} ${L['pnl_usd']} buy trig+{L['buy_offset']} {L['buy']}; sell ({L['why']}, amount from {L['amount_src']}) landed +{L['hold']} {L['sell']}; "
                                     f"pull +{L['pull_after_buy']}{' PULLED FIRST' if L['pulled_first'] else ''}" + (f"; tokens left {L['tokens_left']}" if L["tokens_left"] else ""))
        print(f"  {r['t']} {r['pid']} fee {r['fee']/1e4:g}% trigger +{r['trig']}: {pp}; {r['buys_behind']} buys ({r['eth_behind']:.3f} ETH) behind in the hold; pull {r['pull_after_trig']} blocks after the trigger{live}")
    v = [r["paper"][2] for r in rows if r["paper"].get(2) is not None]
    if v: print(f"\n  paper, land 2: n {len(v)}, mean {st.mean(v):+.1%}, median {st.median(v):+.1%}, win {sum(1 for x in v if x > 0) / len(v):.0%} (backtest of this exit, Oct 5-8: +3.4% mean, 85% win, worst -1.9%)")
    lv = [r["live"]["ret"] for r in rows if r["live"] and r["live"]["ret"] is not None]
    if lv: print(f"  live: n {len(lv)}, mean {st.mean(lv):+.1%}, win {sum(1 for x in lv if x > 0) / len(lv):.0%}, total ${sum(r['live']['pnl_usd'] for r in rows if r['live'] and r['live']['pnl_usd'] is not None):+.2f}; "
                 f"pulled before our sell: {sum(1 for r in rows if r['live'] and r['live']['pulled_first'])}; pulled within 20 blocks of our buy: {sum(1 for r in rows if r['live'] and r['live']['pull_after_buy'] is not None and r['live']['pull_after_buy'] <= 20)}")


if __name__ == "__main__":
    main()
