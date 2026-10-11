"""Decode the recent launches from their calldata alone and check every field against the receipt (Initialize, Mint) and the factory log"""
import json, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v3dec import *
from eth_utils import keccak
D = json.load(open(sys.argv[1]))
T_IN = keccak(text="Initialize(uint160,int24)").hex(); T_MI = keccak(text="Mint(address,address,int24,int24,uint128,uint256,uint256)").hex()
ok = 0; n = 0; shown = 0
for x in D["line"]:
    d = decode_launch_v3(bytes.fromhex(x["tx"]["input"][2:])); n += 1
    rc = x["receipt"]; init = [l for l in rc["logs"] if l["topics"][0][2:] == T_IN]; mint = [l for l in rc["logs"] if l["topics"][0][2:] == T_MI]
    sp_r = int(init[0]["data"][2:66], 16); tick_r = int(init[0]["data"][66:130], 16); tick_r = tick_r - (1 << 256) if tick_r >> 255 else tick_r
    m = mint[0]; L_r = int(m["data"][66:130], 16); lo_r = int(m["topics"][2], 16); hi_r = int(m["topics"][3], 16)
    lo_r = lo_r - (1 << 256) if lo_r >> 255 else lo_r; hi_r = hi_r - (1 << 256) if hi_r >> 255 else hi_r
    good = d and d["pool"] == x["pool"][2:] and d["pool"] == init[0]["address"][2:].lower() and d["sqrt_p"] == sp_r and d["liq"] == L_r and (d["lo"], d["hi"]) == (lo_r, hi_r)
    ok += bool(good)
    if shown < 3 or not good:
        shown += 1
        print(f"launch {x['tx']['hash']} block {x['lb']} from {x['tx']['from']} nonce {int(x['tx']['nonce'], 16)} gas {int(x['tx']['gas'], 16)} used {int(rc['gasUsed'], 16)}")
        print(f"  decoded: pool 0x{d['pool']} token 0x{d['token']} qs {d['qs']} fee {d['fee']} sqrtP {d['sqrt_p']} range [{d['lo']}, {d['hi']}] amount0 {d['amount0']} amount1 {d['amount1']/1e18:.6g}e18 L {d['liq']} recipient 0x{d['recipient']}")
        print(f"  receipt: pool {init[0]['address']} sqrtP {sp_r} tick {tick_r} mint range [{lo_r}, {hi_r}] L {L_r}  -> all equal: {good}; launch tick - hi = {tick_r - hi_r}")
print(f"{ok}/{n} launches decoded exactly from calldata (pool address, sqrtP, range, liquidity)")
