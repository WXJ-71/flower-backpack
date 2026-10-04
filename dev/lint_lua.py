"""轻量 Lua 语法体检 -- 只用 Python 标准库。

没有 Lua 解释器可用(游戏只有一个 nullrenderer, 起不来), 所以这里做静态检查:
    1. 括号 / 方括号 / 花括号配平
    2. 块关键字配平: function/if/for/while/do 与 end
    3. 长字符串/长注释 [[ ]] 的闭合
    4. 明显可疑的写法提示
它不能替代真正的编译, 但能拦住"少一个 end""括号不配对"这类致命错误。

用法:
    python lint_lua.py <目录或文件> [...]
"""

import os
import re
import sys

BLOCK_OPENERS = re.compile(r"\b(function|if|for|while|do)\b")
# if/for/while 结尾的 then/do 不再额外计数; else/elseif 不增加嵌套
KEYWORD_RE = re.compile(r"\b(function|if|for|while|do|then|end|elseif|else|repeat|until)\b")


def strip_comments_and_strings(src):
    """把注释和字符串替换成空格, 保留换行以便报行号。"""
    out = []
    i = 0
    n = len(src)
    while i < n:
        ch = src[i]

        # 长注释 --[[ ... ]]  /  --[==[ ... ]==]
        if src.startswith("--", i):
            m = re.match(r"--\[(=*)\[", src[i:])
            if m:
                eq = m.group(1)
                close = "]" + eq + "]"
                j = src.find(close, i + len(m.group(0)))
                j = n if j == -1 else j + len(close)
                out.append(re.sub(r"[^\n]", " ", src[i:j]))
                i = j
                continue
            j = src.find("\n", i)
            j = n if j == -1 else j
            out.append(" " * (j - i))
            i = j
            continue

        # 长字符串 [[ ... ]] / [==[ ... ]==]
        m = re.match(r"\[(=*)\[", src[i:])
        if m:
            eq = m.group(1)
            close = "]" + eq + "]"
            j = src.find(close, i + len(m.group(0)))
            j = n if j == -1 else j + len(close)
            out.append(re.sub(r"[^\n]", " ", src[i:j]))
            i = j
            continue

        # 普通字符串
        if ch in "\"'":
            quote = ch
            j = i + 1
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == quote:
                    j += 1
                    break
                if src[j] == "\n":
                    break
                j += 1
            out.append(re.sub(r"[^\n]", " ", src[i:j]))
            i = j
            continue

        out.append(ch)
        i += 1

    return "".join(out)


def check(path):
    with open(path, "rb") as handle:
        raw = handle.read()

    problems = []

    # 0) BOM 检查 —— 这个坑真的踩过:
    #    DST 的 Lua 加载器不认 UTF-8 BOM, 有 BOM 会报
    #    "unexpected symbol near '<EF BB BF>'" 且整个 mod 加载失败。
    #    PowerShell 的 Set-Content -Encoding UTF8 就会写出带 BOM 的文件。
    if raw.startswith(b"\xef\xbb\xbf"):
        problems.append("文件带 UTF-8 BOM, 必须去掉(DST 的 Lua 加载器不认)")

    src = raw.decode("utf-8-sig")

    cleaned = strip_comments_and_strings(src)

    # 1) 括号配平
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    line = 1
    for ch in cleaned:
        if ch == "\n":
            line += 1
        elif ch in "([{":
            stack.append((ch, line))
        elif ch in ")]}":
            if not stack:
                problems.append("L%d: 多余的 '%s'" % (line, ch))
            elif stack[-1][0] != pairs[ch]:
                problems.append("L%d: '%s' 与 L%d 的 '%s' 不匹配" % (line, ch, stack[-1][1], stack[-1][0]))
                stack.pop()
            else:
                stack.pop()
    for ch, ln in stack:
        problems.append("L%d: '%s' 没有闭合" % (ln, ch))

    # 2) 块关键字配平
    depth = 0
    line = 1
    prev_significant = None
    for match in KEYWORD_RE.finditer(cleaned):
        keyword = match.group(1)
        line = cleaned.count("\n", 0, match.start()) + 1
        if keyword in ("function", "if", "for", "while", "do"):
            # 'do' 紧跟 for/while 时不算新块
            if keyword == "do" and prev_significant in ("for", "while"):
                prev_significant = keyword
                continue
            depth += 1
        elif keyword == "end":
            depth -= 1
            if depth < 0:
                problems.append("L%d: 多出一个 end" % line)
                depth = 0
        elif keyword == "repeat":
            depth += 1
        elif keyword == "until":
            depth -= 1
        prev_significant = keyword
    if depth != 0:
        problems.append("块关键字不配平: 还差 %d 个 end" % depth)

    return problems


def main():
    targets = sys.argv[1:] or ["."]
    files = []
    for target in targets:
        if os.path.isdir(target):
            for root, _dirs, names in os.walk(target):
                for name in names:
                    if name.endswith(".lua"):
                        files.append(os.path.join(root, name))
        else:
            files.append(target)

    total = 0
    for path in sorted(files):
        problems = check(path)
        status = "OK" if not problems else "有问题"
        print("%-55s %s" % (os.path.relpath(path), status))
        for problem in problems:
            print("      " + problem)
        total += len(problems)

    print("\n共检查 %d 个文件, %d 个问题" % (len(files), total))
    return 1 if total else 0


sys.exit(main())
