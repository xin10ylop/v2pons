"""Token-contract events of the bot's tokens: (1) event-type census; (2) in each 3.0/5.0 pool, any token event between L+4 and T-1
(a precursor inside the pool); (3) the bot wallets' sells anywhere (Transfer wallet -> PoolManager) and Approvals, cross-correlated with T."""
import json, pickle, collections, bisect
from eth_utils import keccak
D = pickle.load(open("cache/data.pkl", "rb")); pools = D["pools"]; acts = D["acts"]
PM = "0x8366a39cc670b4001a1121b8f6a443a643e40951"; BOT = "0x1cbaf24d53fe930fce8eff149fa797d2611da149"
T_TR = "0x" + keccak(text="Transfer(address,address,uint256)").hex(); T_AP = "0x" + keccak(text="Approval(address,address,uint256)").hex()
botw = set(a["wallet"] for a in acts if a["kind"] == "buy")
ev = collections.defaultdict(list); topics = collections.Counter(); sells = []; approvals = []
a2 = lambda t: "0x" + t[-40:]
for l in open("cache/logs/tok.jsonl"):
    x = json.loads(l); t0 = x["t"][0] if x["t"] else None
    topics[t0 if t0 in (T_TR, T_AP) else "other:" + str(t0)[:10]] += 1
    ev[x["addr"]].append(x)
    if t0 == T_TR and len(x["t"]) == 3 and a2(x["t"][2]) == PM and a2(x["t"][1]) in botw: sells.append(x["bn"])
    if t0 == T_AP and len(x["t"]) == 3 and a2(x["t"][1]) in botw: approvals.append(x["bn"])
print("token events by topic:", topics.most_common(8))
print("bot-wallet sells (Transfer wallet->PM):", len(sells), " bot-wallet approvals:", len(approvals))
P = [p for p in pools if p["line"] in ("3.0", "5.0") and p["T"] is not None]
pre = collections.Counter(); n_with = 0
for p in P:
    e = [x for x in ev[p["token"]] if p["L"] + 4 <= x["bn"] < p["Tbn"]]
    if e: n_with += 1
    for x in e:
        t0 = x["t"][0]
        kind = "Transfer" if t0 == T_TR else "Approval" if t0 == T_AP else "other"
        if kind != "other" and len(x["t"]) == 3: kind += f" {a2(x['t'][1])[:10]}->{a2(x['t'][2])[:10]}"
        pre[(kind, p["Tbn"] - x["bn"])] += 1
print(f"3.0/5.0 pools with any token event in [L+4, T-1]: {n_with} of {len(P)}; by (kind, T - block):", pre.most_common(12))
def xc(name, evs, P):
    evs = sorted(evs); h = collections.Counter()
    for p in P:
        a = bisect.bisect_left(evs, p["Tbn"] - 40); b = bisect.bisect_left(evs, p["Tbn"])
        for e in evs[a:b]: h[p["Tbn"] - e] += 1
    span = D["meta"]["head"] - D["meta"]["start"]
    print(f"{name}: per-lag expected {len(P) * len(evs) / span:.1f}; lags 1..40:", [h.get(k, 0) for k in range(1, 41)])
xc("bot-wallet sells before T", sells, P)
xc("bot-wallet approvals before T", approvals, P)
