"""B04: are wallets 0xe62d605b and 0xb93262d3 the line or another launcher? For every 13ead562 launch of the b01 window: the token's code
hash and size (eth_getCode), the launch tx's type and gas fields, the launch nonce, the pool share of the supply (mint amount / (mint + dEaD)),
the mint offset and range, the own-buy route; grouped by token code hash. Public RPC, read-only. -> b04_identity.out"""
from collections import Counter, defaultdict
from bc import *
M, RR = load(); TH = M["t_head"]
CC = Cache("b04_code"); TX = Cache("b01_tx"); TX2 = Cache("b02_tx")
need = [r["token"] for r in RR if r["token"] not in CC]
for i in range(0, len(need), 20):
    ch = need[i:i + 20]; res = R.batch("eth_getCode", [[a, "latest"] for a in ch], n=20)
    for a, c in zip(ch, res): CC.put(a, [keccak(bytes.fromhex(c[2:])).hex()[:12], (len(c) - 2) // 2])
D = json.load(open(p("b01_launches.json"))); LT = {x["pool"]: x["launch_tx"] for x in D["launches"]}
full = {}
for r in RR:   # launch tx gas fields (b01_tx has the slim tx; refetch the 85 full launch txs once for gasPrice / maxFee / type)
    pass
FT = Cache("b04_launchtx")
need = [LT[r["pool"]] for r in RR if LT[r["pool"]] not in FT]
for i in range(0, len(need), 20):
    ch = need[i:i + 20]; res = R.batch("eth_getTransactionByHash", [[h] for h in ch], n=20)
    for h, t in zip(ch, res): FT.put(h, {"type": t.get("type"), "gasPrice": int(t["gasPrice"], 16), "maxFee": int(t["maxFeePerGas"], 16) if t.get("maxFeePerGas") else None,
                                         "prio": int(t["maxPriorityFeePerGas"], 16) if t.get("maxPriorityFeePerGas") else None, "gas": int(t["gas"], 16)})
out = [f"head {M['head']} {ts(TH)}; 13ead562 WETH-side launches {len(RR)}"]
def P(s=""): out.append(s)
grp = defaultdict(list)
for r in RR: grp[tuple(CC[r["token"]])].append(r)
for k, rs in sorted(grp.items(), key=lambda kv: -len(kv[1])):
    P(f"\n=== token code {k[0]} ({k[1]} B): {len(rs)} launches, line shape {sum(r['line'] for r in rs)}, wallets {len(set(r['lw'] for r in rs))}, "
      f"{ts(rs[0]['ts'])} .. {ts(rs[-1]['ts'])}")
    P(f"   fees {Counter(r['fee'] for r in rs).most_common()}; launch tx type/gas {Counter((FT[LT[r['pool']]]['type'], FT[LT[r['pool']]]['gas']) for r in rs).most_common(4)}")
    P(f"   launch nonce {Counter(r['nonce'] for r in rs).most_common(6)}; mint range {Counter((r['mints'][0]['lo'], r['mints'][0]['hi']) if r['mints'] else None for r in rs).most_common(3)}")
    for r in rs[-12:]:
        m = r["mints"][0] if r["mints"] else None
        pool_amt = (m["a1"] if r["qs"] == 0 else m["a0"]) / 1e18 if m else None
        dead = sum(t[2] for t in r["tr"] if t[1] == DEAD) / 1e18
        o = r["own1"]; ft = FT[LT[r["pool"]]]
        P(f"   {r['lb']} {ts(r['ts'])} {r['lw'][:10]} n{r['nonce']} fee {r['fee']} {'LINE' if r['line'] else '-'} type {ft['type']} gasPrice {ft['gasPrice']} gas {ft['gas']} "
          f"mint +{m['off'] if m else '-'} L {m['L'] if m else 0:.4g} pool {pool_amt or 0:.4g} dEaD {dead:.4g} +{r['dead_off']} "
          f"own1 {('+%d %.4f %s:%s/%s type %s' % (o['off'], o['eth'], o.get('to', '?')[:10], o.get('sel'), o.get('len'), o.get('type'))) if o else 'none'}")
open(p("b04_identity.out"), "w").write("\n".join(out) + "\n"); print("\n".join(out)); print(R.STATS)
