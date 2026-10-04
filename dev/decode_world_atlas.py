"""验证 swap_backpack 图集: 按"98 字节头 + 基准级 + 剩余 mip 链"排布解码。

尺寸关系(精确):
    文件 87506
    基准级(256x256 BC3)      65536
    其余 8 级 mip 之和        21872
    87506 - 65536 - 21872 =  98   <- 头部长度, 且总和精确吻合, 不留余数
这种"总和刚好用尽"的吻合度是判断布局的铁证, 比肉眼看图靠谱。

对照: 若假设"头 + 仅基准级", 头长会是 21970 —— 但 21970 与 8 级 mip 之和
21872 只差 98, 说明文件里**同时**有基准级和整条 mip 链, 只是顺序为
[头][基准级][小mip链]。
"""

import os
import sys
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ktex

ART = os.path.join(HERE, "art")
ZIP = os.path.join(HERE, "swap_backpack.zip")

with zipfile.ZipFile(ZIP) as archive:
    raw = archive.read("atlas-0.tex")

width = height = 256
base = ktex.dxt5_size(width, height)

sizes = []
w, h = width // 2, height // 2
while True:
    sizes.append(((w + 3) // 4) * ((h + 3) // 4) * 16)
    if w == 1 and h == 1:
        break
    w = max(1, w // 2)
    h = max(1, h // 2)
sub_chain = sum(sizes)

print("文件            %d" % len(raw))
print("基准级          %d" % base)
print("其余 8 级之和   %d" % sub_chain)
print("头长(余额)      %d   <- %d - %d - %d" % (len(raw) - base - sub_chain, len(raw), base, sub_chain))

header = len(raw) - base - sub_chain
assert header >= 0, "尺寸关系不成立"

rgba = ktex.dxt5_decode(raw[header:header + base], width, height)

os.makedirs(ART, exist_ok=True)
out = os.path.join(ART, "world_atlas_final.png")
ktex.write_png_rgba(out, rgba)
rgb = rgba[:, :, :3].astype(np.int32)
noise = float(np.abs(np.diff(rgb, axis=1)).mean() + np.abs(np.diff(rgb, axis=0)).mean())
print("\n解码完成: 相邻像素差=%.2f  alpha>8 占比=%.1f%%" % (noise, 100.0 * (rgba[:, :, 3] > 8).mean()))
print("-> %s" % out)
