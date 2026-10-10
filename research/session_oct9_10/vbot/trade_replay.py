#!/usr/bin/env python3
"""Cross-check of the hold-30 follow on this family with the feed-side recognition only (vbot_feed): arm from the launch calldata in the
launch block; the engine's buy rule moves an exact integer copy of the pool, the Universal Router decoder its sells, the bot-router pull
empties it; trigger = the first buy >= MIN_TRIGGER after the launch tx; our buy (0.0012 ETH, minOut = copy's quote - 3%) lands in block
T + LAND, at the HEAD of that block (optimistic) or its TAIL (after every tx sequenced in it: pessimistic); take-profit on a buy >= MIN_TRIGGER
behind ours that prices the sell (after the block's real base fee x 207.8k gas) >= +1%; else sent at buy + HOLD (the census convention); the sell lands one
block after it is sent, head or tail. A pull sequenced before our sell = the sell returns ~0 (-100%).

    python3 trade_replay.py           (every launch with full blocks [b0, b0 + 100] in vbot/blocks; writes vbot/trade_replay.json)
"""
import sys, os, json, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); SCR = os.path.dirname(HERE); sys.path.insert(0, HERE); sys.path.insert(0, "/home/user/v2pons/src")
import fetch_blocks as fb, v4math
from vbot_feed import launch_of, ur_swaps, bot_pull, buy_sqrt, sell_sqrt
SYS_TYPES = {"0x64", "0x65", "0x66", "0x68", "0x69", "0x6a"}
STAKE = int(0.0012e18); MIN_TRIG = int(0.0002e18); TP = 0.01; SLIP = 0.03; GAS_UNITS = 207_800; LEAD = 2


def run(b0, B, launch_tx, land=1, hold=30, place="head"):
    p = None; T = None; bought = None; tokens = None; expected = None; send = None; out = None; pulled = False; sp = L = fee = None; tok = None
    for n in range(b0, b0 + 101):
        if n not in B: return {"why": "no blocks"}
        ts, bf, txs = B[n]; gas_wei = bf * GAS_UNITS
        events = []                                                              # our own txs at the head or the tail of the block
        if T is not None and bought is None and n == T + land: events.append("buy")
        if send is not None and out is None and n == send + 1: events.append("sell")
        def ours(ev):
            nonlocal sp, bought, tokens, out
            if ev == "buy":
                got = v4math.buy_out_int(sp, L, STAKE, fee) if not pulled else 0
                if got < expected * (1 - SLIP):
                    out = {"why": "buy reverts (slip)", "ret": 0.0, "T": T - b0}; return
                tokens = got; sp = buy_sqrt(sp, L, STAKE, fee); bought = n
            else:
                eth = 0 if pulled else v4math.sell_out_int(sp, L, tokens, fee)
                if not pulled: sp = sell_sqrt(sp, L, tokens, fee)
                out = {"why": why, "ret": (eth - STAKE - gas_wei) / STAKE, "T": T - b0, "buy": bought - b0, "sell": n - b0, "pulled": pulled}
        if place == "head":
            for ev in events:
                ours(ev)
                if out: return out
        for t in txs:
            idx, h, frm, to, val, nonce, typ, gas, tipv, data = t
            if typ in SYS_TYPES: continue
            to_ = to[2:]
            if p is None:
                if h == launch_tx:
                    p = launch_of(to_, val, data)
                    if p is None: return {"why": "not recognised"}
                    sp, L, fee, tok = p["sqrt_p"], p["liq"], p["fee"], p["token_bytes"]
                continue
            if tok not in data: continue
            if val > 0 and len(data) >= 20 and to_ != p["token"]:
                if not pulled: sp = buy_sqrt(sp, L, val, fee)
                if val >= MIN_TRIG:
                    if T is None:
                        T = n; expected = v4math.buy_out_int(sp, L, STAKE, fee)
                    elif bought is not None and send is None and not pulled:
                        eth = v4math.sell_out_int(sp, L, tokens, fee)
                        if (eth - STAKE - gas_wei) / STAKE >= TP: send = n; why = "tp"
            else:
                for x in ur_swaps(to_, val, data):
                    if x["pid"] == p["pid"] and not pulled:
                        sp = sell_sqrt(sp, L, x["amount_in"], fee) if not x["zero_for_one"] else buy_sqrt(sp, L, x["amount_in"], fee)
                pl = bot_pull(to_, val, data)
                if pl and pl["token"] == p["token"]: pulled = True
        if place == "tail":
            for ev in events:
                ours(ev)
                if out: return out
        if bought is not None and send is None and n >= bought + hold: send = n; why = "deadline"          # the census convention: hold = the last block the sell may be sent after our buy
    return {"why": "window end", "T": (T - b0) if T else None}


