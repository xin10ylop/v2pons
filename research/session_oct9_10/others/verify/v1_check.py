#!/usr/bin/env python3
"""Verifier step 1b: compare the fresh data (fresh.pkl) with the census row and the census cache; re-derive the gates, trigger, pull;
re-price FOLLOW (land 1 fast, hold 2 and hold 30) with the independent pricer; print each pool's swap tape (first 120 blocks)."""
import sys, os, json, pickle
HERE = os.path.dirname(os.path.abspath(__file__)); SCR = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, SCR); sys.path.insert(0, HERE)
from chain import T_INIT, T_SWAP, T_ML, W, sgn
import vprice
def s128(x):
    x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
R = {json.loads(l)["pid"]: json.loads(l) for l in open(os.path.join(HERE, "..", "census.jsonl"))}
D = pickle.load(open(os.path.join(HERE, "fresh.pkl"), "rb"))
PL = pickle.load(open(os.path.join(HERE, "..", "cache_plogs.pkl"), "rb"))
RELAY = "2abb5653352f6b2f3b4f4261877cd02d9e05a957"; OURW = "ab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
verbose = "-v" in sys.argv
out = []
for pid, d in D.items():
    r = R[pid]; init = d["init"]; dd = init["data"]; tx = d["tx"]; b0 = int(init["blockNumber"], 16)
    fee = W(dd, 0); ts = sgn(W(dd, 1)); hooks = "0x" + dd[2 + 128 + 24: 2 + 192]; sp0 = W(dd, 3); tick0 = sgn(W(dd, 4))
    token = "0x" + init["topics"][3][-40:]
    ev = sorted(d["logs"], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    sw = []; adds = []; rem = []
    for l in ev:
        bn = int(l["blockNumber"], 16); x = l["data"]
        if l["topics"][0] == T_SWAP:
            if l["topics"][2][-40:] == RELAY: continue
            sw.append((bn, int(l["logIndex"], 16), s128(W(x, 0)), s128(W(x, 1)), W(x, 2), W(x, 3), sgn(W(x, 4)), l["transactionHash"]))
        else:
            lo, hi, dl = sgn(W(x, 0)), sgn(W(x, 1)), sgn(W(x, 2))
            if dl > 0 and l["transactionHash"] == init["transactionHash"]: adds.append((lo, hi, dl))
            if dl < 0: rem.append((bn, dl, l["transactionHash"]))
    L0 = sum(dl for lo, hi, dl in adds if lo < tick0 <= hi)
    pull = rem[0][0] if rem else None
    real = [s for s in sw if -s[2] >= 2 * 10**14]
    trig = real[0][0] - b0 if real else None
    # cache comparison (census window [b0, b0 + 3000]; fresh [b0, b0 + 700])
    cache = [x for x in PL.get(pid, []) if x[0] <= b0 + 700]
    chk = {"from": (tx["from"].lower(), (r["from"] or "").lower()), "to": ((tx["to"] or "").lower(), (r["to"] or "").lower()), "nonce": (int(tx["nonce"], 16), r["nonce"]),
           "value": (round(int(tx["value"], 16) / 1e18, 6), round(r["value"], 6)), "inlen": ((len(tx["input"]) - 2) // 2, r["inlen"]), "sel": (tx["input"][:10], r["sel"]),
           "fee": (fee, r["fee"]), "ts": (ts, r["ts"]), "hooks": (hooks, r["hooks"]), "liq": (L0, r.get("liq")), "trig": (trig, r.get("trig")),
           "pull": ((pull - b0) if pull is not None and pull - b0 <= 700 else None, r.get("pull") if (r.get("pull") is not None and r["pull"] <= 700) else None),
           "nlogs700": (len(ev), len(cache))}
    bad = {k: v for k, v in chk.items() if v[0] != v[1]}
    swv = [s[:7] for s in sw]
    err, oneL = vprice.validate(swv, sp0, fee, b0 + 400)
    res = {}
    if trig is not None and 6 < trig <= 150:
        tb = real[0][0]
        for hold in (2, 30):
            res[f"hold{hold}"] = vprice.follow(swv, sp0, L0, fee, tb + 1, hold, 1, pull)
    cp = (r.get("paper") or {})
    o = {"fam": d["fam"], "pid": pid, "b0": b0, "mismatch": bad, "replay_err": err, "single_L": oneL, "trig": trig, "pull": (pull - b0) if pull else None,
         "mine": {k: (round(v["ret"], 5), v["why"], v["send"]) if v else None for k, v in res.items()},
         "census": {k: (round(cp[k]["ret"], 5), cp[k]["why"], cp[k]["send"]) if cp.get(k) else None for k in ("land1_fast", "hold30")}, "rc_status": d["rc_status"]}
    out.append(o)
    print(f"{d['fam']:6s} {pid[:12]} b0 {b0} fee {fee} ts {ts} nonce {int(tx['nonce'],16)} val {int(tx['value'],16)/1e18:.3f} len {(len(tx['input'])-2)//2} "
          f"trig {trig} pull {o['pull']} | mismatch {bad or 'none'} | replay err {err:.1e} 1L {oneL} | mine {o['mine']} | census {o['census']}")
    if verbose:
        tok = token[2:].lower()
        for s in sw:
            if s[0] - b0 > 120: break
            t = d["txs"].get(s[7]) or {}
            inp = (t.get("input") or "").lower()
            print(f"     +{s[0]-b0:3d} {'BUY ' if s[2] < 0 else 'SELL'} {abs(s[2])/1e18:9.5f} ETH  from {t.get('from','?')[:12]} n{int(t.get('nonce','0x0'),16):6d} to {(t.get('to') or '')[:12]} "
                  f"len {(len(inp)-2)//2:5d} val {int(t.get('value','0x0'),16)/1e18:8.5f} tokInData {tok in inp} prio {int(t.get('maxPriorityFeePerGas') or '0x0',16)/1e9:.4f}")
        for bn, dl, th in rem[:2]:
            t = d["txs"].get(th) or {}
            print(f"     PULL +{bn-b0} from {t.get('from','?')[:12]} n{int(t.get('nonce','0x0'),16)} to {(t.get('to') or '')[:12]} sel {(t.get('input') or '')[:10]}  deployer {tx['from'][:12]}")
json.dump(out, open(os.path.join(HERE, "v1_check.json"), "w"), indent=1)
