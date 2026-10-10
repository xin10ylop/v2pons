import sys; sys.path.insert(0, "/home/user/v2pons/src")
import v4math
SP=1604517591721945638372359205383840; L=49279426163460954002188; F=2500
def net(x): return x - (x*F+999_999)//1_000_000
for bot in (0.04,0.05,0.1,0.25):
    v=int(bot*1e18); q0=v4math.buy_out_int(SP,L,v,F)
    # find the ahead amount where q1 < 0.99 q0
    lo,hi=0,int(0.1e18)
    while hi-lo>1e12:
        m=(lo+hi)//2; sp=int(v4math.sqrt_after_buy(float(SP),L,net(m)))
        q1=v4math.buy_out_int(sp,L,v,F)
        if q1 < q0*0.99: hi=m
        else: lo=m
    print(bot, "reverts once ahead >=", hi/1e18)
