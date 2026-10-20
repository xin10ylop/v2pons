"""honeypot check for F4b: do the outside routers that buy F4b pools ever sell, in F4b and elsewhere on the chain (census events, all pools)?"""
import sys, os, json, collections
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
from load import *
P = load_pools(); E = load_events(); C = json.load(open("cache/postwin.json"))
PMA = "0x8366a39cc670b4001a1121b8f6a443a643e40951"
def grp(p):
    if p["launch_to"] == PMA and p["selector"] == "6276cbbe" and p["fee"] == 500 and p["tick_spacing"] == 1: return "F4a" if p["hooks_zero"] else "F4b"
    return "hooked-other" if not p["hooks_zero"] else "hookless-other"
WATCH = ["0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc", "0xec9aa0a6c2372131a0502aba6188269ab52cacb5", "0x204faca1764b154221e35c0d20abb3c525710498",
         "0x6aa80dbbed9ae5ab45fbf61f9644fada3b29326e", "0xa8f012fa", "0xf0b7eaaf868191adc00065ca13391ef436ce8faf", "0x8f10b468b06c6fd214b65f87778827f7d113f996",
         "0x36dc95f1f088e11c0066dc19173f745655002bc2", "0x6b54a6a13c70df23620ebad6ddee2d6265690eba", "0x81da6bcd"]
cnt = collections.Counter()
for pid, e in E.items():
    g = grp(P[pid])
    for s in e["swaps"]:
        for w in WATCH:
            if s["sender"].startswith(w): cnt[(w[:10], g, "B" if s["a0"] < 0 else "S")] += 1
for x in C["f4b_swaps"]:
    for w in WATCH:
        if x["sender"].startswith(w): cnt[(w[:10], "F4b-post", "B" if x["a0"] < 0 else "S")] += 1
for w in WATCH:
    print(w[:10], {f"{g}:{s}": n for (ww, g, s), n in sorted(cnt.items()) if ww == w[:10]})
# all non-UR sells anywhere in F4b (census window) and F4a
for g in ("F4a", "F4b"):
    c = collections.Counter()
    for pid, e in E.items():
        if grp(P[pid]) != g: continue
        for s in e["swaps"]:
            if s["a0"] > 0: c[s["sender"][:10]] += 1
    print(g, "sells by sender:", c.most_common(8))
