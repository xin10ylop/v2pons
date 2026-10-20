"""Candidate line definitions (selectors over the non-vbot rows) shared by the detail and replay scripts."""
from common import *
Z40 = "0x" + "0" * 40


def odd2(r):
    """the fresh-wallet ~1.6-2 ETH 'odd wei' line: 1444 bytes, ETH, no hook, value in [1.5, 2.0] ETH but not a round number"""
    v = r["launch"]["value_wei"]
    return r["launch"]["calldata_len"] == 1444 and r["quote"] == "ETH" and r["hooks"] == Z40 and 15 * 10**17 <= v <= 2 * 10**18 and v % 10**15 != 0


CANDS = {
    "C1_eth": lambda r: r["fam"]["tok"].startswith("cb79985d") and r["launch"]["calldata_len"] == 2276 and r["quote"] == "ETH" and r["hooks"] == Z40,
    "C1_weth": lambda r: r["fam"]["tok"].startswith("cb79985d") and r["launch"]["calldata_len"] == 2276 and r["quote"] == "WETH" and r["hooks"] == Z40,
    "a98b_hook": lambda r: r["fam"]["tok"].startswith("a98b3b9e") and r["launch"]["calldata_len"] == 2020 and r["quote"] == "ETH",
    "564f_weth_hook": lambda r: r["fam"]["tok"].startswith("564fe314") and r["launch"]["calldata_len"] == 2276 and r["quote"] == "WETH" and r["hooks"] != Z40,
    "odd2_1444": odd2,
    "v0_1444_1pct": lambda r: r["launch"]["value_wei"] == 0 and r["launch"]["calldata_len"] == 1444 and r["fee"] == 10000 and r["quote"] == "ETH" and r["hooks"] == Z40,
    "v0_1444_03pct": lambda r: r["launch"]["value_wei"] == 0 and r["launch"]["calldata_len"] == 1444 and r["fee"] == 3000 and r["quote"] == "ETH" and r["hooks"] == Z40,
}
