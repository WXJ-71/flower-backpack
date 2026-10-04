"""生成鲜花背包的图标 PNG -- 只用 Python 标准库(zlib + struct), 不依赖 PIL / Blender。

产出两个文件:
    dev/modicon_src/images/modicon.png          128x128  mod 图标(带圆角底板的徽章)
    dev/item_icon_src/images/flowerpack.png      64x64   物品图标(背包格 / 配方里显示)

用法:
    python make_icons.py            # 两个都生成
    python make_icons.py modicon    # 只生成 mod 图标
    python make_icons.py item       # 只生成物品图标

之后用官方贴图编译链转成 .tex / .xml:
    powershell -File dev/compile_modicon.ps1      # -> modicon.tex / modicon.xml
    powershell -File dev/compile_item_icon.ps1    # -> images/inventoryimages/flowerpack.tex/.xml

画法说明: 所有形状都按 128 为基准写坐标, 再按 size/128 缩放, 所以两个尺寸
出来的是同一张图的不同分辨率, 风格一致。
"""

import os
import struct
import sys
import zlib

# 配色: 原版背包的暖棕 + 鲜花主题的粉/绿
OUTLINE = (58, 33, 24)          # 深棕描边
PACK_MID = (166, 118, 66)       # 包体主色
PACK_LIGHT = (206, 152, 88)     # 包体受光面
FLAP = (146, 98, 54)            # 顶部翻盖
PACK_DARK = (118, 76, 42)       # 翻盖扣带
STRAP = (96, 60, 34)            # 背带
BUCKLE = (222, 190, 108)        # 金属扣
PETAL = (238, 150, 176)         # 花瓣
PETAL_DARK = (198, 104, 140)    # 花瓣根部
FLOWER_CORE = (247, 218, 116)   # 花心
LEAF = (120, 168, 78)           # 叶子
BASE_BG = (44, 40, 48)          # mod 图标底板


def rounded_rect(x, y, x0, y0, x1, y1, radius):
    """点 (x, y) 是否落在圆角矩形内。"""
    if x < x0 or x > x1 or y < y0 or y > y1:
        return False
    cx = min(max(x, x0 + radius), x1 - radius)
    cy = min(max(y, y0 + radius), y1 - radius)
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius * radius


def circle(x, y, cx, cy, radius):
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius * radius


def blend(base, color, alpha):
    return tuple(int(round(base[i] * (1.0 - alpha) + color[i] * alpha)) for i in range(3))


def draw_base(width, height):
    """按缩放后的坐标画一张背包图, 返回二维 RGB 列表(先画在临时画布上再裁剪)。"""
    return [[None for _ in range(width)] for _ in range(height)]


def paint(canvas, width, height, scale, shape_test, color):
    """把 shape_test(逻辑坐标) 为真的像素涂成 color。"""
    for py in range(height):
        for px in range(width):
            # 像素中心映射回 128 基准的逻辑坐标
            lx = (px + 0.5) / scale
            ly = (py + 0.5) / scale
            if shape_test(lx, ly):
                canvas[py][px] = color


def paint_layer(canvas, width, height, scale, shape_test, color, alpha):
    for py in range(height):
        for px in range(width):
            lx = (px + 0.5) / scale
            ly = (py + 0.5) / scale
            if shape_test(lx, ly):
                current = canvas[py][px]
                canvas[py][px] = blend(current, color, alpha)


