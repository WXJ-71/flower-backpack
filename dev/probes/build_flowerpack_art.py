"""生成背包的两套贴图资源。

做法:
    1. 解码原版 data/anim/swap_backpack.zip 里的 atlas-0.tex (BC3/DXT5);
    2. 地面用: 原版 atlas-0.tex **原样**打包 -> anim/swap_backpack.zip
       (用户要求地面恢复成原版外观, 不加花、不缩放);
    3. 背上用: 在图集的空白处画一朵纯白的鲜花 -> 缩放 50% -> 重新编码
       -> anim/flowerpack_worn.zip;
    4. 两套都沿用原版 build.bin, 保证符号结构/几何/UV 完全一致。

用法: python build_flowerpack_art.py
"""

import io
import os
import shutil
import sys
import zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ktex

HERE = os.path.dirname(os.path.abspath(__file__))
MOD_ROOT = os.path.dirname(HERE)
SRC_ZIP = os.path.join(HERE, "swap_backpack.zip")
SRC_DIR = os.path.join(HERE, "swap_backpack_unzip")
OUT_DIR = os.path.join(MOD_ROOT, "anim")

# 背包本体符号在图集上的区域(由 analyze_atlas.py 的连通域分析得到)
# 最大的连通块 (168,61)-(255,163) 就是背包主体, 贴到图集右边缘
BODY_X1 = 255
BODY_Y1 = 163

# 鲜花印记: 用纯白画, 不带描边。
# 注意: 现在已经没有任何染色逻辑了 —— 引擎的 SetAddColour / SetMultColour 都没有
# 像素选择能力, 染色会作用到整个物品(含背包本体), 那套"满红未满绿"的方案已废弃
# (原因见 dev_notes.md)。所以这里留白只是为了观感干净, 不再有染色含义。
#
# 位置: 由 dev/find_flower_slot.py 自动搜索得到 —— 该处与背包本体重叠约 1%,
# 所以原版背包图形基本保持完整, 鲜花只是旁边的一个印记(不会盖住包体)。
# 这份带花的贴图**只用在背上**(anim/flowerpack_worn.zip);
# 地面用的是原版 atlas-0.tex 原样(见下面的 write_build 调用)。
FLOWER_CX = 178.0
FLOWER_CY = 152.0
FLOWER_R = 23.0

FLOWER_PETAL = (255, 255, 255, 255)
FLOWER_CORE = (255, 244, 206, 255)   # 花心略暖, 白花看着更像花
FLOWER_OUTLINE = None                # 不描边

# 贴图缩放: 用户要求"只有背上时变小", 所以出两套:
#   anim/swap_backpack.zip       地面用, 完整尺寸(256x256)
#   anim/flowerpack_worn.zip     背上用, 缩小尺寸(128x128), 符号结构与前者完全相同
# 游戏侧的预制体在装备/卸下时用 AnimState:SetBuild 在两套之间切换。
# 注意: 输出尺寸必须是 2 的幂(DST 贴图要求)。256 * 0.5 = 128 ✓
ATLAS_SCALE = 0.5


def draw_flower(rgba, cx, cy, radius):
    """在 rgba 上画一朵五瓣花(带描边和花心), 直接改像素。"""
    height, width = rgba.shape[0], rgba.shape[1]
    yy, xx = np.mgrid[0:height, 0:width]

    def stamp(mask, color):
        rgba[mask] = color

    # 五片花瓣: 围绕中心均匀分布
    import math
    petal_centers = []
    for index in range(5):
        angle = math.pi * 2.0 * index / 5.0 - math.pi / 2.0
        px = cx + math.cos(angle) * (radius * 0.58)
        py = cy + math.sin(angle) * (radius * 0.58)
        petal_centers.append((px, py))

    petal_r = radius * 0.46

    petal_mask = np.zeros((height, width), dtype=bool)
    for px, py in petal_centers:
        petal_mask |= ((xx - px) ** 2 + (yy - py) ** 2) <= petal_r ** 2
    stamp(petal_mask, FLOWER_PETAL)

    # 花心
    core_r = radius * 0.30
    stamp(((xx - cx) ** 2 + (yy - cy) ** 2) <= core_r ** 2, FLOWER_CORE)


def main():
    with open(os.path.join(SRC_DIR, "atlas-0.tex"), "rb") as handle:
        info = ktex.parse_ktex(handle.read())

    with open(os.path.join(SRC_DIR, "atlas-0.tex"), "rb") as handle:
        rgba = ktex.dxt5_decode(info.payload, info.width, info.height)
    print("原版图集: %dx%d 格式=0x%02X" % (info.width, info.height, info.format_code))

    # 先在原尺寸上画花(坐标是按原图集测出来的)
    # 注意: 当前需求是"地面和背上都要原版外观", 所以下面两套都不使用带花的版本;
    # 这段绘制保留着, 方便以后想加花时直接启用(改 write_build 的入参即可)。
    draw_flower(rgba, FLOWER_CX, FLOWER_CY, FLOWER_R)

    os.makedirs(OUT_DIR, exist_ok=True)
    build_bin_path = os.path.join(SRC_DIR, "build.bin")
    with open(build_bin_path, "rb") as handle:
        build_bin = handle.read()

    # 原版图集**原封不动**的字节(地面和背上都用它)
    with open(os.path.join(SRC_DIR, "atlas-0.tex"), "rb") as handle:
        vanilla_tex = handle.read()

    def write_build(zip_name, image, label):
        size = image.shape[1]
        tex = ktex.build_ktex(ktex.dxt5_encode(image), size, size)
        out_zip = os.path.join(OUT_DIR, zip_name)
        with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("atlas-0.tex", tex)
            # build.bin 原样沿用: 符号结构、几何、UV 都不变, 只换贴图分辨率
            archive.writestr("build.bin", build_bin)
        print("已写出 %-26s %s  %dx%d  %d 字节"
              % (zip_name, label, size, size, len(tex)))

    # ---- 地面用: 完全原版贴图(不加花、不缩放、不染色) ----
    out_zip = os.path.join(OUT_DIR, "swap_backpack.zip")
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("atlas-0.tex", vanilla_tex)
        archive.writestr("build.bin", build_bin)
    print("已写出 %-26s %s  %d 字节(与原版逐字节相同)"
          % ("swap_backpack.zip", "地面(原版原样)", len(vanilla_tex)))

    # ---- 背上用: 同样是原版贴图, 只缩小(保留"只有背上变小"的效果) ----
    if ATLAS_SCALE != 1.0:
        out_w = max(4, int(round(info.width * ATLAS_SCALE)) // 4 * 4)
        # 用原版解码结果缩放, 而不是用带花的 rgba
        vanilla_rgba = ktex.dxt5_decode(info.payload, info.width, info.height)
        scaled = ktex.resize_bilinear(vanilla_rgba, out_w, out_w)
        write_build("flowerpack_worn.zip", scaled, "背上(原版+缩小)")
    else:
        print("ATLAS_SCALE = 1.0, 不生成缩小版")

    # 预览图: 一份原版、一份带花(仅参考)
    preview_dir = os.path.join(HERE, "art")
    os.makedirs(preview_dir, exist_ok=True)
    ktex.write_png_rgba(os.path.join(preview_dir, "atlas_with_flower_UNUSED.png"), rgba)
    ktex.write_png_rgba(os.path.join(preview_dir, "atlas_vanilla.png"),
                        ktex.dxt5_decode(info.payload, info.width, info.height))
    print("预览图已更新(art/ 下)")


main()
