"""检查候选中文名是否与**任何**原版字符串撞名(不只是物品名)。

项目现状: mod 显示名「保鲜背包」与 STRINGS.NAMES.ICEPACK 撞名 —— 那是原版的
"Insulated Pack"(8 格、食物腐烂减半), 中文官方译名正是「保鲜背包」。
两个功能极像的背包同名, 玩家必然分不清, 所以必须改名。

本脚本在**整份中文语言文件**里搜候选名, 报出每个候选是否被占用及占用在哪。
"""

import io
import re
import sys

PO = r"E:\ds h\upload_tmp2\ex\scripts\languages\chinese_s.po"

# 候选名(都要带"背包"二字, 保持与原版同类物品的一致命名)
CANDIDATES = [
    "鲜花背包",
    "花语背包",
    "花饰背包",
    "花香背包",
    "鲜花保鲜背包",
    "花印背包",
    "保鲜花背包",
]

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with io.open(PO, encoding="utf-8") as handle:
    lines = handle.read().split("\n")

# 建立 译文 -> [msgctxt] 的反查表
owners = {}
for index, line in enumerate(lines):
    match = re.match(r'^msgctxt "([^"]+)"', line)
    if not match:
        continue
    key = match.group(1)
    for offset in range(index + 1, min(index + 6, len(lines))):
        msgstr = re.match(r'^msgstr "(.*)"', lines[offset])
        if msgstr:
            owners.setdefault(msgstr.group(1), []).append(key)
            break

print("语言文件共 %d 条带 msgctxt 的译文\n" % len(owners))

for name in CANDIDATES:
    hit = owners.get(name)
    if hit:
        print("  [占用] %-14s <- %s" % (name, ", ".join(hit[:4])))
    else:
        print("  [可用] %s" % name)

print("\n=== 参考: 原版几个背包/容器的中文名 ===")
for key in sorted(owners):
    if key.startswith("STRINGS.NAMES."):
        value = None
        for candidate, keys in owners.items():
            if key in keys:
                value = candidate
                break
        if value and ("背包" in value or "袋" in value or "桶" in value):
            print("  %-34s %s" % (key, value))
