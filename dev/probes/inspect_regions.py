"""把图集里的几个候选符号区域分别导出成 PNG, 便于目视确认哪块是"背包本体"。

用法: python inspect_regions.py
输出: dev/art/region_<name>.png
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ktex

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "art")

# 由 analyze_atlas.py 得到的 8 个最大连通块
REGIONS = {
    "biggest_168_61": (168, 61, 256, 164),
    "second_35_24": (35, 24, 100, 92),
    "third_35_101": (35, 101, 100, 167),
    "fourth_169_0": (169, 0, 232, 53),
    "fifth_109_97": (109, 97, 155, 168),
    "sixth_0_66": (0, 66, 26, 167),
    "lower_168_180": (168, 180, 256, 256),
    "lower_0_180": (0, 180, 160, 256),
}


def main():
    os.makedirs(OUT, exist_ok=True)
    import zipfile
    with zipfile.ZipFile(os.path.join(os.path.dirname(HERE), "anim", "swap_backpack.zip")) as archive:
        data = archive.read("atlas-0.tex")
    info = ktex.parse_ktex(data)
    atlas = ktex.dxt5_decode(info.payload, info.width, info.height)

    for name, (x0, y0, x1, y1) in REGIONS.items():
        x1 = min(x1, atlas.shape[1])
        y1 = min(y1, atlas.shape[0])
        patch = atlas[y0:y1, x0:x1]
        # 放大 2 倍便于看清
        patch = np.repeat(np.repeat(patch, 2, axis=0), 2, axis=1)
        path = os.path.join(OUT, "region_%s.png" % name)
        ktex.write_png_rgba(path, patch)
        print("%-18s -> %s (%dx%d)" % (name, os.path.basename(path), patch.shape[1], patch.shape[0]))


main()
