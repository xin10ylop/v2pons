import sys, json, collections, statistics as st
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools()
G = [p for p in P.values() if (p.get("to_code_hash") or "").replace("0x","").startswith("f07d1c53")]
G.sort(key=lambda p:(p["launch_block"],p["log_index"]))
print("n", len(G))
E = load_events(set(p["pid"] for p in G))
T = load_txs()
json.dump({"pools":G,"events":{p["pid"]:E.get(p["pid"]) for p in G},
           "txs":{h:t for h,t in T.items() if any(r[0] in E for r in t.get("refs",[]))}}, open("g3_raw.json","w"))
p=G[0]; print(json.dumps({k:v for k,v in p.items()}, indent=0)[:3000])
e=E[p["pid"]]; print(json.dumps(e)[:3000])
