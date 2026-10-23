#!/usr/bin/env python3
"""rugcensus.py HOURS OUT.json [CHAIN...]: every pump-and-pull on each EVM chain in the last HOURS, found by what it does, not by its
shape: a pool created in the window whose own liquidity was taken out again within PULL_H hours (default 2). Venues: Uniswap v4 (any
PoolManager: Initialize + ModifyLiquidity), every V2 fork (PairCreated + Mint + Burn, any factory) and every V3 fork (PoolCreated + Mint
+ Burn, any factory), native-paired only (v4 native currency0 or the wrapped native token; V2/V3 the wrapped native token).

Per pulled pool: venue, fee/tick spacing/hook, the native put in, the minutes to the pull, the launch transaction's sender and target.
Lines: pulled pools grouped by (venue, fee/tick spacing, native in to 3 significant figures) and by the launch target (a launcher
contract or router), each with its count, distinct launch wallets, size range and median minutes to the pull. Read-only, public RPCs."""
import json, os, sys, time, collections, statistics as st, concurrent.futures as cf
import v4census as V

T_ML = "0xf208f4912782fd25c7f114ca3723a2d5dd6f3bcc3ac8db5af63baa85f711d5ec"
T_PC2 = "0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9"    # PairCreated(address,address,address,uint256)
T_MINT2 = "0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f"  # Mint(address,uint256,uint256)
T_BURN2 = "0xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496"  # Burn(address,uint256,uint256,address)
T_PC3 = "0x783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118"    # PoolCreated(address,address,uint24,int24,address)
T_MINT3 = "0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde"  # Mint(address,address,int24,int24,uint128,uint256,uint256)
T_BURN3 = "0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c"  # Burn(address,int24,int24,uint128,uint256,uint256)
PULL_H = float(os.environ.get("PULL_H", "2"))
ZERO = "0x" + "0" * 40
# log endpoints per chain, tried in order: (url, blocks a call)
EP = {"base": [("https://gateway.tenderly.co/public/base", 1000), ("https://base.drpc.org", 1000)],
      "bsc": [("https://rpc-bsc.48.club", 5000), ("https://bsc-rpc.publicnode.com", 5000)],
      "eth": [("https://gateway.tenderly.co/public/mainnet", 1000), ("https://eth.drpc.org", 1000)],
      "arbitrum": [("https://arb1.arbitrum.io/rpc", 50000)], "rh": [("https://rpc.mainnet.chain.robinhood.com", 50000)],
      "polygon": [("https://gateway.tenderly.co/public/polygon", 1000), ("https://polygon-rpc.com", 1000)],
      "avalanche": [("https://gateway.tenderly.co/public/avalanche", 1000), ("https://api.avax.network/ext/bc/C/rpc", 2000)],
      "unichain": [("https://mainnet.unichain.org", 5000), ("https://unichain-rpc.publicnode.com", 5000)],
      "optimism": [("https://mainnet.optimism.io", 10000)], "sonic": [("https://rpc.soniclabs.com", 10000)],
      "linea": [("https://rpc.linea.build", 10000)], "hyperevm": [("https://rpc.hyperliquid.xyz/evm", 1000)],
      "berachain": [("https://rpc.berachain.com", 10000)], "abstract": [("https://api.mainnet.abs.xyz", 10000)],
      "plasma": [("https://rpc.plasma.to", 10000)], "ink": [("https://rpc-gel.inkonchain.com", 10000)],
      "worldchain": [("https://worldchain-mainnet.g.alchemy.com/public", 10000)], "blast": [("https://rpc.blast.io", 10000)],
      "monad": [("https://rpc.monad.xyz", 100)], "sei": [("https://evm-rpc.sei-apis.com", 2000)], "mantle": [("https://rpc.mantle.xyz", 10000)],
      "celo": [("https://forno.celo.org", 10000)], "katana": [("https://rpc.katana.network", 10000)], "soneium": [("https://rpc.soneium.org", 10000)],
      "zora": [("https://rpc.zora.energy", 10000)], "scroll": [("https://rpc.scroll.io", 10000)], "mode": [("https://mainnet.mode.network", 10000)]}
# wrapped native tokens known; for the rest the most frequent token among the new pairs is taken (and printed, to check)
WNATIVE = {"base": "0x4200000000000000000000000000000000000006", "optimism": "0x4200000000000000000000000000000000000006",
           "unichain": "0x4200000000000000000000000000000000000006", "ink": "0x4200000000000000000000000000000000000006",
           "worldchain": "0x4200000000000000000000000000000000000006", "soneium": "0x4200000000000000000000000000000000000006",
           "zora": "0x4200000000000000000000000000000000000006", "mode": "0x4200000000000000000000000000000000000006",
           "blast": "0x4300000000000000000000000000000000000004", "eth": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
           "bsc": "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c", "arbitrum": "0x82af49447d8a07e3bd95bd0d56f35241523fbab1",
           "polygon": "0x0d500b1d8e8ef31e21c99d1db9a6444d3adf1270", "avalanche": "0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7",
           "rh": "0x0bd7d308f8e1639fab988df18a8011f41eacad73", "linea": "0xe5d7c2a44ffddf6b295a15c148167daaaf5cf34f",
           "hyperevm": "0x5555555555555555555555555555555555555555", "berachain": "0x6969696969696969696969696969696969696969",
           "sonic": "0x039e2fb66102314ce7b64ce5ce3e5183bc94ad38", "scroll": "0x5300000000000000000000000000000000000004"}


