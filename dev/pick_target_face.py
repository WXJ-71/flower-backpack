"""为"往世界贴图上加花"挑选安全的目标区域。

判据(不需要猜模型拓扑):
  · 模型的每个面在贴图上对应一个**矩形 UV 块**, 所以该块内的非透明像素会
    填满整块矩形 -> "矩形填充率"接近 100%;
  · 而那些形状不规则的部件(背带、翻盖、底座)填充率明显低于 100%;
  · 再把矩形的四个角/四条边检查一遍, 确保是干净的轴对齐矩形。

在这些候选里挑面积最大的(就是背包的主体面), 然后在它的**右下角内侧**加花。
另外会排除掉"横跨整张贴图的大块"(那是我的连通域算法把相邻部件粘在一起的产物)。
"""

import os
import sys
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ktex

WIDTH = HEIGHT = 256
HEADER = 98


def load_atlas():
    with zipfile.ZipFile(os.path.join(HERE, "swap_backpack.zip")) as z:
        raw = z.read("atlas-0.tex")
    return ktex.dxt5_decode(raw[HEADER:HEADER + ktex.dxt5_size(WIDTH, HEIGHT)], WIDTH, HEIGHT)


def components(mask):
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
    labels, count = components(mask)

    print("候选矩形面(填充率 = 非透明像素 / 包围盒面积):\n")
    print("  %-6s %-24s %-9s %-8s %s" % ("编号", "包围盒", "面积", "填充率", "判定"))

    candidates = []
    for index in range(1, count + 1):
        ys, xs = np.where(labels == index)
        area = len(ys)
        if area < 200:
            continue
        x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
        box_w, box_h = x1 - x0 + 1, y1 - y0 + 1
        box_area = box_w * box_h
        fill = area / float(box_area)

        # 面积占比过大(>55% 整图)基本是粘连, 排除
        glued = box_area > 0.55 * WIDTH * HEIGHT
        # 矩形面的四条边应当是实的
        edges_ok = True
        if not glued and box_w > 8 and box_h > 8:
            sub = mask[y0:y1 + 1, x0:x1 + 1]
            edges_ok = bool(sub[0].mean() > 0.9 and sub[-1].mean() > 0.9
                            and sub[:, 0].mean() > 0.9 and sub[:, -1].mean() > 0.9)

        verdict = []
        if glued:
            verdict.append("粘连块(排除)")
        if fill > 0.97:
            verdict.append("矩形")
        if edges_ok:
            verdict.append("四边实")
        print("  %-6d x[%3d,%3d] y[%3d,%3d]  %5d    %5.1f%%   %s"
              % (index, x0, x1, y0, y1, area, fill * 100, " ".join(verdict) or "-"))

        if not glued and fill > 0.97 and edges_ok:
            candidates.append((area, x0, y0, x1, y1, index))

    print()
    if not candidates:
        print("没有找到干净的矩形面 —— 需要改用其它定位办法。")
        return

    candidates.sort(reverse=True)
    print("可安全加花的矩形面(按面积):")
    for area, x0, y0, x1, y1, index in candidates:
        print("  编号 %-4d x[%3d,%3d] y[%3d,%3d]  %3dx%3d  面积 %d"
              % (index, x0, x1, y0, y1, x1 - x0 + 1, y1 - y0 + 1, area))

    area, x0, y0, x1, y1, index = candidates[0]
    print("\n选中: 编号 %d, 矩形 x[%d,%d] y[%d,%d] (%dx%d)"
          % (index, x0, x1, y0, y1, x1 - x0 + 1, y1 - y0 + 1))

    # 导出这块的预览
    art = os.path.join(HERE, "art")
    os.makedirs(art, exist_ok=True)
    crop = rgba[y0:y1 + 1, x0:x1 + 1]
    ktex.write_png_rgba(os.path.join(art, "target_face.png"), crop)
    scale = max(1, 256 // max(crop.shape[0], crop.shape[1]))
    ktex.write_png_rgba(os.path.join(art, "target_face_big.png"),
                        np.repeat(np.repeat(crop, scale, axis=0), scale, axis=1))
    print("目标面预览 -> art/target_face.png (放大 %d 倍: target_face_big.png)" % scale)


main()
