"""一次性补丁脚本: 修正 ktex.py 的 KTEX 解析(头部长度不写死 + 首级 mip 取法)。

用法: python patch_ktex.py
"""

import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "ktex.py")

with io.open(PATH, "r", encoding="utf-8") as handle:
    src = handle.read()

# 1) 替换模块 docstring 里关于 KTEX 格式的说明段
new_doc = '''KTEX 容器格式 —— 头部逐字节 dump 后确定的**可用**部分:
    偏移  长度  含义
    0     4     magic "KTEX" (4B 54 45 58)
    4     1     固定 0x20 (与 swizzle 相关; 所有产物都是 0x20)
    5     1     像素格式代码: 0x22 = BC3/DXT5, 0x42 = ARGB
    6     1     标志位: 0xFC = swizzle|premultiply, 0xF0 = premultiply(旧工具)
    7     1     固定 0xFF
    8     2     宽度  (uint16 小端)
    10    2     高度  (uint16 小端)
    12    2     每行字节 (uint16 小端) = 宽/4*16
    18    N     压缩像素数据(首级 mip 在前, 后续 mip 或附加数据在后)

头部长度**不写死**, 由 文件总长 - 首级 mip 字节数 推出, 因为实测有差异:
    modicon       128x128: 16402  - 16384  = 18
    swap_backpack 256x256: 87506  - 65536  = 20
    ui_backpack   512x512: 349660 - 262144 = 87516  <- 首级 mip 后面还有约 21KB 附加数据
所以首级 mip 一律从数据流**末尾**按尺寸取, 对"首级在前"的排布都成立
(本工具只需要首级: 图标是小尺寸纯色块, 不需要 mipmap)。

已验证的尺寸关系(全部精确吻合):
    swap_backpack 256x256: 65536  = 64*64*16
    ui_backpack   512x512: 262144 = 128*128*16
    modicon       128x128: 16384  = 32*32*16
"""

import struct

import numpy as np

KTEX_MAGIC = b"KTEX"


def dxt5_size(width, height):
    """BC3/DXT5 首级 mip 的字节数。"""
    return ((width + 3) // 4) * ((height + 3) // 4) * 16
'''

# 把从 "KTEX 容器格式" 到 "KTEX_MAGIC = b\"KTEX\"\nHEADER_SIZE = 20\n" 的整段换掉
pattern = re.compile(r"KTEX 容器格式.*?KTEX_MAGIC = b\"KTEX\"\nHEADER_SIZE = 20\n", re.S)
src, count = pattern.subn(new_doc, src, count=1)
assert count == 1, "docstring 段未匹配"

# 2) 替换 KtexInfo 与 parse_ktex
new_parse = '''class KtexInfo:
    def __init__(self, width, height, row_bytes, header_size, first_mip_bytes, format_code, flags, payload):
        self.width = width
        self.height = height
        self.row_bytes = row_bytes
        self.header_size = header_size
        self.first_mip_bytes = first_mip_bytes
        self.format_code = format_code
        self.flags = flags
        self.payload = payload

    def describe(self):
        return ("%dx%d 行字节=%d 头长=%d 首级mip=%d 格式=0x%02X flags=%s"
                % (self.width, self.height, self.row_bytes, self.header_size,
                   self.first_mip_bytes, self.format_code, self.flags))


def parse_ktex(data):
    """解析 KTEX 头, 并切出首级 mip 数据。"""
    if data[0:4] != KTEX_MAGIC:
        raise ValueError("不是 KTEX 文件: %r" % data[0:4])

    format_code = data[5]
    if format_code != 0x22:
        raise ValueError("只支持 BC3/DXT5(0x22), 实际格式码 0x%02X" % format_code)

    flags = data[6:14]
    width = struct.unpack_from("<H", data, 8)[0]
    height = struct.unpack_from("<H", data, 10)[0]
    row_bytes = struct.unpack_from("<H", data, 12)[0]

    mip_bytes = dxt5_size(width, height)
    if len(data) < mip_bytes:
        raise ValueError("文件比首级 mip 还小: %d < %d" % (len(data), mip_bytes))

    header_size = len(data) - mip_bytes
    payload = data[len(data) - mip_bytes:]
    return KtexInfo(width, height, row_bytes, header_size, mip_bytes,
                    format_code, flags, payload)
'''

pattern2 = re.compile(r"class KtexInfo:.*?return KtexInfo\(.*?\)\n", re.S)
src, count2 = pattern2.subn(new_parse, src, count=1)
assert count2 == 1, "KtexInfo/parse_ktex 段未匹配"

# 3) 替换 build_ktex: 输出 18 字节头(与 TextureConverter 产物一致)
new_build = '''def build_ktex(pixel_data, width, height):
    """按 TextureConverter.exe 的产物格式封回 KTEX(单级 mip)。

    头部字段与我们的 modicon 产物一致(游戏已验证可读):
        KTEX 20 22 FC FF | 宽 高 行字节 | 00 00 | 首级字节数   = 18 字节
    """
    row_bytes = (width // 4) * 16
    first_mip_bytes = dxt5_size(width, height)
    header = (
        KTEX_MAGIC
        + bytes([0x20, 0x22, 0xFC, 0xFF])
        + struct.pack("<HHH", width, height, row_bytes)
        + struct.pack("<H", 0)
        + struct.pack("<I", first_mip_bytes)
    )
    assert len(header) == 18, len(header)
    return header + pixel_data
'''

pattern3 = re.compile(r"def build_ktex\(.*?\n    return header \+ pixel_data\n", re.S)
src, count3 = pattern3.subn(new_build, src, count=1)
assert count3 == 1, "build_ktex 段未匹配"

with io.open(PATH, "w", encoding="utf-8", newline="\n") as handle:
    handle.write(src)

print("patched:", PATH)
print("remaining HEADER_SIZE refs:", src.count("HEADER_SIZE"))
