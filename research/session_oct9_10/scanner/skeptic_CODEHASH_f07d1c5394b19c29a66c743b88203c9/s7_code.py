import json, sys, os, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10"); import chain
from eth_utils import keccak
D=json.load(open("g3_raw.json")); G=D["pools"]
hooks=[p["hooks"] for p in G]; toks=[p["token"] for p in G]; lts=[p["launch_to"] for p in G]
res=chain.batch([("eth_getCode",[a,"latest"]) for a in hooks+toks+lts])
n=len(G)
hc=collections.Counter(keccak(hexstr=c).hex()[:16]+":%d"%((len(c)-2)//2) for c in res[:n])
tc=collections.Counter(keccak(hexstr=c).hex()[:16]+":%d"%((len(c)-2)//2) for c in res[n:2*n])
lc=collections.Counter(keccak(hexstr=c).hex()[:16]+":%d"%((len(c)-2)//2) for c in res[2*n:])
print("hook code hashes", hc); print("token code hashes", tc); print("launch code", lc)
os.makedirs("code",exist_ok=True)
open("code/hook0.hex","w").write(res[3]); open("code/token0.hex","w").write(res[n+3]); open("code/launch0.hex","w").write(res[2*n+3])
