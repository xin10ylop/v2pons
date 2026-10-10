import sys, math, random, json
sys.path.insert(0, "/home/user/v2pons/src")
def sqrt_at_tick(tick):
    a = abs(tick)
    r = 0xfffcb933bd6fad37aa2d162d1a594001 if a & 1 else 1 << 128
    consts = [0xfff97272373d413259a46990580e213a,0xfff2e50f5f656932ef12357cf3c7fdcc,0xffe5caca7e10e4e61c3624eaa0941cd0,0xffcb9843d60f6159c9db58835c926644,0xff973b41fa98c081472e6896dfb254c0,0xff2ea16466c96a3843ec78b326b52861,0xfe5dee046a99a2a811c461f1969c3053,0xfcbe86c7900a88aedcffc83b479aa3a4,0xf987a7253ac413176f2b074cf7815e54,0xf3392b0822b70005940c7a398e4b70f3,0xe7159475a2c29b7443b29c7fa6e889d9,0xd097f3bdfd2022b8845ad8f792aa5825,0xa9f746462d870fdf8a65dc1f90e061e5,0x70d869a156d2a1b890bb3df62baf32f7,0x31be135f97d08fd981231505542fcfa6,0x9aa508b5b7a84e1c677de54f3e99bc9,0x5d6af8dedb81196699c329225ee604,0x2216e584f5fa1ea926041bedfe98,0x48a170391f7dc42444e8fa2]
    for i, c in enumerate(consts):
        if a & (1 << (i + 1)):
            r = (r * c) >> 128
    if tick > 0:
        r = ((1 << 256) - 1) // r
    return (r >> 32) + (0 if r % (1 << 32) == 0 else 1)
import os
os.environ.setdefault("X", "1")
import importlib.util
spec = importlib.util.spec_from_file_location("fe", "/home/user/v2pons/src/flip_engine.py")
def tick_at(sqrt_p):
    return math.floor(2 * math.log(sqrt_p / 2 ** 96) / math.log(1.0001))
random.seed(1)
bad = 0; N = 0
for _ in range(22000):
    t = random.randint(-887000, 887000)
    N += 1
    if tick_at(sqrt_at_tick(t)) != t: bad += 1
print("exact tick prices wrong:", bad, "/", N)
# non-boundary prices: off-by-one only within float eps of a boundary
bad2=0
for _ in range(200000):
    t = random.randint(-887000, 887000)
    s = random.randint(sqrt_at_tick(t), sqrt_at_tick(t+1)-1)
    if tick_at(s) != t: bad2 += 1
print("random prices wrong:", bad2, "/ 200000")
fx = json.load(open("/home/user/v2pons/tests/data/front_launch.json"))
sp = fx["sqrt_p"]; t = tick_at(sp)
print("fixture tick", t, "exact at tick?", sp == sqrt_at_tick(t) or sp == sqrt_at_tick(t+1), sqrt_at_tick(t) <= sp < sqrt_at_tick(t+1))
