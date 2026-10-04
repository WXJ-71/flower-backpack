"""从 build.bin 里把几何体真正用到的 UV 范围解出来。

这样就能确定 atlas-0.tex 上"哪一块会出现在模型上", 从而把花画在**看得见的面**上,
而不是画到侧面/底面/用不到的区域。

build.bin 头部结构(已从十六进制确认):
    0   4   magic "BILD"
    4   4   version = 6
    8   4   hash? = 1
    12  4   构建名长度
    16  N   构建名              "swap_backpack"
    ..  4   图集数量 = 1
    ..  4 + N   图集名          "atlas-0.tex"
    ..  4   hash
    ..  4   符号数量 = 1
    ..  4   帧数 = 1
    ..  4   顶点数? = 1
    然后每个符号/帧后面跟顶点数组, 顶点里含 UV。

本脚本不硬编码"顶点里 UV 在第几个 float", 而是**整文件扫描 IP 区间内的浮点**,
把落在 [0,1] 的成对值全部收集起来, 求 min/max —— 对"这块贴图被用在哪些 UV 范围"
这个问题, 这个统计答案已经足够, 而且不会因为结构猜错而失效。
"""

import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

BUILD = os.path.join(HERE, "swap_backpack_unzip", "build.bin")


def floats(data):
    count = len(data) // 4
    return np.frombuffer(data[:count * 4], dtype="<f4")


def main():
    with open(BUILD, "rb") as handle:
        data = handle.read()

    print("build.bin %d 字节" % len(data))
    values = floats(data)

    finite = values[np.isfinite(values)]
    in_unit = finite[(finite >= -0.001) & (finite <= 1.001)]
    print("全部 float: %d, 有限: %d, 落在 [0,1]: %d" % (len(values), len(finite), len(in_unit)))

    # 统计 UV 使用范围: 取所有 [0,1] 浮点的直方图
    if len(in_unit):
        print("\n[0,1] 浮点的分布(每 0.0625 一档):")
        hist, edges = np.histogram(in_unit, bins=16, range=(0, 1))
        for i, count in enumerate(hist):
            if count:
                print("  %.4f - %.4f : %5d  %s" % (edges[i], edges[i + 1], count, "#" * min(60, count)))

    # 顶点里通常是 x y z u v w 之类；把 [0,1] 的值当成 UV 候选，
    # 看它们大致占据哪个矩形（用于判断模型用了贴图的哪些区域）
    uvish = in_unit
    if len(uvish):
        print("\n[0,1] 浮点范围: u/最小值=%.4f 最大=%.4f" % (uvish.min(), uvish.max()))

    # 更精确: 找出连续 2 个浮点都在 [0,1] 的位置（uv 成对出现）
    pairs = []
    for offset in range(0, len(data) - 8, 4):
        a, b = struct.unpack_from("<ff", data, offset)
        if 0.0 <= a <= 1.0 and 0.0 <= b <= 1.0:
            pairs.append((offset, a, b))
    print("\n成对落在 [0,1] 的 (offset, a, b) 共 %d 组, 前 40 组:" % len(pairs))
    for offset, a, b in pairs[:40]:
        print("  @%-6d  %.4f  %.4f" % (offset, a, b))

    if pairs:
        arr = np.array([[a, b] for _, a, b in pairs])
        print("\n配对浮点的整体范围: a[%.4f,%.4f]  b[%.4f,%.4f]"
              % (arr[:, 0].min(), arr[:, 0].max(), arr[:, 1].min(), arr[:, 1].max()))
        # 换算成 256x256 图集上的像素矩形
        x0 = arr[:, 0].min() * 256
        x1 = arr[:, 0].max() * 256
        y0 = (1 - arr[:, 1].max()) * 256
        y1 = (1 - arr[:, 1].min()) * 256
        print("若按 256x256 图集解, 像素矩形约 x[%.0f,%.0f] y[%.0f,%.0f] (v 轴原点在下)"
              % (x0, x1, y0, y1))


main()
