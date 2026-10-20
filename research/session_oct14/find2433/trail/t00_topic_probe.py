import rpc, json, time, sys
w=sys.argv[1].lower(); a=int(sys.argv[2]); b=int(sys.argv[3]); P="0x"+"0"*24+w[2:]
for pos in (1,2,3):
    topics=[None]*pos+[P]; n=0
    for s in range(a,b+1,30000):
        e=min(b,s+29999)
        r=rpc.call("eth_getLogs",[{"fromBlock":hex(s),"toBlock":hex(e),"topics":topics}])
        for l in r:
            n+=1
            if n<=40: print(pos,int(l["blockNumber"],16),l["address"],l["topics"][0][:10],[x[-40:][:8] for x in l["topics"][1:]],l["transactionHash"][:14],l["data"][:66])
    print("pos",pos,"total",n)
print(rpc.STATS)
