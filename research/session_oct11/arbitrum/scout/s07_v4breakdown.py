"""decode the 7-day v4 Initialize events, group by quote asset and by launch shape (to:selector:len:fee:ts:value), look for the vbot fingerprint"""
import sys, json, collections, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/scout")
from rpc1 import rpc, post, LOG
from eth_utils import keccak
U = "https://arb1.arbitrum.io/rpc"
WETH = "0x82af49447d8a07e3bd95bd0d56f35241523fbab1"; USDC = "0xaf88d065e77c8cc2239327c5edb3a432268e5831"
USDCe = "0xff970a61a04b1ca14834a43f5de4533ebddb5cc8"; USDT = "0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9"; ZERO = "0x" + "0"*40
ARB = "0x912ce59144191c1204e64559fe8253a0e49e6548"
QUOTES = {ZERO: "ETH", WETH: "WETH", USDC: "USDC", USDCe: "USDC.e", USDT: "USDT"}
W = lambda d, i: int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
def sgn(x): return x - (1 << 256) if x >= (1 << 255) else x
A = lambda t: "0x" + t[26:]
dat = json.load(open("/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/scout/cache/launch_logs_7d.json"))
B24 = dat["b24"]
v4 = dat["logs"]["v4"]
pools = []
for l in v4:
    c0, c1 = A(l["topics"][2]), A(l["topics"][3]); d = l["data"]
    q0, q1 = c0 in QUOTES, c1 in QUOTES
    pools.append({"pid": l["topics"][1], "c0": c0, "c1": c1, "q0": q0, "q1": q1, "fee": W(d, 0), "ts": sgn(W(d, 1)),
                  "hooks": A("0x" + d[2 + 64*2: 2 + 64*3]), "bn": l["bn"], "tx": l["tx"]})
print("v4 Initialize 7d:", len(pools))
qc = collections.Counter()
for p in pools:
    if p["q0"] and p["q1"]: qc["quote-pair"] += 1
    elif p["q0"]: qc[QUOTES[p["c0"]]] += 1
    elif p["q1"]: qc[QUOTES[p["c1"]]] += 1
    else: qc["other/non-quote"] += 1
print("by quote (7d):", dict(qc))
qc24 = collections.Counter()
for p in pools:
    if p["bn"] < B24: continue
    if p["q0"] and p["q1"]: qc24["quote-pair"] += 1
    elif p["q0"]: qc24[QUOTES[p["c0"]]] += 1
    elif p["q1"]: qc24[QUOTES[p["c1"]]] += 1
    else: qc24["other"] += 1
print("by quote (24h):", dict(qc24))
hc = collections.Counter(p["hooks"] for p in pools); print("hooks top:", hc.most_common(6))
feec = collections.Counter((p["fee"], p["ts"]) for p in pools); print("fee/ts top:", feec.most_common(8))
# fetch launch txs (dedup) to read selector/length/value
txs = list(dict.fromkeys(p["tx"] for p in pools))
print("distinct launch txs:", len(txs))
tmap = {}
for i in range(0, len(txs), 50):
    ch = txs[i:i+50]
    r = post(U, [{"jsonrpc":"2.0","id":j,"method":"eth_getTransactionByHash","params":[h]} for j,h in enumerate(ch)])
    for x in r:
        t = x.get("result")
        if t: tmap[t["hash"]] = t
print("launch txs fetched:", len(tmap))
shapes = collections.Counter(); shape24 = collections.Counter()
for p in pools:
    t = tmap.get(p["tx"])
    if not t: continue
    inp = t.get("input") or "0x"; n = (len(inp)-2)//2; val = int(t.get("value") or "0x0", 16)
    to = (t.get("to") or "").lower(); sel = inp[2:10]
    key = (to, sel, n, p["fee"], p["ts"], round(val/1e18, 7))
    shapes[key] += 1
    if p["bn"] >= B24: shape24[key] += 1
print("\n=== top launch shapes (7d) [to, selector, calldata_len, fee, ts, value_eth] ===")
for k, c in shapes.most_common(20):
    print(f"  n={c:4d} 24h={shape24.get(k,0):3d}  to={k[0]} sel={k[1]} len={k[2]} fee={k[3]} ts={k[4]} val={k[5]}")
# vbot fingerprint search: 1444-byte multicall with those values
VB = {2.4333285, 3.0, 5.0}
vb = [p for p in pools if (lambda t: t and ((len(((t.get('input') or '0x')))-2)//2)==1444 and round(int(t.get('value') or '0x0',16)/1e18,7) in VB)(tmap.get(p["tx"]))]
print("\nvbot-shape (1444 bytes, value in {2.4333285,3.0,5.0}) 7d:", len(vb))
# also any 1444-byte multicall regardless of value
mc = [p for p in pools if (lambda t: t and (t.get('input') or '0x')[2:10]=='ac9650d8')(tmap.get(p["tx"]))]
print("multicall ac9650d8 launches 7d:", len(mc), "of which 1444 bytes:", sum(1 for p in mc if ((len((tmap[p['tx']].get('input') or '0x'))-2)//2)==1444))
lens = collections.Counter(((len((tmap[p['tx']].get('input') or '0x'))-2)//2) for p in mc)
print("multicall calldata lengths:", lens.most_common(10))
json.dump({"by_quote_7d": dict(qc), "by_quote_24h": dict(qc24), "shapes": [[list(k), c, shape24.get(k,0)] for k,c in shapes.most_common(40)]},
          open("/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/arb/scout/s07_v4breakdown.json","w"), indent=1)
print("requests", len(LOG), "non-ok", [x for x in LOG if x[1] != "ok"])
