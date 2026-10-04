"""研究 anim/swap_backpack.zip 里的 atlas-0.tex, 为"加花"定位做准备。

要搞清楚的事实:
  1. 256x256 的图集里到底画了什么(背包的哪几个面/哪几个视图);
  2. 贴图内容实际占用的包围盒, 这样加花时才能按同一比例放在"背包右下角";
  3. 同时也解码原版背包的 64x64 物品图标(现已在 images/flowerpack.tex 里),
     量出它在 64x64 画布里的包围盒 —— 两处比例一致, 花的位置才能统一。
"""

import os
import sys
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ktex

ART = os.path.join(HERE, "art")
MOD_ROOT = os.path.dirname(HERE)
ZIP = os.path.join(HERE, "swap_backpack.zip")


def bbox(mask):
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    if not rows.any():
        return None
    y0, y1 = np.where(rows)[0][[0, -1]]
    x0, x1 = np.where(cols)[0][[0, -1]]
    return int(x0), int(y0), int(x1), int(y1)


def report(name, rgba, alpha_threshold=40):
    mask = rgba[:, :, 3] > alpha_threshold
    box = bbox(mask)
    print("%s: %dx%d, 不透明 %d 像素 (%.1f%%)"
          % (name, rgba.shape[1], rgba.shape[0], int(mask.sum()),
             100.0 * mask.sum() / (rgba.shape[0] * rgba.shape[1])))
    if box:
        x0, y0, x1, y1 = box
        print("   包围盒 x[%d,%d] y[%d,%d]  宽 %d 高 %d"
              % (x0, x1, y0, y1, x1 - x0 + 1, y1 - y0 + 1))
        # 每 32 像素一行/列的占用情况, 用来判断是不是多个视图平铺
        print("   按 64px 分块的占用:")
        for by in range(0, rgba.shape[0], 64):
            row = []
            for bx in range(0, rgba.shape[1], 64):
                cell = mask[by:by + 64, bx:bx + 64]
                row.append("%5d" % int(cell.sum()))
            print("      y=%-4d %s" % (by, " ".join(row)))
    return mask, box


print("=== 世界贴图 atlas-0.tex ===")
with zipfile.ZipFile(ZIP) as archive:
    print("zip 内容:", archive.namelist())
    data = archive.read("atlas-0.tex")
info = ktex.parse_ktex(data)
print("  " + info.describe())
world = ktex.dxt5_decode(info.payload, info.width, info.height)
report("swap_backpack atlas", world)

os.makedirs(ART, exist_ok=True)
ktex.write_png_rgba(os.path.join(ART, "world_atlas_decoded.png"), world)
big = np.repeat(np.repeat(world, 2, axis=0), 2, axis=1)
ktex.write_png_rgba(os.path.join(ART, "world_atlas_decoded_x2.png"), big)
print("  -> art/world_atlas_decoded.png / _x2.png")

print("\n=== 物品图标 images/flowerpack.tex ===")
icon_info = ktex.parse_ktex(open(os.path.join(MOD_ROOT, "images", "flowerpack.tex"), "rb").read())
icon = ktex.dxt5_decode(icon_info.payload, icon_info.width, icon_info.height)
report("flowerpack icon", icon)
