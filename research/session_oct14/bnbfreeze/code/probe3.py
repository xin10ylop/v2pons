import sys; sys.path.insert(0,".")
from rpc import rpc, URLS, _one
import json
TOK="0x950e681819a68f595bb3db313346393d64f66bb5"; DEAD="0x000000000000000000000000000000000000dead"
W="0x8881bba6787848f4e86780ef69a34bb45c8d4fcb"; C="0x5339668e4dece6f25645b117265a465859672487"
def xfer_data(to,amt): return "0xa9059cbb"+to[2:].rjust(64,"0")+hex(amt)[2:].rjust(64,"0")
amt=1000
# A: US transfer
print("A US transfer(dead,1000):", rpc("eth_call",[{"from":W,"to":TOK,"data":xfer_data(DEAD,amt)},"latest"]))
# B: crowd transfer
print("B CROWD transfer(dead,1000):", rpc("eth_call",[{"from":C,"to":TOK,"data":xfer_data(DEAD,amt)},"latest"]))
# capability probes on each endpoint
for U in URLS:
    for m,p in [("eth_simulateV1",[{"blockStateCalls":[{"calls":[{"from":W,"to":TOK,"data":xfer_data(DEAD,amt)}]}]},"latest"]),
                ("debug_traceCall",[{"from":W,"to":TOK,"data":xfer_data(DEAD,amt)},"latest",{"tracer":"callTracer"}])]:
        try:
            r=_one(U,{"jsonrpc":"2.0","id":1,"method":m,"params":p})
            ok = "result" in r
            print(f"{U.split('//')[1][:22]:24} {m:16} ->", "OK" if ok else ("ERR "+str(r.get('error',{}).get('message',''))[:50]))
        except Exception as e:
            print(f"{U.split('//')[1][:22]:24} {m:16} -> EXC", str(e)[:40])
