"""确认原版 inventoryimages1 图集里确实有 backpack.tex 这个区域。"""

import re

PATH = r"E:\ds h\hunger_mod\dev\images_unzip\images\inventoryimages1.xml"

data = open(PATH, encoding="utf-8").read()
names = re.findall(r'name="([^"]+)"', data)
print("total elements:", len(names))

hits = [n for n in names if "backpack" in n or "icepack" in n]
print("backpack/icepack regions:", hits)

target = "backpack.tex"
if target in names:
    idx = names.index(target)
    match = re.search(r'<Element name="%s"[^/]*/>' % re.escape(target), data)
    print("FOUND:", match.group(0))
else:
    print("NOT FOUND:", target)
