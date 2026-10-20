"""Independent reprice of the 8 live trades (own v4 integer math, written from the v4-core SqrtPriceMath/SwapMath formulas)."""
import sys, json; sys.path.insert(0,'..')
from chain import W, sgn, T_SWAP, T_ML
P=json.load(open("pools.json")); F=json.load(open("found.json"))
WAL="0xab5a34c3f41e57fdee1a1d6f19d3e21f46df3ea8"
Q96=1<<96; MAXU160=(1<<160)-1
def s(x,bits):
    x&=(1<<bits)-1
    return x-(1<<bits) if x>=(1<<(bits-1)) else x
def less_fee(a,fee): return a*(10**6-fee)//10**6            # SwapMath: amountRemainingLessFee = mulDiv(amountRemaining, 1e6-fee, 1e6)
def buy(sp,L,eth,fee):                                       # zeroForOne exact-in: getNextSqrtPriceFromAmount0RoundingUp, getAmount1Delta(rounding down)
    a=less_fee(eth,fee); n1=L<<96
    den=n1+a*sp; spn=-(-n1*sp//den)
    return spn, L*(sp-spn)//Q96
def sell(sp,L,tok,fee):                                      # oneForZero exact-in: getNextSqrtPriceFromAmount1RoundingDown, getAmount0Delta(rounding down)
    if L==0: return sp,0
    a=less_fee(tok,fee)
    q=(a<<96)//L if a<=MAXU160 else a*Q96//L
    spn=sp+q
    return spn, ((L<<96)*(spn-sp)//spn)//sp
def decode(l):
    d=l["data"]; return dict(bn=int(l["blockNumber"],16), li=int(l["logIndex"],16), h=l["transactionHash"], kind="swap" if l["topics"][0]==T_SWAP else "ml",
        a0=s(W(d,0),128) if l["topics"][0]==T_SWAP else None, a1=s(W(d,1),128) if l["topics"][0]==T_SWAP else None,
        sp=W(d,2) if l["topics"][0]==T_SWAP else None, L=W(d,3) if l["topics"][0]==T_SWAP else None, fee=W(d,5) if l["topics"][0]==T_SWAP else None,
        tl=s(W(d,0),24) if l["topics"][0]==T_ML else None, tu=s(W(d,1),24) if l["topics"][0]==T_ML else None, dL=sgn(W(d,2)) if l["topics"][0]==T_ML else None)
GAS_TP=5_500   # 0.0000055 ETH in gwei-units*1e3 -> use wei below
GAS_TP_WEI=5_500_000_000_000
STAKE=1_200_000_000_000_000
res=[]; maxerr=0; nval=0
for pid,p in sorted(P.items(), key=lambda kv: kv[1]["k"]):
    k=p["k"]; I=p["init"]; fee0=W(I["data"],0); sp=W(I["data"],3)
    ev=[decode(l) for l in p["ev"]]; ev.sort(key=lambda e:(e["bn"],e["li"]))
    for e in ev: e["mine"]=p["tx"][e["h"]]["from"].lower()==WAL; e["txi"]=int(p["tx"][e["h"]]["idx"],16)
    # ---- validation: replay every swap from the previous state with its gross input, compare to the event
    L=0; st=[]   # st[i] = state AFTER event i : (sp, L)
    for e in ev:
        if e["kind"]=="ml":
            if e["tl"]<=0<=e["tu"] or True: L+=e["dL"]     # all positions are full range [-887200,887200] (checked in the timeline)
            assert e["tl"]==-887200 and e["tu"]==887200
        else:
            if e["a0"]<0 and e["a1"]>=0:   # buy: eth in = -a0
                spn,out=buy(sp,L,-e["a0"],e["fee"]); err=(out-e["a1"]); nval+=1
                if e["a1"]: maxerr=max(maxerr,abs(err)/e["a1"])
                if spn!=e["sp"] or out!=e["a1"]: print(f"  [val] trade {k} buy blk {e['bn']} sim out {out} vs ev {e['a1']} (rel {err/max(1,e['a1']):.2e}); sp {spn} vs {e['sp']}")
            elif e["a1"]<0:                # sell: tokens in = -a1
                spn,out=sell(sp,L,-e["a1"],e["fee"]); err=(out-e["a0"]); nval+=1
                maxerr=max(maxerr,abs(err)/e["a0"])
                print(f"  [val] trade {k} SELL blk {e['bn']} {'(ours)' if e['mine'] else ''} sim ETH out {out} vs event {e['a0']} (diff {err} wei, rel {err/e['a0']:.2e}); sqrtP sim {spn} vs ev {e['sp']}")
            else:
                spn=e["sp"]   # zero swap after the pull
            sp=e["sp"]; assert L==e["L"] or L==0, (k,L,e["L"])
        st.append((sp,L))
    json.dump(None,open("/dev/null","w"))
    res.append((k,pid,ev,st,fee0))
print("validated swaps",nval,"max rel err",maxerr)
json.dump([[k,pid] for k,pid,_,_,_ in res],open("order.json","w"))
import pickle; pickle.dump(res,open("res.pkl","wb"))
