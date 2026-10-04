"""搞清 build.bin 的字段顺序, 以便精确改写构建名。

上一次假设是 [magic][version][hash][名字长度][名字], 结果在 offset 12 读到的是 0x0D,
正确的位置应该是 offset 8。说明少算了一个字段。

本脚本把头部字段一个个按 u32 和字符串读出来, 直接看出真实顺序。
"""

import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "swap_backpack_unzip", "build.bin")

with open(BUILD, "rb") as handle:
    data = handle.read()

print("文件 %d 字节" % len(data))
print("magic %r" % data[0:4])
print("\n按 u32 逐个读前 20 个字段:")
for index in range(20):
    offset = index * 4
    value = struct.unpack_from("<I", data, offset)[0]
    as_float = struct.unpack_from("<f", data, offset)[0]
    text = ""
    if 4 <= value <= 64 and offset + 4 + value <= len(data):
        candidate = data[offset + 4:offset + 4 + value]
        if all(32 <= b < 127 for b in candidate):
            text = "  <- 字符串: %r" % candidate.decode()
    print("  [%2d] @%-4d  u32=%-12d hex=0x%08X  f=%.4f%s"
          % (index, offset, value, value, as_float, text))

print("\n前 32 字节:")
print("  " + " ".join("%02X" % b for b in data[:32]))

# 直接在文件里搜 "swap_backpack" 的位置
position = data.find(b"swap_backpack")
print("\n'swap_backpack' 字符串出现位置: %d" % position)
if position >= 4:
    length = struct.unpack_from("<I", data, position - 4)[0]
    print("  它前面的 u32 = %d (长度)  -> %s" % (length, "自洽" if length == 13 else "不对"))

# 最后的 'swap_body' 符号名也一并确认(改名时不能动它)
symbol = data.find(b"swap_body")
print("'swap_body' 符号名位置: %d, 前面 u32 = %d"
      % (symbol, struct.unpack_from("<I", data, symbol - 4)[0]))
print("\n结论: 构建名位于 offset %d, 共 %d 字节; 前面 4 字节是长度字段。"
      % (position, 13))
