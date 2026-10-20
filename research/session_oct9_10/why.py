import json
from chain import *
from eth_utils import keccak
H = {"T1+6": None}
# find the reverted txs again by scanning
D = json.load(open("oct8.json")); pools = D["pools"]; ev = D["ev"]
cands = [("T1", 83341743 + 6, "64386cda"), ("T3", 83342495 + 4, "86faebe1"), ("T5", 83343304 + 15, "f149b78f")]
for name, bn, frm in cands:
    b = rpc("eth_getBlockByNumber", [hex(bn), True])
    t = [x for x in b["transactions"] if x["from"][2:10] == frm][0]
    for at in (hex(bn - 1), hex(bn)):
        r = post({"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": [{"from": t["from"], "to": t["to"], "value": t["value"], "data": t["input"], "gas": t["gas"]}, at]})
        print(name, frm, "state at", int(at, 16) - bn, "->", json.dumps(r.get("error") or r.get("result"))[:300])
    tr = post({"jsonrpc": "2.0", "id": 1, "method": "debug_traceTransaction", "params": [t["hash"], {"tracer": "callTracer"}]})
    print("   trace:", json.dumps(tr)[:1500])
sels = ["V4TooLittleReceived(uint256,uint256)", "TooLittleReceived()", "DeadlinePassed(uint256)", "TransactionDeadlinePassed()", "ExecutionFailed(uint256,bytes)", "InsufficientBalance()", "TransferFromFailed()", "CurrencyNotSettled()", "PoolNotInitialized()", "PriceLimitAlreadyExceeded(uint160,uint160)", "SwapAmountCannotBeZero()", "NoLiquidityToReceiveFees()", "WrappedError(address,bytes4,bytes,bytes)", "AllowanceExpired(uint256)", "InsufficientAllowance(uint256)", "V4TooMuchRequested(uint256,uint256)"]
for s in sels: print(keccak(text=s).hex()[:8], s)
