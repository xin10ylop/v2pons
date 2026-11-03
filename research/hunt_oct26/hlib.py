"""hlib.py: shared read-only helpers for the Oct 26 hunt: JSON-RPC with retries, batched calls, windowed eth_getLogs, the block at a UTC time.
Robinhood's own RPC takes topic-only log queries of up to 30,000 blocks; Base's publicnode takes 10,000 blocks but only with an address
filter, Tenderly's public gateway 1,000 blocks topic-only (rate-limited)."""
import json, time, calendar, urllib.request, urllib.error, concurrent.futures as cf

CH = {"rh": {"rpc": "https://rpc.mainnet.chain.robinhood.com", "logs": "https://rpc.mainnet.chain.robinhood.com", "span": 25000, "span_addr": 25000,
             "topic_logs": "https://rpc.mainnet.chain.robinhood.com", "topic_span": 25000,
             "pm": "0x8366a39cc670b4001a1121b8f6a443a643e40951", "weth": "0x0bd7d308f8e1639fab988df18a8011f41eacad73"},
      "base": {"rpc": "https://base-rpc.publicnode.com", "logs": "https://base-rpc.publicnode.com", "span": 10000, "span_addr": 10000,
               "topic_logs": "https://gateway.tenderly.co/public/base", "topic_span": 1000,
               "pm": "0x498581ff718922c3f8e6a244956af099b2652b2b", "weth": "0x4200000000000000000000000000000000000006"},
      # BNB Chain (Nov 3): publicnode takes 50,000 blocks with an address filter and refuses topic-only queries
      "bnb": {"rpc": "https://bsc-rpc.publicnode.com", "logs": "https://bsc-rpc.publicnode.com", "span": 50000, "span_addr": 50000,
              "topic_logs": "https://bsc-rpc.publicnode.com", "topic_span": 50000,
              "pm": "0x28e2ea090877bf75740558f6bfb36a5ffee9e9df", "weth": "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"},
      # Ethereum (Nov 3): publicnode takes a day of blocks with an address filter; MEV Blocker's RPC also answers topic-only queries
      "eth": {"rpc": "https://rpc.mevblocker.io", "logs": "https://rpc.mevblocker.io", "span": 5000, "span_addr": 5000,     # publicnode's refused us mid-run (403)
              "topic_logs": "https://rpc.mevblocker.io", "topic_span": 2000,
              "pm": "0x000000000004444c5dc75cb358380d2e3de08a90", "weth": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"}}
UA = {"Content-Type": "application/json", "User-Agent": "curl/8"}
T_INIT = "0xdd466e674ea557f56295e2d0218a125ea4b4f0f6f3307b95f85e6110838d6438"
T_ML = "0xf208f4912782fd25c7f114ca3723a2d5dd6f3bcc3ac8db5af63baa85f711d5ec"
T_SWAP4 = "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f"
T_PC2 = "0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9"
T_MINT2 = "0x4c209b5fc8ad50758f13e2e1088ba56a560dff690a1c6fef26394f4c03821c4f"
T_BURN2 = "0xdccd412f0b1252819cb1fd330b93224ca42612892bb3f4f789976e6d81936496"
T_SWAP2 = "0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"
T_PC3 = "0x783cca1c0412dd0d695e784568c96da2e9c22ff989357a2e8b1d9b2b4e6b7118"
T_MINT3 = "0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde"
T_BURN3 = "0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c"
T_SWAP3 = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
T_SWAP3_PCS = "0x19b47279256b2a23a1665c810c8d55a1758940ee09377d4f8d26497a3577dc83"   # PancakeSwap V3: Uniswap V3's fields plus two protocol-fee words at the end
ZERO = "0x" + "0" * 40


def post(url, body, timeout=60):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, json.dumps(body).encode(), UA), timeout=timeout))


