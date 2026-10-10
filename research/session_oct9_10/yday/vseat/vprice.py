#!/usr/bin/env python3
"""Independent re-pricing of the seat entry (flip_engine 0.8) on chosen Oct 8 copy launches, from raw/<L>.json (vfetch.py).
Written fresh; imports only v4math and chain constants.

Rules (from src/flip_engine.py):
  feed       a tx is a "buy" of the pool if value > 0, len(input) >= 20, token's 20 bytes in the input, to != token, and it is not a
             launch call (to == original launcher or selector 2fcb9108). apply_buy moves sqrtP by net_of_fee(tx.value).
  late       seat: a feed buy with value >= 0.0002 ETH in L..L+6 (incl. the arm replay of `recent`) -> no trade.
  fire       at L+6: expected = buy_out_int(int(feed sp through L+6), liq_receipt, stake, fee); minOut = int(expected * 0.97).
  buy        lands in B (L+7 / L+8) after every other swap of B: fill = buy_out_int(chain sqrtP after B, chain L, stake, fee).
             fill < minOut -> revert.
  TP         feed_tokens = buy_out_int(feed sp through all of B, liq, stake, fee); feed sp then += our buy; each feed buy in B+1..B+2
             moves it; one with value >= 0.0002 checks (sell_out_int(sp, liq, feed_tokens, fee) - stake - basefee*250000)/stake >= 0.01.
  deadline   send at B+2 if no TP. Land send+1 (fast) / send+2 (slow).
  sell       head of S: chain sqrtP after S-1, 1/sqrtP += net(stake)/L (our buy), sell_out_int(that, L, fill, fee).
  pull       first ML with liquidityDelta < 0; pull block <= S -> -100% - gas.
  gas        relay gasUsed medians (from raw/relay.json) x baseFeePerGas of B (buy) and S (sell).
"""
import sys, os, json, statistics as st
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad"); sys.path.insert(0, "/home/user/v2pons/src")
from chain import PM, T_INIT, T_SWAP, T_ML, W, sgn
from eth_utils import keccak
import v4math

HERE = os.path.dirname(os.path.abspath(__file__)); RAW = os.path.join(HERE, "raw")
Q96 = 1 << 96
OP = "3194e32622c5d860a0572c74edda99dcfd8fc827"; SEL = "2fcb9108"; RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"
SEAT_HASH = "2793923de1845d8707004ebbf2ab49fe7286113b7b69991aea7d6656f26f6d1c"
MIN_TRIG = int(0.0002 * 1e18); SLIP = 0.03; TP = 0.01; HOLD = 4; LEAD = 2; FIRE_AT = 6


def i128(x):
    x = sgn(x)
    return x


def net(x, fee):
    return x - (x * fee + 999_999) // 1_000_000


def gas_model():
    R = json.load(open(os.path.join(RAW, "relay.json")))
    buys, sells, zero = [], [], []
    for l, r in zip(R["logs"], R["recs"]):
        a0 = sgn(W(l["data"], 0)); g = int(r["gasUsed"], 16)
        egp = int(r["effectiveGasPrice"], 16)
        if r["status"] != "0x1":
            continue
        (buys if a0 < 0 else sells if a0 > 0 else zero).append(g)
    return {"buy": int(st.median(buys)), "sell": int(st.median(sells)), "zero": int(st.median(zero)) if zero else None, "buys": buys, "sells": sells, "zero_list": zero}


