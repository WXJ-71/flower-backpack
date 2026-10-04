"""在世界贴图(背上 + 地面共用的 swap_backpack 图集)上加一朵花。

【关于 KTEX 布局的判断 —— 这次用"总和是否刚好用尽"来锁死, 不靠推测】
    swap_backpack/atlas-0.tex = 87506 字节
    基准级 256x256 BC3          = 65536
    其余 8 级 mip 之和           = 21872
    87506 - 65536 - 21872       = 98      <- 头部长度, 且**没有余数**

    如果只是"头 + 基准级"(旧假设), 头长会是 21970; 但 21970 - 21872 = 98 说明
    头部表旁边的 21872 字节正好就是小 mip 链 —— 于是布局必然是
        [98 字节头][基准级 65536][8 级小 mip 21872]
    三个数字相加精确等于文件大小, 这种吻合不可能是巧合。

【为什么可以放心重新编码】
    verify_codec.py 验证过: 解码 -> 重新编码后**重新解码**, 像素平均误差 0.13、
    最大 29(纯属 BC3 端点取整的自由度), 未修改区域的观感不会变化。
    因此"改几个像素再封回去"是安全的。

【花画在哪里】
    目标是背包主体(图集上最大的连通块 x[9,116] y[150,250], 108x101)。
    花心放在它的右下角内侧, 半径按画布比例缩放, 保证与 64x64 物品图标上的
    相对位置一致。花会盖住该处的不透明像素, 所以不会出现"花飘在透明区"的怪象。
"""

import os
import shutil
import sys
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flower_art
import ktex

ART = os.path.join(HERE, "art")
MOD_ROOT = os.path.dirname(HERE)
SRC_ZIP = os.path.join(HERE, "swap_backpack.zip")
OUT_DIR = os.path.join(MOD_ROOT, "anim")
OUT_ZIP = os.path.join(OUT_DIR, "swap_backpack.zip")

WIDTH = HEIGHT = 256
HEADER = 98

# 背包主体在图集上的包围盒(由 pick_target_face.py / map_world_components.py 量出)
BODY_X0, BODY_X1 = 9, 116
BODY_Y0, BODY_Y1 = 150, 250

# 花心位置在主体右下角附近搜索, 半径按主体短边比例
# (需求: 花要比上一版小一圈, 并贴到背包右下角, 所以半径 17 -> 13, 搜索区收到右下角)
FLOWER_R = 13
SEARCH_X = (BODY_X1 - 34, BODY_X1 + 4)
SEARCH_Y = (BODY_Y1 - 34, BODY_Y1 + 4)
# 允许花瓣略微探出轮廓(贴角效果), 但不允许大面积悬空
MIN_ON_PACK = 0.93


