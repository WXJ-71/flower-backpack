"""清掉文本文件的 UTF-8 BOM(以及把 CRLF 统一成 LF, 便于跨工具处理)。

为什么需要: PowerShell 的 Set-Content -Encoding UTF8 会写出带 BOM 的文件,
而 DST 的 Lua 加载器不认 BOM(会报 unexpected symbol near '<EF BB BF>')。
本项目的 .lua / .xml / .py 都要求无 BOM。
唯一的例外是 dev/*.ps1 —— 那两个必须带 BOM, 否则 PowerShell 5.1 会按 GBK 解析。

用法:
    python fix_bom.py <目录>            # 递归清理 .lua/.xml/.py(跳过 dev/*.ps1)
    python fix_bom.py <目录> --check    # 只报告不修改
"""

import os
import sys

TEXT_EXTENSIONS = (".lua", ".xml", ".py", ".md", ".txt", ".json")
KEEP_BOM = (".ps1",)   # PowerShell 脚本需要 BOM


def should_process(path):
    if path.endswith(KEEP_BOM):
        return False
    return path.endswith(TEXT_EXTENSIONS)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    target = sys.argv[1]
    check_only = "--check" in sys.argv
    fixed = []
    kept = []

    paths = []
    if os.path.isfile(target):
        paths.append(target)
    else:
        for root, _dirs, names in os.walk(target):
            for name in names:
                paths.append(os.path.join(root, name))

    for path in sorted(paths):
        if not should_process(path):
            continue
        with open(path, "rb") as handle:
            raw = handle.read()
        if not raw.startswith(b"\xef\xbb\xbf"):
            continue
        if check_only:
            fixed.append(path)
            continue
        with open(path, "wb") as handle:
            handle.write(raw[3:])
        fixed.append(path)

    for path in fixed:
        print("%s %s" % ("需要去 BOM:" if check_only else "已去 BOM:", path))
    for path in kept:
        print("保留 BOM:", path)
    print("\n%s: %d 个文件" % ("待处理" if check_only else "已处理", len(fixed)))
    return 0


sys.exit(main())
