"""Oct 8 pot wallets from the earlier loop traces (full addresses): A pot 11:19-11:48 (loop_A.jsonl) + the 21:57 restart hubs,
B pot 11:11-11:54 (loop_B2.jsonl), 17:33-17:43 (loop_hubexit.jsonl), 10:57 (loopback_B.jsonl) + the 14:21-14:50 B wallets found here"""
import json
L = "/tmp/claude-0/-home-user-v2pons/f653fbde-aa08-514f-a7a0-470737d59aa4/scratchpad/ops/lch/"
def addrs(f):
    s = set()
    for line in open(L + f):
        d = json.loads(line)
        for k in ("addr", "cap_to"):
            if d.get(k): s.add(d[k])
        for o in d.get("odd_in", []): s.add(o[0])
    return s
A_OCT8 = addrs("loop_A.jsonl") | {"0xc139beb5c26f01ea5c4dfd84ebddb65a39336e2e", "0x501f4f53e2865908c0d8e4183318d035790b9ea7", "0x4348ffca6467fdb687fb771c2370f691a7a940e9",
                                  "0x3ee51814a1b2d336a9da81019148aa76da470b2f"}
B_OCT8 = addrs("loop_B2.jsonl") | addrs("loop_hubexit.jsonl") | addrs("loopback_B.jsonl") | {
    "0xded28cc0001917222aa2b55ad55f1d236ef1be74", "0x58fc6f17ea0d2e472867fed709cedb6b131a40dc", "0x4001b198964c7d77aa66472b457c5d0ccea886c9",
    "0xa59d8f2cafa8f00638ca56fc2444d4342078842c", "0x9614ea90533fe312c36a09a9fdfacb6b09b267cd", "0x6cdcd541dee2b18e9569650d96c73cbd912cb96f",
    "0x1821144f9d9c8f773ba295641a5a730c9b8cb066", "0x1d18f10325a5b4fa584dbad259473107a29a79ac", "0xe50dd00a357018225b86e232e5cb8b762b533556"}
B_OCT8 -= {"0x3fc5b8b8dada622d7f41a35a0ad8ac2e5d0f8d8a"}
if __name__ == "__main__":
    print(len(A_OCT8), len(B_OCT8), A_OCT8 & B_OCT8)
