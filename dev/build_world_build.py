"""把加花后的世界贴图打包成一个**独立命名**的 build, 避免影响原版冰背包。

为什么必须改名:
    swap_backpack 这个 build 不只原版背包在用 ——
        * scripts/prefabs/backpack.lua 里 SetBuild("swap_backpack")
        * 冰背包 params.icepack = params.backpack, 用的是同一个预制体
        * prefabskin.lua 的背包皮肤也以 "swap_backpack" 作为基准 build
    如果本 mod 直接交一份同名 anim/swap_backpack.zip, mod 资源优先级更高,
    会把上面这些统统改掉(冰背包上也会长出一朵花)。

    所以这里把 build 名改成 swap_backpack_flower, 并把 zip 一起改名。
    build.bin 里只改**构建名字段**(4 字节长度 + 字符串), 几何数据一个字节不动。

用法: python build_world_build.py
"""

import os
import struct
import sys
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MOD_ROOT = os.path.dirname(HERE)

# 加花后的贴图来源(build_world_flower.py 的产物)
SRC_ZIP = os.path.join(MOD_ROOT, "anim", "swap_backpack.zip")
OUT_DIR = os.path.join(MOD_ROOT, "anim")
OUT_ZIP = os.path.join(OUT_DIR, "swap_backpack_flower.zip")

OLD_NAME = b"swap_backpack"
NEW_NAME = b"swap_backpack_flower"

# 世界贴图的 KTEX 布局: [98 字节头][基准级 65536][8 级小 mip 21872]
ATLAS_HEADER = 98
# 世界贴图上花心位置(build_world_flower.py 自动定位的产物值)
WORLD_FLOWER_CENTRE = (82, 236)


def patch_build_name(build):
    """只替换 build.bin 里的构建名字符串(含长度字段), 其余原样复制。

    字段顺序(由 probe_buildbin.py 逐字段读出确认):
        0   4   magic "BILD"
        4   4   version = 6
        8   4   hash? = 1
        12  4   字符串长度 = 12   (内容 "swap_backpack"? 不是 —— 见下)
        ...
    实际布局:
        @12 u32 = 12   -> 这是一个长度为 12 的字符串, 内容是 "swap_backpack" 的
                          前 12 字节出现在 @16, 也就是 "swap_backpack" 本身。
        简化起见不依赖完整解析: 直接在文件里定位 b"swap_backpack",
        它前面的 u32 就是长度字段, 只改这两处。
    """
    if build[0:4] != b"BILD":
        raise SystemExit("build.bin magic 不对: %r" % build[0:4])

    # 该文件里 "swap_backpack" 只出现一次(即构建名), 直接定位即可。
    occurrences = build.count(OLD_NAME)
    if occurrences != 1:
        raise SystemExit("构建名 %r 出现 %d 次, 位置不唯一, 拒绝改写"
                         % (OLD_NAME, occurrences))
    position = build.find(OLD_NAME)
    length = struct.unpack_from("<I", build, position - 4)[0]
    if length != len(OLD_NAME):
        raise SystemExit("构建名长度不符: %d != %d" % (length, len(OLD_NAME)))
    print("构建名 @%d, 长度字段 %d —— 自洽" % (position, length))

    # 符号名 swap_body 必须保持原样
    symbol = build.find(b"swap_body")
    if symbol < 0:
        raise SystemExit("找不到符号名 swap_body")

    patched = (build[:position - 4]
               + struct.pack("<I", len(NEW_NAME)) + NEW_NAME
               + build[position + len(OLD_NAME):])

    print("build.bin: %d -> %d 字节" % (len(build), len(patched)))
    print("  构建名 @%d: %r -> %r" % (position, OLD_NAME.decode(), NEW_NAME.decode()))
    print("  符号名 @%d 保持 %r" % (build.find(b"swap_body"), "swap_body"))
    duration = len(patched) - len(build)
    print("  整体偏移变化 %+d 字节(几何数据随之平移, 内容不变)" % duration)
    return patched


