"""When were the 2.433 operator's keys last active on Ethereum, Base and BSC? Nonce of the 31 buyer wallets, the hub, the mainnet launch
wallet 0x8b499c5a and the operator's exchange deposit address 0x31c8cf1c at several past dates (public archive endpoints, Blast) and now."""
import sys, json, time, datetime
sys.path.insert(0, "/home/user/v2pons/research/session_oct14/find2433/trail")
import xrpc
from common import HUB
BUY = sorted(json.load(open("/home/user/v2pons/research/session_oct12/v2433/wallets/w05_buyers_now.json")).keys()) if False else None
import re
BUY = []
for line in open("/home/user/v2pons/research/session_oct12/v2433/wallets/w05_hub_inflows.out"):
    m = re.search(r"to (0x[0-9a-f]{40}) -> " + HUB + r" [0-9.e-]+ nonce (\d+)", line)
    if m and int(m.group(2)) > 1000 and m.group(1) not in BUY: BUY.append(m.group(1))
print("buyers", len(BUY))
EXTRA = [HUB, "0x8b499c5a56d5d0bed60527463bb1de389d6327e1", "0x31c8cf1c5edf64777d70727a92a6f46b6b794664"]
ARCH = {"ethereum": ("eth_archive", 12.0), "base": ("base_archive", 2.0), "bsc": ("bsc_archive", 0.75)}
def call(c, m, p):
    for i in range(10):
        try: time.sleep(0.6); return xrpc.call(c, m, p)
        except RuntimeError as e:
            if "429" in str(e) or "rate" in str(e).lower(): time.sleep(5 * (i + 1)); continue
            raise
def block_at(c, t):
    h = int(call(c, "eth_blockNumber", []), 16); th = int(call(c, "eth_getBlockByNumber", [hex(h), False])["timestamp"], 16)
    b = h - int((th - t) / ARCH_BT[c])
    for _ in range(3):
        tb = int(call(c, "eth_getBlockByNumber", [hex(b), False])["timestamp"], 16)
        b = b - int((tb - t) / ARCH_BT[c])
    return b, h
ARCH_BT = {v[0]: v[1] for v in ARCH.values()}
dates = [("Oct 01", 1790812800), ("Oct 08", 1791417600), ("Oct 11 00:00", 1791676800), ("Oct 12 02:13", 1791771180), ("Oct 12 14:00", 1791813600), ("Oct 13 12:00", 1791892800)]
out = {}
for chain, (c, bt) in ARCH.items():
    cols = []
    for nm, t in dates:
        b, h = block_at(c, t); cols.append((nm, b))
    cols.append(("now", h))
    res = {}
    for a in BUY + EXTRA:
        res[a] = [int(x, 16) if x else None for x in xrpc.batch(c, "eth_getTransactionCount", [[a, hex(b)] for _, b in cols], n=10)]
    out[chain] = {"cols": cols, "nonces": res}
    tot = [sum(res[a][i] or 0 for a in BUY) for i in range(len(cols))]
    print(chain, "buyers' total nonce at", [(nm, n) for (nm, _), n in zip(cols, tot)], flush=True)
    for a in EXTRA: print("   ", a, [(nm, n) for (nm, _), n in zip(cols, res[a])], flush=True)
json.dump(out, open("/home/user/v2pons/research/session_oct14/find2433/trail/t20_buyers_when.json", "w"))
