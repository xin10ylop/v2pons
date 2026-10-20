"""Every log in a few launch receipts, every address named, every Transfer decoded: is any value routed to a fixed (fee) address?"""
import sys, json, time
sys.path.insert(0, "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad")
from chain import batch, rpc
from eth_utils import keccak
T = json.load(open("/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/launcher_txs.json"))
srt = sorted(T.items(), key=lambda kv: kv[1]["bn"])
picks = [srt[0][0], srt[len(srt) // 3][0], srt[2 * len(srt) // 3][0], srt[-1][0],
         "0x081bd2300a44d8864460148abf5541d42053205df24974e1e2cf1d1318b9fd0c"]  # last: a launch through one-shot copy 0x8ea696db
EV = {}
for s in ["Transfer(address,address,uint256)", "Approval(address,address,uint256)", "Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)",
          "ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)", "Permit(address,address,address,uint160,uint48,uint48)", "Approval(address,address,address,uint160,uint48)",
          "Transfer(address,address,address,uint256,uint256)", "OwnershipTransferred(address,address)"]:
    EV["0x" + keccak(text=s).hex()] = s.split("(")[0] + ("/p2" if s.startswith("Approval(address,address,address") else "") + ("/6909" if s.startswith("Transfer(address,address,address") else "")
EV["0x03f29fb2049a216108887bac46b54b1f8d8db31efb6e3cc67bb6a63f2441e84f"] = "Launched(launcher event)"
NAME = {"0x3194e32622c5d860a0572c74edda99dcfd8fc827": "LAUNCHER", "0x8366a39cc670b4001a1121b8f6a443a643e40951": "PoolManager", "0x58daec3116aae6d93017baaea7749052e8a04fa7": "PositionManager",
        "0x000000000022d473030f116ddee9f6b43ac78ba3": "Permit2", "0x0000000000000000000000000000000000000000": "0x0"}
txs = batch([("eth_getTransactionByHash", [h]) for h in picks]); rcs = batch([("eth_getTransactionReceipt", [h]) for h in picks])
allother = set()
for h, tx, rc in zip(picks, txs, rcs):
    nm = dict(NAME); nm[tx["from"].lower()] = "SENDER"; nm[tx["to"].lower()] = nm.get(tx["to"].lower(), "COPY-LAUNCHER")
    for lg in rc["logs"]:
        if lg["topics"][0] == "0x03f29fb2049a216108887bac46b54b1f8d8db31efb6e3cc67bb6a63f2441e84f": nm["0x" + lg["topics"][2][-40:]] = "TOKEN"
    print(f"\n== tx {h[:14]} block {int(tx['blockNumber'],16)} from {tx['from']} nonce {int(tx['nonce'],16)} to {nm[tx['to'].lower()]} value {int(tx['value'],16)/1e18} ETH status {rc['status']} gasUsed {int(rc['gasUsed'],16)} logs {len(rc['logs'])}")
    for lg in rc["logs"]:
        a = lg["address"].lower(); ev = EV.get(lg["topics"][0], lg["topics"][0][:10]); tp = ["0x" + x[-40:] for x in lg["topics"][1:]]
        named = [nm.get(x, x) for x in tp]
        for x in tp + [a]:
            if x not in nm and not (ev.startswith("Initialize") or ev.startswith("ModifyLiquidity")): allother.add(x)
        extra = ""
        if ev in ("Transfer", "Approval") and len(lg["topics"]) == 3: extra = " amount %.6g" % (int(lg["data"], 16) / 1e18 if lg["data"] != "0x" else 0)
        if ev == "Transfer" and len(lg["topics"]) == 4: extra = " ERC721 id %d" % int(lg["topics"][3], 16); named = named[:2]
        if ev.startswith("Launched"): extra = " data words " + str([int(lg["data"][2 + 64*i: 66 + 64*i], 16) for i in range((len(lg["data"]) - 2) // 64)])
        if ev.startswith("ModifyLiquidity"): named = ["poolId", nm.get(tp[1], tp[1])]
        if ev.startswith("Initialize"): named = ["poolId", nm.get(tp[1], tp[1]), nm.get(tp[2], tp[2])]
        print(f"   {nm.get(a, a)[:16]:16s} {ev:24s} {named}{extra}")
print("\naddresses in these logs that are not sender/launcher/token/PoolManager/PositionManager/Permit2/0x0:", allother or "NONE")
