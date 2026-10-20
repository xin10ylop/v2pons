"""wider context of the four families: same launch_to / same hook / same deployer / same selector across the census"""
import sys, os, json, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common20 import *
P = load_pools()
def show(name, pids):
    ps = [P[x] for x in pids]
    print("==", name, "pools", len(ps))
    print("   launch_to", collections.Counter(p["launch_to"] for p in ps).most_common(6))
    print("   from", len(set(p["launch_from"] for p in ps)), collections.Counter(p["launch_from"] for p in ps).most_common(4))
    print("   sel", collections.Counter((p["selector"], p["calldata_len"]) for p in ps).most_common(6))
    print("   fee/ts/hooks", collections.Counter((p["fee"], p["tick_spacing"], p["hooks"]) for p in ps).most_common(6))
    print("   families", collections.Counter(p["family"] for p in ps).most_common(8))
    print("   known", collections.Counter(p["known"] for p in ps).most_common())
    print("   n_swaps>0", sum(1 for p in ps if p["n_swaps"]), "pulled", sum(1 for p in ps if p["first_pull_rel"] is not None), "first_buy_rel", q([p["first_buy_rel"] for p in ps if p["first_buy_rel"] is not None]), "first_buy_eth", q([p["first_buy_eth"] for p in ps if p["first_buy_eth"] is not None]))
show("hook 0x4e346895", [p["pid"] for p in P.values() if p["hooks"] == "0x4e3468951d49f2eea976ed0d6e75ffcb44a9a544"])
show("launch_to 0x1eef016f", [p["pid"] for p in P.values() if p["launch_to"] == "0x1eef016f22a943abc7dd11422edee9d235942104"])
show("selector 60956835", [p["pid"] for p in P.values() if p["selector"] == "60956835"])
show("launch_to 0x1756c648", [p["pid"] for p in P.values() if p["launch_to"] == "0x1756c648a426a5a7548ac42350ce3fa980070e65"])
show("deployer 0x17ad4d45", [p["pid"] for p in P.values() if p["launch_from"] == "0x17ad4d45f347794ddc38211de615fb90a641ef1c"])
show("launch_to 0x258dd351", [p["pid"] for p in P.values() if p["launch_to"] == "0x258dd351af960bc487532c0108d3f90e8d115369"])
show("deployer 0x06cb3a68", [p["pid"] for p in P.values() if p["launch_from"] == "0x06cb3a6841c92525e7a1998328e7c9d37e98d937"])
show("selector 7fde822e", [p["pid"] for p in P.values() if p["selector"] == "7fde822e"])
show("launch_to 0x2cf3de56", [p["pid"] for p in P.values() if p["launch_to"] == "0x2cf3de560af4e1922246cb867b4eabcc1ad3e4a0"])
show("deployer 0xa776baa1", [p["pid"] for p in P.values() if p["launch_from"] == "0xa776baa122b287abce00f0fc859bd6e2f289a2cb"])
show("selector aad1232c", [p["pid"] for p in P.values() if p["selector"] == "aad1232c"])
show("hooks ending 00cc", [p["pid"] for p in P.values() if p["hooks"].endswith("00cc")])
