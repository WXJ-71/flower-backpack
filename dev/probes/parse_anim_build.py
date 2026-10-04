"""解析 anim.bin 与 build.bin 的二进制结构。

目标:
  1. 看懂 anim.bin(动画/符号表)的格式 —— 如果够简单, 就可以手写一个
     "只有一朵花"的 build, 用于背上的叠加显示(原版皮肤特效就是这么做的);
  2. 从 build.bin 里找出几何体用到的 UV 范围, 从而确定 atlas-0.tex 上
     哪一块对应模型上"朝外"的那个面。
"""

import os
import struct
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))


def hexdump(data, start=0, length=128):
    for offset in range(start, min(start + length, len(data)), 16):
        chunk = data[offset:offset + 16]
        text = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print("  %04X  %-47s  %s" % (offset, " ".join("%02X" % b for b in chunk), text))


def main():
    anim_path = os.path.join(HERE, "backpack_unzip", "anim.bin")
    build_path = os.path.join(HERE, "swap_backpack_unzip", "build.bin")

    print("=== anim.bin (%d 字节) ===" % os.path.getsize(anim_path))
    with open(anim_path, "rb") as handle:
        anim = handle.read()
    hexdump(anim, 0, 176)

    print("\n=== build.bin 开头 (%d 字节) ===" % os.path.getsize(build_path))
    with open(build_path, "rb") as handle:
        build = handle.read()
    hexdump(build, 0, 160)

    print("\n=== build.bin 里的浮点数(找 UV) ===")
    # 扫描连续的 float, 打印落在 [0,1.2] 区间的(可能是 UV)
    found = []
    for offset in range(0, len(build) - 4):
        value = struct.unpack_from("<f", build, offset)[0]
        if 0.0 <= value <= 1.2 and value == value:
            found.append((offset, value))
    # 只打印成串出现的
    runs = []
    current = [found[0]] if found else []
    for previous, item in zip(found, found[1:]):
        if item[0] - previous[0] == 4:
            current.append(item)
        else:
            if len(current) >= 4:
                runs.append(current)
            current = [item]
    if len(current) >= 4:
        runs.append(current)

    print("成串出现的 [0,1.2] 浮点(可能是 UV 坐标):")
    for run in runs[:12]:
        values = ["%.4f" % v for _, v in run]
        print("  @%-6d 共 %2d 个: %s" % (run[0][0], len(run), ", ".join(values[:12])))


main()
