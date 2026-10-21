#!/usr/bin/env python3
"""watch2433.py [--hours 1]: has the 2.433 operator moved in the last HOURS? Stateless (no file between runs), read-only, public endpoints.

  1. Its wallets (the 31 bot buyers, the 10 more BNB fleet wallets, its admins, hub, next-launch, consolidation, the Base collector and the
     BNB sweep wallet that holds its 26.65 BNB) on BNB, Base and Ethereum: the nonce now against HOURS ago (archive reads), and the sweep
     wallet's balance now against HOURS ago.
  2. Robinhood (no public archive): the same wallets' nonces against the Oct 21 baseline (the line stopped there Oct 12); any rise is news.
  3. Its fingerprint on BNB: Uniswap v4 pools initialized native/token with fee 5000, tick spacing 100 and no hook in the last HOURS, and
     how many were launched with 10.4-10.7 BNB (its Oct 15-19 line: 10.5333 BNB, ~$6,300). The same fingerprint on Base (fee 5000, tick
     spacing 100, no hook, native): the pools and their launch values.
  4. Its key wallets on 23 other EVM chains against their Oct 21 nonces (OTHER_BASELINE: only the consolidation wallet had ever sent
     anything there, 11 transactions on Arbitrum and 1 on Optimism, all older than 30 days).

Prints one line per check; exit code 10 when anything moved (the lines start with "MOVED" or "NEW"), 0 when quiet, 2 when a check could not
be read (the line says which). research/chase/REPORT_OCT21.md has the background."""
import json, sys, time, urllib.request, concurrent.futures as cf

HOURS = float(sys.argv[sys.argv.index("--hours") + 1]) if "--hours" in sys.argv else 1.0
BUYERS31 = ["0x020a1015916c3faf296ce9c28ad7a1eb51d5d00c", "0x033258a16c137c8de553e8c3e07442c13d73cf60", "0x039475670b67126f91a7de3729d56c5b40c75eb0",
            "0x1376af7e961ee8e0840e62e5e0c55965531ca61f", "0x1e5ad030322862b4cfb609be0580c64fe72b5c9b", "0x31335015d24c4ba8faf974e6b6400268d21d658f",
            "0x324c82de93a022be0fb3f5c8cafb022d4f277153", "0x3c1b65ed8cb98866dabc5489b04e266b747c5ec0", "0x4180672adc800d66237917f21444e3f00b7f4114",
            "0x578b7cc30e9389bbb73d600eac69542853c927be", "0x5aed6bc8403ab1d1bb03816600e3206e496281db", "0x5b3f4a2e3426d6257cc5daa0425365b572ba9c1b",
            "0x7e0bef2c74efbefc62e5e19b821ad284c5b66e94", "0x7f4d15e9a79d777a43b54244af6ee66a3977a9af", "0x80837e53f97992d35e18e1f7fbe9bc68cfd8521d",
            "0x8755d81e215993e81690150edbbb01c4d2cc8ead", "0x8cd2a79c8c83d18e5b1a0a66a955188f538b0460", "0x8eb4bbe5bc255a8afe39670208a5ef37bc6a054c",
            "0x943bfd27181ac2e399c68a0b72c3d6bc0a273e71", "0xb1c867cbb39fcd346a9b1b5bfac7120340dd4d6a", "0xc13f6774094cfb94a3afec6d09a10333fc9206d0",
            "0xc4e1e81f08ea3ac1a586f9637166aac02562eaf9", "0xc89e901a91c77c0ebab41435ede97d58cc22e376", "0xc9c827ada367118e85712abc958de48f5508de9e",
            "0xcbca9880771ef1e7876e9a510c396e57afb68c24", "0xdf2c6f64308dc7537bca2c4336f464b1c8b92b2f", "0xdf3c7421fc8872b02e031cff6fc4595f3726454e",
            "0xe5ab8b8bb7feacc8ed86aa15fc2a645724f58cd5", "0xecd658c15322ae175ced5d3d6a4a9328943cdae3", "0xf8b3c188f8136ae5b7f44efebab86c9db25980ea",
            "0xfba0e37c02da3446209adef41bcc20b81ed0c04c"]   # its 31 bot buyers (research/session_oct14/find2433/chains/c16_rh_wallets_xchain.json)
