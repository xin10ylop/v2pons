"""Forward watch (read-only): new v3crowd launches as they happen; for each, the relay's buy simulated as soon as the node has the pool
(eth_call, state overrides, nothing sent: FlipRelayV3's runtime at a test address, GasProbe at its owner), then the relay holding exactly those
tokens (the token's balances slot 0 set by override) selling everything at about launch + 80 (our sell), + 150 and + 300: an outsider's exit
at the engine's time on the live chain, whatever the crowd did meanwhile. Polls the factory every 4 s for up to MINUTES. Appends
s06_watch.jsonl and prints one line per check."""
from common import *
import rpc, solcx
from eth_abi import encode, decode
from v3dec import decode_launch_v3
MINUTES = float(sys.argv[1]) if len(sys.argv) > 1 else 70
art = json.load(open(os.path.join(HERE, "..", "..", "..", "..", "contracts", "FlipRelayV3.json")))
HARN = "0xa3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3a3"; RELAY_AT = "0xf3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3f3"
code = bytearray(bytes.fromhex(art["deployedBytecode"][2:]))
for refs in art["immutableReferences"].values():
    for r in refs: code[r["start"]:r["start"] + r["length"]] = bytes(12) + bytes.fromhex(HARN[2:])
RELAY_CODE = "0x" + code.hex()
PROBE = "0x" + [v for k, v in solcx.compile_files([J("GasProbe.sol")], output_values=["bin-runtime"], solc_version="0.8.26", optimize=True, optimize_runs=200,
                                                   evm_version="cancun").items() if k.endswith(":GasProbe")][0]["bin-runtime"]
sel = lambda s: keccak(text=s)[:4]
def probe(data, tag, extra=None):
    pd = sel("probe(address,bytes,uint256)") + encode(["address", "bytes", "uint256"], [RELAY_AT, data, 479000])
    o = {HARN: {"code": PROBE}, RELAY_AT: {"code": RELAY_CODE, "balance": hex(int(0.02e18))}}
    if extra: o.update(extra)
    r = rpc.call("eth_call", [{"from": "0x" + "c0" * 20, "to": HARN, "data": "0x" + pd.hex(), "gas": hex(30_000_000)}, tag, o])
    return decode(["bool", "uint256", "bytes"], bytes.fromhex(r[2:]))
LOG = J("s06_watch.jsonl")
def rec(d):
    with open(LOG, "a") as f: f.write(json.dumps(d) + "\n")
    print(json.dumps(d), flush=True)
STAKE = int(0.004e18)
t_end = time.time() + 60 * MINUTES; last = int(rpc.call("eth_blockNumber", []), 16); watch = {}
rec({"ev": "start", "head": last, "utc": utc(time.time()), "minutes": MINUTES})
while time.time() < t_end or watch:
    try:
        head = int(rpc.call("eth_blockNumber", []), 16)
        if time.time() < t_end and head > last:
            for l in rpc.logs({"address": FACT, "topics": [T_PC]}, last + 1, head):
                if int(l["topics"][3], 16) != 100 or WETH[2:] not in (l["topics"][1][-40:] + l["topics"][2][-40:]): continue
                t = rpc.call("eth_getTransactionByHash", [l["transactionHash"]]); n = (len(t["input"]) - 2) // 2
                shape = (t["to"] or "").lower() == NPM and t["input"][:10] == "0xac9650d8" and n == 836 and int(t["value"], 16) == 0
                d = decode_launch_v3(bytes.fromhex(t["input"][2:])) if shape else None
                lb = int(l["blockNumber"], 16)
                rec({"ev": "launch", "lb": lb, "pool": "0x" + l["data"][-40:], "shape": shape, "qs": d["qs"] if d else None, "tx": l["transactionHash"], "seen_at_head": head, "seen_off": head - lb})
                if d and d["qs"] == 0:
                    watch["0x" + l["data"][-40:]] = {"lb": lb, "token": "0x" + d["token"], "got": None, "todo": [80, 150, 300]}
            last = head
        for pool, w in list(watch.items()):
            tag = hex(head); ts = int(rpc.call("eth_getBlockByNumber", [tag, False])["timestamp"], 16)
            if w["got"] is None:
                ok, used, ret = probe(sel("buy(address,uint24,uint256,uint256,uint256)") + encode(["address", "uint24", "uint256", "uint256", "uint256"], [w["token"], 100, STAKE, 0, ts + 600]), tag)
                w["got"] = decode(["uint256"], ret)[0] if ok else 0
                rec({"ev": "buy_sim", "pool": pool, "off": head - w["lb"], "ok": ok, "gas": used, "tokens": w["got"], "err": None if ok else ret[:4].hex()})
                if not ok: watch.pop(pool); continue
            if w["todo"] and head - w["lb"] >= w["todo"][0]:
                off = w["todo"].pop(0); slot = "0x" + keccak(bytes.fromhex(word(RELAY_AT)) + bytes.fromhex(word(0))).hex()
                ok, used, ret = probe(sel("sell(address,uint24,uint256,uint256)") + encode(["address", "uint24", "uint256", "uint256"], [w["token"], 100, 0, ts + 600]), tag,
                                      {w["token"]: {"stateDiff": {slot: "0x" + word(w["got"])}}})
                back = decode(["uint256"], ret)[0] if ok else None
                burns = rpc.call("eth_getLogs", [{"address": pool, "topics": [T_BU], "fromBlock": hex(w["lb"]), "toBlock": tag}])
                rec({"ev": "sell_sim", "pool": pool, "target_off": off, "off": head - w["lb"], "ok": ok, "gas": used, "eth_back": back, "ret": back / STAKE - 1 if back else None,
                     "err": None if ok else ret[:4].hex(), "burns_so_far": sum(1 for b in burns if int(b["data"][2:66], 16) > 0)})
            if not w["todo"]: watch.pop(pool)
    except Exception as e:
        rec({"ev": "error", "err": str(e)[:200]})
    time.sleep(4)
rec({"ev": "end", "utc": utc(time.time()), "rpc": rpc.STATS})
