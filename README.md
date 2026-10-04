# 鲜花背包 / Flower Backpack

饥荒联机版（Don't Starve Together）服务端 mod。**一只带鲜花印记的保鲜背包**：把食物放进去，腐烂速度大幅降低。

以原版「背包」为基础做成的**独立新物品** —— 不替换、不修改原版背包，和其他 mod 互不影响。

> 名字说明：中文名刻意**不叫**「保鲜背包」。因为原版 *Insulated Pack*（`icepack`，中文官方译名就是「保鲜背包」）功能与它很像，同名会让玩家分不清。

---

## 安装

1. 下载本仓库（`Code` → `Download ZIP`），或者从 [Releases](../../releases) 下载打包好的 `flower-backpack-<版本>.zip`；
2. 解压后把整个文件夹放进：

   ```
   ...\Don't Starve Together\mods\
   ```

   最终路径应该长这样（`modinfo.lua` 直接在这个目录下）：

   ```
   ...\Don't Starve Together\mods\flower-backpack\modinfo.lua
   ```

3. 启动游戏 → 主菜单 `Mods` → 勾选 **Flower Backpack**；
4. **房主/开服的人必须装**，客机不需要（`all_clients_require_mod = false`，逻辑全在服务端）。

## 怎么造

| | |
| --- | --- |
| 科技 | 科学机器（一级） |
| 材料 | 草 ×4、树枝 ×4 |
| 位置 | 建造菜单的「**模组**」分类 |

## 有什么用

- 和原版背包一样：背在身体栏、8 个格子；
- **放进去的食物腐烂速度大幅降低**，倍率可在 mod 设置里调：

  | 选项 | 效果 |
  | --- | --- |
  | 关闭 | 和原版一样（1x） |
  | 轻微 | 0.6x |
  | 保鲜（默认） | 0.35x |
  | 强效 | 0.15x |
  | 接近永鲜 | 0.05x |
  | 完全不腐烂 | 0 |
  | 逆向回鲜 | -0.25x（越放越新鲜） |

- 保鲜用的是**官方 `preserver` 组件**，不是自己 hook `perishable`，所以和其他 mod 冲突概率极低。

## 外观

![物品栏图标](dev/art/flowerpack_icon_x6.png)

外观 = **原版背包 + 右下角一朵绿花红边的鲜花印记**，三处都有且位置一致：

| 位置 | 实现 |
| --- | --- |
| 物品栏 / 容器格子 / 配方图标 | `images/flowerpack.tex`（64×64，像素抠自原版图集） |
| 背在身上 | `anim/swap_backpack_flower.zip` |
| 丢在地上 | 同上（背和地面共用同一份 build，所以必然一致） |

那朵花是**直接画在原版贴图上的**（解码原版图集 → 叠加花朵 → 重新编码），
所以除了这朵花，背包本体与原版像素级一致。

---

## 开发者内容

### 目录结构

```
flower-backpack/
├── modinfo.lua                  # mod 元数据 + 设置项（PERISH_FACTOR）
├── modmain.lua                  # 入口：预制体/资源/图标注册/容器 UI/配方/本地化
├── modicon.tex / .xml           # mod 列表图标
├── images/flowerpack.tex/.xml   # 物品图标图集（64×64）
├── anim/swap_backpack_flower.zip# 背上 + 地面外观
├── scripts/
│   ├── flowerpack_config.lua    # 读 mod 设置
│   ├── languages/*.po           # 简中 / 繁中翻译
│   └── prefabs/flowerpack.lua   # 背包预制体本体
├── dev_notes.md                 # ★ 完整开发笔记（踩过的坑、原理、工具用法）
└── dev/                         # 开发工具（游戏不会读取）
```

**强烈建议先读 [`dev_notes.md`](dev_notes.md)** —— 里面记录了所有非显然的坑，包括 KTEX 贴图格式、
modmain 沙箱的全局白名单、物品图标必须注册的三个条件等。

### 重建贴图

```powershell
# 1. 从游戏目录解包原版资源（只需第一次 / 游戏更新后）
powershell -NoProfile -ExecutionPolicy Bypass -File dev\prepare_vanilla.ps1

# 2. 物品图标：抠原版 backpack.tex -> 加花 -> 打包
& 'E:\app\Blender\5.2\python\bin\python.exe' dev\build_item_icon.py
& 'E:\app\Blender\5.2\python\bin\python.exe' dev\check_item_icon.py      # 自检

# 3. 世界贴图：解码原版图集 -> 加花 -> 封回 -> 改成独立 build 名
& 'E:\app\Blender\5.2\python\bin\python.exe' dev\build_world_flower.py
& 'E:\app\Blender\5.2\python\bin\python.exe' dev\build_world_build.py

# 4. mod 列表图标（含 BOM 清理与 Lua 体检）
powershell -NoProfile -ExecutionPolicy Bypass -File dev\build_modicon.ps1
```

所有脚本只依赖 Python 标准库 + `numpy`（不需要 PIL）。

### 自检脚本

```powershell
$py = 'E:\app\Blender\5.2\python\bin\python.exe'
& $py dev\lint_lua.py modmain.lua modinfo.lua scripts\prefabs\flowerpack.lua scripts\flowerpack_config.lua
& $py dev\check_item_icon.py          # 图标图集：尺寸/格式/区域名/UV
& $py dev\build_world_build.py --verify-only   # 世界 build：构建名/几何一致性/贴图
& $py dev\check_po.py                 # 翻译文件能否被游戏正确解析
& $py dev\check_name_collision.py     # 显示名有没有和原版撞名
& $py dev\verify_codec.py             # BC3 编解码器保真度
```

### 值得一提的技术点

- **自己写了 KTEX / BC3(DXT5) 编解码器**（`dev/ktex.py`）。官方 Mod Tools 只能单向 PNG → `.tex`，
  没有任何工具能把原版贴图反解成图片；要「在原版背包上加一朵花」就必须自己解析。
- **破解了原版贴图的容器格式**。KTEX 头部是一张变长的 mip 记录表，像素数据在最后；
  早期误以为「头长 = 文件长 − 基准级」，在带完整 mip 链的图集上会取错数据、解出噪声 ——
  这个误判曾让项目以为原版图集「加密/平台 swizzle，解不开」，转而手绘图标。
  正确的判定方式见 `dev_notes.md`。
- **`build.bin` 只改构建名，几何数据逐字节不动**。因为原版 `swap_backpack` 这个 build
  是多个物品共用的，直接交一份同名资源会连累它们；改名做隔离，并由脚本断言几何未变。
- **物品图标必须同时满足三个条件**（登记映射 / 图集里真的有同名区域 / 资源要声明），
  缺一个物品在界面上就是空白 —— 详见 `dev_notes.md`。

### 内部 ID 约定

| | 值 | 能不能改 |
| --- | --- | --- |
| mod 显示名 | `Flower Backpack` / 鲜花背包 | 随便改 |
| 预制体 / 配方 / 标签 / 容器 widget | `flowerpack` | **不能**（存档标识） |
| mod 目录名 | 仓库名 `flower-backpack` | 发布前可改，改后旧存档会失联 |

---

## 许可 / 致谢

- 本 mod 的代码与自制贴图可自由使用、修改、再分发。
- 外观基于 Klei 的原版美术资源（背包贴图与图标）二次修改；饥荒（Don't Starve）及其美术资源
  版权归 **Klei Entertainment** 所有。本仓库仅为 mod 开发用途，不包含游戏本体。
- `dev/` 下的原版资源解包产物仅用于开发，未随仓库分发（见 `.gitignore`）。
