#!/usr/bin/env python3
"""Full blocks (every transaction, with calldata), as the sequencer feed carries them, cached in vbot/blocks/<n // 1000>.pkl:
{block: (timestamp, base_fee, [(index, hash, from, to, value, nonce, type, gas, tip, input bytes)])}.

    python3 fetch_blocks.py A-B [C-D ...]          block ranges (inclusive)
    python3 fetch_blocks.py --sample K SPAN SEED    K random PM1444 v3.0 launches, [b0 - 3, b0 + SPAN]
"""
import sys, os, json, pickle, time, random
HERE = os.path.dirname(os.path.abspath(__file__)); SCR = os.path.dirname(HERE); sys.path.insert(0, SCR)
from chain import batch
BD = os.path.join(HERE, "blocks"); os.makedirs(BD, exist_ok=True)


def chunk_path(c): return os.path.join(BD, f"{c}.pkl")


def load_chunk(c):
    try: return pickle.load(open(chunk_path(c), "rb"))
    except Exception: return {}


def compact(b):
    txs = []
    for t in b["transactions"]:
        tip = t.get("maxPriorityFeePerGas") or t.get("gasPrice") or "0x0"
        txs.append((int(t["transactionIndex"], 16), t["hash"], t["from"].lower(), (t.get("to") or "").lower(), int(t["value"], 16), int(t["nonce"], 16),
                    t.get("type"), int(t["gas"], 16), int(tip, 16), bytes.fromhex(t["input"][2:])))
    return (int(b["timestamp"], 16), int(b.get("baseFeePerGas") or "0x0", 16), txs)


def fetch(blocks):
    by = {}
    for n in sorted(set(blocks)): by.setdefault(n // 1000, []).append(n)
    done = 0
    for c, ns in sorted(by.items()):
        ch = load_chunk(c); need = [n for n in ns if n not in ch]
        for i in range(0, len(need), 50):
            part = need[i:i + 50]
            for n, b in zip(part, batch([("eth_getBlockByNumber", [hex(n), True]) for n in part])):
                if b: ch[n] = compact(b)
            time.sleep(0.05)
        if need:
            pickle.dump(ch, open(chunk_path(c) + ".tmp", "wb")); os.replace(chunk_path(c) + ".tmp", chunk_path(c))
        done += len(ns)
        print(f"chunk {c}: +{len(need)} ({done}/{len(set(blocks))})", flush=True)


def get(a, b):
    """{n: block} for n in [a, b] from the cache"""
    out = {}
    for c in range(a // 1000, b // 1000 + 1):
        ch = load_chunk(c); out.update({n: v for n, v in ch.items() if a <= n <= b})
    return out


if __name__ == "__main__":
    if sys.argv[1] == "--sample":
        K, SPAN, SEED = int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
        R = [json.loads(l) for l in open(os.path.join(SCR, "others", "census.jsonl"))]
        v3 = sorted(r["b0"] for r in R if r["sel"] == "0xac9650d8" and r["inlen"] == 1444 and r["fee"] == 10000 and r["ts"] == 200 and round(r["value"] or 0, 3) == 3.0)
        random.seed(SEED); pick = sorted(random.sample(v3, K)); print("sample", pick)
        fetch([n for b0 in pick for n in range(b0 - 3, b0 + SPAN + 1)])
    else:
        bl = []
        for rg in sys.argv[1:]:
            a, b = map(int, rg.split("-")); bl += list(range(a, b + 1))
        fetch(bl)