def logs(ch, a, b, topics, address=None):
    eps, i = EP[ch], 0
    step, out, lo = eps[0][1], [], a
    while lo <= b:
        url = eps[i][0]; hi = min(b, lo + step - 1)
        q = {"fromBlock": hex(lo), "toBlock": hex(hi), "topics": topics}
        if address:
            q["address"] = address
        try:
            out += V.rpc(url, "eth_getLogs", [q], tries=3); lo = hi + 1
        except Exception as e:
            if step > 100:
                step //= 2
            elif i + 1 < len(eps):
                i += 1; step = eps[i][1]
            else:
                raise RuntimeError(f"logs {ch} {topics[0][:10]} at {lo}: {str(e)[:80]}")
    return out


def i256(h):
    v = int(h, 16)
    return v - (1 << 256) if v >= 1 << 255 else v


def a_of(topic):
    return "0x" + topic[26:]


def one(ch, hours):
    url = V.CH[ch][0] if ch in V.CH else EP[ch][0][0]; bt = V.CH[ch][1] if ch in V.CH else 2.0
    try:
        hb = None
        for _ in range(5):                                   # "latest" itself: a load-balanced RPC can answer a block number another node lacks
            hb = V.rpc(EP[ch][0][0], "eth_getBlockByNumber", ["latest", False])
            if hb:
                break
            time.sleep(2)
        head, t_head = int(hb["number"], 16), int(hb["timestamp"], 16)
        a = head - int(hours * 3600 / bt)
        t_a = int(V.rpc(EP[ch][0][0], "eth_getBlockByNumber", [hex(a), False])["timestamp"], 16)
        bt = (t_head - t_a) / max(1, head - a); a = head - int(hours * 3600 / bt); pull_blocks = int(PULL_H * 3600 / bt)
        res = {"bt": bt, "from": a, "head": head, "pools": {}, "errors": []}
        # creations
        L_init = logs(ch, a, head, [V.T_INIT]); L_pc2 = logs(ch, a, head, [T_PC2]); L_pc3 = logs(ch, a, head, [T_PC3])
        toks = collections.Counter()
        for x in L_pc2 + L_pc3:
            toks[a_of(x["topics"][1])] += 1; toks[a_of(x["topics"][2])] += 1
        W = WNATIVE.get(ch) or (toks.most_common(1)[0][0] if toks else None)
        res["wnative"] = W; res["top_tokens"] = toks.most_common(3)
        P = {}
        for x in L_init:
            d = x["data"][2:]; c0, c1 = a_of(x["topics"][2]), a_of(x["topics"][3])
            if c0 == ZERO or W in (c0, c1):
                P["v4:" + x["topics"][1]] = {"venue": "v4", "pm": x["address"].lower(), "bn": int(x["blockNumber"], 16), "tx": x["transactionHash"],
                                             "nat": 0 if c0 in (ZERO, W) else 1, "native_eth": c0 == ZERO, "fee": int(d[0:64], 16),
                                             "ts": i256(d[64:128]), "hooks": "0x" + d[152:192], "tok": c1 if c0 in (ZERO, W) else c0, "add": 0, "rem": 0}
        for x in L_pc2:
            t0, t1 = a_of(x["topics"][1]), a_of(x["topics"][2])
            if W in (t0, t1):
                pair = "0x" + x["data"][26:66]
                P["v2:" + pair] = {"venue": "v2", "factory": x["address"].lower(), "bn": int(x["blockNumber"], 16), "tx": x["transactionHash"],
                                   "nat": 0 if t0 == W else 1, "tok": t1 if t0 == W else t0, "add": 0, "rem": 0, "nat_in": 0.0, "nat_out": 0.0}
        for x in L_pc3:
            t0, t1 = a_of(x["topics"][1]), a_of(x["topics"][2])
            if W in (t0, t1):
                pool = "0x" + x["data"][64 + 26:128]
                P["v3:" + pool] = {"venue": "v3", "factory": x["address"].lower(), "bn": int(x["blockNumber"], 16), "tx": x["transactionHash"],
                                   "nat": 0 if t0 == W else 1, "fee": int(x["topics"][3], 16), "ts": i256(x["data"][2:66]),
                                   "tok": t1 if t0 == W else t0, "add": 0, "rem": 0, "nat_in": 0.0, "nat_out": 0.0}
        # liquidity in and out
        pms = sorted({p["pm"] for p in P.values() if p["venue"] == "v4"})
        if pms:
            for x in logs(ch, a, head, [T_ML], pms if len(pms) > 1 else pms[0]):
                p = P.get("v4:" + x["topics"][1])
                if not p:
                    continue
                dl = i256(x["data"][2 + 128:2 + 192]); bn = int(x["blockNumber"], 16)
                if dl > 0:
                    p["add"] += dl; p.setdefault("add_bn", bn); p.setdefault("add_tx", x["transactionHash"])
                elif dl < 0 and bn - p["bn"] <= pull_blocks:
                    p["rem"] -= dl; p.setdefault("rem_bn", bn)
        for venue, tm, tb in (("v2", T_MINT2, T_BURN2), ("v3", T_MINT3, T_BURN3)):
            if not any(p["venue"] == venue for p in P.values()):
                continue
            for kind, topic in (("mint", tm), ("burn", tb)):
                for x in logs(ch, a, head, [topic]):
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
                        p["rem"] += liq; p["nat_out"] += amt[p["nat"]] / 1e18; p.setdefault("rem_bn", bn)
        # pulled: v4 and v3 by liquidity, v2 by the native side taken out (the LP amount is not in the event)
        rugs = []
        for k, p in P.items():
            if not p["add"] or "rem_bn" not in p:
                continue
            if p["venue"] == "v2":
                ok = p["nat_out"] >= 0.7 * p["nat_in"] > 0
            else:
                ok = p["rem"] >= 0.9 * p["add"]
            if ok:
                p["id"] = k; p["pull_min"] = round((p["rem_bn"] - p.get("add_bn", p["bn"])) * bt / 60, 1); rugs.append(p)

        def launch(p):
            try:
                t = V.rpc(url, "eth_getTransactionByHash", [p.get("add_tx") or p["tx"]], tries=3)
                p["frm"] = t["from"].lower(); p["to"] = (t.get("to") or "").lower()
                if p["venue"] == "v4" and p.get("native_eth"):
                    p["nat_in"] = int(t["value"], 16) / 1e18
            except Exception:
                p["frm"] = p["to"] = None
            return p
        with cf.ThreadPoolExecutor(4) as ex:
            rugs = list(ex.map(launch, rugs[:2500]))
        res.update(n_created=len(P), n_v4=sum(p["venue"] == "v4" for p in P.values()), n_v2=sum(p["venue"] == "v2" for p in P.values()),
                   n_v3=sum(p["venue"] == "v3" for p in P.values()), rugs=rugs)
        return ch, res
    except Exception as e:
        return ch, {"error": str(e)[:200]}


