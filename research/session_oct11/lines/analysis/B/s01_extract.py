"""Stream pools.jsonl once; keep the v4 pools of angle B: every v4 pool NOT launched through lc c873e135|ac9650d8 (analyst A's),
plus the token families the caller assigned to B even where they launch through that lc (16afd61e, 58d59320, c0b7d400, a98b3b9e,
97c7ba1b, cb79985d, 2dfcf583, 65daaea0, 99e0b5e8, 59571c74). Output: b_pools.jsonl (one row per pool, same schema) + a flag in_A."""
import json, os
CEN = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/census"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "b_pools.jsonl")
A_LC = "c873e135dc9aaec88489cfbad146b4cb49d6a32e0d80326377784b7ba17670b2|ac9650d8"
TOK = ("16afd61e", "58d59320", "c0b7d400", "a98b3b9e", "97c7ba1b", "cb79985d", "2dfcf583", "65daaea0", "99e0b5e8", "59571c74")
n = nk = 0
with open(os.path.join(CEN, "pools.jsonl")) as f, open(OUT, "w") as o:
    for line in f:
        r = json.loads(line)
        if r["dex"] != "v4" or r.get("quote_pair"): continue
        n += 1
        lc = (r.get("fam") or {}).get("lc"); tok = ((r.get("fam") or {}).get("tok") or "")[:8]
        inA = lc == A_LC
        if inA and tok not in TOK: continue
        r["in_A"] = inA; nk += 1
        o.write(json.dumps(r) + "\n")
print("v4 non-quote-pair pools", n, "kept", nk)
