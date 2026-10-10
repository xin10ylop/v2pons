def sgn_w(d, i):
    x = int(d[2 + 64 * i: 2 + 64 * (i + 1)], 16)
    return x - (1 << 256) if x >= (1 << 255) else x
