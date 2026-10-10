"""token metadata URI (launch calldata string s3) and gas parameters for sample launches of each pot: copy launches (per-launch launcher
copies), B launches, fresh-pot launches, A launches"""
import sys, json
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/lch")
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2")
from decode import dec
from lib2 import gentle_post
L = json.load(open("/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/lch/launches.json"))
x = L if isinstance(L, list) else L.get("launches", L)
if isinstance(x, dict): x = list(x.values())
by = {}
for r in x:
    if 83000000 <= r["b0"] <= 83700000: by.setdefault(r["family"], []).append(r)
pick = []
for fam, rs in by.items():
    rs.sort(key=lambda r: r["b0"]); k = len(rs)
    for i in sorted({0, k // 2, k - 1}): pick.append((fam, rs[i]))
r = gentle_post([{"jsonrpc": "2.0", "id": j, "method": "eth_getTransactionByHash", "params": [p[1]["launch_tx"]]} for j, p in enumerate(pick)])
r = {y["id"]: y["result"] for y in r}
for j, (fam, L1) in enumerate(pick):
    t = r.get(j)
    if not t: print(fam, "no tx"); continue
    d = dec(t["input"])
    print(f"{fam:13s} {L1['utc']} to {t['to'][:10]} from {t['from'][:10]} n{int(t['nonce'], 16)} type {t['type']} gas {int(t['gas'], 16)} tip {int(t.get('maxPriorityFeePerGas', '0x0'), 16) / 1e9} gwei "
          f"value {int(t['value'], 16) / 1e18} len {(len(t['input']) - 2) // 2} | uri {d.get('s3', d)} | name {d.get('name')} sym {d.get('symbol')} fee {d.get('fee')} recipient==from {str(d.get('recipient', '')).lower() == t['from']}")
