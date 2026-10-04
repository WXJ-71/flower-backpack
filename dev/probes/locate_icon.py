"""在 inventoryimages1.tex 里定位 backpack.tex 图标: 导出候选区域对比。

用法: python locate_icon.py
输出: dev/art/icon_candidate_*.png
"""

import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ktex

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "art")
WORK = os.path.join(HERE, "images_unzip")


def find_uv():
    xml_path = os.path.join(WORK, "images", "inventoryimages1.xml")
    with open(xml_path, "r", encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    for match in re.finditer(r'<Element\s+name="backpack\.tex"([^/>]*)/>', text):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', match.group(1)))
        return {k: float(attrs[k]) for k in ("u1", "u2", "v1", "v2") if k in attrs}
    return None


def save(name, rgba):
    path = os.path.join(OUT, name)
    ktex.write_png_rgba(path, rgba)
    print("%-28s %dx%d -> %s" % (name, rgba.shape[1], rgba.shape[0], os.path.basename(path)))


def main():
    uv = find_uv()
    print("uv:", uv)

    with open(os.path.join(WORK, "images", "inventoryimages1.tex"), "rb") as handle:
        info = ktex.parse_ktex(handle.read())
    atlas = ktex.dxt5_decode(info.payload, info.width, info.height)
    print("atlas %dx%d" % (info.width, info.height))

    w = uv["u2"] - uv["u1"]
    h = uv["v2"] - uv["v1"]
    x0 = int(round(uv["u1"] * info.width))
    y_top = int(round(uv["v1"] * info.height))
    y_bottom_flipped = int(round((1.0 - uv["v2"]) * info.height))
    px_w = int(round(w * info.width))
    px_h = int(round(h * info.height))
    print("像素尺寸 %dx%d" % (px_w, px_h))

    # 候选 1: v 向下
    save("icon_candidate_vdown.png",
         atlas[y_top:y_top + px_h, x0:x0 + px_w].copy())
    # 候选 2: v 向上(翻转)
    save("icon_candidate_vflip.png",
         atlas[y_bottom_flipped:y_bottom_flipped + px_h, x0:x0 + px_w].copy())

    # 顺带把图集左上角切一小块出来看看排布规律
    save("atlas_topleft.png", atlas[0:192, 0:192].copy())


main()
