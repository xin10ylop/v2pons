"""The 7-day census (Oct 4 13:52 - Oct 11 13:52 UTC, scanner2/census/pools.jsonl, built from the same public RPC) for the 3.0 line:
every pool with known_fp vbot-v3.0: launch block/ts, the first 12 swaps with their wallet / target / selector / router, every pull with
its wallet / target / selector / via, ours. -> cache/census30.json. Also checks the shape (value 3.0, 1,444 bytes, fee 10000, ts 200)."""
import json, os, collections
CEN = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/census/pools.jsonl"
out = []; shapes = collections.Counter()
with open(CEN) as f:
    for l in f:
        if '"vbot-v3.0"' not in l: continue
        r = json.loads(l)
        if r.get("known_fp") != "vbot-v3.0": continue
        la = r.get("launch") or {}
        shapes[(la.get("value_eth"), la.get("calldata_len"), r.get("fee"), r.get("tick_spacing"), r.get("dex"))] += 1
        out.append({"pool": r["pool"], "lb": r["launch_block"], "ts": r["launch_ts"], "launcher": la.get("from"), "sw12": r.get("swaps12") or [],
                    "pulls": r.get("pulls") or [], "ours": r.get("ours"), "ev_to": r.get("ev_to"), "ev_complete": r.get("ev_complete"), "n_swaps": r.get("n_swaps")})
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", "census30.json"), "w"))
print("census 3.0 pools:", len(out), "shapes:", dict(shapes))
