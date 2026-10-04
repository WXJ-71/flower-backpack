"""自动寻找鲜花印记的最佳位置: 尽量不与背包任何部件重叠。

算法: 遍历候选中心, 计算"花朵圆盘内的不透明像素数", 取最小的那些,
      再在其中挑离背包本体中心最近的(视觉上贴着背包)。

用法: python find_flower_slot.py
"""

import os
import sys
import zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ktex

HERE = os.path.dirname(os.path.abspath(__file__))


def flower_mask(shape, cx, cy, radius):
    height, width = shape
    yy, xx = np.mgrid[0:height, 0:width]
    mask = np.zeros((height, width), dtype=bool)
    import math
    for index in range(5):
        angle = math.pi * 2.0 * index / 5.0 - math.pi / 2.0
        px = cx + math.cos(angle) * radius * 0.58
        py = cy + math.sin(angle) * radius * 0.58
        mask |= ((xx - px) ** 2 + (yy - py) ** 2) <= (radius * 0.46) ** 2
    return mask


def main():
    with zipfile.ZipFile(os.path.join(HERE, "swap_backpack.zip")) as archive:
        data = archive.read("atlas-0.tex")
    info = ktex.parse_ktex(data)
    atlas = ktex.dxt5_decode(info.payload, info.width, info.height)
    opaque = atlas[:, :, 3] > 40

    radius = float(sys.argv[1]) if len(sys.argv) > 1 else 15.0
    best = []
    for cy in range(int(radius) + 2, info.height - int(radius) - 2, 3):
        for cx in range(160, info.width - int(radius) - 2, 3):
            mask = flower_mask(opaque.shape, cx, cy, radius)
            overlap = int((mask & opaque).sum())
            total = int(mask.sum())
            if total == 0:
                continue
            ratio = overlap / float(total)
            if ratio < 0.06:   # 允许极少重叠
                best.append((ratio, overlap, cx, cy))

    best.sort(key=lambda t: (t[1], abs(t[2] - 210) + abs(t[3] - 115)))
    print("花朵半径 %.0f, 候选(重叠像素少 -> 且靠近背包):" % radius)
    for ratio, overlap, cx, cy in best[:12]:
        print("  (%3d,%3d) 重叠 %4d 像素 (%.1f%%)" % (cx, cy, overlap, ratio * 100))

    if best:
        ratio, overlap, cx, cy = best[0]
        print("\n推荐: FLOWER_CX = %d, FLOWER_CY = %d, FLOWER_R = %d (重叠 %d 像素)"
              % (cx, cy, int(radius), overlap))
        # 导出该位置的预览
        preview = atlas.copy()
        mask = flower_mask(opaque.shape, cx, cy, radius)
        preview[mask] = (255, 60, 60, 255)
        out = os.path.join(HERE, "art", "flower_slot_preview.png")
        ktex.write_png_rgba(out, preview)
        print("预览(红色标出花朵位置): %s" % out)


main()
