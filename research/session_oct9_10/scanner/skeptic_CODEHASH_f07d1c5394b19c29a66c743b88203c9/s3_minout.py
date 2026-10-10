"""Decode the scheduled buy's Universal Router execute(0x3593564c): commands, the V4_SWAP actions and the
SWAP_EXACT_IN_SINGLE amountIn / amountOutMinimum; compare with the launch-state quote, the actual output and compute
the exact room (ETH that can sit ahead of it before its output falls under its own minOut)."""
import sys, json, collections, statistics as st
sys.path.insert(0, "/home/user/v2pons/src"); import v4math
D=json.load(open("g3_raw.json")); G=D["pools"]; E=D["events"]; T=D["txs"]
Q96=1<<96
def words(h): h=h[10:]; return [h[i:i+64] for i in range(0,len(h),64)]
def ur_decode(inp):
    b=bytes.fromhex(inp[10:])
    w=lambda o: int.from_bytes(b[o:o+32],"big")
    o_cmd=w(0); o_inp=w(32); deadline=w(64)
    ncmd=w(o_cmd); cmds=b[o_cmd+32:o_cmd+32+ncmd]
    ninp=w(o_inp); base=o_inp+32
    inputs=[]
    for i in range(ninp):
        off=base+w(base+32*i); ln=w(off); inputs.append(b[off+32:off+32+ln])
    return cmds, inputs, deadline
def v4swap(inb):
    w=lambda o: int.from_bytes(inb[o:o+32],"big")
    o_act=w(0); o_par=w(32)
    na=w(o_act); acts=inb[o_act+32:o_act+32+na]
    npar=w(o_par); base=o_par+32; params=[]
    for i in range(npar):
        off=base+w(base+32*i); ln=w(off); params.append(inb[off+32:off+32+ln])
    return acts, params
def exact_in_single(pb):
    w=lambda o: int.from_bytes(pb[o:o+32],"big")
    s=w(0)  # tuple offset
    c0=w(s); c1=w(s+32); fee=w(s+64); ts=w(s+96); hook=w(s+128); z41=w(s+160); amt_in=w(s+192); min_out=w(s+224); extra=w(s+256)
    return dict(c0=c0,c1="0x%040x"%c1,fee=fee,ts=ts,hook="0x%040x"%hook,zfo=z41,amt_in=amt_in,min_out=min_out,extra=extra)
out=[]; cmdc=collections.Counter(); actc=collections.Counter(); rat=[]; ratq=[]; rooms=[]; deadlines=[]; lens=collections.Counter()
for p in G:
    sw=E[p["pid"]]["swaps"]
    if not sw: continue
    s=sw[0]; t=T[s["tx"]]
    lens[t["calldata_len"]]+=1
    cmds,inputs,dl=ur_decode(t["input"]); cmdc[cmds.hex()]+=1
    i10=[k for k,c in enumerate(cmds) if c&0x3f==0x10][0]
    acts,params=v4swap(inputs[i10]); actc[acts.hex()]+=1
    x=exact_in_single(params[0])
    assert x["c1"]==p["token"] and x["hook"]==p["hooks"] and x["fee"]==2500 and x["ts"]==25 and x["zfo"]==1, (x,p["token"])
    sq0=p["sqrt_p0"]; L=p["liq_launch"]
    q=v4math.buy_out_int(sq0,L,x["amt_in"],2500)
    actual=s["a1"]
    rat.append(x["min_out"]/actual); ratq.append(x["min_out"]/q)
    # exact room ahead: largest eth ahead (bisection, wei) s.t. buy_out_int(after us, amt_in) >= min_out
    lo,hi=0,10**19
    def ok(a):
        if a==0: return q>=x["min_out"]
        xin=a-(a*2500+999999)//1000000
        sqa=(L*sq0 + (L+(xin*sq0)//Q96) -1)//(L+(xin*sq0)//Q96)
        return v4math.buy_out_int(sqa,L,x["amt_in"],2500)>=x["min_out"]
    while hi-lo>10**9:
        m=(lo+hi)//2
        if ok(m): lo=m
        else: hi=m
    rooms.append(lo/1e18)
    deadlines.append(dl - B if (B:=None) else dl)
    out.append(dict(pid=p["pid"],lb=p["launch_block"],sb=s["bn"],amt_in=x["amt_in"],value=t["value_wei"],min_out=x["min_out"],quote=q,actual=actual,room_eth=lo/1e18,deadline=dl,
                    extra=x["extra"],gas=t["gas"],gas_price=t["gas_price"],prio=t["max_prio"],nonce=t["nonce"],ti=t["ti"]))
def pct(xs): xs=sorted(xs); n=len(xs); return [round(xs[int(q*(n-1))],6) for q in (0,0.1,0.5,0.9,1)]
print("n", len(out), "calldata lens", lens, "commands", cmdc, "actions", actc)
print("minOut / actual output  min,p10,p50,p90,max", pct(rat))
print("minOut / launch-state quote", pct(ratq))
print("actual / quote", pct([o["actual"]/o["quote"] for o in out]))
print("room ahead ETH", pct(rooms))
print("rooms <0.0058:", sum(r<0.0058 for r in rooms), "<0.004:", sum(r<0.004 for r in rooms), "<0.002:", sum(r<0.002 for r in rooms))
print("value==amt_in", sum(o["value"]==o["amt_in"] for o in out), "extra field", collections.Counter(o["extra"] for o in out))
print("nonce range", min(o["nonce"] for o in out), max(o["nonce"] for o in out), "prio", collections.Counter(o["prio"] for o in out))
print("tx index in block", collections.Counter(o["ti"] for o in out))
json.dump(out, open("minout.json","w"))