def rpc(url, m, p, tries=6):
    err = None
    for i in range(tries):
        try:
            r = post(url, {"jsonrpc": "2.0", "id": 1, "method": m, "params": p})
            if "result" in r:
                return r["result"]
            err = r.get("error")
        except urllib.error.HTTPError as e:
            err = f"HTTP {e.code}"
        except Exception as e:
            err = e
        time.sleep(0.7 * (i + 1))
    raise RuntimeError(f"{m} {url.split('/')[2]}: {str(err)[:120]}")


def batch(url, calls, size=50, workers=4, tries=6):
    """calls: [(method, params)]; returns results in order (None where a call failed)"""
    chunks = [calls[i:i + size] for i in range(0, len(calls), size)]

    def go(ch):
        for i in range(tries):
            try:
                r = post(url, [{"jsonrpc": "2.0", "id": k, "method": m, "params": p} for k, (m, p) in enumerate(ch)])
                if isinstance(r, list):
                    d = {x.get("id"): x.get("result") for x in r}
                    if sum(v is None for v in d.values()) <= len(ch) // 10 or i == tries - 1:
                        return [d.get(k) for k in range(len(ch))]
            except Exception:
                pass
            time.sleep(1.0 * (i + 1))
        return [None] * len(ch)
    with cf.ThreadPoolExecutor(workers) as ex:
        return [x for part in ex.map(go, chunks) for x in part]


def logs(ch, a, b, topics, address=None, workers=4):
    """every log in [a, b]; topic-only queries go to the chain's topic endpoint, address-filtered ones to its log endpoint"""
    c = CH[ch]
    url, span = (c["logs"], c["span_addr"]) if address else (c["topic_logs"], c["topic_span"])
    q0 = {"topics": topics}
    if address:
        q0["address"] = address

    def rng(lo, hi, depth=0):
        try:
            return rpc(url, "eth_getLogs", [dict(q0, fromBlock=hex(lo), toBlock=hex(hi))], tries=4)
        except RuntimeError:
            if hi - lo < 50 or depth > 6:
                raise
            mid = (lo + hi) // 2
            return rng(lo, mid, depth + 1) + rng(mid + 1, hi, depth + 1)
    jobs = [(lo, min(b, lo + span - 1)) for lo in range(a, b + 1, span)]
    if not address and ch != "rh":                         # Tenderly's public gateway: one at a time, paced
        out = []
        for j in jobs:
            out += rng(*j); time.sleep(0.15)
        return out
    with cf.ThreadPoolExecutor(workers) as ex:
        parts = list(ex.map(lambda j: rng(*j), jobs))
    return [x for p in parts for x in p]


def ts(url, bn):
    for i in range(6):                                     # a load-balanced node can answer null for a block it has not caught up to
        b = rpc(url, "eth_getBlockByNumber", [hex(bn), False])
        if b:
            return int(b["timestamp"], 16)
        time.sleep(1 + i)
    raise RuntimeError(f"block {bn} unreadable on {url.split('/')[2]}")


def block_at(ch, when):
    """first block at or after the UTC time when ('YYYY-MM-DD HH:MM' or a unix time)"""
    url = CH[ch]["rpc"]
    t = when if isinstance(when, (int, float)) else calendar.timegm(time.strptime(when, "%Y-%m-%d %H:%M"))
    hi = int(rpc(url, "eth_blockNumber", []), 16); lo = max(1, hi - 200_000_000)
    if ch == "base":                                       # a block every 2 s exactly
        t_hi = ts(url, hi)
        return hi - (t_hi - t + 1) // 2 if t < t_hi else hi
    if ts(url, hi) < t:
        return hi
    while lo < hi:
        mid = (lo + hi) // 2
        try:
            tm = ts(url, mid)
        except RuntimeError:
            lo = mid + 1; continue
        if tm < t:
            lo = mid + 1
        else:
            hi = mid
    return lo


def i256(h):
    v = int(h, 16)
    return v - (1 << 256) if v >= 1 << 255 else v


def a_of(topic):
    return "0x" + topic[26:]
