"""B01: every V3 factory PoolCreated from H hours (default 56) before the head to the head; keep the pools whose creating tx is
createAndInitializePoolIfNecessary (13ead562) sent straight to the NonfungiblePositionManager 0x73991a25 (code hash prefix 0a493d1a, checked).
Freezes the head in b01_meta.json (delete it to move the head). -> b01_launches.json"""
import sys, os, json
from bc import *
H = float(sys.argv[1]) if len(sys.argv) > 1 else 56.0
mf = p("b01_meta.json")
if os.path.exists(mf): meta = json.load(open(mf))
else:
    head = int(R.call("eth_blockNumber", []), 16); th = int(R.call("eth_getBlockByNumber", [hex(head), False])["timestamp"], 16)
    code = R.call("eth_getCode", [NPM, "latest"]); ch = keccak(bytes.fromhex(code[2:])).hex()
    lo, hi = head - int(H * 3600 * 11), head
    while lo < hi:
        m = (lo + hi) // 2
        if int(R.call("eth_getBlockByNumber", [hex(m), False])["timestamp"], 16) < th - H * 3600: lo = m + 1
        else: hi = m
    meta = {"head": head, "t_head": th, "start": lo, "H": H, "npm_code_hash": ch}
    json.dump(meta, open(mf, "w"))
head, start = meta["head"], meta["start"]
print(f"head {head} {ts(meta['t_head'])} UTC; start {start} ({meta['H']} h, {(head - start) / (meta['H'] * 3600):.3f} blocks/s); NPM code {meta['npm_code_hash'][:8]}")
PC = Cache("b01_pc"); TX = Cache("b01_tx")
pc = []
for a in range(start, head + 1, 50000):
    b = min(a + 49999, head); k = f"{a}-{b}"
    if k not in PC: PC.put(k, R.logs({"address": FACT, "topics": [T_PC]}, a, b))
    pc += PC[k]
print(f"PoolCreated {len(pc)}")
tx = txs(TX, [l["transactionHash"] for l in pc])
fam, shapes = [], {}
for l in pc:
    t = tx[l["transactionHash"]]
    if not t: continue
    k = f"{t['to'][:10]}:{t['input'][2:10]}:{(len(t['input']) - 2) // 2}"; shapes[k] = shapes.get(k, 0) + 1
    if t["to"] != NPM or t["input"][2:10] != "13ead562": continue
    t0 = "0x" + l["topics"][1][-40:]; t1 = "0x" + l["topics"][2][-40:]
    fam.append({"pool": "0x" + l["data"][-40:], "token0": t0, "token1": t1, "fee": int(l["topics"][3], 16), "lb": int(l["blockNumber"], 16),
                "ti": int(l["transactionIndex"], 16), "launch_tx": t["hash"], "launch_from": t["from"], "launch_len": (len(t["input"]) - 2) // 2,
                "launch_value": int(t["value"], 16), "launch_nonce": t["nonce"], "qs": 0 if t0 == WETH else 1 if t1 == WETH else None,
                "token": t1 if t0 == WETH else t0})
BT = Cache("b01_bt"); bt = block_ts(BT, [x["lb"] for x in fam])
for x in fam: x["ts"] = bt[x["lb"]]
json.dump({"meta": meta, "n_poolcreated": len(pc), "shapes": shapes, "launches": fam}, open(p("b01_launches.json"), "w"), indent=0)
print(f"13ead562->NPM launches {len(fam)}; WETH side {sum(1 for x in fam if x['qs'] is not None)}; fees {sorted(set(x['fee'] for x in fam))}; "
      f"wallets {len(set(x['launch_from'] for x in fam))}; first {ts(fam[0]['ts']) if fam else '-'}; rpc {R.STATS}")