def build_icon(size, with_base):
    """画一张 size x size 的鲜花背包图标。逻辑坐标以 128 为基准。"""
    scale = size / 128.0
    canvas = draw_base(size, size)

    # 打底: mod 图标用深色底板, 物品图标要透明 -> 先用白色占位再转 alpha
    if with_base:
        paint(canvas, size, size, scale, lambda x, y: True, BASE_BG)
    else:
        paint(canvas, size, size, scale, lambda x, y: True, (255, 0, 255))  # 洋红 = 待会抠掉

    # --- 背包主体 ---
    paint(canvas, size, size, scale,
          lambda x, y: rounded_rect(x, y, 22, 38, 106, 112, 18), OUTLINE)
    paint(canvas, size, size, scale,
          lambda x, y: rounded_rect(x, y, 25, 41, 103, 109, 16), PACK_MID)
    # 左侧受光面
    paint_layer(canvas, size, size, scale,
                lambda x, y: rounded_rect(x, y, 28, 44, 62, 106, 12), PACK_LIGHT, 0.55)

    # --- 顶部翻盖 ---
    paint(canvas, size, size, scale,
          lambda x, y: rounded_rect(x, y, 22, 38, 106, 74, 18), OUTLINE)
    paint(canvas, size, size, scale,
          lambda x, y: rounded_rect(x, y, 25, 41, 103, 71, 15), FLAP)

    # --- 两条背带 ---
    for strap_x in (40, 76):
        paint(canvas, size, size, scale,
              lambda x, y, sx=strap_x: rounded_rect(x, y, sx, 30, sx + 12, 60, 5), OUTLINE)
        paint(canvas, size, size, scale,
              lambda x, y, sx=strap_x: rounded_rect(x, y, sx + 2, 30, sx + 10, 60, 4), STRAP)

    # --- 翻盖扣带 + 金属扣 ---
    paint(canvas, size, size, scale,
          lambda x, y: rounded_rect(x, y, 58, 62, 70, 92, 4), OUTLINE)
    paint(canvas, size, size, scale,
          lambda x, y: rounded_rect(x, y, 60, 64, 68, 90, 3), PACK_DARK)
    paint(canvas, size, size, scale,
          lambda x, y: circle(x, y, 64, 80, 3.5), BUCKLE)

    # --- 鲜花(核心特征): 五瓣花 + 花心 ---
    flower_cx, flower_cy = 84.0, 92.0
    petal_r = 9.0
    petal_d = 11.0
    for index in range(5):
        import math
        angle = math.pi * 2.0 * index / 5.0 - math.pi / 2.0
        px = flower_cx + math.cos(angle) * petal_d
        py = flower_cy + math.sin(angle) * petal_d
        paint(canvas, size, size, scale,
              lambda x, y, cx=px, cy=py: circle(x, y, cx, cy, petal_r), OUTLINE)
        paint(canvas, size, size, scale,
              lambda x, y, cx=px, cy=py: circle(x, y, cx, cy, petal_r - 1.6), PETAL)
    paint(canvas, size, size, scale,
          lambda x, y: circle(x, y, flower_cx, flower_cy, 6.0), OUTLINE)
    paint(canvas, size, size, scale,
          lambda x, y: circle(x, y, flower_cx, flower_cy, 4.6), PETAL_DARK)
    paint(canvas, size, size, scale,
          lambda x, y: circle(x, y, flower_cx, flower_cy, 2.6), FLOWER_CORE)

    # 说明: 曾经在左下角画过一片叶子, 但在 64x64 的物品图标上会糊成一个小团,
    # 反而干扰识别, 所以去掉 —— 花本身已经足够表达"鲜花背包"。

    return canvas


def write_png(path, canvas, transparent_key=None):
    """把 RGB 画布写成 PNG; transparent_key 指定要变成透明的占位色。"""
    height = len(canvas)
    width = len(canvas[0])
    use_alpha = transparent_key is not None
    color_type = 6 if use_alpha else 2

    raw = bytearray()
    for row in canvas:
        raw.append(0)  # 每行的 filter type
        for pixel in row:
            if use_alpha:
                if pixel == transparent_key:
                    raw.extend((0, 0, 0, 0))
                else:
                    raw.extend((pixel[0], pixel[1], pixel[2], 255))
            else:
                raw.extend(pixel)

    def chunk(tag, data):
        payload = tag + data
        return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + chunk(b"IEND", b""))

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(png)
    return path


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    targets = sys.argv[1:] or ["modicon", "item"]
    made = []

    if "modicon" in targets:
        canvas = build_icon(128, with_base=True)
        made.append(write_png(os.path.join(here, "modicon_src", "images", "modicon.png"), canvas))

    if "item" in targets:
        canvas = build_icon(64, with_base=False)
        made.append(write_png(
            os.path.join(here, "item_icon_src", "images", "flowerpack.png"),
            canvas,
            transparent_key=(255, 0, 255),
        ))

    for path in made:
        print("saved:", path, os.path.getsize(path), "bytes")


main()
