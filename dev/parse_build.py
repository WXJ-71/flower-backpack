"""解析原版 build.bin, 列出里面的构建名 / 图集名 / 符号名。

用途: 搞清楚"地面上显示的背包"到底是哪个符号, 以及符号结构,
      这样才能判断为什么物品图标与实物不一致。

build.bin 结构(逆出来的, 够用即可):
    0   4   magic "BILD" (42 49 4C 44)
    4   4   version (uint32)
    8   4   hash (uint32)
    12  4   build name length (uint32)
    16  N   build name
    ... 4   atlas count (uint32) -> 每个: 4 长度 + 名称
    ...     symbol 数量与名称(后续为二进制几何数据)

用法: python parse_build.py
"""

import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def read_string(data, offset):
    length = struct.unpack_from("<I", data, offset)[0]
    if length > 512:
        return None, offset
    text = data[offset + 4:offset + 4 + length]
    try:
        return text.decode("utf-8"), offset + 4 + length
    except UnicodeDecodeError:
        return None, offset


def main():
    path = os.path.join(HERE, "swap_backpack_unzip", "build.bin")
    with open(path, "rb") as handle:
        data = handle.read()

    print("文件大小: %d 字节" % len(data))
    magic = data[0:4]
    print("magic: %r %s" % (magic, "OK" if magic == b"BILD" else "??"))

    version = struct.unpack_from("<I", data, 4)[0]
    hash_value = struct.unpack_from("<I", data, 8)[0]
    print("version=%d hash=0x%08X" % (version, hash_value))

    offset = 12
    name, offset = read_string(data, offset)
    print("构建名(build name): %r" % name)

    atlas_count = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    print("图集数量: %d" % atlas_count)
    for index in range(atlas_count):
        atlas, offset = read_string(data, offset)
        print("  图集[%d]: %r" % (index, atlas))

    # 后面是符号表: 通常是 4 字节数量 + 每项 4 字节长度 + 名称
    print("\n尝试扫描后续的字符串(符号名等):")
    found = []
    pos = offset
    while pos < len(data) - 4:
        text, new_pos = read_string(data, pos)
        if text and 0 < len(text) < 64 and all(32 <= ord(c) < 127 for c in text):
            found.append((pos, text))
            pos = new_pos
        else:
            pos += 1
    for pos, text in found[:40]:
        print("  @%-6d %r" % (pos, text))

    print("\n所有可读字符串汇总:")
    strings = []
    current = ""
    for byte in data:
        if 32 <= byte < 127:
            current += chr(byte)
        else:
            if len(current) >= 3:
                strings.append(current)
            current = ""
    if len(current) >= 3:
        strings.append(current)
    for text in strings:
        print("  %r" % text)


main()
