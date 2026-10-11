"""H: the a98b3b9e hooked core pools from the census (ETH, fee 3000, ts 60, hooks != 0, POSM multicall 2020 B value 0)."""
import json, os, collections as C
CEN = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/census"
H = os.path.dirname(os.path.abspath(__file__))
Z = "0x" + "0" * 40
out = []; allfam = C.Counter()
with open(os.path.join(CEN, "pools.jsonl")) as f:
    for line in f:
        if "a98b3b9e" not in line: continue
        r = json.loads(line)
        if not (r["fam"].get("tok") or "").startswith("a98b3b9e"): continue
        L = r["launch"]
        allfam[(r["quote"], r["fee"], r["tick_spacing"], r["hooks"] != Z, L["selector"], L["calldata_len"], L["value_wei"] == 0)] += 1
        if r["quote"] == "ETH" and r["fee"] == 3000 and r["tick_spacing"] == 60 and r["hooks"] != Z:
            keep = {k: r.get(k) for k in ("pool", "token", "hooks", "fee", "tick_spacing", "sqrt_p0", "tick0", "launch_block", "launch_utc", "launch_tx", "n_swaps", "n_buys", "n_sells",
                                          "buy_eth_total", "n_pulls", "first_pull_off", "pulls", "first_real_buys", "frb", "swaps12", "ev_to", "quote_side")}
            keep["launch"] = L; keep["tok"] = r["fam"]["tok"]
            out.append(keep)
for k, v in allfam.most_common(): print(v, k)
out.sort(key=lambda r: r["launch_block"])
json.dump(out, open(os.path.join(H, "core_pools.json"), "w"))
print("core pools", len(out))
for r in out[-12:]:
    print(r["launch_utc"], r["pool"][:12], "tok", r["token"], "hook", r["hooks"], "from", r["launch"]["from"][:10], "len", r["launch"]["calldata_len"], "val", r["launch"]["value_wei"], "swaps", r["n_swaps"], "pulls", r["n_pulls"], "ev_to", r["ev_to"])
