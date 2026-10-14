"""The 2.433 operator's five Base pools (b09_census.out), event by event: every ModifyLiquidity and Swap from the launch to the pull,
with the transaction behind each (from, to, selector, value), the actor (the operator's wallets or an OUTSIDER), and for every bot
buy through 0x987d5db8 its calldata minOut against the tokens it got (the bot's price tolerance). Answers, per pool: the Swap event's
`sender` for the bot's buys and sells, the add's offset/ETH/liquidity, the bot's first-buy offset, the pull's offset, the outsiders
and how fast the pull followed them. Tenderly's public Base gateway (old blocks), read-only. Writes b10_pools.json for b11_room.py.
usage: python3 b10_pools.py"""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/home/user/v2pons/research/session_oct14/find2433/skeptic"); import xr
xr.EP["base_t"] = "https://base.gateway.tenderly.co"; xr.PACE["base_t"] = 0.25
from eth_utils import keccak
PM = "0x498581ff718922c3f8e6a244956af099b2652b2b"; BOT = "0x987d5db84d105c1f49391af409cc34c6050fb1d0"; UR = "0x6ff5693b99212da76ad316178a184ab56d299b43"
T_SWAP = "0x" + keccak(text="Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)").hex()
T_ML = "0x" + keccak(text="ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)").hex()
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
sgn = lambda x: x - (1 << 256) if x >= (1 << 255) else x
s128 = lambda x: x - (1 << 128) if x >= (1 << 127) else x
SRC = "/home/user/v2pons/research/session_oct14/find2433/chains/c16_rh_wallets_xchain.json"
buyers = {a.lower() for a, n, b in json.load(open(SRC))["buyers_bsc"]}
COLLECT = "0x8f79d153630b327cc84487804f152972cce93cb4"
POOLS = [  # launch block, pool id, token, hook, launch wallet, sqrtPriceX96 at init, tick (b09_census.out)
    (52590492, "0x4719b41bba4b7db657edc0b97bf5672690467da63d72d54f82ef099233acd820", "0xbe07c8c3cadd6f601684ef708573215d230ea777", "0x0a37fce6d240d416bc5955173c9a6c1af586c080", "0x4d40df2e5fb79b8b4cfc03ca9451a3462e813084", 6854619590099208105460076086768381, 227373),
    (52590658, "0x722c5de4d74abd40035dea417fb421aed5e4d1258221c05c413b80a1091acc19", "0xccc17382f57e463928ab29f8d4006b94ae3de777", "0x9e3653bb4ad13ba5d8a6d9f4bd8ae475a109c080", "0x505b452dc968ff72aade79fcd87fd31552d212e3", 6854619590099208105460076086768381, 227373),
    (52590807, "0x3085339d7dfb63848c153b4ada18662659f3f6ba287e5e5df4549b6d8ddbb16d", "0x3a73002fcad288a2ce1aff82fad49229b060a777", "0x1c888901220490eb5a1dc0a0e8ee106616c28080", "0x72d0cac5017dd7e2bcf3cfbde9079eae796c163c", 1713625778466099769665432700006961, 199645),
    (52592240, "0xb41ad027e2b4eeee991dec24dbb84199aeaef093b5aa4e37b4c5eae8bbba3efa", "0x86a7f72b5a93667aba76331de2d41d6c356ed777", "0xc7a81a2a9f1ca471f9adf5b2d9aae19656ce8080", COLLECT, 1713625778466099769665432700006961, 199645),
    (52592379, "0x909c1fdac64d5e8907c2e298f1b07302ac9d2b724edeed7a1c21472b6838d820", "0xcff4d5a446438b717ce88167712b8ede39361777", "0x48b80af6df394a425aaefc59ba1c53088fc24080", "0x78f4b6cc88490151cd2622506aff74863d12e637", 1713625778466099769665432700006961, 199645),
]
OPERATOR = buyers | {COLLECT, "0x78f4b6cc88490151cd2622506aff74863d12e637"} | {p[4] for p in POOLS}
out = {}
for L, pid, token, hook, wallet, sqrt0, tick0 in POOLS:
    print(f"\n=== launch {L} pool {pid[:10]} token {token[:10]} hook {hook[:10]} wallet {wallet[:10]}")
    logs = xr.call("base_t", "eth_getLogs", [{"fromBlock": hex(L), "toBlock": hex(L + 800), "address": PM, "topics": [[T_ML, T_SWAP], pid]}])
    hashes = sorted({l["transactionHash"] for l in logs})
    txs = dict(zip(hashes, xr.batch("base_t", "eth_getTransactionByHash", [[h] for h in hashes], n=10)))
    rows = []; senders_buy = {}; senders_sell = {}; adds = []; pull = None; first_bot = None; outsiders = []
    for l in sorted(logs, key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16))):
        b = int(l["blockNumber"], 16) - L; tx = txs[l["transactionHash"]] or {}
        frm = (tx.get("from") or "").lower(); to = (tx.get("to") or "").lower(); inp = tx.get("input") or "0x"; sel = inp[:10]; val = int(tx.get("value", "0x0"), 16)
        actor = "bot" if frm in OPERATOR else "OUTSIDER"
        sender = "0x" + l["topics"][2][-40:]
        d = l["data"]
        if l["topics"][0] == T_ML:
            lo, hi, delta = sgn(W(d, 0)), sgn(W(d, 1)), sgn(W(d, 2))
            kind = "add" if delta > 0 else "PULL"
            if delta > 0: adds.append({"off": b, "lo": lo, "hi": hi, "delta": delta, "eth": val, "tx": l["transactionHash"], "sender": sender})
            elif pull is None: pull = {"off": b, "delta": delta, "tx": l["transactionHash"], "from": frm, "to": to, "sel": sel}
            print(f"  +{b:<3} ML {kind:4} delta {delta:>28} ticks {lo}..{hi} sender {sender[:10]} tx from {frm[:10]} ({actor}) to {to[:10]} {sel} val {val / 1e18:.6f}")
            rows.append({"off": b, "idx": int(tx.get("transactionIndex", "0x0"), 16), "kind": kind, "delta": delta, "lo": lo, "hi": hi, "from": frm, "to": to, "sel": sel, "value": val, "tx": l["transactionHash"]})
        else:
            a0, a1 = sgn(W(d, 0)), sgn(W(d, 1)); sp, liq = W(d, 2), W(d, 3)        # int128, sign-extended to the 32-byte word
            kind = "BUY" if a0 < 0 else "sell"
            tol = None
            if kind == "BUY" and to == BOT and sel == "0x27f7e6ee":
                words = [int(inp[10 + 64 * k: 74 + 64 * k], 16) for k in range((len(inp) - 10) // 64)]
                min_out = words[9]; tol = min_out / a1 if a1 else None
                if first_bot is None and actor == "bot": first_bot = {"off": b, "eth": -a0, "tokens": a1, "min_out": min_out, "tol": tol, "tx": l["transactionHash"], "sender": sender, "sqrt_after": sp, "liq": liq, "idx": int(tx.get("transactionIndex", "0x0"), 16)}
            (senders_buy if kind == "BUY" else senders_sell).setdefault(actor, {}).setdefault(sender, 0)
            (senders_buy if kind == "BUY" else senders_sell)[actor][sender] += 1
            if actor == "OUTSIDER": outsiders.append({"off": b, "kind": kind, "eth": -a0 if kind == "BUY" else a0, "from": frm, "to": to, "sel": sel, "tx": l["transactionHash"]})
            print(f"  +{b:<3} {kind:4} a0 {a0 / 1e18:+.6f} ETH a1 {a1:+.6g} sender {sender[:10]} tx from {frm[:10]} ({actor}) to {to[:10]} {sel} val {val / 1e18:.4f}" + (f"  minOut/out {tol:.4f}" if tol else ""))
            rows.append({"off": b, "idx": int(tx.get("transactionIndex", "0x0"), 16), "kind": kind, "a0": a0, "a1": a1, "sqrt_after": sp, "liq_after": liq, "from": frm, "to": to, "sel": sel, "value": val, "actor": actor, "tx": l["transactionHash"],
                         "min_out": (int(inp[10 + 64 * 9: 74 + 64 * 9], 16) if (to == BOT and sel == "0x27f7e6ee" and len(inp) >= 74 + 64 * 9) else None)})
    liq_active = sum(a["delta"] for a in adds if a["lo"] < tick0 <= a["hi"])
    print(f"  summary: adds {[(a['off'], round(a['eth'] / 1e18, 4)) for a in adds]} active liquidity at tick {tick0}: {liq_active}; first bot buy {first_bot and (first_bot['off'], round(first_bot['eth'] / 1e18, 4), round(first_bot['tol'], 4))}; pull {pull and (pull['off'], pull['sel'], pull['to'][:10])}")
    print(f"  Swap sender, buys: {senders_buy}; sells: {senders_sell}")
    print(f"  outsiders: {len(outsiders)}: {[(o['off'], o['kind'], round(o['eth'] / 1e18, 5), o['from'][:10]) for o in outsiders]}"
          + (f"; first outsider buy at +{min(o['off'] for o in outsiders if o['kind'] == 'BUY')}, pull {pull['off'] - min(o['off'] for o in outsiders if o['kind'] == 'BUY')} blocks later" if pull and any(o['kind'] == 'BUY' for o in outsiders) else ""))
    out[str(L)] = {"pid": pid, "token": token, "hook": hook, "wallet": wallet, "sqrt0": sqrt0, "tick0": tick0, "adds": adds, "liq_active": liq_active, "first_bot": first_bot, "pull": pull, "rows": rows, "outsiders": outsiders,
                   "senders_buy": senders_buy, "senders_sell": senders_sell}
json.dump(out, open(os.path.join(HERE, "b10_pools.json"), "w"))
print(f"\nrequests: {xr.STATS}; wrote b10_pools.json")
