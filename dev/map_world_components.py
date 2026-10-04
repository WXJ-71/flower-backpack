"""找出 swap_backpack 图集上每块"部件"的像素矩形。

目的: 要往背包上加花, 必须知道图集上哪一块对应模型的哪个面, 才能把花画在
"朝外的那个面"上, 而不是画到侧面/底面去。

做法: 解码图集 -> 取 alpha>128 的连通区域(用简单的行列投影法分块,
      因为这些部件之间留了明显的空隙) -> 输出每块的包围盒与尺寸,
      并导出一张"分块预览"(每块描一个不同的纯色边框), 便于肉眼对照。
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
WIDTH = HEIGHT = 256
# 由尺寸关系精确确定: 87506 - 65536(基准级) - 21872(其余 mip) = 98
HEADER = 98


def load_atlas():
    with zipfile.ZipFile(ZIP) as archive:
        raw = archive.read("atlas-0.tex")
    return ktex.dxt5_decode(raw[HEADER:HEADER + ktex.dxt5_size(WIDTH, HEIGHT)], WIDTH, HEIGHT)


def label_components(mask):
    """4 邻域 flood fill 标连通区域(纯 numpy 实现, 不用 scipy)。"""
    labels = np.zeros(mask.shape, dtype=np.int32)
    current = 0
    height, width = mask.shape
    for sy in range(height):
        for sx in range(width):
            if not mask[sy, sx] or labels[sy, sx]:
                continue
            current += 1
            stack = [(sy, sx)]
            labels[sy, sx] = current
            while stack:
                y, x = stack.pop()
                for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not labels[ny, nx]:
                        labels[ny, nx] = current
                        stack.append((ny, nx))
    return labels, current


def main():
    rgba = load_atlas()
    mask = rgba[:, :, 3] > 128
    print("不透明像素 %d / %d" % (int(mask.sum()), WIDTH * HEIGHT))

    labels, count = label_components(mask)
    print("连通部件数: %d" % count)

    preview = rgba.copy()
    palette = [
        (255, 0, 0, 255), (0, 200, 0, 255), (0, 80, 255, 255), (255, 160, 0, 255),
        (200, 0, 255, 255), (0, 220, 220, 255), (255, 255, 0, 255), (255, 0, 160, 255),
        (120, 90, 40, 255), (0, 0, 0, 255),
    ]

    items = []
    for index in range(1, count + 1):
        ys, xs = np.where(labels == index)
        area = len(ys)
        if area < 20:
            continue
        x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
        items.append((area, x0, y0, x1, y1, index))

    items.sort(reverse=True)
    print("\n按面积排序的部件(前 20):")
    print("  面积    包围盒                宽  高   中心")
    for area, x0, y0, x1, y1, index in items[:20]:
        colour = palette[(index - 1) % len(palette)]
        # 给这块描边
        preview[y0:y1 + 1, x0] = colour
        preview[y0:y1 + 1, x1] = colour
        preview[y0, x0:x1 + 1] = colour
        preview[y1, x0:x1 + 1] = colour
        print("  %5d  x[%3d,%3d] y[%3d,%3d]  %3d %3d  (%3d,%3d)"
              % (area, x0, x1, y0, y1, x1 - x0 + 1, y1 - y0 + 1,
                 (x0 + x1) // 2, (y0 + y1) // 2))

    os.makedirs(ART, exist_ok=True)
    ktex.write_png_rgba(os.path.join(ART, "world_atlas_components.png"), preview)
    big = np.repeat(np.repeat(preview, 2, axis=0), 2, axis=1)
    ktex.write_png_rgba(os.path.join(ART, "world_atlas_components_x2.png"), big)
    print("\n分块预览 -> art/world_atlas_components.png / _x2.png")


main()
