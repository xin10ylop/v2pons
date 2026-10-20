import sys
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import *
from load_all import load_all
pools, head = load_all()
recent = [p for p in pools if p["pull"] and p["kind"] == "orig" and p["pull"]["bn"] < head - 3000][-4:]
def scan_from(addr, start, span=4000):
    addr = addr.lower(); out = []
    for a in range(start, start + span, 100):
        bs = batch([("eth_getBlockByNumber", [hex(b), True]) for b in range(a, a + 100)])
        for b in bs:
            for x in (b or {}).get("transactions", []):
                if x["from"].lower() == addr: out.append((int(b["number"], 16), x))
        if len(out) >= 2: break
    return out
for p in recent:
    d = p["deployer"]; pb = p["pull"]["bn"]
    print(f"pool {p['pid'][:10]} deployer {d[:10]} pulled at {pb}")
    for bn, x in scan_from(d, pb + 1):
        print(f"   deployer tx nonce {int(x['nonce'],16)} at +{bn-pb}: to {x['to']} value {int(x['value'],16)/1e18:.4f} ETH input {x['input'][:10]}")
        if int(x["value"], 16) > 10**17 and x["to"]:
            for bn2, y in scan_from(x["to"], bn + 1, 3000):
                print(f"      then {x['to'][:10]} nonce {int(y['nonce'],16)} at +{bn2-bn}: to {y['to']} value {int(y['value'],16)/1e18:.4f} ETH")
