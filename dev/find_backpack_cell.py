"""在解开的原版图集里**实际找**背包图标。

上一版直接按 XML 的 u/v 反算像素坐标, 结果裁出来是一段角色贴图 —— 说明
XML 的 v 轴与像素数组的行方向对应关系和我假设的不一样(图集很可能按行分块,
且每行 <= 图集宽度, 块顺序是"从左到右、从上到下", 但 v 是否翻转需要实测)。

与其继续猜坐标映射, 不如直接把整张图集按 64x64 网格铺开, 看**每一格**长什么样,
肉眼看哪一格是背包。这一步是纯客观的: 解码已经证明是正确的(整张图看得出是
整齐的图标网格), 所以只要把格子对上, 就能拿到真正的原版图标。
"""

import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ktex

WORK = os.path.join(HERE, "images_unzip", "images")
ART = os.path.join(HERE, "art")
TEX = os.path.join(WORK, "inventoryimages1.tex")
XML = os.path.join(WORK, "inventoryimages1.xml")

CELL = 64
TARGET = "backpack.tex"


def decode_atlas():
    raw = open(TEX, "rb").read()
    width = int.from_bytes(raw[8:10], "little")
    height = int.from_bytes(raw[10:12], "little")
    payload = raw[128:128 + ktex.dxt5_size(width, height)]
    return ktex.dxt5_decode(payload, width, height)


def parse_regions():
    data = open(XML, encoding="utf-8").read()
    pattern = re.compile(
        r'<Element name="([^"]+)" u1="([\d.]+)" u2="([\d.]+)" v1="([\d.]+)" v2="([\d.]+)"'
    )
    return {
        name: (float(u1), float(u2), float(v1), float(v2))
        for name, u1, u2, v1, v2 in pattern.findall(data)
    }


def save_contact_sheet(rgba, out_path, start_col, start_row, cols, rows, scale=2):
    """把 [start_row, start_row+rows) x [start_col, start_col+cols) 的格子铺成一张图。"""
    height, width = rgba.shape[0], rgba.shape[1]
    sheet = np.zeros((rows * CELL, cols * CELL, 4), dtype=np.uint8)
    for row in range(rows):
        for col in range(cols):
            y = (start_row + row) * CELL
            x = (start_col + col) * CELL
            if y + CELL <= height and x + CELL <= width:
                sheet[row * CELL:(row + 1) * CELL, col * CELL:(col + 1) * CELL] = \
                    rgba[y:y + CELL, x:x + CELL]
    big = np.repeat(np.repeat(sheet, scale, axis=0), scale, axis=1)
    ktex.write_png_rgba(out_path, big)
    return out_path


def main():
    rgba = decode_atlas()
    height, width = rgba.shape[0], rgba.shape[1]
    print("decoded atlas: %dx%d -> %d x %d cells of %dpx"
          % (width, height, width // CELL, height // CELL, CELL))

    regions = parse_regions()
    print("regions in xml: %d" % len(regions))

    os.makedirs(ART, exist_ok=True)

    # 1) 找出每个区域按**两种 v 方向**算出来的格子坐标
    u1, u2, v1, v2 = regions[TARGET]
    col = int(round(u1 * width)) // CELL
    row_from_top = int(round((1.0 - v2) * height)) // CELL   # v 原点在下
    row_from_bottom = int(round(v1 * height)) // CELL        # v 原点在上
    print("\n%s uv=(%.6f,%.6f,%.6f,%.6f)" % (TARGET, u1, u2, v1, v2))
    print("  col=%d  row(若v原点在下)=%d  row(若v原点在上)=%d"
          % (col, row_from_top, row_from_bottom))

    # 2) 把这两种候选行都铺出来看
    for label, row in (("vtop", row_from_top), ("vbottom", row_from_bottom)):
        sheet = save_contact_sheet(
            rgba, os.path.join(ART, "sheet_%s_r%d.png" % (label, row)),
            max(0, col - 3), max(0, row - 2), 7, 5, scale=2)
        print("  %s -> %s" % (label, sheet))

    # 3) 顺便铺一张大图: 图集左上角 16x8 格, 先确认行/列方向
    save_contact_sheet(rgba, os.path.join(ART, "sheet_topleft.png"), 0, 0, 16, 8, scale=2)
    print("  topleft -> art/sheet_topleft.png")

    # 4) 统计: 找出所有"平均不透明度高、且颜色偏灰褐"的格子, 缩小候选范围
    print("\n透明度最高的 15 个格子 (row, col, 不透明像素数):")
    stats = []
    for row in range(height // CELL):
        for col in range(width // CELL):
            cell = rgba[row * CELL:(row + 1) * CELL, col * CELL:(col + 1) * CELL]
            stats.append((int((cell[:, :, 3] > 8).sum()), row, col))
    stats.sort(reverse=True)
    for count, row, col in stats[:15]:
        print("   row=%2d col=%2d  %d" % (row, col, count))


main()
