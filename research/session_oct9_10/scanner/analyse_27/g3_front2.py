"""G3 front priced with the scheduled UR buy actually DROPPED from the sell-side replay when our stake pushes it under
0.99 x its launch-state quote. Reverted pools: nothing to sell into -> hold to launch+20; pull is at +26..32 so no stake lost,
we exit at ~two-fees loss. Filled pools: sell one block after the scheduled buy."""
import sys, os, json, collections, statistics as st
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
from common27 import *  # noqa
import v4math
P=load_pools(); T=load_txs(); M=load_blocks_meta()
g3=[p for p in P.values() if (p["to_code_hash"] or "").replace("0x","").startswith("f07d1c53")]
E=load_events(set(p["pid"] for p in g3))
PL={p["pid"]:Pool(p,E.get(p["pid"]),T,M) for p in g3}
DUST="0xe71a69f434a719cd5afa411568b69716aab3b84a"
def sched(pl):
    for x in pl.seq:
        if x["buy"] and not x["relay"] and not x["in_launch"] and x["eth"]>=MIN_REAL and x["from"]!=DUST: return x
    return None

def front(pl, stake, hold=20, slack=0.99):
    lb=pl.b0; B=lb+1
    if pl.pull_bn is not None and pl.pull_bn<=B: return {"exit":"pulled_before_buy","ret":None}
    sb=sched(pl)
    # will the scheduled buy revert with us in front?
    reverts=False
    if sb is not None:
        s0,L0=pl.launch_state(); fee=pl.fee_at(sb["bn"]); Y=sb["eth"]
        quote=v4math.buy_out_int(int(s0),L0,Y,fee)
        s_us=Q96/(Q96/s0 + net_in(stake,fee)/L0)
        reverts = v4math.buy_out_int(int(s_us),L0,Y,fee) < int(quote*slack)
    S = (sb["bn"]+1 if (sb and not reverts and sb["bn"]+1<=lb+hold) else lb+hold)
    # replay by hand so we can drop the scheduled buy if it reverts
    s,L=pl.state_through(B)
    if L<=0: return {"exit":"no_liq","ret":None}
    fb,fs=pl.fee_at(B),pl.fee_at(S)
    tokens=v4math.buy_out_int(int(s),L,stake,fb)
    s=Q96/(Q96/s + net_in(stake,fb)/L)
    if pl.pull_bn is not None and pl.pull_bn<=S: return {"exit":"pulled_first","ret":(-stake-pl.gas)/stake,"S":S-lb}
    for x in pl.seq:
        if x["bn"]<=B: continue
        if x["bn"]>=S: break
        if x["relay"]: continue
        if reverts and sb is not None and (x["bn"],x["li"])==(sb["bn"],sb["li"]): continue   # drop the reverted scheduled buy
        L=x["liq"] if x["liq"] else L
        s=pl.apply(s,x)
    eth_out=v4math.sell_out_int(int(s),L,tokens,fs)
    return {"exit":"sold_reverted" if reverts else ("sold_nosched" if sb is None else "sold"),"ret":(eth_out-stake-pl.gas)/stake,"reverts":reverts,"S":S-lb}

out={}
for stake_eth in (0.0058,0.004,0.003,0.002):
    stake=int(stake_eth*1e18); rs=[front(pl,stake) for pl in PL.values()]
    rev=sum(1 for r in rs if r.get("reverts"))
    s=summarize(rs)
    out["stake_%.4f"%stake_eth]={"summary":s,"reverts":rev,"win_big":sum(1 for r in rs if r.get("ret") and r["ret"]>0.1)}
    print("stake %.4f ($%.1f): reverts %d win>+10%% %d | %s" % (stake_eth, stake_eth*USD_PER_ETH, rev, sum(1 for r in rs if r.get("ret") and r["ret"]>0.1), fmt_rule(s)))
json.dump(out,open(os.path.join(HERE,"g3_front2.json"),"w"),indent=1,default=str)
