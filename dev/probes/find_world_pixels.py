"""直接找 swap_backpack 图集的像素数据到底从第几个字节开始。

已知(由尺寸关系确定):
    256x256 BC3 基准级 = 65536 字节
    文件 = 87506 字节
所以像素数据一定在 offset [0, 21970] 之间的某个位置, 且后面还有约 21970 字节
的其它内容(头部表 + 小 mip 链)。

做法: 取基准级的数据块, 用 DXT5 的已知特征判断"像不像真实贴图":
  · DXT5 每块里两个 RGB565 端点通常不是随机值; 噪声数据的端点分布均匀
  · 真实贴图相邻像素差小; 噪声大
所以滑动若干个候选起点, 各解一次, 取"相邻像素差最小"的那个。
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


def score(rgba):
    rgb = rgba[:, :, :3].astype(np.int32)
    return float(np.abs(np.diff(rgb, axis=1)).mean() + np.abs(np.diff(rgb, axis=0)).mean())


with zipfile.ZipFile(ZIP) as archive:
    raw = archive.read("atlas-0.tex")

size = len(raw)
width, height = 256, 256
base = ktex.dxt5_size(width, height)
print("file=%d base=%d 像素数据起点应在 [0, %d]" % (size, base, size - base))

# 先看看 offset 21900 附近的字节, 找头部表结束的位置
print("\noffset 21940..21990 的字节:")
for start in range(21940, 21990, 16):
    print("  %5d: %s" % (start, " ".join("%02X" % b for b in raw[start:start + 16])))

print("\n候选起点扫描(相邻像素差越小越像真图):")
results = []
step = 1 if len(sys.argv) < 2 else int(sys.argv[1])
for offset in range(0, 160, step):
    payload = raw[offset:offset + base]
    if len(payload) != base:
        continue
    rgba = ktex.dxt5_decode(payload, width, height)
    results.append((score(rgba), offset))

results.sort()
for value, offset in results[:10]:
    print("  offset=%-5d 相邻差=%.2f" % (offset, value))

best_score, best_offset = results[0]
print("\n最佳: offset=%d (相邻差 %.2f)" % (best_offset, best_score))

# 也试"数据在文件末尾"的排布
tail = raw[size - base:]
tail_score = score(ktex.dxt5_decode(tail, width, height))
print("对照: 文件末尾(offset=%d) 相邻差=%.2f" % (size - base, tail_score))

if best_score < tail_score:
    chosen = best_offset
else:
    chosen = size - base
print("采用 offset=%d" % chosen)

os.makedirs(ART, exist_ok=True)
rgba = ktex.dxt5_decode(raw[chosen:chosen + base], width, height)
ktex.write_png_rgba(os.path.join(ART, "world_atlas_best.png"), rgba)
rgb = rgba[:, :, :3].astype(np.int32)
print("导出 -> art/world_atlas_best.png")
print("alpha>8 占比 %.1f%%" % (100.0 * (rgba[:, :, 3] > 8).mean()))
