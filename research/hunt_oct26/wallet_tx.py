#!/usr/bin/env python3
"""wallet_tx.py CHAIN ADDR HOURS [STEP]: an address's recent token activity from logs alone (no explorer, no archive): every ERC-20 Transfer
to or from it in the last HOURS, grouped by transaction, with the token. Read-only, public RPCs."""
import sys, collections, concurrent.futures as cf
from rivals_now import rpc

EP = {"rh": ("https://rpc.mainnet.chain.robinhood.com", 25000, 0.1), "base": ("https://base.drpc.org", 1000, 2.0),
      "bsc": ("https://rpc-bsc.blockmachine.io", 5000, 0.45)}
T = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def transfers(ch, a, hours, step=None, head=None):
    url, st, bs = EP[ch]; st = step or st
    pad = "0x" + "0" * 24 + a.lower()[2:]
    head = head or int(rpc(url, "eth_blockNumber", []), 16)
    lo0 = head - int(hours * 3600 / bs)
    jobs = [(lo, min(head, lo + st - 1), tp) for tp in ([T, None, pad], [T, pad, None]) for lo in range(lo0, head + 1, st)]
    with cf.ThreadPoolExecutor(6) as ex:
        res = list(ex.map(lambda j: (j, rpc(url, "eth_getLogs", [{"fromBlock": hex(j[0]), "toBlock": hex(j[1]), "topics": j[2]}])), jobs))
    bad = [j for j, r in res if r is None]
    out = [l for _, r in res if r for l in r]
    return head, out, bad


if __name__ == "__main__":
    ch, a, hours = sys.argv[1], sys.argv[2].lower(), float(sys.argv[3])
    head, out, bad = transfers(ch, a, hours, int(sys.argv[4]) if len(sys.argv) > 4 else None)
    print(f"{ch} head {head}: {len(out)} transfers, {len(bad)} failed ranges")
    txs = collections.OrderedDict()
    for l in sorted(out, key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16))):
        txs.setdefault(l["transactionHash"], []).append(l)
    tokens = collections.Counter(l["address"] for l in out)
    print("transactions", len(txs), "tokens", len(tokens), "top", tokens.most_common(5))
    for h, ls in list(txs.items())[-40:]:
        for l in ls:
            frm, to = "0x" + l["topics"][1][26:], "0x" + l["topics"][2][26:]
            amt = int(l["data"], 16) / 1e18 if l["data"] not in ("0x", "") else 0
            print(int(l["blockNumber"], 16), h[:14], "tok", l["address"][:12], "from", frm[:12], "to", to[:12], f"{amt:.6g}")
