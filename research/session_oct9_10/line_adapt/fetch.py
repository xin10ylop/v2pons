#!/usr/bin/env python3
"""line_adapt fetch: every v3.0 and v5.0 launch of the volume bot in the last 24 h, its Swap and ModifyLiquidity logs to launch + 1,200,
the launch tx, every swap tx (to/from/value/calldata) in the window, the pull txs, the launch-block headers (base fee, timestamp).
Resumable: every stage caches to data/*.json.   python3 -I fetch.py [stage]
"""
import sys, os, json, time, collections
sys.path.insert(0, "/home/user/v2pons/research/session_oct9_10")
from chain import rpc, batch, logs, block_at, PM, T_INIT, T_SWAP, T_ML, W, sgn
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "data")
os.makedirs(D, exist_ok=True)
SPAN = 1200
FAMS = {679394651928963067279918579724198: "v3.0", 526364174002223567019744861584709: "v5.0"}
POSM = "0x58daec3116aae6d93017baaea7749052e8a04fa7"


def jget(n):
    p = os.path.join(D, n)
    return json.load(open(p)) if os.path.exists(p) else None


def jput(n, o):
    p = os.path.join(D, n); json.dump(o, open(p + ".tmp", "w")); os.replace(p + ".tmp", p)


def log(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)


def window():
    w = jget("window.json")
    if w: return w
    head = int(rpc("eth_blockNumber", []), 16); hb = rpc("eth_getBlockByNumber", [hex(head), False]); head_ts = int(hb["timestamp"], 16)
    start = block_at(head_ts - 86400)
    sb = rpc("eth_getBlockByNumber", [hex(start), False])
    w = {"from_block": start, "from_ts": int(sb["timestamp"], 16), "head": head, "head_ts": head_ts}
    jput("window.json", w); log("window", w); return w


def cl(l):
    return {"bn": int(l["blockNumber"], 16), "ti": int(l["transactionIndex"], 16), "li": int(l["logIndex"], 16), "tx": l["transactionHash"], "t": l["topics"][0],
            "topics": l["topics"], "data": l["data"]}


def inits():
    x = jget("inits.json")
    if x: return x
    w = window(); out = []; a = w["from_block"]
    while a <= w["head"]:
        b = min(a + 99_999, w["head"])
        ls = logs({"address": PM, "topics": [T_INIT]}, a, b)
        keep = [cl(l) for l in ls if W(l["data"], 3) in FAMS]
        out += keep; log("inits", a, b, len(ls), "kept", len(keep)); a = b + 1
    jput("inits.json", out); return out


def pools():
    x = jget("pools.json")
    if x: return x
    I = inits(); w = window()
    txs = batch([("eth_getTransactionByHash", [l["tx"]]) for l in I])
    bns = sorted({l["bn"] for l in I})
    hdr = dict(zip(bns, batch([("eth_getBlockByNumber", [hex(b), False]) for b in bns])))
    out = []
    for l, t in zip(I, txs):
        d = l["data"]; inp = t["input"]
        b = hdr[l["bn"]]
        out.append({"pid": l["topics"][1], "c0": "0x" + l["topics"][2][-40:], "token": "0x" + l["topics"][3][-40:], "b0": l["bn"], "ti0": l["ti"], "li0": l["li"],
                    "fee": W(d, 0), "ts": sgn(W(d, 1)), "hooks": "0x" + d[2 + 64 * 2 + 24: 2 + 64 * 3], "sp0": W(d, 3), "tick0": sgn(W(d, 4)),
                    "fam": FAMS[W(d, 3)], "tx": l["tx"], "from": t["from"].lower(), "to": (t["to"] or "").lower(), "value": int(t["value"], 16), "nonce": int(t["nonce"], 16),
                    "sel": inp[2:10], "clen": (len(inp) - 2) // 2, "input": inp, "gas": int(t["gas"], 16), "gasPrice": int(t.get("gasPrice") or "0x0", 16),
                    "maxPrio": int(t["maxPriorityFeePerGas"], 16) if t.get("maxPriorityFeePerGas") else None,
                    "ts0": int(b["timestamp"], 16), "basefee0": int(b["baseFeePerGas"], 16)})
    jput("pools.json", out); log("pools", len(out), collections.Counter((p["fam"], p["value"], p["fee"], p["ts"], p["clen"], p["to"]) for p in out)); return out


def events():
    x = jget("events.json")
    if x: return x
    P = sorted(pools(), key=lambda p: p["b0"]); w = window(); ev = {p["pid"]: [] for p in P}
    groups = []; cur = []
    for p in P:
        if cur and (p["b0"] - cur[0]["b0"] > 40_000 or len(cur) >= 60):
            groups.append(cur); cur = []
        cur.append(p)
    if cur: groups.append(cur)
    for g in groups:
        a = g[0]["b0"]; b = min(g[-1]["b0"] + SPAN, w["head"])
        pids = [p["pid"] for p in g]
        ls = logs({"address": PM, "topics": [[T_SWAP, T_ML], pids]}, a, b)
        b0 = {p["pid"]: p["b0"] for p in g}
        for l in ls:
            pid = l["topics"][1]; c = cl(l)
            if b0[pid] <= c["bn"] <= b0[pid] + SPAN: ev[pid].append(c)
        log("events", a, b, len(g), "pools", len(ls), "logs")
    for k in ev: ev[k].sort(key=lambda c: (c["bn"], c["li"]))
    jput("events.json", ev); return ev


def txs():
    have = jget("txs.json") or {}
    ev = events(); need = []
    for pid, L in ev.items():
        for c in L:
            if c["tx"] not in have: need.append(c["tx"])
    need = list(dict.fromkeys(need)); log("txs needed", len(need), "have", len(have))
    for i in range(0, len(need), 500):
        ch = need[i:i + 500]
        for h, t in zip(ch, batch([("eth_getTransactionByHash", [h]) for h in ch])):
            if t is None: continue
            inp = t["input"]
            have[h] = {"from": t["from"].lower(), "to": (t["to"] or "").lower(), "value": int(t["value"], 16), "nonce": int(t["nonce"], 16), "sel": inp[2:10],
                       "clen": (len(inp) - 2) // 2, "input": inp[:2 + 64 * 16 + 8], "bn": int(t["blockNumber"], 16), "ti": int(t["transactionIndex"], 16),
                       "gasPrice": int(t.get("gasPrice") or "0x0", 16), "maxPrio": int(t["maxPriorityFeePerGas"], 16) if t.get("maxPriorityFeePerGas") else None,
                       "gas": int(t["gas"], 16)}
        jput("txs.json", have); log("txs", i + len(ch), "/", len(need))
    return have


def heads():
    """base fee and timestamp of every block from launch to launch + 120 (gas, hour of each event)"""
    x = jget("heads.json") or {}
    P = pools(); need = set()
    for p in P:
        for k in (0, 1, 2):
            need.add(p["b0"] + k)
    need = sorted(b for b in need if str(b) not in x)
    for i in range(0, len(need), 500):
        ch = need[i:i + 500]
        for b, h in zip(ch, batch([("eth_getBlockByNumber", [hex(b), False]) for b in ch])):
            if h: x[str(b)] = [int(h["timestamp"], 16), int(h["baseFeePerGas"], 16)]
        jput("heads.json", x)
    return x


if __name__ == "__main__":
    st = sys.argv[1] if len(sys.argv) > 1 else "all"
    window(); inits(); pools(); events(); txs(); heads(); log("done")
