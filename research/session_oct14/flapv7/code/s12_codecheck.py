"""s12: every family token at the head: EIP-1167 proxy target, owner (slot 0xcc), state slot 0x103, the Dividend (0x104) clone's
implementation and owner, the TaxProcessor (0x105) clone's implementation, the hook (0x106). Also the implementation contracts' code is
immutable (no DELEGATECALL / SELFDESTRUCT in the v7 implementation or the Dividend implementation). -> data/s12.json, stdout"""
import json, os, sys, collections as C
sys.path.insert(0, os.path.dirname(__file__))
import rpc
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
fam = json.load(open(os.path.join(D, "s02_family.json")))["family"]
c = C.Counter(); rows = []
def st(a, s): return rpc.call("eth_getStorageAt", [a, s, "latest"])
for f in fam:
    t = f["token"]; code = rpc.call("eth_getCode", [t, "latest"])
    impl = "0x" + code[22:62] if (len(code) - 2) // 2 == 45 else "not-1167"
    owner = "0x" + st(t, "0xcc")[-40:]; state = int(st(t, "0x103"), 16)
    dv = "0x" + st(t, "0x104")[-40:]; tp = "0x" + st(t, "0x105")[-40:]; hk = "0x" + st(t, "0x106")[-40:]
    dcode = rpc.call("eth_getCode", [dv, "latest"]); dimpl = "0x" + dcode[22:62]
    tcode = rpc.call("eth_getCode", [tp, "latest"]); timpl = "0x" + tcode[22:62]
    downer = "0x" + rpc.ethcall(dv, "0x8da5cb5b")[-40:]
    r = {"token": t, "impl": impl, "owner": owner, "state": state & 0xff, "state_ts": state >> 8, "div_impl": dimpl, "div_owner": downer, "tp_impl": timpl, "hook": hk}
    rows.append(r)
    for k in ("impl", "owner", "state", "div_impl", "div_owner", "tp_impl", "hook"): c[(k, r[k])] += 1
for k, v in sorted(c.items(), key=str): print(k, v)
json.dump(rows, open(os.path.join(D, "s12.json"), "w"), indent=1)