def load(L):
    d = json.load(open(os.path.join(RAW, f"{L}.json")))
    rec = d["rec"]; init = None; adds = []
    for l in rec["logs"]:
        if l["address"].lower() != PM: continue
        if l["topics"][0] == T_INIT: init = l
        elif l["topics"][0] == T_ML: adds.append((sgn(W(l["data"], 0)), sgn(W(l["data"], 1)), sgn(W(l["data"], 2)), l["topics"][1]))
    pid = init["topics"][1]; dd = init["data"]
    pool = {"pid": pid, "c0": init["topics"][2][-40:], "token": init["topics"][3][-40:].lower(), "fee": W(dd, 0), "ts": sgn(W(dd, 1)),
            "hooks": dd[2 + 128 + 24: 2 + 192], "sp0": W(dd, 3), "tick0": sgn(W(dd, 4))}
    pool["liq"] = v4math.active_liquidity(pool["tick0"], [(a, b, c) for a, b, c, p in adds if p == pid])
    pool["ranges"] = [(a, b, c) for a, b, c, p in adds if p == pid]
    code = d["code_latest"]; pool["code_hash"] = keccak(bytes.fromhex(code[2:])).hex() if len(code) > 2 else None
    pool["code_at_L"] = d["code_at_L"][:80]
    blocks = {int(b["number"], 16): b for b in d["blocks"]}
    # chain swaps (exclude relay), pulls, adds after launch
    swaps = []; pull = None; later_adds = []
    for l in sorted(d["logs"], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16))):
        bn = int(l["blockNumber"], 16)
        if l["topics"][0] == T_ML:
            dl = sgn(W(l["data"], 2))
            if dl < 0 and pull is None: pull = bn
            if dl > 0 and l["transactionHash"] != d["tx"]["hash"]: later_adds.append((bn, dl))
            continue
        sender = l["topics"][2][-40:].lower()
        a0 = sgn(W(l["data"], 0)); a1 = sgn(W(l["data"], 1))
        swaps.append({"bn": bn, "li": int(l["logIndex"], 16), "a0": a0, "a1": a1, "sp": W(l["data"], 2), "L": W(l["data"], 3), "tick": sgn(W(l["data"], 4)),
                      "fee": W(l["data"], 5), "relay": sender == RELAY, "tx": l["transactionHash"]})
    # feed buys
    tb = bytes.fromhex(pool["token"]); feed = []
    for bn in sorted(blocks):
        for t in sorted(blocks[bn]["transactions"], key=lambda t: int(t["transactionIndex"], 16)):
            to = (t["to"] or "")[2:].lower(); data = bytes.fromhex(t["input"][2:]); v = int(t["value"], 16)
            if to == OP or data[:4].hex() == SEL: continue
            if v == 0 or len(data) < 20: continue
            if tb in data and to != pool["token"]:
                feed.append((bn, int(t["transactionIndex"], 16), v, t["hash"], t["from"].lower()))
    return d, pool, blocks, swaps, pull, later_adds, feed


def chain_after(swaps, pool, blk):
    prev = [x for x in swaps if x["bn"] <= blk and not x["relay"]]
    return (prev[-1]["sp"], prev[-1]["L"]) if prev else (pool["sp0"], pool["liq"])


def feed_sp(pool, feed, upto, start=None, sp=None):
    sp = float(pool["sp0"]) if sp is None else sp
    for bn, ix, v, h, fr in feed:
        if start is not None and bn <= start: continue
        if bn > upto: break
        sp = v4math.sqrt_after_buy(sp, pool["liq"], net(v, pool["fee"]))
    return sp


