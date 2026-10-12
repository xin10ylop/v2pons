"""The small checks behind the report, in one place: (1) the two 752-byte routers (0x65050a9b, 0xfd1b271f): their code differs only by
an embedded 20-byte admin, the admin's owner(), the owners' nonces; (2) the collectors' nonces/balances; (3) whether the router owners,
collectors or the 3.0 launcher's funder appear among the bot's 141 buyer wallets, its launch wallets, or any pool transaction; (4) every
T+10 pull before our first live trade; (5) first/last time of each kind of 0x65050a9b/0xfd1b271f buy ahead of the bot, per day;
(6) the 2.433 line's launch gaps; (7) the gas settings of each kind of buyer."""
import pickle, collections, hashlib
from rpc import call
from xcommon import *
R65 = "0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc"; RFD = "0xfd1b271f235e5230eaee9d914ccb1af495bfb758"
a = call("eth_getCode", [R65, "latest"])[2:]; b = call("eth_getCode", [RFD, "latest"])[2:]
diff = [i // 2 for i in range(0, len(a), 2) if a[i:i + 2] != b[i:i + 2]]
print(f"(1) code bytes {len(a)//2} / {len(b)//2}; differing bytes {len(diff)} (offsets {diff[0]}..{diff[-1]})")
ADMIN = "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"
owners = {}
for name, p in (("0x65050a9b", R65), ("0xfd1b271f", RFD)):
    adm = "0x" + call("eth_getStorageAt", [p, ADMIN, "latest"])[-40:]
    own = "0x" + call("eth_call", [{"to": adm, "data": "0x8da5cb5b"}, "latest"])[-40:]
    owners[name] = own
    print(f"    {name}: admin {adm} (code {(len(call('eth_getCode', [adm, 'latest'])) - 2)//2} bytes), admin owner {own}, owner nonce {int(call('eth_getTransactionCount', [own, 'latest']), 16)}")
col = ["0x544ef4354283261fb9e258247a80d49c86b9f107", "0xe322fc6ddb6b29d110b7f84c728d2d743e904616", "0x488faf521a2d5f16ee55d1335841bb3ba9a0946e"]
for c in col: print(f"(2) collector {c} nonce {int(call('eth_getTransactionCount', [c, 'latest']), 16)} balance {int(call('eth_getBalance', [c, 'latest']), 16)/1e18:.5f}")
D = pickle.load(open("x02_pools.pkl", "rb")); pools = D["pools"]; botw = set(D["botw"])
launchers = set(p["from"].lower() for p in pools)
alleoa = set(s["eoa"] for p in pools for s in p["sw"]) | set(m["eoa"] for p in pools for m in p["ml"])
dw = set(s["eoa"] for p in pools for s in p["sw"] if s["to"] in (R65, RFD))
print(f"(3) wallets calling the two routers: {len(dw)}; of them bot buyer wallets {len(dw & botw)}, launch wallets {len(dw & launchers)}")
for x in list(owners.values()) + col + ["0x8970c56f5be5e1e2896acd68219eae9ae8a3d10d"]:
    print(f"    {x[:12]}: bot wallet {x in botw}, launcher {x in launchers}, in any pool transaction {x in alleoa}")
first_us = min(p["ts"] for p in pools if p["ours"])
print(f"(4) pulls by T+10 before our first live trade ({utc(first_us)}):")
for p in sorted(pools, key=lambda p: p["ts"]):
    if p["ts"] >= first_us or p["T"] is None or p["pull"] is None or p["pull"] - p["T"] > 10: continue
    ah = [s for s in p["sw"] if s["buy"] and s["who"] == "w" and (s["bn"], s["li"]) < p["T_li"]]
    print(f"    {utc(p['ts'])} {p['line']:5s} T {p['T']} pull T+{p['pull']-p['T']}: " + ", ".join(f"+{s['off']} {s['q']/1e18:.6f} {s['eoa'][:10]} via {s['to'][:10]}" for s in ah))
print("(5) buys through the two routers ahead of the bot's first buy: first/last per day")
ev = collections.defaultdict(list)
for p in sorted(pools, key=lambda p: p["ts"]):
    for s in p["sw"]:
        if not s["buy"] or s["to"] not in (R65, RFD) or (p["T_li"] is not None and (s["bn"], s["li"]) > p["T_li"]): continue
        ev[(p["line"], s["to"][:10], "fresh" if (s["nonce"] or 0) <= 1 else "recurring", ">=0.001" if s["q"] >= 1e15 else "<0.001", utc(p["ts"])[:5])].append((p["ts"], s["eoa"][:10], round(s["q"] / 1e18, 6)))
for k, v in sorted(ev.items()):
    print(f"    {k}: n {len(v)}, wallets {len(set(x[1] for x in v))}, first {utc(v[0][0])} {v[0][1:]}, last {utc(v[-1][0])} {v[-1][1:]}")
ts = sorted(p["ts"] for p in pools if p["line"] == "2.433")
print("(6) 2.433 launch gaps over 1 h:", [(utc(x), utc(y), round((y - x) / 3600, 1)) for x, y in zip(ts, ts[1:]) if y - x > 3600])
fp = collections.defaultdict(collections.Counter)
for p in pools:
    for s in p["sw"]:
        if not s["buy"] or not s["has_tx"] or s["off"] > 400: continue
        k = "bot" if s["who"] == "bot" else "ours" if s["who"] == "ours" else "0x65050a9b" if s["to"] == R65 else "0xfd1b271f" if s["to"] == RFD else "Universal Router" if s["to"] == UR else "other"
        fp[k][("legacy" if s["tip"] is None else f"tip {s['tip']/1e9:.4f}", round(s["gp"] / 1e9, 3))] += 1
print("(7) buyers' gas settings (tx type / tip gwei, gasPrice gwei): top 3 each")
for k, c in fp.items(): print(f"    {k}: {c.most_common(3)} (n {sum(c.values())})")
