"""Stage 10: the line's pre-launch transaction. The live monitor (u_mon) found T's buyer last funded by a 7422a284 call on the bot router
0x1cbaf24d from a nonce-0 sender carrying ~6 ETH: token bytecode + salt + (wallets[], ETH amounts[], token holders[], token amounts[]) -
it deploys the token and tops up ~50 bot wallets. Here, for every pool of the last 2 h: the whole blocks [L-40, L-4], the 7422a284 call
whose token-holder/wallet data belongs to this pool (the T buyer listed in its wallets[]), its lead to L and to T, T's buyer index and
amount in it, and whether any of its fields could carry timing (all four arrays decoded)."""
import pickle, collections, os, json
from lib import *
os.chdir(HERE)
D = pickle.load(open("u2_parsed.pkl", "rb")); kb = KV("blk")
G = [p for p in D["pools"] if p["recent2h"] and p["T"] is not None]
need = sorted(set(b for p in G for b in range(p["L"] - 40, p["L"] - 3)))
get_blocks(need, kb, None, receipts=False)
def decode(inp):
    body = inp[10:]; ws = [int(body[64 * i: 64 * (i + 1)], 16) for i in range(len(body) // 64)]
    base = ws[2] // 32; offs = ws[base: base + 4]; arr = []
    for o in offs:
        s = base + o // 32; n = ws[s]; arr.append(ws[s + 1: s + 1 + n])
    return {"codelen": ws[3], "wallets": ["0x%040x" % a for a in arr[0]], "eth": arr[1], "holders": ["0x%040x" % a for a in arr[2]], "tok": arr[3]}
rows = []; nodep = 0
for p in G:
    found = None; cands = 0
    for bn in range(p["L"] - 40, p["L"] - 3):
        for t in kb.d[str(bn)]["txs"]:
            if (t.get("to") or "").lower() == BOT and (t.get("input") or "")[2:10] == "7422a284":
                cands += 1
                try: d = decode(t["input"])
                except Exception: continue
                if p["buyer"] in d["wallets"]: found = (bn, t, d)
    if not found: nodep += 1; rows.append(dict(pid=p["pid"], found=False, cands=cands)); continue
    bn, t, d = found; i = d["wallets"].index(p["buyer"])
    rows.append(dict(pid=p["pid"], found=True, lead_L=p["L"] - bn, lead_T=p["Tbn"] - bn, T=p["T"], idx=i, n=len(d["wallets"]), eth=d["eth"][i] / 1e18,
                     Tq=p["Tq"], sender=t["from"].lower(), nonce=int(t["nonce"], 16), value=int(t["value"], 16) / 1e18, launcher=p["launcher"],
                     launcher_nonce=p["launcher_nonce"], nholders=len(d["holders"]), codelen=d["codelen"],
                     others_in_list=sum(1 for q in G if q is not p and q["buyer"] in d["wallets"]), bot2_in=sum(1 for s in p["sw"] if s["who"] == "bot" and s["eoa"] in d["wallets"])))
F = [r for r in rows if r["found"]]
print(f"pools {len(G)}; a 7422a284 call in [L-40, L-4] listing T's buyer: {len(F)}; not found {nodep}")
c = collections.Counter
print("lead to L (blocks):", sorted(c(r["lead_L"] for r in F).items()))
print("lead to T (blocks):", sorted(r["lead_T"] for r in F))
print("T (blocks after L):", sorted(r["T"] for r in F))
print("T's buyer index in wallets[] / list length:", sorted((r["idx"], r["n"]) for r in F)[:60])
print("sender nonce:", c(r["nonce"] for r in F), "| tx value p50 %.3f ETH" % pct([r["value"] for r in F], .5), "| sender == launcher:", sum(1 for r in F if r["sender"] == r["launcher"]),
      "| launcher nonce:", c(r["launcher_nonce"] for r in F).most_common(3))
print("ETH sent to T's buyer in it vs T's buy size (ETH):", [(round(r["eth"], 4), round(r["Tq"], 4)) for r in F][:20])
print("the pool's later bot buys by wallets in the same list (p50):", pct([r["bot2_in"] for r in F], .5), "of bot buys; other pools' T buyers in the list (p50):", pct([r["others_in_list"] for r in F], .5))
lt = [r["lead_T"] for r in F]
print(f"as a T predictor: lead_T p10/50/90 {pct(lt,.1)}/{pct(lt,.5)}/{pct(lt,.9)}; best +-1 window holds {max(sum(1 for x in lt if abs(x - m) <= 1) for m in range(min(lt), max(lt) + 1))} of {len(lt)}")
json.dump(rows, open("u10_deploy.json", "w"))
