"""精确测量背包本体(地面/背上那个大符号)在图集上的边界。

做法: 取"右侧那一大块"作为种子区域, 用连通域把它和相关部件抱在一起,
再报告整体边界 —— 这样就得到背包本体实际占据的像素范围。

用法: python measure_body.py
"""

import os
import sys
import zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ktex

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    with zipfile.ZipFile(os.path.join(HERE, "swap_backpack.zip")) as archive:
        data = archive.read("atlas-0.tex")
    info = ktex.parse_ktex(data)
    atlas = ktex.dxt5_decode(info.payload, info.width, info.height)
    mask = atlas[:, :, 3] > 40

    # 逐行统计右侧(x>=160)的不透明像素, 找出背包本体的上下范围
    right = mask[:, 160:]
    rows = right.sum(axis=1)
    print("右侧 x>=160 区域的逐行不透明像素数(每 4 行汇总):")
    for y in range(0, info.height, 4):
        count = int(rows[y:y + 4].sum())
        if count:
            print("  y=%3d-%3d: %s" % (y, y + 3, "#" * min(60, count // 8) or str(count)))

    ys = np.where(rows > 0)[0]
    print("\n右侧内容 y 范围: %d - %d" % (ys.min(), ys.max()))

    # x 方向
    cols = mask[:, :].sum(axis=0)
    xs_right = np.where(cols[160:] > 0)[0] + 160
    print("右侧内容 x 范围: %d - %d" % (xs_right.min(), xs_right.max()))

    # 找出"大块"的边界: 只统计面积较大的连通块, 忽略碎片
    height, width = mask.shape
    labels = np.zeros((height, width), dtype=np.int32)
    sizes = [0]
    current = 0
    for y in range(height):
        for x in range(width):
            if not mask[y, x] or labels[y, x]:
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

    # 右侧 x>=160 且面积 >= 300 的块, 合成整体边界
    keep = np.zeros_like(mask)
    for label in range(1, len(sizes)):
        if sizes[label] < 300:
            continue
        ys2, xs2 = np.where(labels == label)
        if xs2.min() >= 160:
            keep[labels == label] = True
    ys3, xs3 = np.where(keep)
    print("\n右侧主要部件合并边界: x %d-%d, y %d-%d  (%dx%d)"
          % (xs3.min(), xs3.max(), ys3.min(), ys3.max(),
             xs3.max() - xs3.min() + 1, ys3.max() - ys3.min() + 1))


main()
