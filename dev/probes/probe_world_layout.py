"""对 swap_backpack 的 atlas-0.tex 试所有合理的字节排布, 找出哪一种是正确的。

背景: ktex.parse_ktex 用的是"头长 = 文件长 - 首级mip, 首级在末尾"这条规则,
对动画图集(modicon / swap_backpack)以前是work的。但这次把 swap_backpack
解出来是噪声, 所以必须用尺寸关系把排布重新验一遍, 而不是继续套公式。

已知: 256x256 BC3 首级 = 65536 字节; 文件 87506 字节。
    若是"头 + 首级":      头长 = 87506 - 65536 = 21970
    若是"头 + 整条mip链": 链长(含首级) = 87376 -> 头长 = 130
两种都可能, 差别在于"首级是紧跟头部, 还是在文件末尾"。
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


def mip_chain(width, height):
    total = 0
    sizes = []
    w, h = width, height
    while True:
        size = ((w + 3) // 4) * ((h + 3) // 4) * 16
        sizes.append((w, h, size))
        total += size
        if w == 1 and h == 1:
            break
        w = max(1, w // 2)
        h = max(1, h // 2)
    return total, sizes


def quality(rgba):
    """噪声图的判据: 相邻像素差异大、且几乎每个像素都不透明。"""
    if rgba is None:
        return None
    alpha = rgba[:, :, 3]
    rgb = rgba[:, :, :3].astype(np.int32)
    dx = np.abs(np.diff(rgb, axis=1)).mean()
    dy = np.abs(np.diff(rgb, axis=0)).mean()
    opaque = float((alpha > 8).mean())
    return dx + dy, opaque


def main():
    with zipfile.ZipFile(ZIP) as archive:
        raw = archive.read("atlas-0.tex")

    size = len(raw)
    width = int.from_bytes(raw[8:10], "little")
    height = int.from_bytes(raw[10:12], "little")
    base = ((width + 3) // 4) * ((height + 3) // 4) * 16
    chain, sizes = mip_chain(width, height)

    print("file=%d  %dx%d  base=%d  chain=%d" % (size, width, height, base, chain))
    print("header if base at start : %d" % (size - chain))
    print("header if base at end   : %d" % (size - base))
    print("mip sizes:", [s[2] for s in sizes][:6], "...")

    os.makedirs(ART, exist_ok=True)

    candidates = [
        ("base_at_end", raw[size - base:]),
        ("base_after_130", raw[130:130 + base]),
        ("base_after_18", raw[18:18 + base]),
        ("base_after_21970", raw[21970:21970 + base]),
        ("base_at_start", raw[:base]),
    ]

    for name, payload in candidates:
        if len(payload) != base:
            print("%-18s SKIP (只有 %d 字节)" % (name, len(payload)))
            continue
        rgba = ktex.dxt5_decode(payload, width, height)
        score, opaque = quality(rgba)
        out = os.path.join(ART, "world_%s.png" % name)
        ktex.write_png_rgba(out, rgba)
        print("%-18s 相邻差=%.1f  不透明=%.1f%%  -> %s"
              % (name, score, opaque * 100, os.path.basename(out)))

    print("\n判据: 噪声图的相邻像素差会非常大(>20); 正常贴图通常在 10 以下。")


main()
