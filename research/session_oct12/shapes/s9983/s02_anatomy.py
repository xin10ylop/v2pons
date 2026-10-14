"""Anatomy: the target 0x6fda94ac..9983bb8c, the hook 0x4eb19769..4924e0cc and the quote token 0x32ac8c..: code sizes, ERC-20 metadata, hook flags,
simple view calls; the calldata words of sample launches of each calldata size; the receipts of the sample launches (every log decoded where
known). Caches receipts in cache/s02_rcpt_cache.jsonl. Prints s02_anatomy.out."""
from common import *
import rpc, collections
from eth_abi import decode
X = json.load(open(J("s01_launches.json"))); core = X["core"]; head = X["meta"]["head"]
R = {r["transactionHash"]: r for r in jl(C("s02_rcpt_cache.jsonl"))}
SIG = {T_INIT: "Initialize", T_SWAP: "Swap", T_ML: "ModifyLiquidity", T_TRANSFER: "Transfer", T_APPROVAL: "Approval", T_DONATE: "Donate",
       "0x" + keccak(text="OwnershipTransferred(address,address)").hex(): "OwnershipTransferred",
       "0x" + keccak(text="Deposit(address,uint256)").hex(): "WETH.Deposit", "0x" + keccak(text="Withdrawal(address,uint256)").hex(): "WETH.Withdrawal",
       "0x" + keccak(text="Swap(address,uint256,uint256,uint256,uint256,address)").hex(): "V2.Swap",
       "0x" + keccak(text="Sync(uint112,uint112)").hex(): "V2.Sync",
       "0x" + keccak(text="Swap(address,address,int256,int256,uint160,uint128,int24)").hex(): "V3.Swap"}
codes = {}
def code(a):
    if a not in codes: codes[a] = rpc.call("eth_getCode", [a, "latest"])
    return codes[a]
def ec(to, data, blk="latest"):
    try: return rpc.call("eth_call", [{"to": to, "data": data}, blk])
    except Exception as e: return "ERR " + str(e)[:120]
def erc20(a):
    out = {}
    for nm, s, typ in (("name", "06fdde03", "string"), ("symbol", "95d89b41", "string"), ("decimals", "313ce567", "uint8"), ("totalSupply", "18160ddd", "uint256"),
                       ("owner", "8da5cb5b", "address")):
        r = ec(a, "0x" + s)
        try: out[nm] = decode([typ], bytes.fromhex(r[2:]))[0] if not r.startswith("ERR") and len(r) > 2 else r
        except Exception: out[nm] = r[:80]
    return out
TGT = core[0]["to"]; HOOK = core[0]["hook"]
print(f"target {TGT}: code {len(code(TGT)) // 2 - 1} B keccak {keccak(bytes.fromhex(code(TGT)[2:])).hex()[:12]}")
for nm, s in (("owner()", "8da5cb5b"), ("poolManager()", "dc4c90d3"), ("WETH()", "ad5c4648"), ("hook()", "7f5a7c7b"), ("fee()", "ddca3f43"), ("feeRecipient()", "46904840"),
              ("treasury()", "61d027b3"), ("quoteToken()", "217a4b70"), ("positionManager()", "791b98bc")):
    print(f"   {nm:18s} {ec(TGT, '0x' + s)[:140]}")
c = code(TGT)[2:]
# PUSH4 selectors in the dispatcher (63 xx xx xx xx followed by 14 / EQ) -> the public selectors
sels = sorted({c[i + 2:i + 10] for i in range(0, len(c) - 12, 2) if c[i:i + 2] == "63" and c[i + 10:i + 12] == "14"})
print(f"   dispatcher selectors ({len(sels)}): {sels}")
print(f"hook {HOOK}: code {len(code(HOOK)) // 2 - 1} B keccak {keccak(bytes.fromhex(code(HOOK)[2:])).hex()[:12]} flags {hook_flags(HOOK)}")
for nm, s in (("owner()", "8da5cb5b"), ("poolManager()", "dc4c90d3"), ("fee()", "ddca3f43"), ("feeRecipient()", "46904840"), ("treasury()", "61d027b3")):
    print(f"   {nm:18s} {ec(HOOK, '0x' + s)[:140]}")
