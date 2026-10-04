"""放大导出鲜花印记所在的区域, 用于确认位置与外观。

用法: python zoom_flower.py
"""

import os
import sys
import zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ktex

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "art")

# 花的中心(原图集坐标)与缩放系数, 与 build_flowerpack_art.py 保持一致
FLOWER_CX, FLOWER_CY, FLOWER_R = 178.0, 152.0, 23.0
ATLAS_SCALE = 0.75


def main():
    with zipfile.ZipFile(os.path.join(os.path.dirname(HERE), "anim", "swap_backpack.zip")) as archive:
        data = archive.read("atlas-0.tex")
    info = ktex.parse_ktex(data)
    atlas = ktex.dxt5_decode(info.payload, info.width, info.height)
    print("图集 %dx%d" % (info.width, info.height))

    # 花在缩放后的位置
    cx = int(round(FLOWER_CX * ATLAS_SCALE))
    cy = int(round(FLOWER_CY * ATLAS_SCALE))
    half = 46
    x0 = max(0, cx - half)
    y0 = max(0, cy - half)
    x1 = min(info.width, cx + half)
    y1 = min(info.height, cy + half)
    patch = atlas[y0:y1, x0:x1]

    # 放在深色背景上, 纯白的花才能看清; 同时标记花心
    canvas = np.zeros((patch.shape[0], patch.shape[1], 4), dtype=np.uint8)
    canvas[:, :, 0:3] = (40, 40, 46)
    canvas[:, :, 3] = 255
    opaque = patch[:, :, 3] > 8
    canvas[opaque] = patch[opaque]

    scale = 3
    canvas = np.repeat(np.repeat(canvas, scale, axis=0), scale, axis=1)
    path = os.path.join(OUT, "flower_zoom.png")
    ktex.write_png_rgba(path, canvas)
    print("花中心(缩放后): (%d,%d)  裁剪 (%d,%d)-(%d,%d)" % (cx, cy, x0, y0, x1, y1))
    print("-> %s" % path)


main()
