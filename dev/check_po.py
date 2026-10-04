"""按 DST 的 translator.lua 解析规则, 预演一遍 .po 文件能不能被正确读出。

DST 的解析逻辑(scripts/translator.lua:LoadPOFile):
  · 用 ^msgctxt%s*"(%S*)" 取 key
  · 紧接着的 ^msgstr%s*"(.*)" 取译文(空串表示多行, 会继续收集)
  · 空行/下一个 #: 行结束一条记录
这里把同一套规则重现一遍, 用来在没有 Lua 解释器的情况下先验证格式。
"""

import os
import re

LANG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scripts", "languages",
)

MSGCtxt_RE = re.compile(r'^msgctxt\s*"(\S*)"')
MSGSTR_RE = re.compile(r'^msgstr\s*"(.*)"')
REF_RE = re.compile(r"^#:(\s*)(\S*)")


def parse(path):
    """返回 {key: 译文} —— 与 translator.lua 的行为保持一致。"""
    with open(path, "rb") as handle:
        raw = handle.read()

    if raw.startswith(b"\xef\xbb\xbf"):
        print("  !! 带 UTF-8 BOM, DST 的解析器会把第一行读坏")

    text = raw.decode("utf-8")

    strings = {}
    current_id = None
    current_str = ""
    msgstr_flag = False

    for line in text.split("\n"):
        line = line.rstrip("\r")

        if msgstr_flag:
            match = re.match(r'^(\s*)"(.*)"', line)
            if not match:
                if current_str != "":
                    strings[current_id] = current_str
                msgstr_flag = False
                current_str = ""
                current_id = None
            else:
                current_str += match.group(2)
        elif current_id is not None:
            match = MSGSTR_RE.match(line)
            if match:
                if match.group(1) == "":
                    msgstr_flag = True
                else:
                    strings[current_id] = match.group(1)
                    current_id = None
        else:
            match = MSGCtxt_RE.match(line)
            if match:
                current_id = match.group(1)

    # 文件末尾没有空行时补收最后一条
    if msgstr_flag and current_id is not None and current_str != "":
        strings[current_id] = current_str

    return strings


EXPECTED_KEYS = {
    "STRINGS.NAMES.FLOWERPACK",
    "STRINGS.RECIPE_DESC.FLOWERPACK",
    "STRINGS.CHARACTERS.GENERIC.DESCRIBE.FLOWERPACK",
}

problems = 0
for name in sorted(os.listdir(LANG_DIR)):
    if not name.endswith(".po"):
        continue
    path = os.path.join(LANG_DIR, name)
    print("%s (%d bytes)" % (name, os.path.getsize(path)))
    parsed = parse(path)
    for key in sorted(EXPECTED_KEYS):
        value = parsed.get(key)
        if value is None:
            print("  !! 缺少 %s" % key)
            problems += 1
        else:
            print("   %-46s -> %s" % (key, value))
    extra = set(parsed) - EXPECTED_KEYS
    if extra:
        print("  (多余条目: %s)" % ", ".join(sorted(extra)))
    print()

print("问题数: %d" % problems)
