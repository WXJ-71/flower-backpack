"""从原版物品图标图集里取出 backpack.tex 的图标, 并解码成 PNG。

用法: python extract_vanilla_icon.py
输出: dev/art/vanilla_backpack_icon.png
"""

import os
import re
import sys
import zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ktex

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "art")
GAME = r"E:\app\steam\steamapps\common\Don't Starve Together\data\databundles\images.zip"
WORK = os.path.join(HERE, "images_unzip")

TARGET = "backpack.tex"


def ensure_extracted():
    os.makedirs(WORK, exist_ok=True)
    need = ["images/inventoryimages%d.xml" % i for i in (1, 2, 3, 4)]
    need += ["images/inventoryimages1.tex"]
    missing = [n for n in need if not os.path.exists(os.path.join(WORK, n.replace("/", os.sep)))]
    if not missing:
        return
    with zipfile.ZipFile(GAME) as archive:
        for name in need:
            target = os.path.join(WORK, name.replace("/", os.sep))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with archive.open(name) as src, open(target, "wb") as dst:
                dst.write(src.read())
            print("extracted", name)


def find_in_xml(path):
    """在 xml 里找 TARGET 的 uv。返回 (u1, u2, v1, v2) 或 None。"""
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    for match in re.finditer(r'<Element\s+name="([^"]+)"([^/>]*)/>', text):
        if match.group(1) == TARGET:
            attrs = dict(re.findall(r'(\w+)="([^"]*)"', match.group(2)))
            return {k: float(attrs[k]) for k in ("u1", "u2", "v1", "v2") if k in attrs}
    return None


def main():
    ensure_extracted()
    os.makedirs(OUT, exist_ok=True)

    found = None
    for index in (1, 2, 3, 4):
        xml_path = os.path.join(WORK, "images", "inventoryimages%d.xml" % index)
        if not os.path.exists(xml_path):
            continue
        uv = find_in_xml(xml_path)
        print("inventoryimages%d.xml: %s" % (index, uv))
        if uv and found is None:
            found = (index, uv)

    if found is None:
        print("没有在任何图集里找到 %s" % TARGET)
        return

    index, uv = found
    tex_path = os.path.join(WORK, "images", "inventoryimages%d.tex" % index)
    if not os.path.exists(tex_path):
        # 需要的话把对应 tex 也解出来
        with zipfile.ZipFile(GAME) as archive:
            with archive.open("images/inventoryimages%d.tex" % index) as src, open(tex_path, "wb") as dst:
                dst.write(src.read())
        print("extracted inventoryimages%d.tex" % index)

    with open(tex_path, "rb") as handle:
        info = ktex.parse_ktex(handle.read())
    print("图集: %dx%d 格式=0x%02X" % (info.width, info.height, info.format_code))

    atlas = (ktex.argb_decode(info.payload, info.width, info.height, info.row_bytes)
             if ktex.is_argb(info.format_code)
             else ktex.dxt5_decode(info.payload, info.width, info.height))

    # uv -> 像素 (v 轴向下)
    x0 = int(round(uv["u1"] * info.width))
    x1 = int(round(uv["u2"] * info.width))
    y0 = int(round(uv["v1"] * info.height))
    y1 = int(round(uv["v2"] * info.height))
    print("backpack.tex 像素范围: (%d,%d)-(%d,%d)  %dx%d"
          % (x0, y0, x1, y1, x1 - x0, y1 - y0))

    icon = atlas[y0:y1, x0:x1].copy()
    path = os.path.join(OUT, "vanilla_backpack_icon.png")
    ktex.write_png_rgba(path, icon)
    print("-> %s (%dx%d)" % (path, icon.shape[1], icon.shape[0]))


main()
