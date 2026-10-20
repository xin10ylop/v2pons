"""k01: nonce and balance of the operator's known keys on many chains, now; run twice to see who is moving where.
usage: python3 k01_snapshot.py TAG"""
import json, sys, time
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import xr
SRC = "/home/user/v2pons/research/session_oct14/find2433/chains/"
d = json.load(open(SRC + "c16_rh_wallets_xchain.json"))
buyers = [a for a, n, b in d["buyers_bsc"]]
L = json.load(open(SRC + "c18_launches.json"))
bsclaunch = sorted({x["from"] for x in L})
keys = {"admin_0152": ["0x0152c954397718abfe4716eb3aaf86903cff3796"], "admin_5b2b": ["0x5b2b20e15e96b015908a323ddbaee4aa25b04f4d"],
        "hub_6c3b": ["0x6c3bd8f6fbca130f95305e9fa5a37d1dbf31622d"], "next_8b49": ["0x8b499c5a56d5d0bed60527463bb1de389d6327e1"],
        "consol_31c8": ["0x31c8cf1c5edf64777d70727a92a6f46b6b794664"], "buyers31": buyers, "bsc_v4_launch52": bsclaunch}
chains = sys.argv[2].split(",") if len(sys.argv) > 2 else ["bsc", "base", "eth", "arb", "uni", "op", "polygon", "hyper", "rh", "avax", "sonic", "linea"]
out = {"t": time.time(), "heads": {}, "keys": {}}
for ch in chains:
    try:
        out["heads"][ch] = xr.head(ch)
        for grp, addrs in keys.items():
            ns = xr.batch(ch, "eth_getTransactionCount", [[a, "latest"] for a in addrs], n=20)
            bs = xr.batch(ch, "eth_getBalance", [[a, "latest"] for a in addrs], n=20)
            out["keys"].setdefault(ch, {})[grp] = [[a, int(n, 16), int(b, 16) / 1e18] for a, n, b in zip(addrs, ns, bs)]
        print(ch, "ok", {g: sum(x[1] for x in v) for g, v in out["keys"][ch].items()}, flush=True)
    except Exception as e:
        print(ch, "ERR", str(e)[:200], flush=True)
json.dump(out, open(f"k01_snap_{sys.argv[1]}.json", "w"))
