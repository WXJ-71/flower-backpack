"""把 mod 打包成可以直接丢进 mods\\ 目录的 zip。

产出: dist/flower-backpack-<版本>.zip

zip 内部结构(单层同名文件夹, 和创意工坊下载的 mod 一样):
    flower-backpack/
        modinfo.lua
        modmain.lua
        scripts/...
        images/...
        anim/...
        modicon.tex / .xml

排除: dev/、dev_notes.md、.git、.gitignore —— 这些是开发资料, 玩家不需要,
      而且 dev/art 里有较大的预览图。

版本号从 modinfo.lua 里读, 保证 zip 名和 mod 内声明的版本永远一致。

用法: python dev/package_release.py
"""

import os
import re
import shutil
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
MOD_ROOT = os.path.dirname(HERE)
DIST = os.path.join(MOD_ROOT, "dist")

# zip 里的顶层文件夹名(mod 名)
PACKAGE_NAME = "flower-backpack"

# 发布时**排除**的顶层条目
EXCLUDE_TOP = {"dev", "dev_notes.md", ".git", ".gitignore", "dist", ".github"}


def read_version():
    text = open(os.path.join(MOD_ROOT, "modinfo.lua"), encoding="utf-8").read()
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    if not match:
        raise SystemExit("modinfo.lua 里找不到 version")
    return match.group(1)


def collect_files():
    """返回 [(相对路径, 绝对路径), ...], 只收发布需要的文件。"""
    files = []
    for root, dirs, names in os.walk(MOD_ROOT):
        # 原地过滤目录, 避免走进不该去的地方
        dirs[:] = [d for d in dirs
                   if d not in EXCLUDE_TOP and d != "__pycache__" and not d.startswith(".")]
        for name in names:
            if name.endswith((".pyc", ".pyo")):
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, MOD_ROOT).replace("\\", "/")
            if rel.split("/")[0] in EXCLUDE_TOP:
                continue
            files.append((rel, full))
    return sorted(files)


def main():
    version = read_version()
    files = collect_files()
    if not files:
        raise SystemExit("没有收集到任何文件")

    os.makedirs(DIST, exist_ok=True)
    out_path = os.path.join(DIST, "flower-backpack-%s.zip" % version)

    total = 0
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for rel, full in files:
            arcname = "%s/%s" % (PACKAGE_NAME, rel)
            archive.write(full, arcname)
            total += os.path.getsize(full)

    print("版本号(读自 modinfo.lua): %s" % version)
    print("打包 %d 个文件, 原始大小 %.1f KB" % (len(files), total / 1024.0))
    print("产物: %s (%.1f KB)" % (out_path, os.path.getsize(out_path) / 1024.0))

    print("\n清单:")
    for rel, full in files:
        print("  %-42s %7d" % (rel, os.path.getsize(full)))

    # 自检: zip 里必须有 modinfo.lua, 且版本号对得上
    with zipfile.ZipFile(out_path) as archive:
        names = archive.namelist()
        required = "%s/modinfo.lua" % PACKAGE_NAME
        if required not in names:
            raise SystemExit("zip 里缺少 %s" % required)
        text = archive.read(required).decode("utf-8")
        if ('version = "%s"' % version) not in text:
            raise SystemExit("zip 里的版本号与文件名不一致")
        bad = [n for n in names if "/dev/" in n or n.endswith("dev_notes.md")]
        if bad:
            raise SystemExit("zip 里混进了开发文件: %s" % bad[:3])
    print("\n自检通过: modinfo.lua 就位, 版本号一致, 无开发文件混入。")
    return out_path


if __name__ == "__main__":
    main()
