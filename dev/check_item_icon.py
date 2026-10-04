"""自检: mod 物品图标图集(images/flowerpack.tex + .xml)是否符合引擎要求。

检查项(全部来自 DST 的实际读取方式):
  1. .tex 是合法 KTEX, 64x64, BC3, 能被本项目的解码器解开且不是空图;
  2. .xml 里恰好有一个区域, 名字**必须**是 "flowerpack.tex"
     (widgets/itemtile.lua 传给 Image:SetTexture 的就是这个名字);
  3. UV 能把整张 64x64 完整映射出来, 且四周留半像素内缩(避免采样吃到边界);
  4. 反算每个像素的 UV 中心, 确认落在 [0,1) 内。

用法: python check_item_icon.py
"""

import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ktex

MOD_ROOT = os.path.dirname(HERE)
TEX = os.path.join(MOD_ROOT, "images", "flowerpack.tex")
XML = os.path.join(MOD_ROOT, "images", "flowerpack.xml")

EXPECTED_REGION = "flowerpack.tex"
EXPECTED_SIZE = 64

problems = []


def check(condition, message):
    print(("  OK   " if condition else "  FAIL ") + message)
    if not condition:
        problems.append(message)


print("== 贴图 %s ==" % TEX)
info = ktex.parse_ktex(open(TEX, "rb").read())
print("  " + info.describe())
check(info.width == EXPECTED_SIZE and info.height == EXPECTED_SIZE,
      "尺寸是 %dx%d" % (EXPECTED_SIZE, EXPECTED_SIZE))
check((info.format_code & 0x0F) == 0x02, "格式是 BC3/DXT5")

icon = ktex.dxt5_decode(info.payload, info.width, info.height)
check(icon.shape == (EXPECTED_SIZE, EXPECTED_SIZE, 4),
      "解码得到 %s" % (icon.shape,))
opaque = int((icon[:, :, 3] > 8).sum())
check(opaque > 500,
      "不是空图(不透明像素 %d / %d)" % (opaque, EXPECTED_SIZE * EXPECTED_SIZE))

print("\n== 图集 %s ==" % XML)
text = open(XML, encoding="utf-8").read()
elements = re.findall(
    r'<Element name="([^"]+)" u1="([\d.]+)" u2="([\d.]+)" v1="([\d.]+)" v2="([\d.]+)"', text)
check(len(elements) == 1, "只有一个区域(实际 %d 个)" % len(elements))

if elements:
    name, u1, u2, v1, v2 = elements[0]
    u1, u2, v1, v2 = float(u1), float(u2), float(v1), float(v2)
    check(name == EXPECTED_REGION, '区域名是 %s(实际 "%s")' % (EXPECTED_REGION, name))

    half = 0.5 / EXPECTED_SIZE
    check(abs(u1 - half) < 1e-6 and abs(v1 - half) < 1e-6,
          "左上角留了半像素内缩 (%.7f)" % half)
    check(abs(u2 - (1.0 - half)) < 1e-6 and abs(v2 - (1.0 - half)) < 1e-6,
          "右下角留了半像素内缩")

    # 反算: 第 i 个像素中心的 UV 应当落在区域内
    center_first = (0 + 0.5) / EXPECTED_SIZE
    center_last = (EXPECTED_SIZE - 0.5) / EXPECTED_SIZE
    check(u1 <= center_first <= u2 and u1 <= center_last <= u2,
          "首/末像素中心 (%.5f / %.5f) 都落在区域内" % (center_first, center_last))

    # 区域覆盖的像素范围应当正好是 [0, 64)
    x0 = int(round(u1 * EXPECTED_SIZE))
    x1 = int(round(u2 * EXPECTED_SIZE))
    print("  区域覆盖像素 x[%d,%d) y[%d,%d) —— 目标 0..%d"
          % (x0, x1, int(round(v1 * EXPECTED_SIZE)), int(round(v2 * EXPECTED_SIZE)), EXPECTED_SIZE))

print("\n== 与 modmain 的注册是否一致 ==")
modmain = open(os.path.join(MOD_ROOT, "modmain.lua"), encoding="utf-8").read()
m = re.search(r'local FLOWERPACK_ICON_ATLAS = "([^"]+)"', modmain)
check(m is not None and m.group(1) == "images/flowerpack.xml",
      "modmain 里注册的图集路径 = %s" % (m.group(1) if m else "未找到"))
check('RegisterInventoryItemAtlas(FLOWERPACK_ICON_ATLAS, "flowerpack.tex")' in modmain,
      'modmain 里登记的键是 "flowerpack.tex"(引擎查的就是这个名字)')
check('Asset("ATLAS", "images/flowerpack.xml")' in modmain, "modmain 声明了 ATLAS 资源")
check('Asset("IMAGE", "images/flowerpack.tex")' in modmain, "modmain 声明了 IMAGE 资源")

print()
if problems:
    print("有问题: %d 项" % len(problems))
    sys.exit(1)
print("全部通过。")