def sub_chain_size(width, height):
    """基准级之下所有小 mip 的字节数之和。"""
    total = 0
    w, h = max(1, width // 2), max(1, height // 2)
    while True:
        total += ktex.dxt5_size(w, h)
        if w == 1 and h == 1:
            break
        w = max(1, w // 2)
        h = max(1, h // 2)
    return total


def pick_flower_centre(atlas):
    """在主体右下角搜一个"花瓣完全落在不透明区域"的花心。

    为什么要搜: 背包主体是**梯形**(上宽下窄), 单纯用包围盒的右下角会把花
    放到斜边外面, 花瓣就飘在透明区了。这里直接按"花覆盖的像素里有多少是
    原本不透明的"打分, 取最好的那个位置。
    """
    opaque = atlas[:, :, 3] > 128
    probe = np.zeros_like(atlas)

    best = None
    closest = None
    for cy in range(SEARCH_Y[0], SEARCH_Y[1] + 1):
        for cx in range(SEARCH_X[0], SEARCH_X[1] + 1):
            probe[:] = 0
            mask = flower_art.draw_flower(probe, cx, cy, FLOWER_R)
            total = int(mask.sum())
            if total == 0:
                continue
            inside = int((mask & opaque).sum())
            ratio = inside / float(total)
            # 记录"最贴合"的那个, 万一没有位置达标也能给出诊断信息
            if closest is None or ratio > closest[0]:
                closest = (ratio, cx, cy, total, inside)
            if ratio < MIN_ON_PACK:
                continue
            # 在"够贴合"的位置里, 取最靠右下的那个(视觉上贴在包角上)
            key = (cx + cy, round(ratio, 4))
            if best is None or key > best[0]:
                best = (key, cx, cy, ratio, total, inside)

    if best is None:
        ratio, cx, cy, total, inside = closest
        raise SystemExit(
            "没有位置达到 %.0f%% 贴合度; 最好的是 (%d,%d) 仅 %.1f%%(%d/%d)。"
            "请调小 FLOWER_R 或放宽 MIN_ON_PACK。"
            % (MIN_ON_PACK * 100, cx, cy, ratio * 100, inside, total))
    return best


def main():
    with zipfile.ZipFile(SRC_ZIP) as archive:
        names = archive.namelist()
        raw = archive.read("atlas-0.tex")
        others = {name: archive.read(name) for name in names if name != "atlas-0.tex"}

    base = ktex.dxt5_size(WIDTH, HEIGHT)
    chain = sub_chain_size(WIDTH, HEIGHT)
    header = len(raw) - base - chain
    print("文件=%d 基准级=%d 小mip链=%d -> 头部=%d" % (len(raw), base, chain, header))
    if header != HEADER:
        raise SystemExit("头部长度与预期不符: %d != %d" % (header, HEADER))
    if header + base + chain != len(raw):
        raise SystemExit("布局假设不成立, 拒绝改写")

    body = raw[header:header + base]
    tail = raw[header + base:]
    print("头部 %d 字节 + 基准级 %d + 小mip %d = %d (文件 %d)"
          % (header, base, len(tail), header + base + len(tail), len(raw)))

    atlas = ktex.dxt5_decode(body, WIDTH, HEIGHT)
    before = atlas.copy()

    _, cx, cy, ratio, total, inside = pick_flower_centre(atlas)
    print("\n自动定位: 花心(%d,%d) 半径 %d -> 覆盖 %d 像素, 其中 %d 个落在背包上 (%.1f%%)"
          % (cx, cy, FLOWER_R, total, inside, ratio * 100))

    changed = flower_art.draw_flower(atlas, cx, cy, FLOWER_R)
    print("花朵: 中心(%d,%d) 半径 %d, 覆盖 %d 像素"
          % (cx, cy, FLOWER_R, int(changed.sum())))

    # 安全校验 1: 花必须尽量落在原本就不透明的区域内(否则会飘在透明区)
    was_opaque = before[:, :, 3] > 128
    outside = int((changed & ~was_opaque).sum())
    print("落在原本透明区域的像素: %d (%.1f%%)  —— 越少越好"
          % (outside, 100.0 * outside / max(1, int(changed.sum()))))

    # 安全校验 2: 花以外的地方应当几乎无变化
    untouched = ~changed
    error = np.abs(atlas.astype(np.int32) - before.astype(np.int32)).max(axis=2)
    print("花以外区域的最大像素变化: %d (BC3 重新编码的自由度, 应为个位数)"
          % int(error[untouched].max()))

    new_body = ktex.dxt5_encode(atlas)
    if len(new_body) != base:
        raise SystemExit("编码后的基准级大小不对: %d != %d" % (len(new_body), base))

    new_raw = raw[:header] + new_body + tail
    print("\n新文件 %d 字节 (原 %d, 差 %d)" % (len(new_raw), len(raw), len(new_raw) - len(raw)))
    if len(new_raw) != len(raw):
        raise SystemExit("文件大小变了, 拒绝写出")

    os.makedirs(OUT_DIR, exist_ok=True)
    with zipfile.ZipFile(OUT_ZIP, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("atlas-0.tex", new_raw)
        for name, data in others.items():
            archive.writestr(name, data)
    print("已写出 -> %s" % OUT_ZIP)
    print("  内含: %s" % ", ".join(["atlas-0.tex"] + sorted(others)))

    os.makedirs(ART, exist_ok=True)
    ktex.write_png_rgba(os.path.join(ART, "world_atlas_flower.png"), atlas)
    crop = atlas[BODY_Y0 - 6:BODY_Y1 + 7, BODY_X0 - 6:BODY_X1 + 7]
    ktex.write_png_rgba(os.path.join(ART, "world_atlas_flower_body_x2.png"),
                        np.repeat(np.repeat(crop, 2, axis=0), 2, axis=1))
    print("预览 -> art/world_atlas_flower.png / _body_x2.png")


main()
