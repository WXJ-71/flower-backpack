"""从游戏的中文语言文件里查出几个背包物品的官方中文名。

用途: 向用户说明"冰背包"到底是哪个物品时, 不能靠猜译名 —— 直接在
scripts/languages/chinese_s.po 里按 msgctxt 精确查。
"""

import io
import os
import re
import sys

PO = r"E:\ds h\upload_tmp2\ex\scripts\languages\chinese_s.po"

WANTED = [
    "STRINGS.NAMES.BACKPACK",
    "STRINGS.NAMES.ICEPACK",
    "STRINGS.NAMES.ICEBOX",
    "STRINGS.NAMES.PIGGYBACK",
    "STRINGS.NAMES.SPICEPACK",
    "STRINGS.NAMES.KRAMPUS_SACK",
]

# 让 print 输出 UTF-8, 避免在 GBK 控制台上炸掉
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with io.open(PO, encoding="utf-8") as handle:
    lines = handle.read().split("\n")

print("语言文件 %d 行\n" % len(lines))

results = {}
for index, line in enumerate(lines):
    match = re.match(r'^msgctxt "(STRINGS\.NAMES\.[A-Z_]+)"', line)
    if not match:
        continue
    key = match.group(1)
    # 往后找第一条 msgstr
    for offset in range(index + 1, min(index + 6, len(lines))):
        msgstr = re.match(r'^msgstr "(.*)"', lines[offset])
        if msgstr:
            results[key] = msgstr.group(1)
            break

for key in WANTED:
    print("%-32s -> %s" % (key, results.get(key, "(未找到)")))

print("\n顺带列出所有含 PACK / SACK 的物品名:")
for key, value in sorted(results.items()):
    if "PACK" in key or "SACK" in key:
        print("  %-34s %s" % (key, value))
