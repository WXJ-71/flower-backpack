"""生成物品图标(64x64)与 mod 图标(128x128)。

为什么是"手绘 + 取自真实贴图的颜色":
    - 地面/背上的外观用的是**游戏真实贴图**(anim/swap_backpack.zip, 已合成鲜花),
      那部分是完全真实的;
    - 而物品栏里的图标是一张独立的 64x64 贴图。原版这张图在 inventoryimages1.tex 里,
      该图集是**平台 swizzle 格式**(格式码 0x82), 线性解码出来是错乱的网格
      (已验证), 所以无法直接摘取。
    - 因此这里手绘一张同风格的图, 颜色直接采自真实图集, 保证色调一致。

用法: python build_icons.py
"""

import math
import os
import sys
import zipfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ktex

HERE = os.path.dirname(os.path.abspath(__file__))
MOD_ROOT = os.path.dirname(HERE)

# 配色(取自真实图集的采样, 保证和游戏内背包一致)
OUTLINE = (46, 30, 20, 255)
BODY = (198, 176, 120, 255)
BODY_DARK = (170, 148, 96, 255)
BODY_LIGHT = (215, 196, 142, 255)
FLAP = (186, 164, 108, 255)
STRAP = (122, 84, 48, 255)
BUCKLE = (198, 198, 198, 255)
BUCKLE_DARK = (140, 140, 140, 255)

PETAL = (255, 246, 236, 255)
PETAL_CORE = (255, 238, 190, 255)


def draw_backpack(rgba, cx, cy, width, height):
    """画一只原版风格的背包: 圆角包体 + 翻盖 + 两条背带 + 两个小金属扣。"""
    h, w = rgba.shape[0], rgba.shape[1]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)

    left = cx - width / 2.0
    right = cx + width / 2.0
    top = cy - height / 2.0
    bottom = cy + height / 2.0

    def rounded(x0, y0, x1, y1, r):
        rx = np.clip(xx, x0 + r, x1 - r)
        ry = np.clip(yy, y0 + r, y1 - r)
        return ((xx - rx) ** 2 + (yy - ry) ** 2 <= r * r) & (xx >= x0) & (xx <= x1) & (yy >= y0) & (yy <= y1)

    radius = max(3.0, width * 0.18)

    # 背带: 细一点, 只露出包体上方一段
    strap_w = width * 0.10
    for offset in (-width * 0.26, width * 0.26):
        sx = cx + offset
        rgba[rounded(sx - strap_w / 2 - 1, top - height * 0.26,
                     sx + strap_w / 2 + 1, top + height * 0.10, 1.5)] = OUTLINE
        rgba[rounded(sx - strap_w / 2, top - height * 0.26,
                     sx + strap_w / 2, top + height * 0.10, 1.0)] = STRAP

    # 包体
    rgba[rounded(left, top, right, bottom, radius)] = OUTLINE
    rgba[rounded(left + 2, top + 2, right - 2, bottom - 2, radius - 1)] = BODY

    # 左上受光面
    rgba[rounded(left + 3, top + height * 0.34, left + width * 0.34,
                 bottom - 3, radius - 2)] = BODY_LIGHT

    # 翻盖: 上三分之一, 颜色略深
    flap_bottom = top + height * 0.38
    rgba[rounded(left, top, right, flap_bottom, radius)] = OUTLINE
    rgba[rounded(left + 2, top + 2, right - 2, flap_bottom - 2, radius - 1)] = FLAP
    # 翻盖下缘的厚度线
    rgba[rounded(left + 2, flap_bottom - 3, right - 2, flap_bottom - 1, 0.8)] = OUTLINE

    # 两个小金属扣(只有一点点大)
    buckle_w = width * 0.085
    buckle_h = height * 0.14
    buckle_y = top + height * 0.52
    for offset in (-width * 0.24, width * 0.24):
        bx = cx + offset
        rgba[rounded(bx - buckle_w, buckle_y - buckle_h, bx + buckle_w, buckle_y + buckle_h, 1.2)] = OUTLINE
        rgba[rounded(bx - buckle_w + 1, buckle_y - buckle_h + 1,
                     bx + buckle_w - 1, buckle_y + buckle_h - 1, 0.8)] = BUCKLE

    # 底部暗面
    rgba[rounded(left + 2, bottom - height * 0.14, right - 2, bottom - 2, radius - 1)] = BODY_DARK


def draw_flower(rgba, cx, cy, radius):
    h, w = rgba.shape[0], rgba.shape[1]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)

    centers = []
    for index in range(5):
        angle = math.pi * 2.0 * index / 5.0 - math.pi / 2.0
        centers.append((cx + math.cos(angle) * radius * 0.60,
                        cy + math.sin(angle) * radius * 0.60))
    petal_r = radius * 0.47

    outline = np.zeros((h, w), dtype=bool)
    for px, py in centers:
        outline |= ((xx - px) ** 2 + (yy - py) ** 2) <= (petal_r + 1.3) ** 2
    rgba[outline] = OUTLINE

    petals = np.zeros((h, w), dtype=bool)
    for px, py in centers:
        petals |= ((xx - px) ** 2 + (yy - py) ** 2) <= petal_r ** 2
    rgba[petals] = PETAL

    core_r = radius * 0.30
    rgba[((xx - cx) ** 2 + (yy - cy) ** 2) <= (core_r + 1.1) ** 2] = OUTLINE
    rgba[((xx - cx) ** 2 + (yy - cy) ** 2) <= core_r ** 2] = PETAL_CORE


def main():
    # ---- 物品图标 64x64 ----
    # 背包画小一点(对应贴图整体缩到 75%), 鲜花作为旁边的印记(只压住一点点边缘)
    item = np.zeros((64, 64, 4), dtype=np.uint8)
    draw_backpack(item, 29.0, 31.0, 44.0, 40.0)
    draw_flower(item, 47.0, 48.0, 12.0)
    item_path = os.path.join(HERE, "item_icon_src", "images", "flowerpack.png")
    os.makedirs(os.path.dirname(item_path), exist_ok=True)
    ktex.write_png_rgba(item_path, item)
    print("物品图标 -> %s" % item_path)

    # ---- mod 图标 128x128 ----
    mod_icon = np.zeros((128, 128, 4), dtype=np.uint8)
    yy, xx = np.mgrid[0:128, 0:128].astype(np.float64)
    r = 14.0
    cx = np.clip(xx, r, 127 - r)
    cy = np.clip(yy, r, 127 - r)
    mod_icon[((xx - cx) ** 2 + (yy - cy) ** 2) <= r * r] = (44, 40, 48, 255)

    draw_backpack(mod_icon, 58.0, 60.0, 78.0, 70.0)
    draw_flower(mod_icon, 94.0, 94.0, 25.0)
    mod_path = os.path.join(HERE, "modicon_src", "images", "modicon.png")
    os.makedirs(os.path.dirname(mod_path), exist_ok=True)
    ktex.write_png_rgba(mod_path, mod_icon)
    print("mod 图标 -> %s" % mod_path)


main()
