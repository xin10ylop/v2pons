import sys, json, pickle
sys.path.insert(0, "..")
from chain import batch
d = json.load(open("tokcode.json"))
P = pickle.load(open("pools.pkl", "rb"))
tok2p = {p["token"].lower(): p for p in P.values()}
sels = ['0861ac61', '089fe6aa', '12f16a07', '3c130d90', '3de35b79', '536dac9b', '53cd512a', '665a11ca', '66a88d96', '70bffe1b', '7284e416', '791b98bc', '8036d590', '8c0b5e22', 'aa4bde28', 'abb1dc44', 'b8d8fbb4', 'baed0765', 'd00efb2f', 'd5f39488', 'fb7f21eb', 'ff8ea3e5', '18160ddd']
for fam in ("L:0x58daec31|0xac9650d8|len1444|fee10000|ts200|v5.0", "L:0x58daec31|0xac9650d8|len1444|fee10000|ts200|v3.0", "L:0x58daec31|0xac9650d8|len1444|fee2500|ts50|v2.433"):
    for x in d[fam][:2]:
        t = x["token"]; p = tok2p[t.lower()]
        r = batch([("eth_call", [{"to": t, "data": "0x" + s}, "latest"]) for s in sels])
        print("==", fam[-20:], t, "b0", p["b0"], "deployer", p["from"])
        for s, v in zip(sels, r):
            if v is None or v == "0x": continue
            if len(v) <= 66: print("  ", s, int(v, 16) if len(v) > 2 else v, v[-40:] if len(v) == 66 else "")
            else: print("  ", s, "len", len(v), bytes.fromhex(v[130:130 + 2 * min(80, int(v[66:130], 16))]).decode(errors="replace") if len(v) > 130 else v[:80])
