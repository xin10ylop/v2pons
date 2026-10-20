"""Stage 4: the candidate's claims, re-measured on my slices.
 (a) deadline (word 6 of the c1120e3d calldata) minus the T block's timestamp; by the T block's position inside its second (j = number of
     earlier blocks with the same timestamp), the share signed in the previous second -> the sign-to-land lag in blocks;
 (b) a presigned or failed copy of the bot's first buy: in blocks T-12..T-1 (and block T before the bot's tx) any tx to the bot router, any tx
     from the T buyer or from any bot wallet, any tx whose calldata holds the pool id, the token or the T buyer; any failed tx (receipts T-6..T)
     to the bot router / from a bot wallet / holding the token or pool id; every log in T-6..T touching the pool id, the token or the buyer.
usage: s4_presign.py <slice> [<slice> ...]"""
import sys, pickle, collections
from lib import *
kb, kr = KV("blk"), KV("rcp")
for name in sys.argv[1:]:
    D = pickle.load(open(f"parsed_{name}.pkl", "rb")); botw = D["botw"]
    P = sorted([p for p in D["pools"] if p["T"] is not None], key=lambda p: p["L"])
    print(f"===== slice {name}: {len(P)} pools with a bot buy, L {P[0]['L']}..{P[-1]['L']} ({utc(D['meta']['ta'])} .. {utc(D['meta']['tb'])} UTC)")
    gap = collections.Counter(); byj = collections.defaultdict(collections.Counter); nfull = 0
    flags = collections.Counter(); flag_rows = []; failed_rows = []; logtouch = []
    for p in P:
        T = p["Tbn"]; bt = kb.d.get(str(T))
        if not bt: continue
        dl = p["Twords"][6]; g = dl - bt["ts"]; gap[g] += 1
        j = 0
        for k in range(1, 13):
            b = kb.d.get(str(T - k))
            if b and b["ts"] == bt["ts"]: j += 1
            else: break
        byj[min(j, 6)][g] += 1
        tok = p["token"][2:].lower(); pid = p["pid"][2:].lower(); buyer = p["buyer"][2:].lower()
        ok = all(str(n) in kb.d for n in range(T - 12, T + 1)); nfull += ok
        for d in range(0, 13):
            b = kb.d.get(str(T - d))
            if not b: continue
            for t in b["txs"]:
                if d == 0 and int(t["transactionIndex"], 16) >= p["Tti"]: continue
                fr = (t["from"] or "").lower(); to = (t.get("to") or "").lower(); inp = (t["input"] or "").lower()
                hits = []
                if to == BOT: hits.append("to bot router:" + inp[2:10])
                if fr == p["buyer"]: hits.append("from T buyer")
                elif fr in botw: hits.append("from a bot wallet:" + to[:10] + ":" + inp[2:10])
                if tok in inp: hits.append("calldata holds token")
                if pid in inp: hits.append("calldata holds pool id")
                if buyer in inp and fr != p["buyer"]: hits.append("calldata holds T buyer")
                for h in hits: flags[(h.split(":")[0], d)] += 1; flag_rows.append((p["L"], p["T"], d, h, fr[:10], to[:10], inp[:10]))
        for d in range(0, 7):
            rs = kr.d.get(str(T - d))
            if rs is None: continue
            b = kb.d.get(str(T - d)); txi = {t["hash"]: t for t in b["txs"]} if b else {}
            for r in rs:
                t = txi.get(r["tx"], {}); fr = (r.get("from") or "").lower(); to = (r.get("to") or "").lower(); inp = (t.get("input") or "").lower()
                if d == 0 and t and int(t["transactionIndex"], 16) >= p["Tti"]: continue
                if r["status"] == "0x0" and (to == BOT or fr in botw or tok in inp or pid in inp):
                    failed_rows.append((p["L"], p["T"], d, fr[:10], to[:10], inp[:10]))
                for l in r["logs"]:
                    if l["a"] == "0x" + tok or any(pid in x.lower() or tok in x.lower() or buyer in x.lower() for x in l["t"]) or buyer in l["d"].lower():
                        logtouch.append((p["L"], p["T"], d, l["a"][:10], l["t"][0][:10], fr[:10], to[:10]))
    print(f"(a) deadline - ts(T block), seconds: {sorted(gap.items())}  (n {sum(gap.values())})")
    print("    by j = earlier blocks in T's own second: share with deadline - ts = 1199 (signed in the previous second if deadline = wall clock + 1,200)")
    for j in sorted(byj):
        c = byj[j]; n = sum(c.values())
        print(f"      j {j}{'+' if j == 6 else ' '}: n {n:3d}  {dict(sorted(c.items()))}  prev-second share {sum(v for k, v in c.items() if k < 1200) / n:.2f}")
    print(f"(b) pools with every block T-12..T: {nfull}; flags (kind, d blocks before T): {sorted(flags.items())}")
    for r in flag_rows[:40]: print("      ", r)
    print(f"    failed txs (receipts T-6..T, ahead of the bot's buy) to the bot router / from a bot wallet / holding the token or pool id: {len(failed_rows)}", failed_rows[:10])
    print(f"    logs in T-6..T ahead of the bot's buy touching the pool id / token / T buyer: {len(logtouch)}", logtouch[:10])
    st = collections.Counter()
    for p in P:
        rs = kr.d.get(str(p["Tbn"])) or []
        st.update(r["status"] for r in rs if r["tx"] == p["Ttx"])
    print(f"    status of the bot's T tx: {dict(st)}")
