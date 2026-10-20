import sys, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
KEY = "0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|500|1|true"
F = load_families(); pids = F[KEY]["pids"]
P = load_pools(); E = load_events(set(pids)); T = load_txs()
n_sw = 0; n_sw600 = 0; txs = set(); txs600 = set(); have = 0
for p in pids:
    e = E[p]; a = e["adds"][0]["bn"]
    for s in e["swaps"]:
        n_sw += 1; txs.add(s["tx"])
        if s["bn"] <= a + 600: n_sw600 += 1; txs600.add(s["tx"])
print("swaps", n_sw, "distinct tx", len(txs), "<=add+600", n_sw600, len(txs600), "already in census", len(txs & set(T)), len(txs600 & set(T)))
print("senders", collections.Counter(s["sender"] for p in pids for s in E[p]["swaps"]).most_common(10))
print("n adds per pool", collections.Counter(len(E[p]["adds"]) for p in pids), "n pulls", collections.Counter(len(E[p]["pulls"]) for p in pids))
