"""s07b: every failed transaction found by s07: its input (family token in calldata, Portal direction), and its revert reason from an archive
eth_call of the same call at the parent block (sentio/blockmachine). -> data/s07b.json, stdout"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import rpc
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
F = json.load(open(os.path.join(D, "s07_failed.json")))
toks = set(json.load(open(os.path.join(D, "s02_family.json"))) ["family"][i]["token"] for i in range(56))
P = "0xe2ce6ab80874fa9fa2aae65d277dd6b8e65c9de0"
def reason(e):
    d = e.get("data", "") if isinstance(e, dict) else ""
    if isinstance(d, str) and d.startswith("0x08c379a0"):
        try: return bytes.fromhex(d[138:]).rstrip(b"\0").decode(errors="replace")
        except Exception: pass
    return (d[:10] if d else str(e)[:80])
out = []
for e, r in F["res"].items():
    for t in r.get("txs", []):
        if t["status"] != 0: continue
        tx = rpc.call("eth_getTransactionByHash", [t["h"]], urls=rpc.HIST)
        inp = tx["input"].lower(); fam_in = [x for x in toks if x[2:] in inp]
        direction = None
        if tx["to"].lower() == P and inp[2:10] == "ef7ec2e7":
            w = [inp[10 + 64 * i: 10 + 64 * (i + 1)] for i in range(6)]
            direction = "sell" if int(w[1], 16) != 0 and int(w[2], 16) == 0 else "buy"
        sim = rpc.call("eth_call", [{"from": tx["from"], "to": tx["to"], "data": tx["input"], "value": tx["value"], "gas": tx["gas"]}, hex(t["b"] - 1)], urls=rpc.HIST)
        why = reason(sim["__revert__"]) if isinstance(sim, dict) else "passes at parent block (failed on in-block state: front-run / slippage / deadline)"
        o = {"eoa": e, "grp": r["grp"], "h": t["h"], "b": t["b"], "to": t["to"], "sel": t["sel"], "family_tokens_in_calldata": fam_in, "portal_dir": direction,
             "gasUsed": t["gasUsed"], "gas": t["gas"], "why": why}
        out.append(o); print(o)
json.dump(out, open(os.path.join(D, "s07b.json"), "w"), indent=1)
