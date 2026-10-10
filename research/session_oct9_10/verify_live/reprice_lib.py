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
