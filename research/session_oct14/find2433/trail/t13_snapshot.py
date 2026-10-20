"""Nonce and balance now of the operator-adjacent wallets (decoy funders, fronters, decoy-router admins, the hub, the exchange-like sender,
the dust sentinel); compared with the values in the Oct 12 reports where known."""
from common import *
W_ = {"0x544ef4354283261fb9e258247a80d49c86b9f107": ("decoy funder/collector (funded fresh decoy 0xc32ccde1)", 7885),
      "0x488faf521a2d5f16ee55d1335841bb3ba9a0946e": ("decoy funder (bought 0.001485 itself, Oct 10)", None),
      "0xe322fc6ddb6b29d110b7f84c728d2d743e904616": ("decoy collector", None),
      "0x8cf143ddc84dedcd7bedd2b362b63af154dfa4f7": ("fronter via 0x65050a9b/0xfd1b271f", 3111),
      "0xb8c879dcd96d5ce0719e6fb056738f09b33bc33c": ("fronter via 0xfd1b271f", None),
      "0x7ae81404e32aef363eb63bc4befba78fb5b636de": ("fronter via UR (2e-5 buys)", None),
      "0xbd936de69d72b3a958ee868348ee93f5282849b6": ("recurring decoy-router buyer", 2361),
      "0xb4c345dcf30be7ef93abbacb5f67bd3cc3dfaa04": ("0xfd1b271f decoy (Oct 10)", 1813),
      "0x2e234882231cdc99c654a213a5ecc848459cceee": ("recurring decoy-router buyer", 12854),
      "0x1845a376e183cca973e64dbf0a1e57a74130f31f": ("recurring decoy-router buyer", 89),
      "0xc32ccde1bd14f14cbf7d97a03872d92c57513111": ("fresh decoy wallet (last pools)", 4),
      "0x0c628d6535b781f6c703ad319af8b1bcec63fbb4": ("decoy-router 0x65050a9b admin", None),
      "0x04a802fe42476e9e9ed3cc3c28ce3a476a73d229": ("0xfd1b271f admin", None),
      SENT: ("dust sentinel", None), HUB: ("2.433 hub (bridged out)", 10),
      "0x39525d91ffdcc126f052eefed6735fda72ad1dee": ("exchange-like, sent 0.7999 to hub", 3445),
      "0x74447adf3e9e7c2c4ef7945d1ccfd2c2ac6157b1": ("2.433 launch wallet (first of the Oct 11 window)", None),
      "0xa65254074287c7458666dbd26a8997c3ec590625": ("8 self-transfers Oct 11 20:46 (nonce 0-7)", 8)}
ws = list(W_)
n = rpc.batch("eth_getTransactionCount", [[w, "latest"] for w in ws], n=20)
b = rpc.batch("eth_getBalance", [[w, "latest"] for w in ws], n=20)
c = rpc.batch("eth_getCode", [[w, "latest"] for w in ws], n=20)
h, th = head(); print("at block", h, utc(th))
for w, x, y, z in zip(ws, n, b, c):
    print("%s nonce %7d (Oct 12: %s) %10.6f ETH code %d B  %s" % (w, int(x, 16), W_[w][1], int(y, 16) / 1e18, (len(z) - 2) // 2, W_[w][0]))
