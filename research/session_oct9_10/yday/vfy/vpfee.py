import json, sys
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import logs, PM
from vprice import *
T_PF = "0x" + keccak(text="ProtocolFeeUpdated(bytes32,uint24)").hex()
OUT = {r["block"]: r for r in json.load(open("vprice_out.json"))}
# all ProtocolFeeUpdated on the PM over the day + margin
ls = logs({"address": PM, "topics": [T_PF]}, 83086000, 83740000)
print("ProtocolFeeUpdated events on the PM Oct 8:", len(ls))
by = {}
for l in ls: by.setdefault(l["topics"][1], []).append((int(l["blockNumber"], 16), int(l["data"], 16)))
for blk, o in sorted(OUT.items()):
    if o["pid"] in by:
        ev = by[o["pid"]]
        win = (o["fire_block"], max(v["sell_land_block"] for s in o["results"].values() for v in s.values())) if o["results"] else None
        print(o["time_utc"][11:], blk, "fee", o["fee_ppm"], "pf updates (offset, value):", [(b - blk, v) for b, v in ev], "trade window offsets", (win[0] - blk, win[1] - blk) if win else None)
# feed copy vs chain at our buy block
mx = []
for blk, o in sorted(OUT.items()):
    if not o["results"]: continue
    R = json.load(open(f"raw/{blk}.json")); fee = o["fee_ppm"]; liq = o["v"]["liq"]
    ev = sorted(R["near"], key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16)))
    sw = [(int(l["blockNumber"], 16), word(l["data"], 2), l["transactionHash"]) for l in ev if l["topics"][0] == T_SWAP and "0x" + l["topics"][2][-40:] != RELAY]
    wal = {t["h"] for b in R["blocks"] for t in b["txs"] if t["from"] == WALLET}
    sw = [x for x in sw if x[2] not in wal]
    tb = bytes.fromhex(R["token"])
    for k in (0, 1, 2):
        B = o["fire_block"] + k
        s = float(int(R["rec"]["logs"][0]["data"][2+64*3:2+64*4], 16)) if False else None
        # feed copy through B
        init = next(l for l in R["rec"]["logs"] if l["topics"][0] == T_INIT and l["topics"][1] == o["pid"]); s = float(word(init["data"], 3))
        for b in R["blocks"]:
            if b["n"] > B: break
            for t in sorted(b["txs"], key=lambda t: t["i"]):
                if t["from"] == WALLET or t["to"] == OP or t["sel"] == SEL_LAUNCH or t["value"] == 0 or t["len"] < 20 or t["input"] is None: continue
                if tb in bytes.fromhex(t["input"][2:]) and t["to"][2:] != R["token"]:
                    s = v4math.sqrt_after_buy(s, liq, nof(t["value"], fee))
        ch = [x for x in sw if x[0] <= B]; c = ch[-1][1]
        mx.append((abs(s / c - 1), blk, k))
mx.sort(reverse=True); print("feed vs chain sqrtP rel diff at T, T+1, T+2 (worst 5):", mx[:5])
