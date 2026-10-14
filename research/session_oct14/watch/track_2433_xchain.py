"""The 2.433 operator across chains (research/session_oct14/find2433/REPORT_FIND2433.md): its router admin, hub, next launch wallet,
Binance-bound consolidation key, its 31 bot-buyer wallets and the 52 BNB launch wallets, on BNB Chain, Ethereum, Base, HyperEVM and
Robinhood. Each run reads nonces and balances (public endpoints, read-only), compares them with the last run (track_2433_xchain.json)
and prints what moved: a rising nonce of the buyer wallets means the line is trading again somewhere.
usage: python3 research/session_oct14/watch/track_2433_xchain.py [--dry]"""
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); STATE = os.path.join(HERE, "track_2433_xchain.json")
sys.path.insert(0, "/home/user/v2pons/research/session_oct14/find2433/skeptic")
import xr
SRC = "/home/user/v2pons/research/session_oct14/find2433/chains/"
buyers = [a for a, n, b in json.load(open(SRC + "c16_rh_wallets_xchain.json"))["buyers_bsc"]]
launch52 = sorted({x["from"] for x in json.load(open(SRC + "c18_launches.json"))})
KEYS = {"admin_0152": ["0x0152c954397718abfe4716eb3aaf86903cff3796"], "admin_5b2b": ["0x5b2b20e15e96b015908a323ddbaee4aa25b04f4d"],
        "hub_6c3b": ["0x6c3bd8f6fbca130f95305e9fa5a37d1dbf31622d"], "next_8b49": ["0x8b499c5a56d5d0bed60527463bb1de389d6327e1"],
        "consol_31c8": ["0x31c8cf1c5edf64777d70727a92a6f46b6b794664"], "buyers31": buyers, "bsc_launch52": launch52}
CHAINS = ["bsc", "eth", "base", "hyper", "rh"]
now = {"t": time.time(), "chains": {}}
for ch in CHAINS:
    try:
        row = {}
        for g, addrs in KEYS.items():
            ns = xr.batch(ch, "eth_getTransactionCount", [[a, "latest"] for a in addrs], n=20)
            bs = xr.batch(ch, "eth_getBalance", [[a, "latest"] for a in addrs], n=20)
            row[g] = {"nonce": sum(int(n, 16) for n in ns), "bal": sum(int(b, 16) for b in bs) / 1e18}
        now["chains"][ch] = row
    except Exception as e:
        print(ch, "could not be read:", str(e)[:120])
old = json.load(open(STATE)) if os.path.exists(STATE) else None
print("the 2.433 operator's keys, %s UTC (nonce sum / balance):" % time.strftime("%m-%d %H:%M", time.gmtime(now["t"])))
moved = []
for ch, row in now["chains"].items():
    print("  %-5s " % ch + "  ".join("%s %d/%.3f" % (g, v["nonce"], v["bal"]) for g, v in row.items()))
    for g, v in row.items():
        o = ((old or {}).get("chains", {}).get(ch) or {}).get(g)
        if o and (v["nonce"] != o["nonce"] or abs(v["bal"] - o["bal"]) > 0.005):
            moved.append("  MOVED %s %s: nonce %d -> %d, balance %.4f -> %.4f" % (ch, g, o["nonce"], v["nonce"], o["bal"], v["bal"]))
if old is None: print("  first run: state saved")
elif moved: print("SINCE %s UTC:" % time.strftime("%m-%d %H:%M", time.gmtime(old["t"]))); print("\n".join(moved))
else: print("  nothing moved since %s UTC" % time.strftime("%m-%d %H:%M", time.gmtime(old["t"])))
if "--dry" not in sys.argv: json.dump(now, open(STATE, "w"), indent=0)
