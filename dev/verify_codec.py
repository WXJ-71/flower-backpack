"""Codec 验证: 解码 -> 重新编码, 必须与原始数据**逐字节相同**。

为什么必须做这一步: 往世界贴图 atlas-0.tex 上加花, 意味着我要把整张图解码、
改几个像素、再按同样格式封回去。只要"原样解码再编码"不能字节还原, 就说明
我的 BC3 编解码器与官方的不一致, 封回去的图会把整个背包画坏。

验证对象:
  1. images/flowerpack.tex  —— 我自己用 dxt5_encode 生成的, 必然是自洽的
  2. modicon.tex            —— 官方 TextureConverter 生成的 128x128 BC3
  3. swap_backpack 图集     —— 官方原版图集(要改的那张)
  4. inventoryimages1       —— 官方原版图集(已知可解)
"""

import os
import sys
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MOD_ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ktex


def roundtrip(label, raw, offset, width, height, compare_original=True):
    base = ktex.dxt5_size(width, height)
    payload = raw[offset:offset + base]
    if len(payload) != base:
        print("%-28s SKIP 数据不足" % label)
        return

    rgba = ktex.dxt5_decode(payload, width, height)
    reencoded = ktex.dxt5_encode(rgba)

    same = reencoded == payload
    mismatch = int((np.frombuffer(reencoded, dtype=np.uint8) !=
                    np.frombuffer(payload, dtype=np.uint8)).sum())
    print("%-28s %dx%d  字节还原=%s  不同字节=%d / %d"
          % (label, width, height, "是" if same else "否", mismatch, len(payload)))

    if not same:
        # 给出差异位置, 判断是不是"端点选择顺序"这类无害差异
        diff = np.frombuffer(reencoded, dtype=np.uint8) != np.frombuffer(payload, dtype=np.uint8)
        positions = np.where(diff)[0]
        print("      首个差异 @%d; 差异共 %d 字节" % (positions[0], len(positions)))
        # 统计解出来的像素误差
        back = ktex.dxt5_decode(reencoded, width, height)
        err = np.abs(back.astype(np.int32) - rgba.astype(np.int32))
        print("      重新解码后的像素误差: 平均 %.3f 最大 %d (0 = 无损)"
              % (err.mean(), err.max()))


print("=== 1. 自产图标 ===")
info = ktex.parse_ktex(open(os.path.join(MOD_ROOT, "images", "flowerpack.tex"), "rb").read())
roundtrip("images/flowerpack.tex", open(os.path.join(MOD_ROOT, "images", "flowerpack.tex"), "rb").read(),
          info.header_size, info.width, info.height)

print("\n=== 2. 官方 modicon.tex ===")
raw = open(os.path.join(MOD_ROOT, "modicon.tex"), "rb").read()
roundtrip("modicon.tex", raw, len(raw) - ktex.dxt5_size(128, 128), 128, 128)

print("\n=== 3. 官方 swap_backpack 图集 ===")
with zipfile.ZipFile(os.path.join(HERE, "swap_backpack.zip")) as z:
    world = z.read("atlas-0.tex")
roundtrip("swap_backpack/atlas-0", world, 98, 256, 256)

print("\n=== 4. 官方 ui_backpack_2x4 图集 ===")
with zipfile.ZipFile(os.path.join(HERE, "ui_backpack_2x4.zip")) as z:
    names = [n for n in z.namelist() if n.endswith(".tex")]
    if names:
        ui = z.read(names[0])
        sizes = 0
        w = h = 512
        while True:
            sizes += ktex.dxt5_size(w, h)
            if w == 1:
                break
            w = max(1, w // 2)
            h = max(1, h // 2)
        roundtrip("ui_backpack_2x4/" + names[0], ui, len(ui) - ktex.dxt5_size(512, 512), 512, 512)