KEYS = {"admin_0152": "0x0152c954397718abfe4716eb3aaf86903cff3796", "admin_5b2b": "0x5b2b20e15e96b015908a323ddbaee4aa25b04f4d",
        "hub_6c3b": "0x6c3bd8f6fbca130f95305e9fa5a37d1dbf31622d", "next_8b49": "0x8b499c5a56d5d0bed60527463bb1de389d6327e1",
        "consol_31c8": "0x31c8cf1c5edf64777d70727a92a6f46b6b794664", "collect_8f79": "0x8f79d153630b327cc84487804f152972cce93cb4",
        "sweep_2305": "0x23055b43851c387cce0d659d388a8ed22ebe8e5a"}
FLEET10 = ["0x2d8c5fe56d3df6ba7a2e1a3ba1e7df954342c80b", "0x47db4bc0580d56ca5167db7e0aa63f0441da88f1", "0x53463474f1de355c41cbe4a17d229dcb98ab385c",
           "0x56f8c7301f3db46415047bf681d2ce475ec0ac66", "0x5f0190f108f21a46c8f6249890b80089dd844f61", "0xa2deb9f0339068626db83993f84fef823f648c40",
           "0xaab209e7b308e0c601e9106d9cef1226f93be3ba", "0xd55e8a229943e8f8c20a80e5ee5a4983ae4145a0", "0xec121a88c2e2a6fee94939390fc18d627bfca2d3",
           "0xf7b323ba75ef95a990c0fa07e483cd4b784f4f47"]
EP = {"bsc": ["https://bsc-mainnet.public.blastapi.io", "https://bsc.meowrpc.com"], "bsc_logs": ["https://rpc-bsc.48.club"],
      "base": ["https://gateway.tenderly.co/public/base", "https://base.drpc.org", "https://mainnet.base.org"],
      "eth": ["https://gateway.tenderly.co/public/mainnet", "https://eth.drpc.org"], "rh": ["https://rpc.mainnet.chain.robinhood.com"]}
BLOCK_S = {"bsc": 0.45, "base": 2.0, "eth": 12.0}
RH_BASELINE = {"buyers31": 1223687, "admin_0152": 228, "hub_6c3b": 10, "next_8b49": 8, "consol_31c8": 1, "collect_8f79": 8, "sweep_2305": 6}
OTHER = {"arbitrum": "https://arb1.arbitrum.io/rpc", "optimism": "https://mainnet.optimism.io", "unichain": "https://mainnet.unichain.org",
         "avalanche": "https://api.avax.network/ext/bc/C/rpc", "linea": "https://rpc.linea.build", "sonic": "https://rpc.soniclabs.com",
         "ink": "https://rpc-gel.inkonchain.com", "soneium": "https://rpc.soneium.org", "worldchain": "https://worldchain-mainnet.g.alchemy.com/public",
         "blast": "https://rpc.blast.io", "mode": "https://mainnet.mode.network", "zora": "https://rpc.zora.energy", "celo": "https://forno.celo.org",
         "gnosis": "https://rpc.gnosischain.com", "opbnb": "https://opbnb-mainnet-rpc.bnbchain.org", "mantle": "https://rpc.mantle.xyz",
         "scroll": "https://rpc.scroll.io", "berachain": "https://rpc.berachain.com", "abstract": "https://api.mainnet.abs.xyz",
         "monad": "https://rpc.monad.xyz", "sei": "https://evm-rpc.sei-apis.com", "plasma": "https://rpc.plasma.to", "katana": "https://rpc.katana.network"}
