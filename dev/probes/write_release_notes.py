"""写 GitHub Release 说明文件(UTF-8 无 BOM), 供 gh release create -F 使用。"""

import io
import os

NOTES = """## 鲜花背包 v0.6.1

饥荒联机版服务端 mod：一只带鲜花印记的保鲜背包。

### 安装

1. 下载下面的 `flower-backpack-0.6.1.zip`；
2. 解压后把 `flower-backpack` 整个文件夹放进
   `...\\Don't Starve Together\\mods\\`
   （最终应存在 `...\\mods\\flower-backpack\\modinfo.lua`）；
3. 启动游戏 → `Mods` → 勾选 **Flower Backpack**；
4. **房主/开服的人必须装**，客机不需要。

### 内容

| | |
| --- | --- |
| 科技 | 科学机器（一级） |
| 材料 | 草 ×4、树枝 ×4 |
| 位置 | 建造菜单「模组」分类 |
| 容量 | 8 格（与原版背包一致） |
| 保鲜 | 默认 0.35x 腐烂速度，可在 mod 设置里调（含"完全不腐烂"与"逆向回鲜"） |

外观 = **原版背包 + 右下角一朵绿花红边的鲜花印记**，物品栏、容器格子、背在身上、
丢在地上四处一致。

### 本版要点

- 新增鲜花印记，三处外观统一；
- mod 显示名由「保鲜背包」改为「**鲜花背包**」—— 原版 *Insulated Pack*
  （`icepack`）的官方中文译名正是「保鲜背包」，两个功能相近的背包同名会让玩家分不清；
- 世界贴图改用独立 build 名 `swap_backpack_flower` 做隔离，
  不影响任何共用原版 `swap_backpack` 的物品。

### 说明

这是一个**独立的新物品**：不替换、不修改原版背包，和其他 mod 互不影响。
保鲜用的是官方 `preserver` 组件，不是自己 hook `perishable`。

完整开发笔记（含贴图格式、踩坑记录、工具链用法）见仓库里的 `dev_notes.md`。
"""

path = os.path.join(os.environ.get("TEMP", "."), "flowerpack_release_notes.md")
with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
    handle.write(NOTES)

raw = open(path, "rb").read()
print("写入 %s (%d 字节, BOM=%s)" % (path, len(raw), raw[:3] == b"\xef\xbb\xbf"))
