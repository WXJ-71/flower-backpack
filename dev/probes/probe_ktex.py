"""验证 KTEX/DXT5/ARGB 工具链: 把原版图集反解成 PNG, 并做往返测试。

用法: python probe_ktex.py
输出: dev/art/vanilla_<name>_decode.png 与 roundtrip_<name>.png
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ktex

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "art")


def decode_any(info):
    if info.format_code == 0x42:
        return ktex.argb_decode(info.payload, info.width, info.height, info.row_bytes)
    return ktex.dxt5_decode(info.payload, info.width, info.height)


def encode_any(rgba, format_code):
    return ktex.argb_encode(rgba) if format_code == 0x42 else ktex.dxt5_encode(rgba)


def main():
    os.makedirs(OUT, exist_ok=True)

    for name in ("swap_backpack", "ui_backpack_2x4"):
        src = os.path.join(HERE, name + "_unzip", "atlas-0.tex")
        if not os.path.exists(src):
            print("%-16s skip" % name)
            continue

        with open(src, "rb") as handle:
            data = handle.read()
        info = ktex.parse_ktex(data)
        print("%-16s %s" % (name, info.describe()))

        started = time.time()
        rgba = decode_any(info)
        print("%-16s decoded in %.2fs" % ("", time.time() - started))

        opaque = int((rgba[:, :, 3] > 8).sum())
        png = os.path.join(OUT, "vanilla_%s_decode.png" % name)
        ktex.write_png_rgba(png, rgba)
        print("%-16s -> %s (opaque %d / %d, %.1f%%)"
              % ("", os.path.basename(png), opaque, info.width * info.height,
                 100.0 * opaque / (info.width * info.height)))

        started = time.time()
        reencoded = encode_any(rgba, info.format_code)
        rgba2 = decode_any(ktex.KtexInfo(info.width, info.height, info.row_bytes, 0,
                                         len(reencoded), info.format_code, b"", reencoded))
        diff = np.abs(rgba.astype(np.int32) - rgba2.astype(np.int32))
        print("%-16s roundtrip in %.2fs: %d bytes, mean_err=%.3f max_err=%d"
              % ("", time.time() - started, len(reencoded), diff.mean(), diff.max()))
        ktex.write_png_rgba(os.path.join(OUT, "roundtrip_%s.png" % name), rgba2)

        rebuilt = ktex.build_ktex(reencoded, info.width, info.height, info.format_code)
        print("%-16s rebuild: %d bytes (orig %d), header18=%s"
              % ("", len(rebuilt), len(data), rebuilt[:18].hex(" ")))


main()
