import json, sys, os
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10"); import chain
D=json.load(open("g3_raw.json")); G=D["pools"]
BUY="0x9fdd8ceab2de4fa2d9b0f1f37475a47baff8cd9a"
addrs=[BUY]+sorted(set(p["launch_from"] for p in G))
res=chain.batch([("eth_getBalance",[a,"latest"]) for a in addrs]+[("eth_getTransactionCount",[a,"latest"]) for a in addrs])
n=len(addrs); out={}
for i,a in enumerate(addrs): out[a]=(int(res[i],16)/1e18, int(res[n+i],16))
print("buyer", out[BUY], "head", int(chain.rpc("eth_blockNumber",[]),16))
tot=0
for a in addrs[1:]: tot+=out[a][0]
import collections
print("launch wallets total ETH now %.4f" % tot, "nonce dist", collections.Counter(v[1] for a,v in out.items() if a!=BUY))
print(sorted((round(v[0],5),a[:10]) for a,v in out.items() if a!=BUY)[-10:])
print(sorted((round(v[0],5),a[:10]) for a,v in out.items() if a!=BUY)[:5])
json.dump(out,open("balances_now.json","w"))
