"""把所有较大的连通块单独导出成 PNG, 用于确认哪个是"背包本体"。

用法: python dump_components.py
输出: dev/art/comp_<标签>_<x0>_<y0>.png
"""

import os
import sys
import zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ktex

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "art")


def label_components(mask):
    height, width = mask.shape
    labels = np.zeros((height, width), dtype=np.int32)
    sizes = [0]
    current = 0
    for y in range(height):
        row = mask[y]
        for x in range(width):
            if not row[x] or labels[y, x]:
                continue
            current += 1
            stack = [(y, x)]
            labels[y, x] = current
            count = 0
            while stack:
                cy, cx = stack.pop()
                count += 1
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not labels[ny, nx]:
                        labels[ny, nx] = current
                        stack.append((ny, nx))
            sizes.append(count)
    return labels, sizes


def main():
    os.makedirs(OUT, exist_ok=True)
    # 用**原版**图集分析, 避免我们画的花把连通块粘在一起
    with zipfile.ZipFile(os.path.join(HERE, "swap_backpack.zip")) as archive:
        data = archive.read("atlas-0.tex")
    info = ktex.parse_ktex(data)
    atlas = ktex.dxt5_decode(info.payload, info.width, info.height)

    mask = atlas[:, :, 3] > 40
    labels, sizes = label_components(mask)
    order = sorted(range(1, len(sizes)), key=lambda i: -sizes[i])

    for rank, label in enumerate(order[:10]):
        ys, xs = np.where(labels == label)
        x0, x1 = int(xs.min()), int(xs.max())
        y0, y1 = int(ys.min()), int(ys.max())
        patch = atlas[y0:y1 + 1, x0:x1 + 1].copy()
        # 透明区域之外的其它符号不要 —— 只保留本连通块的像素
        own = (labels[y0:y1 + 1, x0:x1 + 1] == label)
        patch[~own] = 0
        scale = max(1, 120 // max(patch.shape[0], patch.shape[1]))
        patch = np.repeat(np.repeat(patch, scale, axis=0), scale, axis=1)
        path = os.path.join(OUT, "comp_%02d_%d_%d.png" % (rank, x0, y0))
        ktex.write_png_rgba(path, patch)
        print("rank %-2d label=%-4d size=%-6d box=(%d,%d)-(%d,%d) %dx%d -> %s"
              % (rank, label, sizes[label], x0, y0, x1, y1,
                 x1 - x0 + 1, y1 - y0 + 1, os.path.basename(path)))


main()
