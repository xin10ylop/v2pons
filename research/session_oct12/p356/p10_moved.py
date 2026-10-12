"""p10: did the 356-B line move? After the last 356-B launch (block 86094707, Oct 11 19:56:38 UTC): (a) the chain-wide search of p02 for the
launch position's exact range (-887272..207243, any pool) and its L; (b) the fleet's fingerprint (SwapRouter02 exactInputSingle, 228 B, ETH
as value, priority fee 1) on every other V3 WETH pool created since (p01): their Swaps to +600, the txs of buys >= 0.05 ETH through the
router. -> p10_moved.out"""
import sys, os, json, collections as C
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import rpc, common as K
STOP = 86094707
L = []
def P(*a): L.append(" ".join(str(v) for v in a)); print(*a)
fm = [json.loads(l) for l in open(K.J("p02_fpmints.jsonl"))]
X = K.launches(); lp = {x["pool"]: x for x in X}
aft = [l for l in fm if int(l["blockNumber"], 16) > STOP]
P(f"(a) Mints with ticks -887272..207243 after block {STOP}: {len(aft)}; in launches of code 89885b75: {sum(1 for l in aft if l['address'][2:].lower() in lp)}; "
  f"of those value launches: {sum(1 for l in aft if l['address'][2:].lower() in lp and lp[l['address'][2:].lower()]['len'] != 356)}; "
  f"L = 31,622,807,953,636,212,567,716: {sum(1 for l in aft if int(l['data'][2+64:2+128], 16) == K.LINE_L)}")
rows = [json.loads(x) for x in open(K.J("p01_pools.jsonl"))]
tx = {}
for x in open(K.J("p01_txs.jsonl")):
    t = json.loads(x); tx[t["hash"]] = t
code = json.load(open(K.J("p01_code.json")))
oth = [r for r in rows if r["block"] > STOP and K.WETH in (r["token0"], r["token1"]) and r["pool"] not in lp]
P(f"(b) other V3 WETH pools created after the stop: {len(oth)}; by (launcher code, selector): "
  + str(C.Counter(((code.get((tx[r['tx']]['to'] or '').lower(), {}).get('hash') or 'none')[:8], tx[r['tx']]['input'][2:10]) for r in oth).most_common()))
cache = K.J("p10_swaps.json")
if os.path.exists(cache): SW = json.load(open(cache))
else:
    SW = []
    oth.sort(key=lambda r: r["block"]); g = []
    def flush(g):
        ls = rpc.logs({"address": ["0x" + r["pool"] for r in g], "topics": ["0x" + K.T_SWAP]}, g[0]["block"], g[-1]["block"] + 600)
        return [{"pool": l["address"][2:].lower(), "bn": int(l["blockNumber"], 16), "sender": l["topics"][1][-40:], "data": l["data"], "tx": l["transactionHash"]} for l in ls]
    for r in oth:
        if g and (len(g) >= 20 or r["block"] - g[0]["block"] > 6000): SW += flush(g); g = []
        g.append(r)
    if g: SW += flush(g)
    json.dump(SW, open(cache, "w"))
cb = {r["pool"]: r for r in oth}
big = []
for s_ in SW:
    r = cb.get(s_["pool"])
    if not r or s_["bn"] > r["block"] + 600: continue
    d = s_["data"][2:]; a0 = K.s(K.u(d, 0)); a1 = K.s(K.u(d, 1)); weth_in = a0 if r["token0"] == K.WETH else a1
    if s_["sender"] == K.ROUTER and weth_in >= 5 * 10 ** 16: big.append((s_, weth_in))
P(f"   swaps to +600 in those pools: {sum(1 for s_ in SW if s_['pool'] in cb and s_['bn'] <= cb[s_['pool']]['block'] + 600)}; router buys >= 0.05 ETH: {len(big)} in {len(set(b[0]['pool'] for b in big))} pools")
hs = sorted(set(b[0]["tx"] for b in big)); TX = {}
for i in range(0, len(hs), 100):
    for t in rpc.batch("eth_getTransactionByHash", [[h] for h in hs[i:i + 100]], n=20):
        if t: TX[t["hash"]] = t
fp = [b for b in big if b[0]["tx"] in TX and (TX[b[0]["tx"]]["input"] or "")[2:10] == "04e45aaf" and (len(TX[b[0]["tx"]]["input"]) - 2) // 2 == 228
      and int(TX[b[0]["tx"]]["value"], 16) > 0 and int(TX[b[0]["tx"]].get("maxPriorityFeePerGas") or "0x0", 16) == 1]
P(f"   of them with the fleet's fingerprint (04e45aaf, 228 B, ETH value, priority 1): {len(fp)} in {len(set(b[0]['pool'] for b in fp))} pools; "
  f"by launcher: {C.Counter(((code.get((tx[cb[b[0]['pool']]['tx']]['to'] or '').lower(), {}).get('hash') or 'none')[:8]) for b in fp).most_common()}")
P(f"   all router buys >= 0.05 ETH by fingerprint: {C.Counter(((TX[b[0]['tx']]['input'] or '')[2:10], (len(TX[b[0]['tx']]['input']) - 2)//2, int(TX[b[0]['tx']]['value'],16) > 0, int(TX[b[0]['tx']].get('maxPriorityFeePerGas') or '0x0', 16)) for b in big if b[0]['tx'] in TX).most_common(6)}")
P("rpc", rpc.STATS)
open(K.J("p10_moved.out"), "w").write("\n".join(L) + "\n")
