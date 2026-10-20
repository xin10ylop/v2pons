"""Stream census pools.jsonl once; keep the volume bot's 2.4333 and 3.0 (and 5.0 for context) ETH line pools -> vrows.jsonl"""
import json, collections
CEN = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner2/census"
keep = {"vbot-v2.433", "vbot-v3.0", "vbot-v5.0"}
n = collections.Counter()
with open(CEN + "/pools.jsonl") as f, open("vrows.jsonl", "w") as o:
    for line in f:
        if '"vbot-v' not in line: continue
        r = json.loads(line)
        if r.get("known_fp") in keep:
            o.write(line); n[(r["known_fp"], r["fee"], r["tick_spacing"], r["launch"]["value_wei"], r["launch"]["calldata_len"])] += 1
for k, v in n.most_common(): print(k, v)
