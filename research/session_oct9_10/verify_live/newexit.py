import sys, json, pickle; sys.path.insert(0,'..')
from reprice_lib import *
res=pickle.load(open("res.pkl","rb")); F=json.load(open("found.json"))
STAKE=1_200_000_000_000_000; GAS_TP=5_500_000_000_000; TP=0.01
gas={}
for h,r in F["rcs"].items(): gas[h]=int(r["gasUsed"],16)*int(r["effectiveGasPrice"],16)
table=[]
for k,pid,ev,st,fee0 in res:
    mine=[i for i,e in enumerate(ev) if e["mine"] and e["kind"]=="swap"]
    ib=mine[0]; b=ev[ib]; sl=ev[mine[-1]]
    N=b["bn"]; tok=b["a1"]; assert b["a0"]==-STAKE
    pull=next((e for e in ev if e["kind"]=="ml" and e["dL"]<0),None); PB=pull["bn"]
    buy_gas=gas[b["h"]]; sell_gas=gas[sl["h"]]
    # state after event j, but with our real sell removed: our sell is the last of our events; for points after it, ensure no other swaps between
    def state_upto(pred):
        """state after the last event satisfying pred (events in chain order), our real sell excluded"""
        sp=None; L=None; last=None
        for j,e in enumerate(ev):
            if not pred(e): break
            if j==mine[-1] and len(mine)>1: continue          # skip our real sell
            if j>mine[-1] and e["kind"]=="swap" and len(mine)>1: raise RuntimeError(f"trade {k}: a swap after our real sell before the point; need re-sim")
            sp,L=st[j]; last=e
        return sp,L
    fee=b["fee"]
    def val_at(X, where):
        """our full position sold in block X: where='start' (first tx of X) or 'end' (last tx of X)"""
        if PB<X or (PB==X and where=="end"): return 0, "after pull"
        sp,L=state_upto(lambda e: e["bn"]<X if where=="start" else e["bn"]<=X)
        return sell(sp,L,tok,fee)[1], ("pull in same block: before it only if our tx precedes the pull" if PB==X else "before pull")
    def r(out, net=True): return (out-STAKE-(buy_gas+sell_gas if net else 0))/STAKE
    # validation of the actual sell (re-sim with our actual amount from the state just before it)
    print(f"\n=== trade {k}  buy blk {N} txi {b['txi']}  real sell blk {sl['bn']} (+{sl['bn']-N}) txi {sl['txi']}  pull blk {PB} (+{PB-N}) txi {pull['txi']}  fee {fee}  tokens {tok:.4e}  gas buy {buy_gas/1e18:.7f} sell {sell_gas/1e18:.7f}")
    print(f"   real: ETH out {sl['a0']/1e18:.9f}  gross {sl['a0']/STAKE-1:+.2%}  net of both gas {r(sl['a0']):+.2%}  sold tokens {-sl['a1']:.4e} ({-sl['a1']/tok:.0%} of position)")
    # take profit scan: buys by others after ours, through block N+2 (the deadline send block)
    tp_block=None
    for j,e in enumerate(ev):
        if (e["bn"],e["li"])<=(N,b["li"]) or e["bn"]>N+2: continue
        if e["kind"]=="ml":
            if e["dL"]<0: print(f"   pull seen at blk +{e['bn']-N} before any TP"); break
            continue
        if e["mine"] or e["a0"]>=0: continue
        sp,L=st[j]; out=sell(sp,L,tok,fee)[1]; ret=(out-STAKE-GAS_TP)/STAKE
        print(f"   buy behind ours at +{e['bn']-N} txi {e['txi']} {-e['a0']/1e18:.4f} ETH: feed prices our sell {out/1e18:.9f} -> TP ret {ret:+.2%} {'TRIGGER' if ret>=TP else ''}")
        if ret>=TP: tp_block=e["bn"]; break
    send = tp_block if tp_block is not None else N+2
    why = "take-profit" if tp_block is not None else "deadline"
    row={"k":k,"N":N,"pull_rel":PB-N,"real_sell_rel":sl["bn"]-N,"why":why,"send_rel":send-N}
    for lab,X in (("fast",send+1),("slow",send+2)):
        for where in ("start","end"):
            out,note=val_at(X,where)
            row[f"{lab}_{where}"]=(X-N, out, r(out,False), r(out), note)
        o1=row[f"{lab}_start"]; o2=row[f"{lab}_end"]
        print(f"   new exit ({why}, sent when feed shows +{send-N}) {lab:4s}: lands +{X-N}: first-in-block {o1[2]:+.2%} gross / {o1[3]:+.2%} net;  last-in-block {o2[2]:+.2%} / {o2[3]:+.2%}  [{o2[4]}]")
    # fixed deadline landings +3, +4 regardless of TP
    for X in (N+3,N+4):
        for where in ("start","end"):
            out,note=val_at(X,where); row[f"dl{X-N}_{where}"]=(out, r(out,False), r(out), note)
        print(f"   pure deadline landing +{X-N}: {row[f'dl{X-N}_start'][1]:+.2%}..{row[f'dl{X-N}_end'][1]:+.2%} gross, {row[f'dl{X-N}_start'][2]:+.2%}..{row[f'dl{X-N}_end'][2]:+.2%} net  [{row[f'dl{X-N}_end'][3]}]")
    table.append(row)
json.dump(table,open("newexit.json","w"))
