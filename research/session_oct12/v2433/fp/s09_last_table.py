"""Per-pool table of the last 2.4333 pools (s08): who bought ahead of the bot, the bot's first buy (T), our relay's buy/sell, the bot's buying
(count, ETH), the pull (ModifyLiquidity < 0) and its offset; the ETH value of all bot buys from the Swap amounts."""
import json, time
from common import load_jsonl, BOT
DECOY = "0x65050a9b7e5075a2ba5ced7b1b64ee66262c40dc"; RELAY = "0x2abb5653352f6b2f3b4f4261877cd02d9e05a957"; E1 = "0xe71a69f434a719cd5afa411568b69716aab3b84a"
P = load_jsonl("s08_pools_cache.jsonl")
print("launch(UTC)  block     sender      buys-before-T (offset,ETH,who)                          T   botbuys(<=600) botETH  ours(buy@,sell@)  pull@   pulled-liq-blocks-after-T  swaps<=3000")
for x in P:
    sw = x["swaps"]; bot = [s for s in sw if s["to"] == BOT and s["a0"] < 0]
    T = bot[0]["d"] if bot else None
    who = lambda s: "bot" if s["to"] == BOT else "ours" if s["to"] == RELAY else "decoy" if s["to"] == DECOY else "e71a" if s["from"] == E1 else (s["from"][:8] if s["from"] else "?" + s["snd"][:6])
    ahead = [(s["d"], round(-s["a0"] / 1e18, 5), who(s)) for s in sw if s["a0"] < 0 and (T is None or s["d"] < T) and who(s) != "bot"]
    ours = [(s["d"], "b" if s["a0"] < 0 else "s") for s in sw if s["to"] == RELAY]
    pulls = [m["d"] for m in x["mls"] if m["dl"] < 0]
    print("%s %d %s %-62s %4s %4d %8.3f %-18s %-6s %s %d" % (time.strftime("%H:%M:%S", time.gmtime(x["t"])), x["L"], x["from"][:10], str(ahead)[:62], T, len(bot), sum(-s["a0"] for s in bot) / 1e18,
          str(ours)[:18], str(pulls[0]) if pulls else "-", (pulls[0] - T) if pulls and T is not None else "-", len(sw)))
