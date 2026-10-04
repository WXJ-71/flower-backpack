"""分析原版 swap_backpack 图集: 找出各部件(符号)的边界框。

用途: 做物品图标时需要"原版背包本体"的图像区域; 做鲜花印记时需要知道
右下角有没有和描边重叠。

用法: python analyze_atlas.py
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ktex

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "swap_backpack_unzip", "atlas-0.tex")


def label_components(mask):
    """极简连通域标记(4 邻域), 返回 (标签图, 各标签像素数)。"""
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
    return labels, sizes


def main():
    with open(SRC, "rb") as handle:
        info = ktex.parse_ktex(handle.read())
    rgba = ktex.dxt5_decode(info.payload, info.width, info.height)
    mask = rgba[:, :, 3] > 40

    labels, sizes = label_components(mask)
    order = sorted(range(1, len(sizes)), key=lambda i: -sizes[i])

    print("图集 %dx%d, 不透明像素 %d" % (info.width, info.height, int(mask.sum())))
    print("\n最大的 12 个连通块:")
    print("  %-6s %-8s %s" % ("标签", "像素数", "边界框 (x0,y0)-(x1,y1)  宽x高"))
    for label in order[:12]:
        ys, xs = np.where(labels == label)
        x0, x1 = int(xs.min()), int(xs.max())
        y0, y1 = int(ys.min()), int(ys.max())
        print("  %-6d %-8d (%d,%d)-(%d,%d)  %dx%d"
              % (label, sizes[label], x0, y0, x1, y1, x1 - x0 + 1, y1 - y0 + 1))

    # 右下角区域(鲜花印记要放的地方)的不透明情况
    for size in (48, 64, 80):
        region = mask[info.height - size:, info.width - size:]
        print("\n右下角 %dx%d 区域: 不透明 %d / %d" % (size, size, int(region.sum()), size * size))

    # 左上 / 右上 / 左下 也看一下, 便于挑最空的位置
    for corner, (ys, xs) in {
        "左上": (slice(0, 64), slice(0, 64)),
        "右上": (slice(0, 64), slice(info.width - 64, info.width)),
        "左下": (slice(info.height - 64, info.height), slice(0, 64)),
        "右下": (slice(info.height - 64, info.height), slice(info.width - 64, info.width)),
    }.items():
        region = mask[ys, xs]
        print("%s 64x64: 不透明 %d / %d" % (corner, int(region.sum()), 64 * 64))


main()
