exec(open(__file__.replace("probe_code.py", "probe_base.py")).read())
E.ENTRY = "seat"; E.LAUNCH_SELECTORS = {"2fcb9108"}; FRESH = "0x" + "5e" * 20
OP_CODE = "0x" + "60806040" * 50; E.LAUNCHER_CODE_HASHES = {keccak(bytes.fromhex(OP_CODE[2:])).hex()}
calls = []
_rpc = E.rpc
def lagging(method, params, tries=4, timeout=10):
    if method == "eth_getCode":
        calls.append(params); return "0x" if len(calls) == 1 else OP_CODE      # the first answer from a backend 8 blocks behind: the copy not deployed yet
    return _rpc(method, params, tries, timeout)
E.rpc = lagging
reset(); E.state["nonce"] = 110
raw = signed(DEPLOYER, FRESH, 0, "0x2fcb9108" + w(1), 2); h = "0x" + keccak(raw).hex(); RECEIPTS[h] = launch_receipt(h)
E.ingest(frame(1900, [raw])); assert wait_for(lambda: PID in E.state["armed"])
p = E.state["armed"][PID]; print("eligible", p["eligible"], "launcher_code", p["launcher_code"], "getCode calls", len(calls))
for s_ in range(1901, 1908): E.ingest(frame(s_, []))
print("position", E.state["position"])
