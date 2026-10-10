"""compile traces.jsonl (+ nonces.json) into samples.json and a printed table"""
import json, os, collections
D = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/origins/eras/"
tr = {}
for l in open(D + "traces.jsonl"):
    d = json.loads(l); tr[d["launch"]] = d          # last trace of a launch wins
NN = json.load(open(D + "nonces.json")) if os.path.exists(D + "nonces.json") else {}
rows = []
for h, d in sorted(tr.items(), key=lambda kv: kv[1]["bn"]):
    top = d.get("top") or {}; sw = d.get("sweep") or {}
    nn = sorted(NN.get(h, {}).get("senders", {}).values())
    r = {"tag": d["tag"], "time": d["time"], "bn": d["bn"], "launch_tx": h, "creator": d["creator"], "creator_nonce": d["nonce"], "value": round(d["value"], 3),
         "pull_delay_blocks": (d["pull"] or 0) - d["bn"] if d["pull"] else None, "buyers": d["buyers"], "crowd": len(d["crowd"]),
         "buyer_nonce_min_med_max": [nn[0], nn[len(nn)//2], nn[-1]] if nn else None,
         "crowd_funders": d.get("crowd_funders"), "crowd_hop2": d.get("crowd_hop2"),
         "fund_chain": d.get("fund_chain"), "dispatcher": top.get("addr"), "dispatcher_outs": top.get("n_out"), "pot_dispatcher": round(top.get("out_total", 0), 4) or None,
         "dispatcher_in_top": top.get("in_top", [])[:3], "dispatcher_in_from_prev_creator": top.get("in_from_prev_creators"),
         "sweep": sw.get("addr"), "pot_sweep": round(sw.get("in_total", 0), 4) or None, "sweep_from_crowd": sw.get("from_crowd"), "sweep_n_out": sw.get("n_out"),
         "sweep_first_outs": sw.get("outs", [])[:3], "sweep_next": (sw.get("next") or {}).get("addr"), "payout": d.get("payout")}
    rows.append(r)
json.dump(rows, open(D + "samples.json", "w"), indent=1)
print(f"{'tag':18s} {'time':11s} {'val':>6s} {'buy':>3s} {'crd':>3s} {'nonces':12s} {'pot(disp)':>9s} {'pot(sweep)':>10s} sweep->first out")
for r in rows:
    so = r["sweep_first_outs"][0] if r["sweep_first_outs"] else None
    print(f"{r['tag'][:18]:18s} {r['time']:11s} {r['value']:6.3f} {r['buyers']:3d} {r['crowd']:3d} {str(r['buyer_nonce_min_med_max']):12s} {str(r['pot_dispatcher']):>9s} {str(r['pot_sweep']):>10s} {('%.3f to %s (n%d)' % (so[2], so[1][:10], so[3])) if so else ''}")
