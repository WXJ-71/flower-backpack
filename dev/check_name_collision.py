"""核对本 mod 的译名是否与**任何**原版字符串撞名。

背景(踩过的坑): mod 最初叫「保鲜背包」, 而 STRINGS.NAMES.ICEPACK(原版
"Insulated Pack", 8 格、食物腐烂减半)的官方中文译名**正是**「保鲜背包」。
两个功能极像的背包同名, 玩家必然分不清。已改名为「鲜花背包」。

本脚本用完整的中文语言文件做反查, 任何 STRINGS.* 条目占用了同样的文字都会报出来。
"""

import io
import os
import re
import sys

PO = r"E:\ds h\upload_tmp2\ex\scripts\languages\chinese_s.po"
MOD_PO = r"E:\ds h\hunger_mod\scripts\languages\strings_zh.po"

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with io.open(PO, encoding="utf-8") as handle:
    lines = handle.read().split("\n")

# 反查表: 译文 -> 占用它的所有 msgctxt
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

print("原版中文语言文件: %d 条译文\n" % len(owners))

mod_text = io.open(MOD_PO, encoding="utf-8").read()
mod_entries = dict(re.findall(r'^msgctxt "(\S+)"\nmsgstr "(.*)"', mod_text, re.M))

print("=== 本 mod 的译名与占用检查 ===")
problems = 0
for key in sorted(mod_entries):
    value = mod_entries[key]
    others = [other for other in owners.get(value, []) if other != key]
    if others:
        problems += 1
        print("  [撞名] %-46s 「%s」 <- 原版 %s" % (key, value, ", ".join(others[:3])))
    else:
        print("  [可用] %-46s 「%s」" % (key, value))

print("\n=== 原版同类物品的中文名(供对照) ===")
for key in ("STRINGS.NAMES.BACKPACK", "STRINGS.NAMES.ICEPACK",
            "STRINGS.NAMES.PIGGYBACK", "STRINGS.NAMES.SPICEPACK",
            "STRINGS.NAMES.KRAMPUS_SACK", "STRINGS.NAMES.ICEBOX"):
    value = None
    for text, keys in owners.items():
        if key in keys:
            value = text
            break
    print("  %-32s %s" % (key, value or "(未找到)"))

print("\n结论: %s" % ("仍有 %d 处撞名" % problems if problems else "没有撞名"))
sys.exit(1 if problems else 0)
