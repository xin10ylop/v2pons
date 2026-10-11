"""Tally topic0s emitted by four.meme TokenManager2 over recent BNB blocks and match against candidate signatures."""
import sys, os, collections, json
sys.path.insert(0, os.path.dirname(__file__))
import rpc
from eth_hash.auto import keccak
url = "https://bsc-rpc.publicnode.com"; TM2 = "0x5c952063c7fc8610FFDB798152D69F0B9550762b"
cands = ["TokenCreate(address,address,uint256,string,string,uint256,uint256)",
         "TokenCreate(address,address,uint256,string,string,uint256,uint256,uint256)",
         "TokenPurchase(address,address,uint256,uint256,uint256,uint256,uint256,uint256)",
         "TokenSale(address,address,uint256,uint256,uint256,uint256,uint256,uint256)",
         "LiquidityAdded(address,uint256,address,uint256)", "TradeStop(address)"]
names = {"0x" + keccak(c.encode()).hex(): c for c in cands}
h = rpc.block_number(url)
logs, _ = rpc.get_logs_range(url, TM2, [], h - 400, h, chunk=400)
ct = collections.Counter(l["topics"][0] for l in logs)
for t, n in ct.most_common(): print(n, t, names.get(t, "?"), "ntopics", len([l for l in logs if l["topics"][0] == t][0]["topics"]), "datawords", (len([l for l in logs if l["topics"][0] == t][0]["data"]) - 2) // 64)
ex = [l for l in logs if names.get(l["topics"][0], "").startswith("TokenPurchase")][:1]
if ex: print("purchase data words:", [ex[0]["data"][2+64*i:2+64*(i+1)][-40:] for i in range(3)])
ex = [l for l in logs if names.get(l["topics"][0], "").startswith("TokenCreate")][:1]
if ex: print("create data words:", [ex[0]["data"][2+64*i:2+64*(i+1)][-40:] for i in range(3)])
