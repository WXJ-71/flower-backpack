"""纯粹的分析脚本: 穷举 KTEX 头部字段, 找出"哪个偏移等于数据长度", 从而确定头长。

不再靠肉眼数字节, 直接让数据说话。
"""

import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))

FILES = {
    "swap_backpack 256x256": os.path.join(HERE, "swap_backpack_unzip", "atlas-0.tex"),
    "ui_backpack 512x512": os.path.join(HERE, "ui_backpack_2x4_unzip", "atlas-0.tex"),
    "modicon 128x128": r"E:\ds h\hunger_mod\modicon.tex",
    "vanilla_modicon 128x128": r"E:\app\steam\steamapps\common\Don't Starve Together\mods\workshop-1172839635\modicon.tex",
}


def main():
    for label, path in FILES.items():
        if not os.path.exists(path):
            print("%-26s missing" % label)
            continue
        with open(path, "rb") as handle:
            data = handle.read()

        print("=" * 78)
        print("%s  总长 %d" % (label, len(data)))
        print("  hex: " + " ".join("%02X" % b for b in data[:40]))

        # 对每个可能的头长 H, 看 (总长 - H) 是否等于头里某个 32 位字段
        for header_len in range(4, 32):
            data_len = len(data) - header_len
            hits = []
            for off in range(4, header_len - 3):
                value32 = struct.unpack_from("<I", data, off)[0]
                if value32 == data_len:
                    hits.append("u32@%d" % off)
                value16 = struct.unpack_from("<H", data, off)[0]
                if value16 == data_len:
                    hits.append("u16@%d" % off)
            if hits:
                print("  头长=%-3d 数据长=%-8d 命中: %s" % (header_len, data_len, ", ".join(hits)))

        # 打印各候选偏移的整数值, 便于人工判断哪个像尺寸
        print("  按 u16 逐字段:")
        fields = []
        for off in range(4, 30, 2):
            fields.append("[%d]=%d" % (off, struct.unpack_from("<H", data, off)[0]))
        print("    " + "  ".join(fields))


main()
