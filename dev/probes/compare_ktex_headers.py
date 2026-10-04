"""并排对比几个 KTEX 文件的头部字节, 找出 swap_backpack 图集为什么解不对。"""

import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
MOD_ROOT = os.path.dirname(HERE)


def dump(label, raw, n=48):
    print("== %s ==" % label)
    print("   文件大小 %d" % len(raw))
    print("   " + " ".join("%02X" % b for b in raw[:n]))
    print("   magic=%r  b4=0x%02X fmt=0x%02X b6=0x%02X b7=0x%02X  w=%d h=%d row=%d u32@14=%d"
          % (raw[0:4], raw[4], raw[5], raw[6], raw[7],
             int.from_bytes(raw[8:10], "little"),
             int.from_bytes(raw[10:12], "little"),
             int.from_bytes(raw[12:14], "little"),
             int.from_bytes(raw[14:18], "little")))


with zipfile.ZipFile(os.path.join(HERE, "swap_backpack.zip")) as z:
    dump("swap_backpack/atlas-0.tex", z.read("atlas-0.tex"))

with zipfile.ZipFile(os.path.join(HERE, "backpack.zip")) as z:
    names = z.namelist()
    print("backpack.zip 内容:", names)
    for name in names:
        if name.endswith(".tex"):
            dump("backpack.zip/" + name, z.read(name))

dump("modicon.tex (已知可用)", open(os.path.join(MOD_ROOT, "modicon.tex"), "rb").read())
dump("images/flowerpack.tex (新做的, 已知可用)",
     open(os.path.join(MOD_ROOT, "images", "flowerpack.tex"), "rb").read())

# 原版 inventoryimages1 的头部(已知是 mip 链布局)做对照
atlas1 = os.path.join(HERE, "images_unzip", "images", "inventoryimages1.tex")
if os.path.exists(atlas1):
    with open(atlas1, "rb") as handle:
        head = handle.read(48)
    print("== inventoryimages1.tex (只读头 48 字节) ==")
    print("   " + " ".join("%02X" % b for b in head))
