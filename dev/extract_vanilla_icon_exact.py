"""精确抠出原版 backpack.tex 图标(64x64), 并顺带输出对比用的候选行。

已确认:
  · 图集 2048x2048 = 32x32 个 64x64 格
  · KTEX = 128 字节头 + 整条 BC3 mip 链, 首级在**开头**
  · XML 的 v 轴原点在**上**, 行号 = int(v1 * 2048) / 64
所以 row 25 一片都是背包类图标, 现在只需要定列。
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


def decode_atlas():
    raw = open(TEX, "rb").read()
    width = int.from_bytes(raw[8:10], "little")
    height = int.from_bytes(raw[10:12], "little")
    payload = raw[128:128 + ktex.dxt5_size(width, height)]
    return ktex.dxt5_decode(payload, width, height)


def main():
    rgba = decode_atlas()
    height, width = rgba.shape[0], rgba.shape[1]
    data = open(XML, encoding="utf-8").read()
    pattern = re.compile(
        r'<Element name="([^"]+)" u1="([\d.]+)" u2="([\d.]+)" v1="([\d.]+)" v2="([\d.]+)"'
    )
    regions = {
        name: (float(u1), float(u2), float(v1), float(v2))
        for name, u1, u2, v1, v2 in pattern.findall(data)
    }

    os.makedirs(ART, exist_ok=True)

    # 把 row 25 整行铺出来(32 格), 标出每一格的编号
    row = 25
    row_img = rgba[row * CELL:(row + 1) * CELL, :]
    big = np.repeat(np.repeat(row_img, 3, axis=0), 3, axis=1)
    ktex.write_png_rgba(os.path.join(ART, "row25_full.png"), big)
    print("row 25 全行 -> art/row25_full.png  (32 格, 3 倍放大)")

    # 打印 row 25 上所有区域名与列号, 方便比对
    print("\nrow 25 上的区域:")
    on_row = []
    for name, (u1, u2, v1, v2) in sorted(regions.items(), key=lambda kv: kv[1][0]):
        r = int(round(v1 * height)) // CELL
        if r == row:
            c = int(round(u1 * width)) // CELL
            on_row.append((c, name))
    for c, name in sorted(on_row):
        print("   col=%2d  %s" % (c, name))

    # 抠出 backpack.tex 的格子
    u1, u2, v1, v2 = regions["backpack.tex"]
    col = int(round(u1 * width)) // CELL
    r = int(round(v1 * height)) // CELL
    print("\nbackpack.tex -> col=%d row=%d" % (col, r))

    crop = rgba[r * CELL:(r + 1) * CELL, col * CELL:(col + 1) * CELL]
    out = os.path.join(ART, "vanilla_backpack_icon_64.png")
    ktex.write_png_rgba(out, crop)
    big2 = np.repeat(np.repeat(crop, 6, axis=0), 6, axis=1)
    ktex.write_png_rgba(os.path.join(ART, "vanilla_backpack_icon_x6.png"), big2)
    print("抠出 -> %s" % out)
    print("     不透明像素: %d / %d" % (int((crop[:, :, 3] > 8).sum()), CELL * CELL))

    # 同时导出该格上下左右几格, 便于确认没串行
    neigh = np.zeros((CELL, CELL * 5, 4), dtype=np.uint8)
    for i, offset in enumerate((-2, -1, 0, 1, 2)):
        c = col + offset
        if 0 <= c < width // CELL:
            neigh[:, i * CELL:(i + 1) * CELL] = rgba[r * CELL:(r + 1) * CELL, c * CELL:(c + 1) * CELL]
    ktex.write_png_rgba(
        os.path.join(ART, "backpack_neighbours.png"),
        np.repeat(np.repeat(neigh, 4, axis=0), 4, axis=1))
    print("邻格(col-2..col+2) -> art/backpack_neighbours.png")


main()
