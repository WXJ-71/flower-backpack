"""原版 inventoryimages1.tex 的真实结构探查。

之前判定"swizzle 解不出像素"的依据是 dev/art/vanilla_backpack_icon.png 看起来是
错乱色块。但现在算了一下字节数, 发现**当初取的偏移就是错的**:

    文件大小            5592560
    BC3 首级(2048x2048)  4194304  = 128*128*16*16
    差值                1398256

若是"头 + 首级mip"(首级在文件开头):
    剩余 1398256 应当等于 1024x1024 以下的**整条 mip 链**之和
    1024x1024: 1048576, 512: 262144, 256: 65536, 128: 16384,
    64: 4096, 32: 1024, 16: 256, 8: 64, 4: 16, 2: 1, 1: 1
    合计 = 1398098 ... 与 1398256 差 158
    (差值应该是 mip 链对齐填充 + 头部长度, 需要实测确认)

关键结论: 原来的解码器假定"首级 mip 在文件**末尾**"(用 文件长 - 首级大小 反推头长),
对这张图是错的 -> 它把 mip 链当成了首级, 所以解出来是噪声。
本脚本把两种排布都试一遍, 并把结果导出成 PNG 由肉眼判定。
"""

import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ktex

WORK = os.path.join(HERE, "images_unzip", "images")
ART = os.path.join(HERE, "art")
TEX = os.path.join(WORK, "inventoryimages1.tex")


def mip_chain_size(width, height):
    """BC3 从 width x height 一直到 1x1 的所有 mip 字节数之和。"""
    total = 0
    w, h = width, height
    while True:
        total += ((w + 3) // 4) * ((h + 3) // 4) * 16
        if w == 1 and h == 1:
            break
        w = max(1, w // 2)
        h = max(1, h // 2)
    return total


def main():
    raw = open(TEX, "rb").read()
    size = len(raw)
    width = struct.unpack_from("<H", raw, 8)[0]
    height = struct.unpack_from("<H", raw, 10)[0]
    row_bytes = struct.unpack_from("<H", raw, 12)[0]

    print("file size      : %d" % size)
    print("magic          : %r" % raw[0:4])
    print("bytes 4..17    : %s" % " ".join("%02X" % b for b in raw[4:18]))
    print("width x height : %d x %d" % (width, height))
    print("row bytes      : %d" % row_bytes)
    print()

    base = ktex.dxt5_size(width, height)
    chain = mip_chain_size(width, height)
    print("BC3 base level (%dx%d)      = %d" % (width, height, base))
    print("BC3 full mip chain          = %d" % chain)
    print("size - base                 = %d" % (size - base))
    print("size - chain                = %d   <- 若为小正数, 说明是 头+整条mip链" % (size - chain))
    print()

    os.makedirs(ART, exist_ok=True)

    # 排布 A: 头 + 首级mip(首级在开头)
    header_a = size - chain
    if 0 < header_a < 256:
        payload = raw[header_a:header_a + base]
        rgba = ktex.dxt5_decode(payload, width, height)
        out = os.path.join(ART, "atlas1_tryA_start.png")
        ktex.write_png_rgba(out, ktex.resize_bilinear(rgba, 512, 512))
        alive = int((rgba[:, :, 3] > 8).sum())
        print("排布A 头长=%d  不透明像素=%d (%.1f%%) -> %s"
              % (header_a, alive, 100.0 * alive / (width * height), out))

        # 顺手把 backpack.tex 区域抠出来
        u1, u2, v1, v2 = 0.093994140625, 0.124755859375, 0.781494140625, 0.812255859375
        x0, x1 = int(round(u1 * width)), int(round(u2 * width))
        y0, y1 = int(round(v1 * height)), int(round(v2 * height))
        crop = rgba[height - y1:height - y0, x0:x1]
        ktex.write_png_rgba(os.path.join(ART, "atlas1_backpack_A.png"), crop)
        big = np.repeat(np.repeat(crop, 6, axis=0), 6, axis=1)
        ktex.write_png_rgba(os.path.join(ART, "atlas1_backpack_A_x6.png"), big)
        print("     backpack 区域 %dx%d -> art/atlas1_backpack_A.png / _x6.png"
              % (crop.shape[1], crop.shape[0]))
    else:
        print("排布A 不成立 (头长=%d)" % header_a)

    # 排布 B: 首级mip在末尾(旧假设)
    header_b = size - base
    payload = raw[header_b:]
    rgba_b = ktex.dxt5_decode(payload, width, height)
    out_b = os.path.join(ART, "atlas1_tryB_end.png")
    ktex.write_png_rgba(out_b, ktex.resize_bilinear(rgba_b, 512, 512))
    alive_b = int((rgba_b[:, :, 3] > 8).sum())
    print("排布B 头长=%d  不透明像素=%d (%.1f%%) -> %s"
          % (header_b, alive_b, 100.0 * alive_b / (width * height), out_b))


main()
