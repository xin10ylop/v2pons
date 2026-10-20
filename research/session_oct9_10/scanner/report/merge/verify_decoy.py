# Verify the critic's error 1: 0x8cf143dd sells in fresh v3.0 pools ordered against the bot's buy, and the pull offset after the bot's buy.
import sys, json, collections, statistics as st
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import T_SWAP, T_ML, W, sgn
D = "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/report/work/fresh2"
pools = json.load(open(D + "/pools.json")); ev = json.load(open(D + "/events.json")); txs = json.load(open(D + "/txs.json"))
ROUTER = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"; F = "0x8cf143dd"
def s128(x): x = sgn(x); return x - (1 << 128) if x >= (1 << 127) else x
cat = collections.Counter(); rets = collections.defaultdict(list); pullrel = collections.defaultdict(collections.Counter)
npools = 0; nsell = 0; firstts = None
for p in pools:
    if p["sub"] != "v3.0": continue
    lg = sorted(ev[p["pid"]]["logs"], key=lambda x: (x["bn"], x["li"]))
    sw = []
    for x in lg:
        if x["t"] != T_SWAP: continue
        t = txs.get(x["tx"]); a0 = s128(W(x["data"], 0))
        sw.append((x["bn"], x["li"], a0, t["from"] if t else "", t["to"] if t else "", t["input"][2:10] if t else ""))
    fb = next((s for s in sw if s[2] < 0 and s[4] == ROUTER and s[5] == "c1120e3d"), None)
    mine = [s for s in sw if s[3].startswith(F)]
    if not mine: continue
    npools += 1
    pulls = [x for x in lg if x["t"] == T_ML and sgn(W(x["data"], 2)) < 0]
    pull = pulls[0]["bn"] if pulls else None
    buys = [s for s in mine if s[2] < 0]; sells = [s for s in mine if s[2] > 0]
    beth = sum(-s[2] for s in buys)
    if not sells:
        k = "held"
    else:
        s = sells[0]; nsell += 1
        if fb is None: k = "no bot"
        elif (s[0], s[1]) < (fb[0], fb[1]): k = "before bot"
        elif s[0] == fb[0]: k = "bot block after bot"
        elif s[0] == fb[0] + 1: k = "bot+1"
        else: k = "later"
        rets[k].append(sum(x[2] for x in sells) / beth - 1)
    cat[k] += 1
    if fb: pullrel[k][(pull - fb[0]) if pull else None] += 1
print("pools with F", npools, "sells", nsell)
print(cat)
for k, v in rets.items(): print(k, len(v), "min %.4f max %.4f mean %.4f median %.4f" % (min(v), max(v), st.mean(v), st.median(v)))
for k, c in pullrel.items(): print("pull-bot", k, sorted(c.items(), key=lambda x: (x[0] is None, x[0] or 0)))
after = [r for k in ("bot block after bot", "bot+1", "later") for r in rets[k]]
print("at/after bot", len(after), "min %.4f max %.4f median %.4f" % (min(after), max(after), st.median(after)))
