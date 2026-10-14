import json, re, urllib.request, collections
H = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
URLS = ["https://bsc-dataseed.bnbchain.org", "https://bsc-rpc.publicnode.com"]
def rpc(m, p):
    for U in URLS:
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(U, json.dumps({"jsonrpc": "2.0", "id": 1, "method": m, "params": p}).encode(), H), timeout=30))
            if "result" in r or m == "eth_call": return r.get("result", r.get("error"))
        except Exception as e: pass
W = "0x8881bba6787848f4e86780ef69a34bb45c8d4fcb"; tok = "0x950e681819a68f595bb3db313346393d64f66bb5"; pair = "0x2de2620b04a0382390b18441cd033da7b798e57e"
TT = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
head = int(rpc("eth_blockNumber", []), 16)
logs = []
for a in range(head - 3000, head + 1, 500):
    r = rpc("eth_getLogs", [{"address": tok, "topics": [TT], "fromBlock": hex(a), "toBlock": hex(min(a + 499, head))}])
    if isinstance(r, list): logs += r
print("transfers in the last 3000 blocks:", len(logs))
bal = collections.Counter(); first = {}
for l in logs:
    fr = "0x" + l["topics"][1][-40:]; to = "0x" + l["topics"][2][-40:]; v = int(l["data"], 16); b = int(l["blockNumber"], 16)
    bal[fr] -= v; bal[to] += v; first.setdefault(to, b)
    kind = "BUY " if fr == pair else ("SELL" if to == pair else "xfer")
    print(b, kind, fr[:10], "->", to[:10], v)
holders = [a for a, v in bal.items() if v > 0 and a not in (pair,)]
print("holders from these logs:", len(holders))
for h_ in holders[:8]:
    b = rpc("eth_call", [{"to": tok, "data": "0x70a08231" + h_[2:].rjust(64, "0")}, "latest"])
    amt = int(b, 16) if isinstance(b, str) else 0
    if not amt: continue
    r = rpc("eth_call", [{"from": h_, "to": tok, "data": "0xa9059cbb" + "000000000000000000000000000000000000dead".rjust(64, "0") + hex(amt // 100)[2:].rjust(64, "0"), "gas": hex(300000)}, "latest"])
    print("holder", h_, "balance", amt, "transfer 1% ->", "ok" if isinstance(r, str) else r.get("message", r)[:60], "(us)" if h_ == W else "")
code = rpc("eth_getCode", [tok, "latest"])
sels = sorted(set(re.findall(r"63([0-9a-f]{8})", code[2:])))
print("PUSH4 selectors in the code:", sels)
open("/tmp/claude-0/-home-user-v2pons/eaea4643-8a2f-5d86-b29a-3e3f32a15f31/scratchpad/bnb_tok_code.hex", "w").write(code)
