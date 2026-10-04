"""真刀真枪解码原版 inventoryimages1.tex 的 backpack.tex 区域。

背景: 之前判断"图集是平台 swizzle 格式, 线性解码解不出可用像素", 依据是
dev/art/vanilla_backpack_icon.png 看起来是错乱的色块。但那张图只有 64x64,
**可能只是裁错了区域**(裁到压缩块中间/裁到别的符号), 而不是格式问题。

本脚本做真正的验证: 把整张 2048x2048 解出来, 按 XML 里的 UV 反算像素坐标,
把 backpack.tex 区域单独导出成 PNG 看一眼。
"""

import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ktex

WORK = os.path.join(HERE, "images_unzip", "images")
TEX = os.path.join(WORK, "inventoryimages1.tex")
XML = os.path.join(WORK, "inventoryimages1.xml")
ART = os.path.join(HERE, "art")

TARGET = sys.argv[1] if len(sys.argv) > 1 else "backpack.tex"


def find_region(xml_path, name):
    data = open(xml_path, encoding="utf-8").read()
    match = re.search(
        r'<Element name="%s" u1="([\d.]+)" u2="([\d.]+)" v1="([\d.]+)" v2="([\d.]+)"'
        % re.escape(name),
        data,
    )
    if not match:
        raise SystemExit("图集里没有 %s" % name)
    return [float(value) for value in match.groups()]


def main():
    raw = open(TEX, "rb").read()
    width = int.from_bytes(raw[8:10], "little")
    height = int.from_bytes(raw[10:12], "little")
    print("texture: %dx%d, %d bytes, fmt=0x%02X flags=0x%02X"
          % (width, height, len(raw), raw[5], raw[6]))

    expected = ktex.dxt5_size(width, height)
    print("dxt5 first mip expects %d bytes; header = %d" % (expected, len(raw) - expected))

    rgba = ktex.dxt5_decode(raw, width, height, len(raw) - expected)
    print("decoded:", rgba.shape, "alpha>0 pixels:", int((rgba[:, :, 3] > 8).sum()))

    os.makedirs(ART, exist_ok=True)

    # 整张缩略图: 如果是 swizzle 的, 整张会像噪声; 如果是正常图集, 能看到整齐的图标网格
    thumb = ktex.resize_bilinear(rgba, 512, 512)
    ktex.write_png_rgba(os.path.join(ART, "inventoryimages1_full_512.png"), thumb)
    print("整张缩略图 -> art/inventoryimages1_full_512.png")

    # 目标区域
    u1, u2, v1, v2 = find_region(XML, TARGET)
    x0, x1 = int(round(u1 * width)), int(round(u2 * width))
    y0, y1 = int(round(v1 * height)), int(round(v2 * height))
    print("%s uv=(%.6f,%.6f,%.6f,%.6f) -> px x[%d,%d) y[%d,%d) = %dx%d"
          % (TARGET, u1, u2, v1, v2, x0, x1, y0, y1, x1 - x0, y1 - y0))

    # 注意: 图集 v 轴原点在下, 像素数组第 0 行在上 -> 需要翻转
    crop = rgba[height - y1:height - y0, x0:x1]
    out = os.path.join(ART, "atlas1_%s.png" % TARGET.replace(".tex", ""))
    ktex.write_png_rgba(out, crop)
    print("区域导出 -> %s" % out)

    # 放大 6 倍方便肉眼看
    big = np.repeat(np.repeat(crop, 6, axis=0), 6, axis=1)
    ktex.write_png_rgba(os.path.join(ART, "atlas1_%s_x6.png" % TARGET.replace(".tex", "")), big)
    print("放大 6 倍 -> art/atlas1_%s_x6.png" % TARGET.replace(".tex", ""))


main()