def price(L, stakes=(0.0012, 0.004, 0.012), lands=(7, 8)):
    d, pool, blocks, swaps, pull, later_adds, feed = load(L)
    G = gas_model(); fee = pool["fee"]; liq = pool["liq"]
    bf = {n: int(b["baseFeePerGas"], 16) for n, b in blocks.items()}
    out = {"block": L, "pid": pool["pid"], "fee": fee, "liq": liq, "code_hash_ok": pool["code_hash"] == SEAT_HASH, "code_at_L": pool["code_at_L"],
           "eligible": pool["c0"] == "0" * 40 and pool["hooks"] == "0" * 40 and 0 <= fee <= 9999 and liq >= 1e21, "pull": pull, "pull_off": pull - L if pull else None,
           "later_adds": later_adds, "relay_swaps": sum(1 for x in swaps if x["relay"]), "ranges": pool["ranges"], "tick0": pool["tick0"]}
    fire = L + FIRE_AT
    late = [(bn - L, v) for bn, ix, v, h, fr in feed if bn <= fire and v >= MIN_TRIG]
    out["late"] = late
    out["feed_upto_L12"] = [(bn - L, ix, v / 1e18, fr[:10]) for bn, ix, v, h, fr in feed if bn <= L + 12]
    burst = [x for x in swaps if not x["relay"] and x["a0"] < 0 and -x["a0"] >= MIN_TRIG]
    out["burst_off"] = burst[0]["bn"] - L if burst else None
    # check: swap ETH in vs tx value (exact-in check) for burst block swaps
    txv = {t["hash"]: int(t["value"], 16) for b in blocks.values() for t in b["transactions"]}
    out["exact_in_check"] = [(x["bn"] - L, -x["a0"], txv.get(x["tx"])) for x in swaps if x["a0"] < 0 and x["bn"] <= L + 15][:8]
    if late:
        out["skip"] = "late"; return out
    sp_fire = feed_sp(pool, feed, fire)
    out["feed_vs_chain_at_fire"] = sp_fire / chain_after(swaps, pool, fire)[0] - 1
    res = {}
    for s in stakes:
        X = int(s * 1e18); xn = net(X, fee); res[str(s)] = {}
        expected = v4math.buy_out_int(int(sp_fire), liq, X, fee); minout = int(expected * (1 - SLIP))
        for k in lands:
            B = L + k
            spc, Lc = chain_after(swaps, pool, B)
            fill = v4math.buy_out_int(spc, Lc, X, fee)
            # TP on the feed
            spB = feed_sp(pool, feed, B, start=fire, sp=sp_fire)
            ftok = v4math.buy_out_int(int(spB), liq, X, fee)
            spf = v4math.sqrt_after_buy(spB, liq, xn)
            send = B + HOLD - LEAD; why = "deadline"; tpr = None
            for bn, ix, v, h, fr in feed:
                if bn <= B: continue
                if bn > B + HOLD - LEAD: break
                spf = v4math.sqrt_after_buy(spf, liq, net(v, fee))
                if v < MIN_TRIG: continue
                r = (v4math.sell_out_int(int(spf), liq, ftok, fee) - X - bf[B] * 250_000) / X
                if r >= TP:
                    send = bn; why = "take_profit"; tpr = r; break
            for spd, lag in (("fast", 1), ("slow", 2)):
                S = send + lag
                rr = {"buy_block": B, "sell_send_block": send, "sell_land_block": S, "fill": fill, "min_out": minout, "expected": expected, "fill_vs_exp": fill / expected - 1, "tp_ret": tpr}
                if fill < minout:
                    gas = G["buy"] * bf[B] + G["sell"] * bf[S]
                    rr.update(exit="buy_reverted", ret=-gas / X, pnl=-gas / 1e18)
                elif pull is not None and pull <= S:
                    gas = G["buy"] * bf[B] + G["sell"] * bf[S]
                    rr.update(exit="pull_first", ret=(-X - gas) / X, pnl=(-X - gas) / 1e18)
                else:
                    spS, LS = chain_after(swaps, pool, S - 1)
                    sells_between = [x for x in swaps if not x["relay"] and B < x["bn"] <= S - 1 and x["a0"] > 0]
                    ours = Q96 * Q96 // (Q96 * Q96 // spS + xn * Q96 // LS)          # integer: Q96/sp' = Q96/sp + xn/L
                    eth = v4math.sell_out_int(ours, LS, fill, fee)
                    # range check: price stays within the active range [tickLower, tickUpper] of the receipt's position
                    lo = min(a for a, b, c in pool["ranges"]); hi = max(b for a, b, c in pool["ranges"])
                    slo = 1.0001 ** (lo / 2) * Q96; shi = 1.0001 ** (hi / 2) * Q96
                    crossed = not (slo <= ours <= shi) or LS != liq
                    gas = G["buy"] * bf[B] + G["sell"] * bf[S]
                    rr.update(exit=why, eth_out=eth, ret=(eth - X - gas) / X, pnl=(eth - X - gas) / 1e18, sells_between=len(sells_between), crossed=crossed, LS_eq_liq=LS == liq)
                res[str(s)][f"land{k}_{spd}"] = rr
    out["results"] = res
    out["gas"] = {k: v for k, v in G.items()}
    return out


if __name__ == "__main__":
    Ls = [int(x) for x in sys.argv[1:]] or sorted(int(f[:-5]) for f in os.listdir(RAW) if f[:-5].isdigit())
    allr = [price(L) for L in Ls]
    json.dump(allr, open(os.path.join(HERE, "vprice_out.json"), "w"), indent=1, default=str)
    for r in allr:
        print(r["block"], "fee", r["fee"], "burst", r["burst_off"], "pull", r["pull_off"], "late", r["late"], "code_ok", r["code_hash_ok"], "elig", r["eligible"],
              "adds", r["later_adds"], "relay", r["relay_swaps"], "fvc", r.get("feed_vs_chain_at_fire"))
        if "results" in r:
            for s, v in r["results"].items():
                print("   ", s, " ".join(f"{k[4:]}:{x['ret']:+.4f}/{x['exit'][:4]}/{x['sell_land_block'] - r['block']}" for k, x in v.items()))
