"""DST 贴图(.tex / KTEX)编解码工具 -- 只用 Python 标准库 + numpy。

为什么需要这个: 官方 Mod Tools 只能单向 PNG -> .tex (TextureConverter.exe),
没有任何工具能把原版贴图反解回 PNG。要做"在原版背包图上加一朵花", 就必须
自己解析 KTEX 容器格式 —— 头部逐字节 dump 后确定的**可用**部分:
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


def resize_bilinear(rgba, out_w, out_h):
    """双线性缩放 RGBA 数组。

    用途: 把整个图集等比缩小 —— 所有符号的相对位置不变(缩放是全局的, UV 不动),
    所以不会造成错位; 表现上就是"背包在游戏里变小了"。
    """
    src_h, src_w = rgba.shape[0], rgba.shape[1]
    src = rgba.astype(np.float64)

    # 目标像素中心映射回源坐标
    ys = (np.arange(out_h) + 0.5) * (src_h / float(out_h)) - 0.5
    xs = (np.arange(out_w) + 0.5) * (src_w / float(out_w)) - 0.5
    ys = np.clip(ys, 0, src_h - 1)
    xs = np.clip(xs, 0, src_w - 1)

    y0 = np.floor(ys).astype(np.int32)
    x0 = np.floor(xs).astype(np.int32)
    y1 = np.clip(y0 + 1, 0, src_h - 1)
    x1 = np.clip(x0 + 1, 0, src_w - 1)

    wy = (ys - y0)[:, None, None]
    wx = (xs - x0)[None, :, None]

    top = src[y0][:, x0] * (1 - wx) + src[y0][:, x1] * wx
    bottom = src[y1][:, x0] * (1 - wx) + src[y1][:, x1] * wx
    out = top * (1 - wy) + bottom * wy

    # 处理边缘: 把全透明像素的 RGB 清成 0, 避免缩放时把邻居颜色拖进来
    result = np.clip(np.round(out), 0, 255).astype(np.uint8)
    result[result[:, :, 3] == 0] = 0
    return result


def argb_size(width, height):
    """未压缩 BGRA8888 首级 mip 的字节数。"""
    return width * height * 4


def first_mip_size(format_code, width, height):
    return argb_size(width, height) if is_argb(format_code) else dxt5_size(width, height)


def is_argb(format_code):
    """格式码是否表示未压缩 ARGB(0x42)。其余按 BC3/DXT5 处理。"""
    return format_code == 0x42


# ---------------------------------------------------------------------------
# KTEX 容器
# ---------------------------------------------------------------------------

class KtexInfo:
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
    """解析 KTEX 头, 并切出首级 mip 数据。

    支持两种像素格式:
        0x22 = BC3/DXT5 (压缩)
        0x42 = ARGB     (未压缩, 每像素 4 字节)
    """
    if data[0:4] != KTEX_MAGIC:
        raise ValueError("不是 KTEX 文件: %r" % data[0:4])

    format_code = data[5]
    # 低半字节是像素格式, 高位是平台/swizzle 标志: 0x22 / 0x82 都是 BC3, 0x42 是 ARGB
    if not is_argb(format_code) and (format_code & 0x0F) != 0x02:
        raise ValueError("只支持 BC3(低半字节2)/ARGB(0x42), 实际格式码 0x%02X" % format_code)

    flags = data[6:14]
    width = struct.unpack_from("<H", data, 8)[0]
    height = struct.unpack_from("<H", data, 10)[0]
    row_bytes = struct.unpack_from("<H", data, 12)[0]

    mip_bytes = first_mip_size(format_code, width, height)
    if len(data) < mip_bytes:
        raise ValueError("文件比首级 mip 还小: %d < %d" % (len(data), mip_bytes))

    header_size = len(data) - mip_bytes
    payload = data[len(data) - mip_bytes:]
    return KtexInfo(width, height, row_bytes, header_size, mip_bytes,
                    format_code, flags, payload)


def build_ktex(pixel_data, width, height, format_code=0x22):
    """按 TextureConverter.exe 的产物格式封回 KTEX(单级 mip)。

    头部字段与我们的 modicon 产物一致(游戏已验证可读):
        KTEX 20 <格式> FC FF | 宽 高 行字节 | 首级字节数   = 18 字节
    对照官方 modicon.tex 的真实头部(BC3):
        4B 54 45 58 20 22 F0 FF | 80 00 80 00 | 00 00 | 00 40 00 00
        magic                    | 宽   高    | 0     | 16384
    """
    if format_code == 0x42:
        row_bytes = width * 4
        first_mip_bytes = argb_size(width, height)
    else:
        row_bytes = (width // 4) * 16
        first_mip_bytes = dxt5_size(width, height)

    header = (
        KTEX_MAGIC
        + bytes([0x20, format_code, 0xFC, 0xFF])
        + struct.pack("<HHH", width, height, row_bytes & 0xFFFF)
        + struct.pack("<I", first_mip_bytes)
    )
    assert len(header) == 18, len(header)
    return header + pixel_data


# ---------------------------------------------------------------------------
# ARGB (未压缩, BGRA8888) —— 容器 UI 图集是这种格式
# ---------------------------------------------------------------------------

def argb_decode(payload, width, height, row_bytes=None):
    """未压缩 BGRA8888 -> (h, w, 4) RGBA。row_bytes 是"每行字节"(可能有 padding)。"""
    stride = row_bytes if row_bytes else width * 4
    expected = stride * height
    if len(payload) < expected:
        raise ValueError("ARGB 数据不足: 需要 %d, 实际 %d" % (expected, len(payload)))
    raw = np.frombuffer(payload[:expected], dtype=np.uint8).reshape(height, stride)
    raw = raw[:, :width * 4].reshape(height, width, 4)
    # 存储顺序是 BGRA, 转成 RGBA
    return raw[:, :, [2, 1, 0, 3]].copy()


def argb_encode(rgba):
    """(h, w, 4) RGBA -> 未压缩 BGRA8888 字节串。"""
    return rgba[:, :, [2, 1, 0, 3]].astype(np.uint8).tobytes()


# ---------------------------------------------------------------------------
# DXT5 / BC3
# ---------------------------------------------------------------------------

def _expand565(value):
    """RGB565 -> 8bit RGB。"""
    r = (value >> 11) & 0x1F
    g = (value >> 5) & 0x3F
    b = value & 0x1F
    r = (r << 3) | (r >> 2)
    g = (g << 2) | (g >> 4)
    b = (b << 3) | (b >> 2)
    return r, g, b


def dxt5_decode(payload, width, height):
    """DXT5 解码 -> (h, w, 4) uint8 RGBA 数组。"""
    bw = (width + 3) // 4
    bh = (height + 3) // 4
    expected = bw * bh * 16
    if len(payload) < expected:
        raise ValueError("数据不足: 需要 %d 字节, 实际 %d" % (expected, len(payload)))

    blocks = np.frombuffer(payload[:expected], dtype=np.uint8).reshape(bh, bw, 16)
    out = np.zeros((bh * 4, bw * 4, 4), dtype=np.uint8)

    # ---- alpha ----
    a0 = blocks[:, :, 0].astype(np.int32)
    a1 = blocks[:, :, 1].astype(np.int32)

    # 48 bit 索引, 小端; 每 3 字节含 8 个 3bit 值
    bits = np.zeros((bh, bw, 48), dtype=np.int32)
    for byte_index in range(6):
        byte_val = blocks[:, :, 2 + byte_index].astype(np.int32)
        for bit in range(8):
            bits[:, :, byte_index * 8 + bit] = (byte_val >> bit) & 1

    idx3 = np.zeros((bh, bw, 16), dtype=np.int32)
    for slot in range(16):
        for bit in range(3):
            idx3[:, :, slot] += bits[:, :, slot * 3 + bit] << bit

    # 8 个 alpha 值的调色板
    alpha_lut = np.zeros((bh, bw, 8), dtype=np.int32)
    alpha_lut[:, :, 0] = a0
    alpha_lut[:, :, 1] = a1
    same = a0 > a1
    for i in range(2, 8):
        interp_a = ((8 - i) * a0 + (i - 1) * a1) // 7
        interp_b = ((6 - i) * a0 + (i - 1) * a1) // 5
        alpha_lut[:, :, i] = np.where(same, interp_a, interp_b)
    alpha_lut[:, :, 6] = np.where(same, alpha_lut[:, :, 6], 0)
    alpha_lut[:, :, 7] = np.where(same, alpha_lut[:, :, 7], 255)

    # ---- color ----
    c0 = (blocks[:, :, 8].astype(np.int32) | (blocks[:, :, 9].astype(np.int32) << 8))
    c1 = (blocks[:, :, 10].astype(np.int32) | (blocks[:, :, 11].astype(np.int32) << 8))

    color_lut = np.zeros((bh, bw, 4, 3), dtype=np.float64)
    for slot in range(4):
        pass
    r0, g0, b0 = _expand565(0)
    # 端点展开(逐元素做, 避免 numpy 位移的符号问题)
    def expand_arr(values):
        r = (values >> 11) & 0x1F
        g = (values >> 5) & 0x3F
        b = values & 0x1F
        r = (r << 3) | (r >> 2)
        g = (g << 2) | (g >> 4)
        b = (b << 3) | (b >> 2)
        return np.stack([r, g, b], axis=-1).astype(np.float64)

    e0 = expand_arr(c0)
    e1 = expand_arr(c1)
    color_lut[:, :, 0] = e0
    color_lut[:, :, 1] = e1
    color_lut[:, :, 2] = (2.0 * e0 + e1) / 3.0
    color_lut[:, :, 3] = (e0 + 2.0 * e1) / 3.0
    color_ok = c0 > c1  # 只有 c0 > c1 时才会用 4 色插值
    four_color = np.stack([
        e0, e1,
        (e0 + e1) / 2.0,
        np.zeros_like(e0),
    ], axis=2)
    color_lut = np.where(color_ok[:, :, None, None], color_lut, four_color)

    # 2bit 颜色索引
    idx2 = np.zeros((bh, bw, 16), dtype=np.int32)
    for group in range(4):
        byte_val = blocks[:, :, 12 + group].astype(np.int32)
        for pair in range(4):
            slot = group * 4 + pair
            idx2[:, :, slot] = (byte_val >> (2 * pair)) & 0x03

    # 铺回像素
    for by in range(bh):
        for bx in range(bw):
            for slot in range(16):
                py = by * 4 + slot // 4
                px = bx * 4 + slot % 4
                if py >= out.shape[0] or px >= out.shape[1]:
                    continue
                out[py, px, 0:3] = np.clip(color_lut[by, bx, idx2[by, bx, slot]], 0, 255).astype(np.uint8)
                out[py, px, 3] = alpha_lut[by, bx, idx3[by, bx, slot]].astype(np.uint8)

    return out[:height, :width]


def dxt5_encode(rgba):
    """(h, w, 4) uint8 RGBA -> DXT5 字节串。每块独立算端点, 质量足够图标使用。"""
    height, width = rgba.shape[0], rgba.shape[1]
    bh = (height + 3) // 4
    bw = (width + 3) // 4
    rgba = rgba.astype(np.int32)

    pad_h = bh * 4 - height
    pad_w = bw * 4 - width
    if pad_h or pad_w:
        rgba = np.pad(rgba, ((0, pad_h), (0, pad_w), (0, 0)), mode="edge")

    out = bytearray()
    for by in range(bh):
        for bx in range(bw):
            block = rgba[by * 4:by * 4 + 4, bx * 4:bx * 4 + 4]
            # ---- alpha ----
            alphas = block[:, :, 3].reshape(-1)
            a_min = int(alphas.min())
            a_max = int(alphas.max())
            if a_min == a_max:
                out.extend((a_max, a_min))
                out.extend(b"\x00" * 6)
            else:
                out.extend((a_max, a_min))
                # 8 级 alpha 调色板
                lut = [a_max, a_min]
                for i in range(1, 7):
                    lut.append(int(round(((7 - i) * a_max + i * a_min) / 7.0)))
                idx = 0
                for slot, value in enumerate(alphas):
                    best = min(range(8), key=lambda k: abs(lut[k] - int(value)))
                    idx |= (best & 0x07) << (slot * 3)
                out.extend(idx.to_bytes(6, "little"))

            # ---- color ----
            colors = block[:, :, 0:3].reshape(-1, 3).astype(np.float64)
            # 用包围盒端点(简单但效果稳定)
            mins = colors.min(axis=0)
            maxs = colors.max(axis=0)

            def to565(rgb):
                r = int(round(rgb[0] / 255.0 * 31.0))
                g = int(round(rgb[1] / 255.0 * 63.0))
                b = int(round(rgb[2] / 255.0 * 31.0))
                return (r << 11) | (g << 5) | b

            c0 = to565(maxs)
            c1 = to565(mins)
            if c0 < c1:
                c0, c1 = c1, c0
            if c0 == c1:
                c1 = max(0, c0 - 1)
            out.extend(struct.pack("<HH", c0, c1))

            e0 = np.array(_expand565(c0), dtype=np.float64)
            e1 = np.array(_expand565(c1), dtype=np.float64)
            lut4 = [e0, e1, (2 * e0 + e1) / 3.0, (e0 + 2 * e1) / 3.0]
            idx = 0
            for slot in range(16):
                color = colors[slot]
                best = min(range(4), key=lambda k: float(((lut4[k] - color) ** 2).sum()))
                idx |= (best & 0x03) << (2 * slot)
            out.extend(struct.pack("<I", idx))

    return bytes(out)


# ---------------------------------------------------------------------------
# PNG 读写(标准库实现, 免依赖)
# ---------------------------------------------------------------------------

import zlib


def write_png_rgba(path, rgba):
    height, width = rgba.shape[0], rgba.shape[1]
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw.extend(rgba[y].astype(np.uint8).tobytes())

    def chunk(tag, data):
        payload = tag + data
        return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as handle:
        handle.write(png)


def read_png_rgba(path):
    """只支持我们自己写出的 8bit RGBA 非隔行 PNG(够用即可)。"""
    with open(path, "rb") as handle:
        data = handle.read()
    if data[0:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("不是 PNG")
    pos = 8
    width = height = None
    idat = b""
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        if tag == b"IHDR":
            width, height, depth, color_type = struct.unpack(">IIBB", body[:10])
            if depth != 8 or color_type != 6:
                raise ValueError("只支持 8bit RGBA, 实际 depth=%d color_type=%d" % (depth, color_type))
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break
        pos += 12 + length

    raw = zlib.decompress(idat)
    stride = width * 4
    out = np.zeros((height, width, 4), dtype=np.uint8)
    prev = np.zeros(stride, dtype=np.uint8)
    offset = 0
    for y in range(height):
        filter_type = raw[offset]
        offset += 1
        line = np.frombuffer(raw[offset:offset + stride], dtype=np.uint8).astype(np.int32)
        offset += stride
        recon = np.zeros(stride, dtype=np.int32)
        for i in range(stride):
            left = recon[i - 4] if i >= 4 else 0
            up = int(prev[i])
            up_left = int(prev[i - 4]) if i >= 4 else 0
            value = int(line[i])
            if filter_type == 0:
                recon[i] = value
            elif filter_type == 1:
                recon[i] = (value + left) & 0xFF
            elif filter_type == 2:
                recon[i] = (value + up) & 0xFF
            elif filter_type == 3:
                recon[i] = (value + (left + up) // 2) & 0xFF
            elif filter_type == 4:
                p = left + up - up_left
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - up_left)
                pred = left if (pa <= pb and pa <= pc) else (up if pb <= pc else up_left)
                recon[i] = (value + pred) & 0xFF
            else:
                raise ValueError("未知 filter %d" % filter_type)
        out[y] = recon.astype(np.uint8).reshape(width, 4)
        prev = recon.astype(np.uint8)
    return out
