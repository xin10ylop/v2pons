from chain import *
import sys
def trace(w, start, depth, span=8000):
    w = w.lower()
    for end in range(start, start - span, -100):
        bs = batch([("eth_getBlockByNumber", [hex(b), True]) for b in range(end - 99, end + 1)])
        for b in reversed(bs):
            for x in (b or {}).get("transactions", []):
                if (x.get("to") or "").lower() == w and int(x["value"], 16) > 0:
                    bn = int(b["number"], 16)
                    print("  " * depth + f"{w[:10]} <- {x['from']} (nonce {int(x['nonce'],16)}) {int(x['value'],16)/1e18:.4f} ETH at block {bn} ({start - bn} blocks earlier)")
                    return x["from"], bn, int(x["nonce"], 16)
    print("  " * depth + f"{w[:10]}: no direct transfer in {span} blocks"); return None, None, None
for w, b in [("0x822b5e4c95aaa7c3c0f2f570a2d4e726aa47e337", 84073094 - 1491), ("0x5f31f08bef4e8f0686c3c9466419cf1d5c407fbf", 84076031 - 369),
             ("0x91fe82239c3079d025f0cea034bc1efcb564eb83", 84083388 - 367), ("0xe946db63701a3227c03611284f95b34d43f72dde", 84091675 - 290)]:
    cur, bn = w, b
    for depth in range(4):
        f, bn2, n = trace(cur, bn, depth)
        if f is None or n is None or n > 5: break
        cur, bn = f, bn2