def verify():
    """只校验产物, 不重新打包(方便在上一步已成功后单独复查)。"""
    if not os.path.exists(OUT_ZIP):
        raise SystemExit("还没有产物 %s" % OUT_ZIP)

    with zipfile.ZipFile(OUT_ZIP) as archive:
        check = archive.read("build.bin")
        atlas_back = archive.read("atlas-0.tex")

    with zipfile.ZipFile(os.path.join(HERE, "swap_backpack.zip")) as archive:
        vanilla_build = archive.read("build.bin")

    check_pos = check.find(NEW_NAME)
    check_len = struct.unpack_from("<I", check, check_pos - 4)[0]
    vanilla_pos = vanilla_build.find(OLD_NAME)
    geometry_old = len(vanilla_build) - (vanilla_pos + len(OLD_NAME))
    geometry_new = len(check) - (check_pos + len(NEW_NAME))

    # 读取产物里**真正的构建名字段**(长度前缀 + 字符串)。
    # 注意: 不能用 check.find(OLD_NAME) < 0 来判断"旧名无残留" ——
    # "swap_backpack" 是 "swap_backpack_flower" 的前缀, 那样必然误报。
    actual_name = check[check_pos:check_pos + check_len]

    print("校验 %s:" % os.path.basename(OUT_ZIP))
    print("  构建名字段 @%d 长度 %d -> %r" % (check_pos, check_len, actual_name.decode()))
    print("  符号名 swap_body 仍存在: %s" % ("是" if check.find(b"swap_body") >= 0 else "否"))
    print("  几何数据 %d 字节 vs 原版 %d 字节 -> %s"
          % (geometry_new, geometry_old,
             "完全一致" if geometry_new == geometry_old else "不一致!"))
    print("  贴图 %d 字节" % len(atlas_back))
    print("  是否还存在独立的旧构建名(长度 13): %s"
          % ("有!" if struct.pack("<I", len(OLD_NAME)) + OLD_NAME in check else "无"))

    # 贴图必须能被解开且 alpha 双峰(真图特征)
    sys.path.insert(0, HERE)
    import numpy as np
    import ktex
    info = ktex.parse_ktex(atlas_back)
    # 布局: [98 字节头][基准级 65536][8 级小 mip 21872], 基准级紧跟头部
    base_bytes = ktex.dxt5_size(info.width, info.height)
    rgba = ktex.dxt5_decode(atlas_back[ATLAS_HEADER:ATLAS_HEADER + base_bytes],
                            info.width, info.height)
    alpha = rgba[:, :, 3]
    sharp = float(np.minimum(alpha.astype(np.int32), 255 - alpha).mean())
    ok_texture = sharp < 6.0
    print("  贴图解码: %dx%d, alpha 锐利度 %.2f (真图应 < 6) -> %s"
          % (info.width, info.height, sharp, "正常" if ok_texture else "异常!"))

    # 花确实在图上: 花心应是绿色(绿 > 红且绿 > 蓝), 外圈描边应是红色
    centre = tuple(int(v) for v in rgba[WORLD_FLOWER_CENTRE[1], WORLD_FLOWER_CENTRE[0]][:3])
    r, g, b = centre
    flower_ok = g > r and g > b and g > 80
    print("  花心像素 %s 处颜色 %s -> %s"
          % (WORLD_FLOWER_CENTRE, centre, "绿色花心, 已加花" if flower_ok else "不是绿色, 没找到花!"))

    # 描边: 以花心为中心取一块方形区域, 统计"红色描边像素"的数量。
    # 不沿单条射线找 —— 花瓣之间有空隙, 单射线可能正好穿过空隙。
    cx, cy = WORLD_FLOWER_CENTRE
    half = 22
    window = rgba[max(0, cy - half):cy + half, max(0, cx - half):cx + half][:, :, :3].astype(int)
    red_count = int(((window[:, :, 0] > 150) & (window[:, :, 1] < 90) & (window[:, :, 2] < 90)).sum())
    outline_ok = red_count > 15
    print("  红色描边像素: %d 个 (窗口以花心为中心 %dx%d) -> %s"
          % (red_count, half * 2, half * 2, "找到" if outline_ok else "没找到!"))

    ok_geometry = geometry_new == geometry_old
    ok_oldname = actual_name == NEW_NAME and (struct.pack("<I", len(OLD_NAME)) + OLD_NAME) not in check
    ok = ok_geometry and ok_oldname and ok_texture and flower_ok and outline_ok
    print("\n  汇总: 构建名正确=%s 几何一致=%s 贴图正常=%s 绿花心=%s 红描边=%s -> %s"
          % (ok_oldname, ok_geometry, ok_texture, flower_ok, outline_ok,
             "通过" if ok else "不通过"))
    return ok


def main():
    """默认跑完整流程: 加花后的 zip -> 改构建名 -> 校验。
    带 --verify-only 时只做校验(用于复查)。"""
    if "--verify-only" in sys.argv:
        ok = verify()
        print("\n结果: %s" % ("全部通过" if ok else "有问题"))
        sys.exit(0 if ok else 1)

    if not os.path.exists(SRC_ZIP):
        if os.path.exists(OUT_ZIP):
            print("源文件已改名, 直接校验 %s。" % os.path.basename(OUT_ZIP))
            ok = verify()
            print("\n结果: %s" % ("全部通过" if ok else "有问题"))
            sys.exit(0 if ok else 1)
        raise SystemExit("找不到 %s —— 请先跑 dev/build_world_flower.py" % SRC_ZIP)

    with zipfile.ZipFile(SRC_ZIP) as archive:
        names = archive.namelist()
        build = archive.read("build.bin")
        atlas = archive.read("atlas-0.tex")
    print("来源 %s 内含: %s" % (os.path.basename(SRC_ZIP), ", ".join(names)))

    patched = patch_build_name(build)

    with zipfile.ZipFile(SRC_ZIP, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("atlas-0.tex", atlas)
        archive.writestr("build.bin", patched)
    print("已就地更新 %s" % SRC_ZIP)

    os.replace(SRC_ZIP, OUT_ZIP)
    print("改名 -> %s" % OUT_ZIP)

    ok = verify()
    print("\n结果: %s" % ("全部通过" if ok else "有问题"))
    sys.exit(0 if ok else 1)


main()
