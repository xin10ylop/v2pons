"""cache-wide (no RPC): deposits into 0x4cd00e38 (selector 0x49290c1c) on Oct 8-9 by nonce-0 senders, and who funded each sender
(the plain transfer into it in the same cached data); labels the funders"""
import os, json, sys, collections, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops2")
from labels import lab, A, B
D = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/lch/bc/"
X = "0x4cd00e387622c35bddb9b4c962c136462338bc31"
COPY = set(json.load(open("c_tail_senders.json"))) | {"0x3fc5b8b8dada622d7f41a35a0ad8ac2e5d0f8d8a"}
seen = set(); deps = []; into = collections.defaultdict(list)
for f in sorted(os.listdir(D)):
    if not f.endswith(".json"): continue
    try: d = json.load(open(D + f))
    except Exception: continue
    for k, (ts, tl) in d.items():
        bn = int(k)
        if bn in seen or bn < 82800000: continue
        seen.add(bn)
        for t in tl:
            if t[2] == X and t[5] == "0x49290c1c": deps.append((bn, ts, t))
            if t[5] in ("0x", "") and int(t[3]) > 0: into[t[2]].append((bn, ts, t))
print("deposits seen", len(deps), "by nonce-0 senders", sum(1 for x in deps if x[2][4] == 0))
fund = collections.Counter(); rows = []
for bn, ts, t in deps:
    s = t[1]; fs = [x for x in into.get(s, []) if x[0] <= bn]
    f = fs[-1][2][1] if fs else None
    tag = "OWNER-3ee5" if f == "0x3ee51814a1b2d336a9da81019148aa76da470b2f" else (lab(f) if f else "?")
    if f in COPY: tag = "COPY"
    rows.append((bn, time.strftime("%m-%d %H:%M", time.gmtime(ts)), s, t[4], int(t[3]) / 1e18, f, tag))
    fund[tag or "-"] += 1
print("funder labels:", fund)
for r in rows:
    if r[6] not in ("", "-", "?") or (r[5] and r[5].startswith(("0xdef59ef1", "0x3ee51814"))): print("  ", r)
# senders funded by wallets that themselves have many inputs (sweeps)
json.dump(rows, open("dep4cd.json", "w"))
