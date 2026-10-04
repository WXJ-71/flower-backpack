"""生成物品图标图集: images/flowerpack.tex + images/flowerpack.xml

图标像素**直接取自原版图集**里的 backpack.tex 区域(64x64), 所以物品在物品栏、
容器格子、建造菜单里的图标与原版背包**完全一致**(不是手画的"像")。

原版图集的解包结论(见 probe_atlas1_layout.py / find_backpack_cell.py):
    · images/inventoryimages1.tex = KTEX, 2048x2048, BC3
    · 布局 = 128 字节头 + **整条 mip 链**, 首级在最前面
      (旧代码假设"首级在末尾", 所以解出来是噪声 -> 曾误判为平台 swizzle)
    · 排布 = 32x32 个 64x64 格子, 行主序, XML 的 v 轴原点在**上**
    · backpack.tex 位于 col=3 row=25

输出的 xml 只有**一个**区域, 名字必须**恰好是 flowerpack.tex** —— 引擎是按
"<预制体名>.tex" 去图集里找区域的(scripts/widgets/itemtile.lua 传的就是这个名字),
名字对不上就会渲染成空白。

用法: python build_item_icon.py
"""

import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flower_art
import ktex

MOD_ROOT = os.path.dirname(HERE)
WORK = os.path.join(HERE, "images_unzip", "images")
ART = os.path.join(HERE, "art")

SRC_TEX = os.path.join(WORK, "inventoryimages1.tex")
SRC_XML = os.path.join(WORK, "inventoryimages1.xml")

OUT_DIR = os.path.join(MOD_ROOT, "images")
OUT_TEX = os.path.join(OUT_DIR, "flowerpack.tex")
OUT_XML = os.path.join(OUT_DIR, "flowerpack.xml")

CELL = 64
SOURCE_REGION = "backpack.tex"

# 试出来的 KTEX 常量: 头部 128 字节, 之后是整条 mip 链
ATLAS_HEADER = 128

# ---- 鲜花印记在世界贴图上的位置(图标据此等比换算, 保证观感统一) ----
# 世界贴图: 主体包围盒 x[9,116] y[150,250] (108x101), 花心(82,236) 半径 13
#   (由 dev/build_world_flower.py 自动定位得出)
WORLD_BODY_H = 101
WORLD_FLOWER_RADIUS = 13

# 花瓣至少要这么大比例压在背包本体上, 才算合格位置(允许一点点探出轮廓)
MIN_ON_PACK = 0.93


def alpha_bbox(rgba, threshold=8):
    """返回不透明像素的包围盒 (x0, y0, x1, y1)。"""
    mask = rgba[:, :, 3] > threshold
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    if not rows.any():
        raise SystemExit("图层全透明, 无法定位包围盒")
    y0, y1 = np.where(rows)[0][[0, -1]]
    x0, x1 = np.where(cols)[0][[0, -1]]
    return int(x0), int(y0), int(x1), int(y1)


def decode_source_atlas():
    raw = open(SRC_TEX, "rb").read()
    width = int.from_bytes(raw[8:10], "little")
    height = int.from_bytes(raw[10:12], "little")
    base = ktex.dxt5_size(width, height)
    print("原版图集: %dx%d, %d 字节, 头长 %d" % (width, height, len(raw), len(raw) - base))
    payload = raw[ATLAS_HEADER:ATLAS_HEADER + base]
    return ktex.dxt5_decode(payload, width, height)


def find_region(name):
    data = open(SRC_XML, encoding="utf-8").read()
    match = re.search(
        r'<Element name="%s" u1="([\d.]+)" u2="([\d.]+)" v1="([\d.]+)" v2="([\d.]+)"'
        % re.escape(name), data)
    if not match:
        raise SystemExit("原版图集里没有 %s" % name)
    return [float(v) for v in match.groups()]


