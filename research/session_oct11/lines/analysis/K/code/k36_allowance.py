"""does a curve sell need the holder's approval? allowance(holder, curve) of the k35 holders, and a sell simulated from a fresh holder:
state override gives FRESH the tokens' balance slot is unknown, so instead simulate transferFrom-style: sell from a holder whose allowance is 0."""
import json
from krpc import *
R = json.load(open(os.path.join(OUT, "k35_simulate.json")))
def ea(a): return a[2:].rjust(64, "0")
out = []
for o in R:
    import pickle
    tok = None
    P = pickle.load(open(os.path.join(DATA, "packed.pkl"), "rb")) if not tok else None
    tok = P["creates"][o["curve"]]["token"]
    al = int(rpc("eth_call", [{"to": tok, "data": "0xdd62ed3e" + ea(o["holder"]) + ea(o["curve"])}, "latest"]), 16)
    o2 = {"curve": o["curve"], "holder": o["holder"], "allowance_to_curve": al, "sell_no_approval": o["sell_no_approval"]}
    out.append(o2); print(o2)
json.dump(out, open(os.path.join(OUT, "k36_allowance.json"), "w"), indent=1)
