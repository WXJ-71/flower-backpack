"""导出背包本体所在的完整区域(带坐标网格提示), 用于精确定位鲜花印记。

用法: python inspect_body.py
输出: dev/art/body_region.png
"""

import os
import sys
import zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ktex

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "art")

# 右半部分整块导出来看, 覆盖背包本体可能的范围
BOX = (150, 20, 256, 180)


def main():
    os.makedirs(OUT, exist_ok=True)
    with zipfile.ZipFile(os.path.join(os.path.dirname(HERE), "anim", "swap_backpack.zip")) as archive:
        data = archive.read("atlas-0.tex")
    info = ktex.parse_ktex(data)
    atlas = ktex.dxt5_decode(info.payload, info.width, info.height)

    x0, y0, x1, y1 = BOX
    patch = atlas[y0:y1, x0:x1].copy()

    # 放大 2 倍并叠加每 20 像素的参考线(用低透明度的青色标出绝对坐标)
    patch = np.repeat(np.repeat(patch, 2, axis=0), 2, axis=1)
    height, width = patch.shape[0], patch.shape[1]
    for abs_x in range(x0, x1, 20):
        px = (abs_x - x0) * 2
        if 0 <= px < width:
            patch[:, px] = np.where(patch[:, px, 3:4] > 0,
                                    (patch[:, px] * 0.6 + np.array([0, 200, 255, 255]) * 0.4).astype(np.uint8),
                                    np.array([0, 200, 255, 120], dtype=np.uint8))
    for abs_y in range(y0, y1, 20):
        py = (abs_y - y0) * 2
        if 0 <= py < height:
            patch[py, :] = np.where(patch[py, :, 3:4] > 0,
                                    (patch[py, :] * 0.6 + np.array([0, 200, 255, 255]) * 0.4).astype(np.uint8),
                                    np.array([0, 200, 255, 120], dtype=np.uint8))

    path = os.path.join(OUT, "body_region.png")
    ktex.write_png_rgba(path, patch)
    print("region %s 尺寸 %dx%d (2 倍放大, 青色线每 20 绝对像素)" % (BOX, patch.shape[1], patch.shape[0]))
    print("-> %s" % path)


main()