def sig3(x):
    return float(f"{x:.3g}") if x else 0.0


def lines(rugs):
    g = collections.defaultdict(list)
    for p in rugs:
        shape = f"{p['venue']} fee {p.get('fee', '-')} ts {p.get('ts', '-')}" + (" hook" if p.get("hooks", ZERO) != ZERO else "")
        g[(shape, sig3(p.get("nat_in") or 0))].append(p)
    by_to = collections.defaultdict(list)
    for p in rugs:
        if p.get("to"):
            by_to[(p["venue"], p["to"])].append(p)
    return g, by_to


def show(ch, r, top=8):
    if "error" in r:
        print(f"{ch:10s} ERROR {r['error']}", flush=True); return
    R = r["rugs"]
    print(f"{ch:10s} native pools created {r['n_created']} (v4 {r['n_v4']}, v2 {r['n_v2']}, v3 {r['n_v3']}) | pulled within {PULL_H:g} h: {len(R)}"
          + ("" if ch in WNATIVE else f" | wrapped native taken as {r['wnative']} {r['top_tokens']}"), flush=True)
    g, by_to = lines(R)
    rows = sorted(g.items(), key=lambda kv: -len(kv[1]))[:top]
    for (shape, size), ps in rows:
        if len(ps) < 3:
            break
        print(f"    {len(ps):4d} x {size:<10g} {shape:26s} launchers {len({p.get('frm') for p in ps}):4d} | pull median {st.median(p['pull_min'] for p in ps):5.1f} min"
              f" | via {collections.Counter(p.get('to') for p in ps).most_common(1)[0][0] or '-'}", flush=True)
    for (venue, to), ps in sorted(by_to.items(), key=lambda kv: -len(kv[1]))[:4]:
        if len(ps) < 5:
            break
        sizes = sorted(p.get("nat_in") or 0 for p in ps)
        print(f"    target {to} ({venue}): {len(ps)} pulls, launchers {len({p.get('frm') for p in ps})}, native in {sizes[0]:.4g}-{sizes[-1]:.4g}"
              f" (median {st.median(sizes):.4g}), pull median {st.median(p['pull_min'] for p in ps):.1f} min", flush=True)


def main(hours, out, chains):
    chains = chains or list(EP)
    res = {}
    with cf.ThreadPoolExecutor(10) as ex:
        futs = {ex.submit(one, c, hours): c for c in chains}
        for f in cf.as_completed(futs):
            ch, r = f.result(); res[ch] = r; show(ch, r)
            json.dump({"hours": hours, "pull_h": PULL_H, "t": int(time.time()), "chains": res}, open(out, "w"))
    print("done ->", out, flush=True)


if __name__ == "__main__":
    main(float(sys.argv[1]), sys.argv[2], sys.argv[3:])
