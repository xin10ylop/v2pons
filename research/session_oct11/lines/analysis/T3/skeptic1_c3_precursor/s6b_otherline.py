"""Stage 6b: the finder's strongest d=1 excess ('ANY event in another line pool', x4 / x7 at d=1) per d on my slice, with the background rate
per block (L+4..T-13), and the same for 'a bot buy in any pool' and 'any tx from a bot buyer wallet'."""
import pickle, collections
from lib import *
E = pickle.load(open("touch.pkl", "rb")); rows = [r for r in E["rows"] if r["set"] == "cur"]
facts = {f["pid"]: f for f in E["facts"] if f["set"] == "cur" and f["have"] == f["need"]}
allp = []
for s in ("older", "old", "mid", "recent"): allp += pickle.load(open(f"parsed_{s}.pkl", "rb"))["pools"]
LINE_PID = {p["pid"].lower() for p in allp}; BOTW = {s["eoa"] for p in allp for s in p["sw"] if s["bot"]}
kr = KV("rcp")
def flags(r):
    f = set()
    rr = kr.d.get(str(r["L"] + r["off"])) or []
    for x in rr:
        if x["tx"] != r["hash"]: continue
        for l in x["logs"]:
            if l["a"] == PM and len(l["t"]) > 1 and l["t"][1].lower() in LINE_PID and l["t"][1].lower() != r["pid"].lower(): f.add("event in another 3.0 line pool")
    if r["to"] == BOT and r["sel"] == "c1120e3d": f.add("a bot buy (any pool)")
    if r["frm"] in BOTW: f.add("any tx from a bot buyer wallet")
    if r["to"] == BOT: f.add("any tx to the bot router")
    return f
byd = collections.defaultdict(lambda: collections.defaultdict(set)); bg = collections.defaultdict(set)
for r in rows:
    if r["pid"] not in facts or r["pos"] != "before" or r["off"] < 4: continue
    for k in flags(r):
        if r["d"] <= 12: byd[k][r["d"]].add(r["pid"])
        else: bg[k].add((r["pid"], r["off"]))
nbg = sum(max(0, f["Tbn"] - 13 - (f["L"] + 4) + 1) for f in facts.values())
print(f"pools {len(facts)}; background blocks L+4..T-13: {nbg}")
for k in sorted(byd):
    rate = len(bg[k]) / nbg
    print(f"  {k:38s} pools at d=0..12: " + " ".join(f"{len(byd[k][d]):3d}" for d in range(13)) + f" | background {rate:.3f} per block = {rate*len(facts):.1f} pools expected per d")
