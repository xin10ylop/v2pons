"""Who calls the bot router to buy: all 2.433 buys since block 86100000 and a random sample of 3.0/5.0 buys after the stop; overlap; 2.433 buyers' state now."""
import kc, json, collections, random
rows = [json.loads(l) for l in open(kc.p("k01_launches_cache.jsonl"))]
Z = "0x" + "0" * 40; LAST = 86310320
tok2l = {r["c1"]: r for r in rows if r["c0"] == Z}
lg = []
for l in open(kc.p("k03_botin_cache.jsonl")): lg += json.loads(l)["logs"]
buys = [l for l in lg if kc.topaddr(l["topics"][1]) != Z]
def fam(tok):
    r = tok2l.get(tok)
    if not r: return None
    if r["value"] == kc.V2433: return "2.433"
    return {679394651928963067279918579724198: "3.0", 526364174002223567019744861584709: "5.0"}.get(r["sqrtp"], "other")
b2433 = [l for l in buys if fam(l["address"].lower()) == "2.433"]
post = [l for l in buys if int(l["blockNumber"], 16) > 86314009 and fam(l["address"].lower()) in ("3.0", "5.0")]
pre35 = [l for l in buys if int(l["blockNumber"], 16) <= LAST and fam(l["address"].lower()) in ("3.0", "5.0")]
random.seed(7); sp = random.sample(post, min(3000, len(post))); sq = random.sample(pre35, min(1500, len(pre35)))
tx = kc.txs("k09_tx_cache.jsonl", list(set(l["transactionHash"] for l in b2433 + sp + sq)))
def who(L): return collections.Counter(tx[l["transactionHash"]]["from"] for l in L if l["transactionHash"] in tx)
W2433, Wpost, Wpre = who(b2433), who(sp), who(sq)
print("2.433 buys since 86100000: %d txs, %d distinct callers, selectors %s, to %s" % (len(b2433), len(W2433), collections.Counter(tx[l["transactionHash"]]["input"][:10] for l in b2433), collections.Counter(tx[l["transactionHash"]]["to"][:10] for l in b2433)))
print("ETH spent by bot buyers in 2.433 pools since 86100000: %.2f" % (sum(tx[l["transactionHash"]]["value"] for l in b2433) / 1e18))
print("3.0/5.0 sample after the stop: %d buys, %d callers; overlap with 2.433 callers: %d" % (len(sp), len(Wpost), len(set(Wpost) & set(W2433))))
print("3.0/5.0 sample before the stop: %d buys, %d callers; overlap with 2.433 callers: %d" % (len(sq), len(Wpre), len(set(Wpre) & set(W2433))))
print("overlap callers:", [(a, W2433[a], Wpost.get(a, 0), Wpre.get(a, 0)) for a in set(W2433) & (set(Wpost) | set(Wpre))])
# 2.433 callers now
A = sorted(W2433)
bal = kc.R.batch("eth_getBalance", [[a, "latest"] for a in A]); non = kc.R.batch("eth_getTransactionCount", [[a, "latest"] for a in A])
bal = [int(x, 16) for x in bal]; non = [int(x, 16) for x in non]
last_nonce = {}
for l in b2433:
    t = tx[l["transactionHash"]]; last_nonce[t["from"]] = max(last_nonce.get(t["from"], -1), t["nonce"])
print("2.433 callers now: total balance %.6f ETH, with balance>0: %d of %d" % (sum(bal) / 1e18, sum(1 for x in bal if x > 0), len(A)))
gap = collections.Counter(n - last_nonce[a] for a, n in zip(A, non))
print("current nonce minus nonce of their last 2.433 buy (1 = nothing since that buy, 2 = one tx since, e.g. a sweep):", sorted(gap.items()))
print("callers whose last 2.433 buy is in the final pool:", sum(1 for l in b2433 if l["address"].lower() == "0xb28f2d1f01b659bdffd762f4fac660dd25057777"))
json.dump({"callers2433": W2433, "now": dict(zip(A, zip(bal, non)))}, open(kc.p("k09_buyers.json"), "w"))
