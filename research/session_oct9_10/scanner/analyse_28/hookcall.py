import sys, json
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import batch
sels = ['0a85dc29', '15d7892d', '46904840', '570c1085', '6c2bbe7e', '6fe7e6eb', '9731aa2e', '9f063efc', 'e1b4af69', 'f4364515', 'dc4c90d3']
hooks = {"20%": "0x4661a7531cbe009b894f32fd5e78b68205b640cc", "10%": "0x814cd89f930366081a815f42b74f85f9f303c0cc", "3%": "0x97d734d5aa8bf13f22cf62aa9cfc1100203ec0cc", "5%": "0xbf41b1d7273792d525e19463b0d32b0fc95800cc"}
calls = [("eth_call", [{"to": h, "data": "0x" + s}, "latest"]) for h in hooks.values() for s in sels]
res = batch(calls)
k = 0
out = {}
for name, h in hooks.items():
    for s in sels:
        r = res[k]; k += 1
        print(name, s, r if r is None or len(r) < 200 else r[:200])
        out[f"{name}:{s}"] = r
json.dump(out, open("hookcall.json", "w"), indent=0)
