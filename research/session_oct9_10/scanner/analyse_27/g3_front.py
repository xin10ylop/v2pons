"""G3 front, priced two ways:
 naive  = our buy at launch+1, sell one block after the scheduled UR buy (the pricer never drops a UR buy)
 minout = the scheduled UR buy is dropped (reverts) if, with our stake in front, its output < 0.99 x its launch-state quote;
          when dropped we have no buy to sell into -> we hold to launch+hold; if the pull lands by our sell = stake lost
Also: dust-bot / outsider presence; pull margin after the scheduled buy; capacity per stake."""
import sys, os, json, collections, statistics as st
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
from common27 import *  # noqa
import v4math
P=load_pools(); T=load_txs(); M=load_blocks_meta()
g3=[p for p in P.values() if (p["to_code_hash"] or "").replace("0x","").startswith("f07d1c53")]
E=load_events(set(p["pid"] for p in g3))
PL={p["pid"]:Pool(p,E.get(p["pid"]),T,M) for p in g3}
DUST="0xe71a69f434a719cd5afa411568b69716aab3b84a"
# dust / outsider presence across all 102
dust=sum(1 for pl in PL.values() if any(x["from"]==DUST for x in pl.seq))
nonop=sum(1 for pl in PL.values() if any(x["from"] not in (DUST, "0x9fdd8ceab2de4fa2d9b0f1f37475a47baff8cd9a") and not x["in_launch"] for x in pl.seq))
print("pools", len(PL), "with dust-bot buy", dust, "with any non-op non-dust swap", nonop)

def sched(pl):
    for x in pl.seq:
        if x["buy"] and not x["relay"] and not x["in_launch"] and x["eth"]>=MIN_REAL and x["from"] not in (DUST,):
            return x
    return None

def front_minout_aware(pl, stake, hold=20, slack=0.99):
    lb=pl.b0; B=lb+1
    if pl.pull_bn is not None and pl.pull_bn<=B: return {"exit":"pull_before_buy","ret":(-stake-pl.gas)/stake}
    sb=sched(pl)
    # does our stake in front make the scheduled buy fall under 0.99 x its launch-state quote?
    reverts=False
    if sb is not None:
        s0,L0=pl.launch_state(); fee=pl.fee_at(sb["bn"]); Y=sb["eth"]
        quote=v4math.buy_out_int(int(s0),L0,Y,fee); mo=int(quote*slack)
        s_us=Q96/(Q96/s0 + net_in(stake,fee)/L0)
        out_with_us=v4math.buy_out_int(int(s_us),L0,Y,fee)
        reverts = out_with_us < mo
    if sb is None or reverts:
        S=lb+hold
        r=pl.trade(B,S,stake); r["exit"]=("sched_reverts_"+r["exit"]) if reverts else ("no_sched_"+r["exit"]); r["sched_reverts"]=reverts; return r
    S=sb["bn"]+1 if sb["bn"]+1<=lb+hold else lb+hold
    r=pl.trade(B,S,stake); r["sched_reverts"]=False; return r

def front_naive(pl, stake, hold=20):
    lb=pl.b0; B=lb+1; sb=sched(pl)
    S=sb["bn"]+1 if (sb and sb["bn"]+1<=lb+hold) else lb+hold
    return pl.trade(B,S,stake)

out={}
for stake_eth in (0.0058, 0.004, 0.003, 0.002):
    stake=int(stake_eth*1e18)
    naive=[front_naive(pl,stake) for pl in PL.values()]
    mo=[front_minout_aware(pl,stake) for pl in PL.values()]
    rev=sum(1 for r in mo if r.get("sched_reverts"))
    out["stake_%.4f"%stake_eth]={"naive":summarize(naive),"minout_aware":summarize(mo),"sched_reverts":rev}
    print("stake %.4f ETH ($%.1f): reverts %d/102 | NAIVE %s | MINOUT %s" % (stake_eth, stake_eth*USD_PER_ETH, rev, fmt_rule(summarize(naive)), fmt_rule(summarize(mo))))

# capacity per stake (exact room ahead of the scheduled buy before it falls under 0.99 x launch quote)
caps=[]
for pl in PL.values():
    sb=sched(pl)
    if not sb: continue
    s0,L0=pl.launch_state(); fee=pl.fee_at(sb["bn"]); Y=sb["eth"]; quote=v4math.buy_out_int(int(s0),L0,Y,fee)
    caps.append(room(s0,L0,Y,fee,int(quote*0.99)))
out["capacity_room_p10_50_90"]=q(caps)
out["sched_buy_eth_p10_50_90"]=q([sched(pl)["eth"]/1e18 for pl in PL.values() if sched(pl)])
out["sched_off_p10_50_90"]=q([sched(pl)["bn"]-pl.b0 for pl in PL.values() if sched(pl)])
out["pull_minus_sched_p10_50_90"]=q([pl.pull_bn-sched(pl)["bn"] for pl in PL.values() if sched(pl) and pl.pull_bn])
out["pull_minus_sched_hist"]=collections.Counter(pl.pull_bn-sched(pl)["bn"] for pl in PL.values() if sched(pl) and pl.pull_bn).most_common(8)
print("capacity room p10/50/90", out["capacity_room_p10_50_90"], "ETH;  sched buy eth", out["sched_buy_eth_p10_50_90"])
print("sched off", out["sched_off_p10_50_90"], "pull-minus-sched", out["pull_minus_sched_p10_50_90"], out["pull_minus_sched_hist"])
json.dump(out, open(os.path.join(HERE,"g3_front.json"),"w"), indent=1, default=str)
