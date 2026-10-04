"""写 git 提交信息文件(UTF-8 无 BOM), 供 git commit -F 使用。

为什么不用 PowerShell 写: PS 5.1 的 Set-Content -Encoding UTF8 会写 BOM,
git 会把 BOM 当成提交信息的一部分。
"""

import io
import os
import sys

MESSAGE = """初始提交: 鲜花背包 v0.6.1

饥荒联机版服务端 mod: 一只带鲜花印记的保鲜背包。

功能
- 以原版「背包」为基础的独立新物品, 不替换/不修改原版背包;
- 用官方 preserver 组件延缓食物腐烂, 倍率可在 mod 设置里调;
- 外观 = 原版背包 + 右下角一朵绿花红边的鲜花印记,
  物品栏 / 容器格子 / 背在身上 / 丢在地上四处一致。

实现要点
- 自写 KTEX + BC3(DXT5) 编解码器; 官方 Mod Tools 只能单向 PNG -> .tex,
  要"在原版贴图上加花"就必须自己解析;
- 破解原版贴图的容器格式: 变长的 mip 记录表 + 像素数据在文件末尾;
  早期误判成"平台 swizzle 解不开", 实际是取数据的偏移错了;
- 世界贴图 = 原版图集解码 -> 叠加花朵 -> 重新编码封回,
  build.bin 只改构建名, 几何数据 4036 字节逐字节未变;
- build 改名 swap_backpack_flower 做隔离: 原版那个 build 是多个物品共用的,
  直接交同名资源会连累它们;
- 物品图标自建 64x64 图集 + RegisterInventoryItemAtlas 映射
  (登记映射 / 图集里真有同名区域 / 资源声明, 三个条件缺一个就是空白)。

配套
- dev/ 贴图工具链与自检脚本, dev/probes/ 保留探索过程;
- dev_notes.md 记录全部踩坑、原理与工具用法;
- dev/package_release.py 打包发布 zip (版本号读自 modinfo.lua)。
"""

path = os.path.join(os.environ.get("TEMP", "."), "flowerpack_commit_msg.txt")
with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
    handle.write(MESSAGE)

raw = open(path, "rb").read()
print("写入 %s (%d 字节, BOM=%s)" % (path, len(raw), raw[:3] == b"\xef\xbb\xbf"))