c = code(HOOK)[2:]
sels = sorted({c[i + 2:i + 10] for i in range(0, len(c) - 12, 2) if c[i:i + 2] == "63" and c[i + 10:i + 12] == "14"})
print(f"   dispatcher selectors ({len(sels)}): {sels}")
print(f"quote {QUOTE}: code {len(code(QUOTE)) // 2 - 1} B; {erc20(QUOTE)}")
print(f"   quote balance of the PoolManager {ec(QUOTE, '0x70a08231' + '0' * 24 + PM[2:])}; of the target {ec(QUOTE, '0x70a08231' + '0' * 24 + TGT[2:])}; of the hook {ec(QUOTE, '0x70a08231' + '0' * 24 + HOOK[2:])}")
print("launch selectors:", collections.Counter((r["sel"], r["n"]) for r in core).most_common())
samples = []
for key in [(1220, "ea2c3a42"), (1348, "ea2c3a42"), (1092, "ea2c3a42"), (1156, "ea2c3a42"), (740, "680c2d37"), (612, "258aea82")]:
    v = [r for r in core if (r["n"], r["sel"]) == key]
    if v: samples.append(v[-1])
odd = [r for r in core if r["c0"] != QUOTE and r["c1"] != QUOTE]
samples += odd[-1:]
samples.append([r for r in core if r["c1"] == QUOTE][-1])
for r in samples:
    t = rpc.call("eth_getTransactionByHash", [r["tx"]])
    inp = t["input"][2:]
    print(f"\n== sample {r['tx']} block {r['lb']} from {r['from']} (nonce {r['nonce']}) value {r['value'] / 1e18} sel {inp[:8]} bytes {r['n']} c0 {r['c0']} c1 {r['c1']} sqrtP {r['sqrtP']} tick {r['tick']}")
    for i in range(0, min((len(inp) - 8) // 64, 60)):
        w = inp[8 + 64 * i: 8 + 64 * (i + 1)]
        txt = ""
        try:
            b = bytes.fromhex(w).rstrip(b"\0")
            if b and all(32 <= ch < 127 for ch in b): txt = "  '" + b.decode() + "'"
        except Exception: pass
        print(f"     w{i:3d} {w}{txt}")
    if r["tx"] not in R:
        R[r["tx"]] = rpc.call("eth_getTransactionReceipt", [r["tx"]])
        with open(C("s02_rcpt_cache.jsonl"), "a") as f: f.write(json.dumps(R[r["tx"]]) + "\n")
    rc = R[r["tx"]]
    print(f"   receipt status {rc['status']} gasUsed {int(rc['gasUsed'], 16)} logs {len(rc['logs'])}")
    for l in rc["logs"]:
        nm = SIG.get(l["topics"][0], l["topics"][0][:10]) if l["topics"] else "anon"
        extra = ""
        if nm in ("Transfer", "Approval") and len(l["topics"]) == 3: extra = f"{l['topics'][1][-40:]}->{l['topics'][2][-40:]} {int(l['data'], 16) if l['data'] != '0x' else ''}"
        elif nm == "Swap": extra = f"a0 {sgn(W(l['data'], 0))} a1 {sgn(W(l['data'], 1))} sqrtP {W(l['data'], 2)} L {W(l['data'], 3)} tick {sgn(W(l['data'], 4))} fee {W(l['data'], 5)} sender {l['topics'][2][-40:]}"
        elif nm == "ModifyLiquidity": extra = f"lo {sgn(W(l['data'], 0))} hi {sgn(W(l['data'], 1))} dL {sgn(W(l['data'], 2))} salt {l['data'][-64:][:16]} sender {l['topics'][2][-40:]}"
        elif nm == "Initialize": extra = f"c0 {l['topics'][2][-40:]} c1 {l['topics'][3][-40:]}"
        else: extra = f"topics {[x[:18] for x in l['topics'][1:]]} data {l['data'][:200]}"
        print(f"     {l['address']} {nm:18s} {extra}")
print(rpc.STATS)
