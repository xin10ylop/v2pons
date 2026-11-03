#!/usr/bin/env python3
"""census.py CHAIN "START" "END" OUT.json: rugcensus.py for a past window: every native-paired pool created on CHAIN between START and END
(UTC, "YYYY-MM-DD HH:MM") on Uniswap v4 (the chain's PoolManager), the V2 factories and the V3 factories, the liquidity put in, and the
pull (its own liquidity taken out again within PULL_H hours, default 2). The output has rugcensus.py's layout ({"chains": {CHAIN: {...,
"rugs": [...]}}}), so research/chase/seattest.py and rugline.py read it, plus "created": every native pool of the window (venue, id,
token, block, launch transaction) for the bytecode match. Robinhood: topic-only logs (any factory). Base: the factories below (publicnode
needs an address filter; found by sampling PairCreated/PoolCreated over Sep-Oct through Tenderly). Read-only, public RPCs."""
import os, sys, json, time, collections
import hlib as H

PULL_H = float(os.environ.get("PULL_H", "2"))
FACT = {"base": {"v2": ["0x02a84c1b3bbd7401a5f7fa98a384ebc70bb5749e", "0x25e89b02f0c62b67622b4ebd629c882a73d8cabc",
                        "0x8909dc15e40173ff4699343b6eb8132c65e18ec6", "0xfda619b6d20975be80a10332cd39b9a4b0faa8bb",
                        "0x488db0978b34c6fd901760b9024b565c1117c7c8"],
                 "v3": ["0x33128a8fc17869897dce68ed026d694621f6fdfd"]},
        "rh": {"v2": None, "v3": None},                    # None: topic-only, every factory
        "bnb": {"v2": ["0xca143ce32fe78f1f7019d7d551a6402fc5350c73", "0x8909dc15e40173ff4699343b6eb8132c65e18ec6"],   # PancakeSwap V2, Uniswap V2
                "v3": ["0xdb1d10011ad0ff90774d0c6bb92e5c5c8b4461f7", "0x0bfbcf9fa4f9c56b0f40a671ad40e0805a091865"]},   # Uniswap V3, PancakeSwap V3 (its Swap: T_SWAP3_PCS)
        "eth": {"v2": ["0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f", "0xc0aee478e3658e2610c5f7a4a2e1777ce9e4f2ac"],   # Uniswap V2, SushiSwap
                "v3": ["0x1f98431c8ad98523631ae4a59f267346ea31f984"]}}                                            # Uniswap V3


