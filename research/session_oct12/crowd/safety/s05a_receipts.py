"""two receipts of our own wallet's relay transactions (research/session_oct12/c1/c04_ours.json): gasUsed, gasUsedForL1 (Arbitrum's L1
component, charged as L2 gas), effectiveGasPrice. Writes s05a_receipts.out (stdout)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpc
d = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "c1", "c04_ours.json")))
for x in d[:9]:
    r = rpc.call("eth_getTransactionReceipt", [x["hash"]])
    print(x["hash"][:12], "status", int(r["status"], 16), "gasUsed", int(r["gasUsed"], 16), "gasUsedForL1", int(r.get("gasUsedForL1", "0x0"), 16),
          "effGasPrice gwei", int(r["effectiveGasPrice"], 16) / 1e9, "input bytes", (len(x["input"]) - 2) // 2, "logs", len(r["logs"]))