if __name__ == "__main__":
    R = [json.loads(l) for l in open(os.path.join(SCR, "others", "census.jsonl"))]
    fam = lambda r: r["sel"] == "0xac9650d8" and r["inlen"] == 1444 and r["fee"] == 10000 and r["ts"] == 200 and round(r["value"] or 0, 3) == 3.0
    V3 = sorted((r["b0"], r["tx"], r["pid"]) for r in R if fam(r))
    import pickle
    PC = pickle.load(open(os.path.join(HERE, "cache_post_launch.pkl"), "rb"))                     # launches after the census (post_check.py)
    for l in PC["inits"]:
        t = PC["tx"].get(l["transactionHash"])
        if t and launch_of((t["to"] or "")[2:].lower(), int(t["value"], 16), bytes.fromhex(t["input"][2:])):
            V3.append((int(l["blockNumber"], 16), l["transactionHash"], l["topics"][1]))
    V3.sort(); CENSUS_END = 84238619
    B = {}
    for c in sorted(int(f[:-4]) for f in os.listdir(fb.BD) if f.endswith(".pkl")): B.update(fb.load_chunk(c))
    L = [(b0, tx, pid) for b0, tx, pid in V3 if all(n in B for n in range(b0, b0 + 101))]
    print("launches with full blocks [b0, b0 + 100]:", len(L))
    res = {}
    for land in (1, 2):
        for place in ("head", "tail"):
            for hold in (2, 30):
                rs = [run(b0, B, tx, land, hold, place) for b0, tx, pid in L]
                for b0_, x in zip([b for b, _, _ in L], rs): x["post"] = b0_ > CENSUS_END
                v = [x["ret"] for x in rs if "ret" in x and x["why"] != "buy reverts (slip)"]
                vc = [x["ret"] for x in rs if "ret" in x and x["why"] != "buy reverts (slip)" and not x["post"]]
                vp = [x["ret"] for x in rs if "ret" in x and x["why"] != "buy reverts (slip)" and x["post"]]
                k = f"land{land}/{place}/hold{hold}"
                print(f"   census-window part n {len(vc)} mean {100 * st.mean(vc):+.2f}% | post-census part n {len(vp)} mean {100 * st.mean(vp) if vp else 0:+.2f}% median {100 * st.median(vp) if vp else 0:+.2f}% pulled {sum(1 for x in rs if x['post'] and x.get('pulled'))}")
                res[k] = {"n": len(v), "mean": st.mean(v) if v else None, "median": st.median(v) if v else None, "pos": sum(1 for a in v if a > 0), "worst": min(v) if v else None,
                          "pulled": sum(1 for x in rs if x.get("pulled")), "reverts": sum(1 for x in rs if x["why"] == "buy reverts (slip)"), "why": collections.Counter(x["why"] for x in rs).most_common(),
                          "per": [(pid, x) for (b0, tx, pid), x in zip(L, rs)]}
                print(f"{k:22s} n {len(v):3d} mean {100 * res[k]['mean']:+6.2f}% median {100 * res[k]['median']:+6.2f}% positive {res[k]['pos']:3d} worst {100 * res[k]['worst']:+7.2f}% "
                      f"pulled-first {res[k]['pulled']} slip-reverts {res[k]['reverts']} {res[k]['why']}")
    json.dump(res, open(os.path.join(HERE, "trade_replay.json"), "w"), default=str)