def census(ch, start, end):
    c = H.CH[ch]; W = c["weth"]; url = c["rpc"]
    a, b = H.block_at(ch, start), H.block_at(ch, end)
    bt = (H.ts(url, b) - H.ts(url, a)) / max(1, b - a)
    pull_blocks = int(PULL_H * 3600 / bt); b2 = min(int(H.rpc(url, "eth_blockNumber", []), 16), b + pull_blocks)
    P = {}
    for x in H.logs(ch, a, b, [H.T_INIT], c["pm"]):
        d = x["data"][2:]; c0, c1 = H.a_of(x["topics"][2]), H.a_of(x["topics"][3])
        if c0 == H.ZERO or W in (c0, c1):
            P["v4:" + x["topics"][1]] = {"venue": "v4", "pm": c["pm"], "bn": int(x["blockNumber"], 16), "tx": x["transactionHash"],
                                         "nat": 0 if c0 in (H.ZERO, W) else 1, "native_eth": c0 == H.ZERO, "fee": int(d[0:64], 16),
                                         "ts": H.i256(d[64:128]), "hooks": "0x" + d[152:192], "tok": c1 if c0 in (H.ZERO, W) else c0, "add": 0, "rem": 0}
    for x in H.logs(ch, a, b, [H.T_PC2], FACT[ch]["v2"]):
        t0, t1 = H.a_of(x["topics"][1]), H.a_of(x["topics"][2])
        if W in (t0, t1):
            P["v2:" + "0x" + x["data"][26:66]] = {"venue": "v2", "factory": x["address"].lower(), "bn": int(x["blockNumber"], 16), "tx": x["transactionHash"],
                                                 "nat": 0 if t0 == W else 1, "tok": t1 if t0 == W else t0, "add": 0, "rem": 0, "nat_in": 0.0, "nat_out": 0.0}
    for x in H.logs(ch, a, b, [H.T_PC3], FACT[ch]["v3"]):
        t0, t1 = H.a_of(x["topics"][1]), H.a_of(x["topics"][2])
        if W in (t0, t1):
            P["v3:" + "0x" + x["data"][90:130]] = {"venue": "v3", "factory": x["address"].lower(), "bn": int(x["blockNumber"], 16),
                                                       "tx": x["transactionHash"], "nat": 0 if t0 == W else 1, "fee": int(x["topics"][3], 16),
                                                       "ts": H.i256(x["data"][2:66]), "tok": t1 if t0 == W else t0, "add": 0, "rem": 0, "nat_in": 0.0, "nat_out": 0.0}
    print(f"  {ch} {start}..{end}: blocks {a}-{b}, pools v4 {sum(k[:2] == 'v4' for k in P)} v2 {sum(k[:2] == 'v2' for k in P)} v3 {sum(k[:2] == 'v3' for k in P)}", flush=True)
    v4 = sorted((k for k in P if k[:2] == "v4"), key=lambda k: P[k]["bn"])
    ml = []
    for i in range(0, len(v4), 150):                      # by pool id (topic 1): Base's publicnode refuses the whole PoolManager
        grp = v4[i:i + 150]
        ml += H.logs(ch, P[grp[0]]["bn"], min(b2, P[grp[-1]]["bn"] + pull_blocks), [H.T_ML, [k[3:] for k in grp]], c["pm"])
    for x in sorted(ml, key=lambda x: (int(x["blockNumber"], 16), int(x["logIndex"], 16))):
        p = P.get("v4:" + x["topics"][1])
        if not p:
            continue
        dl = H.i256(x["data"][2 + 128:2 + 192]); bn = int(x["blockNumber"], 16)
        if dl > 0:
            p["add"] += dl; p.setdefault("add_bn", bn); p.setdefault("add_tx", x["transactionHash"])
        elif dl < 0 and bn - p["bn"] <= pull_blocks:
            p["rem"] -= dl; p.setdefault("rem_bn", bn); p.setdefault("rem_tx", x["transactionHash"])
    for venue, tm, tb in (("v2", H.T_MINT2, H.T_BURN2), ("v3", H.T_MINT3, H.T_BURN3)):
        addrs = [k[3:] for k in P if k[:2] == venue]
        # Base's publicnode refuses address lists over ~10: there V2 Mint/Burn is read topic-only (Tenderly) and the window's pairs kept;
        # V3 topic-only is every position change on the chain (117k Burns in 4,900 blocks), so V3 goes by address, 10 pools a query
        topic_only = ch == "base" and venue == "v2"                       # BNB's publicnode refuses topic-only queries: by address, 10 a query
        step = 400 if ch == "rh" else (max(1, len(addrs)) if topic_only else 10)
        for i in range(0, len(addrs), step):
            grp = addrs[i:i + step]
            for kind, topic in (("mint", tm), ("burn", tb)):
                lo = min(P[f"{venue}:{x}"]["bn"] for x in grp)
                hi = min(b2, max(P[f"{venue}:{x}"]["bn"] for x in grp) + pull_blocks)
                for x in H.logs(ch, lo, hi, [topic], None if topic_only else grp):
                    p = P.get(f"{venue}:{x['address'].lower()}")
                    if not p:
                        continue
                    d = x["data"][2:]; bn = int(x["blockNumber"], 16)
                    if venue == "v2":
                        amt = (int(d[0:64], 16), int(d[64:128], 16)); liq = amt[p["nat"]]
                    elif kind == "mint":
                        liq = int(d[64:128], 16); amt = (int(d[128:192], 16), int(d[192:256], 16))
                    else:
                        liq = int(d[0:64], 16); amt = (int(d[64:128], 16), int(d[128:192], 16))
                    if kind == "mint":
                        p["add"] += liq; p["nat_in"] += amt[p["nat"]] / 1e18; p.setdefault("add_bn", bn); p.setdefault("add_tx", x["transactionHash"])
                    elif bn - p["bn"] <= pull_blocks:
                        p["rem"] += liq; p["nat_out"] += amt[p["nat"]] / 1e18; p.setdefault("rem_bn", bn); p.setdefault("rem_tx", x["transactionHash"])
    rugs = []
    for k, p in P.items():
        if not p["add"] or "rem_bn" not in p:
            continue
        ok = p["nat_out"] >= 0.7 * p["nat_in"] > 0 if p["venue"] == "v2" else p["rem"] >= 0.9 * p["add"]
        if ok:
            p["id"] = k; p["pull_min"] = round((p["rem_bn"] - p.get("add_bn", p["bn"])) * bt / 60, 1); rugs.append(p)
    txs = H.batch(url, [("eth_getTransactionByHash", [p.get("add_tx") or p["tx"]]) for p in rugs])
    for p, t in zip(rugs, txs):
        if t:
            p["frm"] = t["from"].lower(); p["to"] = (t.get("to") or "").lower(); p["nonce"] = int(t["nonce"], 16)
            if p["venue"] == "v4" and p.get("native_eth"):
                p["nat_in"] = int(t["value"], 16) / 1e18
        else:
            p["frm"] = p["to"] = None
    created = [[k, p["tok"], p["bn"], p.get("add_tx") or p["tx"], round(p.get("nat_in", 0), 6)] for k, p in P.items()]
    print(f"  {ch} {start}..{end}: pulled within {PULL_H:g} h: {len(rugs)}", flush=True)
    return {"bt": bt, "from": a, "head": b, "window": [start, end], "n_created": len(P), "rugs": rugs, "created": created, "errors": []}


if __name__ == "__main__":
    ch, s, e, out = sys.argv[1:5]
    r = census(ch, s, e)
    json.dump({"hours": None, "pull_h": PULL_H, "t": int(time.time()), "chains": {ch: r}}, open(out, "w"))
    print("->", out)