def main():
    rgba = decode_source_atlas()
    height, width = rgba.shape[0], rgba.shape[1]

    u1, u2, v1, v2 = find_region(SOURCE_REGION)
    col = int(round(u1 * width)) // CELL
    row = int(round(v1 * height)) // CELL
    print("%s uv=(%.6f,%.6f,%.6f,%.6f) -> col=%d row=%d"
          % (SOURCE_REGION, u1, u2, v1, v2, col, row))

    icon = rgba[row * CELL:(row + 1) * CELL, col * CELL:(col + 1) * CELL].copy()
    if icon.shape[0] != CELL or icon.shape[1] != CELL:
        raise SystemExit("抠出来的不是 %dx%d: %s" % (CELL, CELL, icon.shape))
    opaque = int((icon[:, :, 3] > 8).sum())
    print("图标 %dx%d, 不透明像素 %d (%.1f%%)"
          % (CELL, CELL, opaque, 100.0 * opaque / (CELL * CELL)))
    if opaque < 200:
        raise SystemExit("图标几乎是空的, 说明格子定位错了")

    # ---- 加鲜花印记 ----
    # 与世界贴图保持同一套规则: 花心贴在背包**右下角**, 半径按背包高度等比换算
    # (世界贴图: 主体高 101px, 花半径 13 -> 比例 0.129)。
    # 不能直接用包围盒右下角 —— 背包是圆角团块, 那里在轮廓外; 所以同样在
    # 右下角附近搜一个"够贴合"的位置, 再取其中最靠右下的。
    icon_box = alpha_bbox(icon, threshold=8)
    x0, y0, x1, y1 = icon_box
    box_w, box_h = x1 - x0 + 1, y1 - y0 + 1
    print("图标里背包的包围盒 x[%d,%d] y[%d,%d] (%dx%d)" % (x0, x1, y0, y1, box_w, box_h))

    flower_r = max(6.0, round(WORLD_FLOWER_RADIUS * box_h / float(WORLD_BODY_H), 1))
    print("鲜花半径 %.1f (世界贴图 %d x 图标主体高 %d / 世界主体高 %d)"
          % (flower_r, WORLD_FLOWER_RADIUS, box_h, WORLD_BODY_H))

    opaque = icon[:, :, 3] > 8
    probe = np.zeros_like(icon)
    best = None
    closest = None
    for cy in range(y0 + box_h // 2, y1 + 2):
        for cx in range(x0 + box_w // 2, x1 + 2):
            probe[:] = 0
            mask = flower_art.draw_flower(probe, cx, cy, flower_r)
            total = int(mask.sum())
            if total == 0:
                continue
            ratio = int((mask & opaque).sum()) / float(total)
            if closest is None or ratio > closest[0]:
                closest = (ratio, cx, cy, total)
            if ratio < MIN_ON_PACK:
                continue
            key = (cx + cy, round(ratio, 4))
            if best is None or key > best[0]:
                best = (key, cx, cy, ratio, total)

    if best is None:
        ratio, cx, cy, total = closest
        raise SystemExit("图标里没有位置达到 %.0f%% 贴合度; 最好的是 (%d,%d) 仅 %.1f%%"
                         % (MIN_ON_PACK * 100, cx, cy, ratio * 100))

    _, flower_cx, flower_cy, ratio, total = best
    print("鲜花印记: 中心(%d,%d) 半径 %.1f -> 覆盖 %d 像素, %.1f%% 压在背包上"
          % (flower_cx, flower_cy, flower_r, total, ratio * 100))

    before_icon = icon.copy()
    changed = flower_art.draw_flower(icon, flower_cx, flower_cy, flower_r)
    was_opaque = before_icon[:, :, 3] > 8
    outside = int((changed & ~was_opaque).sum())
    print("花朵覆盖 %d 像素, 其中落在透明区 %d 个 (%.1f%%)"
          % (int(changed.sum()), outside, 100.0 * outside / max(1, int(changed.sum()))))

    os.makedirs(OUT_DIR, exist_ok=True)

    # 1) 贴图: 重新按 BC3 编码封成标准 18 字节头的 KTEX
    encoded = ktex.dxt5_encode(icon)
    out = ktex.build_ktex(encoded, CELL, CELL, format_code=0x22)
    with open(OUT_TEX, "wb") as handle:
        handle.write(out)
    print("贴图 -> %s (%d 字节)" % (OUT_TEX, len(out)))

    # 2) 图集描述: 区域名必须是 flowerpack.tex
    #    边距沿用原版图标图集的做法(半像素内缩), 避免采样时吃到邻格
    half = 0.5 / CELL
    xml = (
        '<Atlas><Texture filename="flowerpack.tex" /><Elements>'
        '<Element name="flowerpack.tex" u1="%.10f" u2="%.10f" v1="%.10f" v2="%.10f" />'
        "</Elements></Atlas>"
    ) % (half, 1.0 - half, half, 1.0 - half)
    with open(OUT_XML, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(xml)
    print("图集 -> %s (%d 字节)" % (OUT_XML, len(xml.encode("utf-8"))))

    # 3) 自检: 把产物解回来比对, 并导出预览
    check = ktex.parse_ktex(out)
    back = ktex.dxt5_decode(check.payload, check.width, check.height)
    diff = np.abs(back.astype(np.int32) - icon.astype(np.int32))
    print("往返自检: 平均误差 %.2f, 最大 %d" % (diff.mean(), diff.max()))

    os.makedirs(ART, exist_ok=True)
    ktex.write_png_rgba(os.path.join(ART, "flowerpack_icon_64.png"), icon)
    ktex.write_png_rgba(os.path.join(ART, "flowerpack_icon_x6.png"),
                        np.repeat(np.repeat(icon, 6, axis=0), 6, axis=1))
    print("预览 -> art/flowerpack_icon_64.png / _x6.png")


main()
