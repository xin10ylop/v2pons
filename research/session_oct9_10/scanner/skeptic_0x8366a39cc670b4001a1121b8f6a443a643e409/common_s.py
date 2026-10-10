import sys, os, json, collections, statistics as st
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/scanner/census")
sys.path.insert(0, "/home/user/v2pons/src")
from load import *
import v4math
HERE = os.path.dirname(os.path.abspath(__file__))
KEY = "0x8366a39cc670b4001a1121b8f6a443a643e40951|6276cbbe|196|500|1|true"
CROWD_ROUTERS = {"0x410499a03705092ed02a231783d6e96332d84feb", "0xebe93d2f86639869af18b9fc77a3439092ee0e90", "0x628bd69ecbc135cdda02ffd6d6db918f5cd835ce"}
DUST = "0xe71a69f434a719cd5afa411568b69716aab3b84a"
SNIPER = "0xe9d83e95b2248d8b33d63583762bd7f7465ddb28"
UR = "0x8876789976decbfcbbbe364623c63652db8c0904"
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"
RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"
def load_cache():
    c = {}
    for l in open(os.path.join(HERE, "txcache.jsonl")):
        r = json.loads(l); c[r["hash"]] = r
    return c
def words(inp):
    return [inp[10 + 64 * i: 10 + 64 * (i + 1)] for i in range((len(inp) - 10) // 64)]
def classify(t):
    if t is None: return "unknown"
    if t["from"] == DUST: return "dust"
    if t["to"] in CROWD_ROUTERS: return "crowd"
    if t["from"] == SNIPER: return "sniper"
    if t["to"] == RELAY: return "relay"
    return "other"
def q(v, qs=(.1, .5, .9)):
    v = sorted(x for x in v if x is not None)
    if not v: return None
    return [v[int(round(a * (len(v) - 1)))] for a in qs]