OTHER_BASELINE = {"arbitrum": {"consol_31c8": 11}, "optimism": {"consol_31c8": 1}}
PM = {"bsc": "0x28e2ea090877bf75740558f6bfb36a5ffee9e9df", "base": "0x498581ff718922c3f8e6a244956af099b2652b2b"}
T_INIT = "0xdd466e674ea557f56295e2d0218a125ea4b4f0f6f3307b95f85e6110838d6438"   # Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)
moved, failed = [], []


def call(urls, m, p, tries=6):
    err = None
    for i in range(tries):
        u = urls[i % len(urls)]
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(u, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(),
                                                                        {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}), timeout=20))
            if r.get("result") is not None:
                return r["result"]
            err = r.get("error")
        except Exception as e:
            err = e
        time.sleep(0.6 * (i + 1))
    raise RuntimeError(f"{m} on {urls[0].split('/')[2]}: {str(err)[:80]}")


def say(line, flag=None):
    print(line, flush=True)
    if flag == "moved":
        moved.append(line)
    elif flag == "failed":
        failed.append(line)


def wallets_check(ch):
    """nonce sums now vs HOURS ago, per group; the sweep wallet's balance on BNB"""
    try:
        head = int(call(EP[ch], "eth_blockNumber", []), 16); then = head - int(HOURS * 3600 / BLOCK_S[ch])
        groups = {"buyers31": BUYERS31, "fleet10": FLEET10 if ch == "bsc" else [], **{k: [a] for k, a in KEYS.items()}}
        def nonce(a, b):
            return int(call(EP[ch], "eth_getTransactionCount", [a, hex(b)]), 16)
        out = []
        with cf.ThreadPoolExecutor(4) as ex:
            for g, addrs in groups.items():
                if not addrs:
                    continue
                now = sum(ex.map(lambda a: nonce(a, head), addrs)); before = sum(ex.map(lambda a: nonce(a, then), addrs))
                out.append((g, before, now))
        for g, before, now in out:
            if now != before:
                say(f"MOVED {ch} {g}: {now - before:+d} transactions in the last {HOURS:g} h (nonce sum {before} -> {now})", "moved")
        if ch == "bsc":
            bal = lambda b: int(call(EP[ch], "eth_getBalance", [KEYS["sweep_2305"], hex(b)]), 16) / 1e18
            b0, b1 = bal(then), bal(head)
            if abs(b1 - b0) > 0.001:
                say(f"MOVED bsc sweep_2305 balance: {b0:.4f} -> {b1:.4f} BNB in the last {HOURS:g} h (its parked money)", "moved")
            else:
                say(f"quiet bsc: no wallet moved in {HOURS:g} h; the sweep wallet still holds {b1:.4f} BNB")
        elif not any(now != before for g, before, now in out):
            say(f"quiet {ch}: no wallet moved in {HOURS:g} h")
    except Exception as e:
        say(f"FAILED {ch} wallets: {e}", "failed")


def rh_check():
    try:
        with cf.ThreadPoolExecutor(4) as ex:
            buyers = sum(ex.map(lambda a: int(call(EP["rh"], "eth_getTransactionCount", [a, "latest"]), 16), BUYERS31))
            keys = {k: int(call(EP["rh"], "eth_getTransactionCount", [a, "latest"]), 16) for k, a in KEYS.items()}
        rose = [f"{k} {RH_BASELINE.get(k, 0)} -> {v}" for k, v in {"buyers31": buyers, **keys}.items() if v > RH_BASELINE.get(k, 0)]
        if rose:
            say("MOVED robinhood since the Oct 21 baseline: " + ", ".join(rose), "moved")
        else:
            say("quiet robinhood: every wallet at its Oct 21 nonce")
    except Exception as e:
        say(f"FAILED robinhood wallets: {e}", "failed")


