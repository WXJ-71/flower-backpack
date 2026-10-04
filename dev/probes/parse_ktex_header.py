"""解析 KTEX 头部里那段"每级 mip 一条记录"的表, 弄清真实布局。

从并排对比看到的模式(四个文件都一样):
    offset 8:  w (u16, 大端写法但值是"正常"的, 如 00 01 = 256)
    offset 10: h (u16)
    然后每 5 字节一条 mip 记录, 形如  w h <3字节尺寸>
        swap_backpack: 00 04 00 00 01 | 00 80 00 80 00 | 00 02 00 40 00 | ...
        inventoryimg1: 00 04 00 04 00 | 10 00 00 10 00 | 00 02 00 02 00 | ...
第一条是基准级(尺寸最大), 之后依次减半, 直到 1x1 之后开始就是真实像素数据。

本脚本把表长度算出来, 用"文件大小 - 各级 mip 字节数之和"反推真实数据起点,
再和"表实际占用的字节数"对照, 确认解释是否正确。
"""

import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
MOD_ROOT = os.path.dirname(HERE)


def mip_sizes(width, height):
    sizes = []
    w, h = width, height
    while True:
        sizes.append(((w + 3) // 4) * ((h + 3) // 4) * 16)
        if w == 1 and h == 1:
            break
        w = max(1, w // 2)
        h = max(1, h // 2)
    return sizes


def analyze(label, raw):
    width = int.from_bytes(raw[8:10], "little")
    height = int.from_bytes(raw[10:12], "little")
    sizes = mip_sizes(width, height)
    chain = sum(sizes)

    print("== %s ==" % label)
    print("   %dx%d, 文件 %d 字节" % (width, height, len(raw)))
    print("   完整 mip 链 = %d 字节 (%d 级)" % (chain, len(sizes)))
    print("   文件 - 完整链 = %d   <- 若与'真实数据起点'吻合, 说明存了整条链" % (len(raw) - chain))
    print("   文件 - 仅首级 = %d   <- 若吻合, 说明只存了首级" % (len(raw) - sizes[0]))
    print("   mip 字节数: %s" % sizes[:8])
    print()

    # 头部原始字节, 按 5 字节一组猜记录
    print("   头部字节(前 64): %s" % " ".join("%02X" % b for b in raw[:64]))
    print()


with zipfile.ZipFile(os.path.join(HERE, "swap_backpack.zip")) as z:
    analyze("swap_backpack/atlas-0.tex", z.read("atlas-0.tex"))

with zipfile.ZipFile(os.path.join(HERE, "ui_backpack_2x4.zip")) as z:
    for name in z.namelist():
        if name.endswith(".tex"):
            analyze("ui_backpack_2x4/" + name, z.read(name))

analyze("modicon.tex", open(os.path.join(MOD_ROOT, "modicon.tex"), "rb").read())
analyze("images/flowerpack.tex", open(os.path.join(MOD_ROOT, "images", "flowerpack.tex"), "rb").read())

path = os.path.join(HERE, "images_unzip", "images", "inventoryimages1.tex")
if os.path.exists(path):
    with open(path, "rb") as handle:
        analyze("inventoryimages1.tex", handle.read())
