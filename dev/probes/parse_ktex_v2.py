"""按正确的头部格式解析 KTEX, 并对所有已知文件做解码验证。

【真正的头部格式】(从并排字节对比推出来的)
    offset 0   magic "KTEX"
    offset 4   u8  0x20 固定
    offset 5   u8  像素格式 (低半字节 2 = BC3, 0x42 = ARGB)
    offset 6   u8  标志 (DXT5 法线图为 0xFD, 普通为 0xFC)
    offset 7   u8  0xFF
    offset 8   u16 宽
    offset 10  u16 高
    offset 12  *   **每级 mip 一条 5 字节记录**, 记录数 = 存在多少级:
                       +0 u8  宽/4  (DXT5 的块数)
                       +1 u8  高/4
                       +2..4  该级字节数 / 16 的 24 位小端值
    之后        像素数据(实际只存了**基准级**, 即最后 mip_bytes 个字节)

注意: 旧代码用 "头长 = 文件长 - 基准级字节数" 反推头长 —— 对只存基准级的文件,
这个值**恰好等于真实头部长度**(因为像素数据在文件末尾), 所以一直能用。
但那次改动的错误在于把它套到带完整 mip 链的 inventoryimages1 上。

本脚本用"每条 5 字节记录"的显式解析来交叉验证: 解析出的表长度应当等于
文件长 - 基准级字节数。两条独立算法一致, 才认定布局判断可靠。
"""

import os
import sys
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MOD_ROOT = os.path.dirname(HERE)


def parse_mip_table(raw):
    """返回 [(宽, 高, 字节数), ...]; 解析到记录不再合法为止。"""
    width = int.from_bytes(raw[8:10], "little")
    height = int.from_bytes(raw[10:12], "little")
    entries = []
    offset = 12
    w, h = width, height
    while offset + 5 <= len(raw) and w >= 1 and h >= 1:
        bw, bh, size24 = raw[offset], raw[offset + 1], int.from_bytes(raw[offset + 2:offset + 5], "little")
        if bw != max(1, w // 4) or bh != max(1, h // 4):
            break
        expected = ((w + 3) // 4) * ((h + 3) // 4) * 16
        if size24 != expected // 16:
            break
        entries.append((w, h, expected))
        offset += 5
        if w == 1 and h == 1:
            break
        w = max(1, w // 2)
        h = max(1, h // 2)
    return entries, offset


def analyze(label, raw, expect_image=True):
    width = int.from_bytes(raw[8:10], "little")
    height = int.from_bytes(raw[10:12], "little")
    base = ((width + 3) // 4) * ((height + 3) // 4) * 16
    entries, table_end = parse_mip_table(raw)
    implied_header = len(raw) - base

    print("== %s ==" % label)
    print("   %dx%d, 文件 %d 字节" % (width, height, len(raw)))
    print("   基准级 %d 字节;  文件-基准级 = %d (隐含头长)" % (base, implied_header))
    print("   解析出的 mip 记录 %d 条, 表在 offset %d 结束" % (len(entries), table_end))
    print("   两者%s" % ("一致 ✔" if table_end == implied_header
                        else "不一致 �’ (差 %d)" % (table_end - implied_header)))
    if len(entries) > 1:
        print("   表里还有 %d 级小 mip, 但文件里没有它们的像素数据"
              % (len(entries) - 1))

    if expect_image:
        payload = raw[implied_header:implied_header + base]
        rgba = ktex_import().dxt5_decode(payload, width, height)
        rgb = rgba[:, :, :3].astype(np.int32)
        noise = float(np.abs(np.diff(rgb, axis=1)).mean() + np.abs(np.diff(rgb, axis=0)).mean())
        opaque = float((rgba[:, :, 3] > 8).mean())
        verdict = "正常" if noise < 14 else "疑似噪声"
        print("   解码: 相邻像素差=%.1f 不透明=%.1f%%  -> %s" % (noise, opaque * 100, verdict))
        return rgba
    print()


def ktex_import():
    sys.path.insert(0, HERE)
    import ktex
    return ktex


with zipfile.ZipFile(os.path.join(HERE, "swap_backpack.zip")) as z:
    world = analyze("swap_backpack/atlas-0.tex", z.read("atlas-0.tex"))

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

if world is not None:
    art = os.path.join(HERE, "art")
    os.makedirs(art, exist_ok=True)
    ktex_import().write_png_rgba(os.path.join(art, "world_atlas_fixed.png"), world)
    print("世界图集 -> art/world_atlas_fixed.png")
