"""s06: at the head, for EVERY (token, holder) pair of s05 (all classes) and the dev wallets: balanceOf; for those with a balance,
(a) eth_call token.transfer(0x...dEaD, 1% of balance) FROM the holder's real address, no override;
(b) eth_call Portal.swapExactInput(token -> BNB, 1% of balance, minOut 0, permitData empty) FROM the holder's real address, with ONE state
    override: allowance[holder][Portal] = the amount (the holder's balance and every other slot are the real chain state; the override only
    stands in for the permit signature the holder would attach). Also (c) quoteExactInput for the same amount.
Read-only eth_call; nothing is sent. -> data/s06_head.json"""
import sys, os, json, collections as C, threading, queue
sys.path.insert(0, os.path.dirname(__file__))
import rpc
from eth_utils import keccak
D = os.path.join(os.path.dirname(__file__), "..", "data")
PORTAL = "0xe2ce6ab80874fa9fa2aae65d277dd6b8e65c9de0"; DEAD = "0x000000000000000000000000000000000000dEaD"
S = json.load(open(os.path.join(D, "s05_holders.json")))
fam = {r["token"]: r for r in json.load(open(os.path.join(D, "s02_family.json")))["family"]}
pairs = {(o["token"], o["holder"]): o["cls"] for o in S["rows"]}
for t, f in fam.items():
    for a in (f["from"], f["creator"]): pairs.setdefault((t, a), ["dev"])
HEADB = rpc.bn(); BLK = hex(HEADB)
def a32(a): return "0" * 24 + a[2:].lower()
def u32(x): return "%064x" % x
def slot_allow(o, s):
    inner = keccak(bytes.fromhex(a32(o) + u32(0x34)))
    return "0x" + keccak(bytes.fromhex(a32(s)) + inner).hex()
def dec(r):
    if isinstance(r, dict):
        e = r.get("__revert__"); d = e.get("data", "") if isinstance(e, dict) else ""
        if isinstance(d, str) and d.startswith("0x08c379a0"):
            try: return "REVERT:" + bytes.fromhex(d[138:]).rstrip(b"\0").decode(errors="replace")
            except Exception: pass
        return "REVERT:" + (d[:10] if d else str(e)[:80])
    return None
out = []; lk = threading.Lock(); Q = queue.Queue()
for k, v in pairs.items(): Q.put((k, v))
def work():
    while True:
        try: (tok, h), cls = Q.get_nowait()
        except queue.Empty: return
        try:
            bal = int(rpc.call("eth_call", [{"to": tok, "data": "0x70a08231" + a32(h)}, BLK]), 16)
            r = {"token": tok, "holder": h, "cls": cls, "bal": bal}
            if bal > 0:
                amt = max(1, bal // 100)
                x = rpc.call("eth_call", [{"from": h, "to": tok, "data": "0xa9059cbb" + a32(DEAD) + u32(amt)}, BLK])
                r["transfer_dead"] = dec(x) or ("ok" if isinstance(x, str) and int(x or "0x0", 16) == 1 else f"ret {x}")
                data = "0xef7ec2e7" + u32(0x20) + a32(tok) + "0" * 64 + u32(amt) + u32(0) + u32(0xa0) + u32(0)
                ov = {tok: {"stateDiff": {slot_allow(h, PORTAL): "0x" + u32(amt)}}}
                y = rpc.call("eth_call", [{"from": h, "to": PORTAL, "data": data}, BLK, ov])
                r["portal_sell"] = dec(y) or "ok"; r["sell_out_wei"] = int(y, 16) if isinstance(y, str) and len(y) >= 66 else None
                q = rpc.call("eth_call", [{"from": h, "to": PORTAL, "data": "0xfc847c2b" + a32(tok) + "0" * 64 + u32(amt)}, BLK])
                r["quote"] = dec(q) or int(q, 16)
        except Exception as e:
            r = {"token": tok, "holder": h, "cls": cls, "error": str(e)[:200]}
        with lk: out.append(r)
th = [threading.Thread(target=work) for _ in range(6)]
for t in th: t.start()
for t in th: t.join()
json.dump({"head": HEADB, "rows": out}, open(os.path.join(D, "s06_head.json"), "w"))
withbal = [r for r in out if r.get("bal")]
print("head", HEADB, "pairs", len(out), "with balance", len(withbal), "errors", sum(1 for r in out if "error" in r))
for grp in ("outsider", "crowd", "dev", "other"):
    g = [r for r in withbal if (grp in r["cls"]) or (grp == "other" and not any(c in r["cls"] for c in ("outsider", "crowd", "dev")))]
    print(grp, len(g), "transfer:", C.Counter(r.get("transfer_dead") for r in g), "sell:", C.Counter(r.get("portal_sell") for r in g))
