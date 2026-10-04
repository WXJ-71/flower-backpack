"""探查原版 inventoryimages*.tex 的格式, 判断能否直接解出原版背包图标。

背景: 物品图标必须存在于某个图集里, 否则引擎会去 images/inventoryimages4.xml
(动态图集) 找 flowerpack.tex, 找不到就渲染成空白 -> 容器格子里看着像"空的"。
所以最好直接把原版背包的图标抠出来复用。
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ktex

WORK = os.path.join(HERE, "images_unzip", "images")

for name in ["inventoryimages1.tex", "inventoryimages2.tex",
             "inventoryimages3.tex", "inventoryimages4.tex"]:
    path = os.path.join(WORK, name)
    if not os.path.exists(path):
        print("%-22s MISSING" % name)
        continue
    raw = open(path, "rb").read()
    print("%-22s size=%-9d b4=0x%02X fmt=0x%02X flags=0x%02X b7=0x%02X w=%d h=%d row=%d"
          % (name, len(raw), raw[4], raw[5], raw[6], raw[7],
             int.from_bytes(raw[8:10], "little"),
             int.from_bytes(raw[10:12], "little"),
             int.from_bytes(raw[12:14], "little")))
