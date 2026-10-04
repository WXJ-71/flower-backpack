"""用"alpha 锐利度"定位 swap_backpack 图集里基准级 mip 的起点。

思路: 真实贴图的 alpha 通道是**双峰**的(基本只有 0 和 255, 因为原画是硬边),
而错位/噪声数据的 alpha 会均匀散布在 0~255 之间。
所以打分用 mean(min(a, 255-a)) —— 越接近 0 越锐利、越像真图。
这个判据比"相邻像素差"稳, 因为它不受压缩噪声影响。
"""

import os
import sys
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ktex

ART = os.path.join(HERE, "art")
ZIP = os.path.join(HERE, "swap_backpack.zip")

with zipfile.ZipFile(ZIP) as archive:
    raw = archive.read("atlas-0.tex")

WIDTH = HEIGHT = 256
BASE = ktex.dxt5_size(WIDTH, HEIGHT)


def sharpness(rgba):
    alpha = rgba[:, :, 3].astype(np.int32)
    return float(np.minimum(alpha, 255 - alpha).mean())


results = []
for offset in range(0, 400, 2):
    payload = raw[offset:offset + BASE]
    if len(payload) != BASE:
        break
    rgba = ktex.dxt5_decode(payload, WIDTH, HEIGHT)
    results.append((sharpness(rgba), offset))

results.sort()
print("alpha 锐利度最低(=最像真图)的 12 个起点:")
for value, offset in results[:12]:
    print("   offset=%-5d 锐利度=%.2f" % (offset, value))

print("\n最差的 3 个(作对照, 应该是噪声):")
for value, offset in results[-3:]:
    print("   offset=%-5d 锐利度=%.2f" % (offset, value))

best_value, best_offset = results[0]
print("\n最佳起点 = %d (锐利度 %.2f)" % (best_offset, best_value))

os.makedirs(ART, exist_ok=True)
rgba = ktex.dxt5_decode(raw[best_offset:best_offset + BASE], WIDTH, HEIGHT)
ktex.write_png_rgba(os.path.join(ART, "world_atlas_sharp.png"), rgba)
big = np.repeat(np.repeat(rgba, 2, axis=0), 2, axis=1)
ktex.write_png_rgba(os.path.join(ART, "world_atlas_sharp_x2.png"), big)

alpha = rgba[:, :, 3]
hist, _ = np.histogram(alpha, bins=8, range=(0, 256))
print("alpha 直方图(0..255 分 8 档): %s" % list(hist))
print("-> art/world_atlas_sharp.png / _x2.png")