def fingerprint(ch):
    """fee 5000 / tick spacing 100 / no hook / native pools initialized in the last HOURS, and their launch values"""
    try:
        urls = EP["bsc_logs"] if ch == "bsc" else EP["base"]; step = 2000 if ch == "bsc" else 450
        head = int(call(urls, "eth_blockNumber", []), 16); a0 = head - int(HOURS * 3600 / BLOCK_S[ch])
        hits = []
        for a in range(a0, head + 1, step):
            for l in call(urls, "eth_getLogs", [{"address": PM[ch], "topics": [T_INIT], "fromBlock": hex(a), "toBlock": hex(min(a + step - 1, head))}]):
                d = l["data"][2:]
                if l["topics"][2][-40:] == "0" * 40 and int(d[0:64], 16) == 5000 and int(d[64:128], 16) == 100 and d[152:192] == "0" * 40:
                    hits.append(l["transactionHash"])
        vals = [int(call(urls if ch == "bsc" else EP["base"], "eth_getTransactionByHash", [h])["value"], 16) / 1e18 for h in hits[:40]]
        cur = "BNB" if ch == "bsc" else "ETH"
        if ch == "bsc":
            op = [v for v in vals if 10.4 <= v <= 10.7]
            if op:
                say(f"NEW bsc: {len(op)} pool(s) launched with 10.4-10.7 BNB on its fingerprint in the last {HOURS:g} h (values {sorted(set(round(v, 4) for v in op))})", "moved")
            else:
                say(f"quiet bsc fingerprint: {len(hits)} fee-5000/tick-100 native pools, none at 10.4-10.7 BNB")
        else:
            near = [v for v in vals if 1.3 <= v <= 4.5]
            if near:
                say(f"NEW base: {len(near)} fee-5000/tick-100 native pool(s) launched with 1.3-4.5 ETH in the last {HOURS:g} h (values {sorted(round(v, 4) for v in near)}): check them", "moved")
            else:
                say(f"quiet base fingerprint: {len(hits)} fee-5000/tick-100 native pools, none launched with 1.3-4.5 ETH")
    except Exception as e:
        say(f"FAILED {ch} fingerprint: {e}", "failed")


def other_chains():
    def one(item):
        name, u = item
        try:
            got = {k: int(call([u], "eth_getTransactionCount", [a, "latest"], tries=2), 16) for k, a in KEYS.items()}
            got["buyers31"] = sum(int(call([u], "eth_getTransactionCount", [a, "latest"], tries=2), 16) for a in BUYERS31 + FLEET10)
            base = OTHER_BASELINE.get(name, {})
            return name, {k: (base.get(k, 0), v) for k, v in got.items() if v > base.get(k, 0)}
        except Exception:
            return name, None
    with cf.ThreadPoolExecutor(8) as ex:
        res = dict(ex.map(one, OTHER.items()))
    hot = {k: v for k, v in res.items() if v}
    if hot:
        say("NEW other chains (above the Oct 21 nonces): " + "; ".join(f"{c}: " + ", ".join(f"{k} {b}->{n}" for k, (b, n) in v.items()) for c, v in hot.items()), "moved")
    else:
        say(f"quiet other chains: its keys have sent nothing on {sum(v is not None for v in res.values())} chains"
            + (f" ({', '.join(k for k, v in res.items() if v is None)} unreadable)" if any(v is None for v in res.values()) else ""))


if __name__ == "__main__":
    print(f"watch2433 {time.strftime('%Y-%m-%d %H:%M', time.gmtime())} UTC, the last {HOURS:g} h", flush=True)
    for ch in ("bsc", "base", "eth"):
        wallets_check(ch)
    rh_check()
    fingerprint("bsc"); fingerprint("base")
    other_chains()
    print("RESULT:", "MOVED" if moved else ("INCOMPLETE" if failed else "QUIET"), flush=True)
    sys.exit(10 if moved else 2 if failed else 0)
