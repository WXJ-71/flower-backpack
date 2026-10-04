# 鲜花背包（Flower Backpack）开发说明

饥荒联机版（Don't Starve Together）服务端 mod。核心玩法：**背在身上的背包能延缓食物腐烂**。

以原版「背包」为基础做成的**独立新物品**：外观 = 原版背包 + 右下角一朵鲜花印记，
不替换、不修改原版背包，和其他 mod 互不影响。

> **命名（改过一次，别再踩）**
>
> | | 值 | 说明 |
> | --- | --- | --- |
> | mod 显示名 | `Flower Backpack` / 中文「鲜花背包」 | 显示用，随便改 |
> | 预制体 / 配方 / 标签 / 容器 widget | `flowerpack` | **不能改**，存档标识 |
> | mod 目录名 | `hunger_mod` | **不能改**，`GetModConfigData` 与存档标识 |
> | 世界贴图 build | `swap_backpack_flower` | 见"外观"一节，为隔离而改名 |
>
> 最初中文名叫「保鲜背包」，后来查出**原版保温背包（`icepack` / Insulated Pack，
> 8 格、食物腐烂减半）的官方中文译名就是「保鲜背包」** —— 两个功能极像的背包同名，
> 玩家分不清，所以改成了「鲜花背包」。
> 校验脚本：`dev/check_name_collision.py`（拿整份 `chinese_s.po` 反查撞名）。

本机环境（已确认）：

| 项目 | 值 |
| --- | --- |
| 游戏安装目录 | `E:\app\steam\steamapps\common\Don't Starve Together` |
| 游戏版本 | `756039` |
| mod API 版本 | `10` |
| 开发目录 | `E:\ds h\hunger_mod`（本目录） |
| 游戏内 mod 目录 | `...\Don't Starve Together\mods\hunger_mod`（**junction → 本目录**） |
| 官方 Mod Tools | `E:\app\steam\steamapps\common\Don't Starve Mod Tools\mod_tools` |
| 客户端日志 | `C:\Users\wxj\Documents\Klei\DoNotStarveTogether\client_log.txt` |

junction 已建好：游戏 mods 目录下的 `hunger_mod` 直接指向本开发目录，
所以**改完文件不需要复制**，游戏里就能读到最新代码。

> 目录名 `hunger_mod` 是历史遗留（第一版叫"饥饿背包"）。**内部 ID 一律保持
> `flowerpack`，mod 目录名也仍是 `hunger_mod`** —— 它们是存档和 `GetModConfigData`
> 的标识，改了会导致旧存档里的物品失联、配置读取失败。显示名走
> `STRINGS.NAMES.FLOWERPACK`，与目录名无关。

---

## 目录结构

```
hunger_mod/
├── modinfo.lua                          # mod 元数据 + 设置项（PERISH_FACTOR）
├── modmain.lua                          # 入口：预制体/资源/容器 UI/图标注册/配方/本地化
├── modicon.tex / modicon.xml            # mod 列表图标（128x128，自绘，16402 字节）
├── dev_notes.md                         # 本文件
├── images/
│   └── flowerpack.tex / .xml            # 物品图标图集（64x64，原版图标 + 一朵花）
├── anim/
│   └── swap_backpack_flower.zip         # 背上 + 地面外观（原版图集 + 同款花）
├── scripts/
│   ├── flowerpack_config.lua            # 模组设置，供 modmain 与预制体共用
│   ├── languages/strings_{zh,zht}.po    # 简中 / 繁中 名称与描述（英文用代码里的默认值）
│   └── prefabs/flowerpack.lua           # 背包预制体本体
└── dev/                                 # 只放开发工具，游戏不会读取
    ├── ktex.py                          # KTEX + DXT5 编解码器（自写）
    ├── flower_art.py                    # 鲜花的唯一画法（三处外观共用）
    ├── build_item_icon.py               # 生成 images/flowerpack.tex/.xml
    ├── build_world_flower.py            # 生成加花后的 anim/ 贴图
    ├── build_world_build.py             # 改成独立 build 名并打包
    ├── check_item_icon.py / verify_codec.py      # 自检
    ├── lint_lua.py / fix_bom.py         # Lua 体检 / 清 BOM
    ├── parse_build.py / analyze_atlas.py / ...   # 图集与 build.bin 分析
    └── art/、*_unzip/、*_src/           # 中间产物（游戏不读）
```

> 本 mod 自带的贴图只有两份：`images/flowerpack.tex`（物品图标）与
> `anim/swap_backpack_flower.zip`（背上 + 地面外观），都是"原版像素 + 一朵同款花"。
> bank 与容器 UI 仍用游戏内置资源。

内部 ID 一律用 `flowerpack`（预制体名 / 配方名 / 容器 widget 名 / 图集注册名 /
物品标签），显示名走 `STRINGS.NAMES.FLOWERPACK`。

---

## "独立物品、不影响别人"是怎么保证的

这是本 mod 的硬要求，具体做法：

1. **不碰原版**：没有用 `AddPrefabPostInit("backpack", ...)`、没有改 `containers.params.backpack`、
   也没有改任何原版 `TUNING`。原版背包的行为完全不变。
2. **自己的 ID**：预制体 `flowerpack`、配方 `flowerpack`、容器布局
   `containers.params.flowerpack`、物品标签 `flowerpack`，
   全部带前缀，不会和原版或其他 mod 撞名。
3. **自己的容器 UI**：`containers.params.flowerpack` 是自己的一份参数
   （2 列 x 4 行 = 8 格，位置和原版一致），而不是复用 `params.backpack` 那个对象 ——
   复用的话一旦别的 mod 改了原版布局，我们也会跟着变。
4. **不碰角色的 AnimState 染色**：曾经用 `colouradder` 给本物品加色，现在整块删掉了
   （原因见"外观"一节）。现在只做一次 `OverrideSymbol("swap_body", ...)`，
   和原版背包完全一致，不会和其他 mod 的换装/皮肤系统互相干扰。
5. **保留原版标签**：仍然带 `backpack` 标签，所以熊獾偷吃、浣猫翻包这些原版行为照样认得它。
6. **图标只登记本 mod 专有名字**：`RegisterInventoryItemAtlas` 只往引擎的
   "名字 → 图集"表里加一条 `flowerpack.tex` 的记录，指向本 mod 自己那张图集，
   不修改、不占用任何原版条目（原版 `backpack.tex` 仍在原版图集里，不受影响）。

---

## 保鲜是怎么实现的（重要）

用的是原版自带的 **`preserver` 组件**，不是自己 hook `perishable`：

- `scripts/components/perishable.lua` 每次更新时会问 owner 要倍率：
  `owner.components.preserver:GetPerishRateMultiplier(item)`
- 背包装上 `preserver` 后，容器里的食物 owner 就是这只背包，倍率自然生效。
- `modinfo.lua` 的 `PERISH_FACTOR` 就是这个倍率：

| 取值 | 效果 |
| --- | --- |
| `1` | 和原版一样（等于关闭保鲜） |
| `0.6` / `0.35` / `0.15` / `0.05` | 腐烂速度降到 60% / 35%（默认）/ 15% / 5% |
| `0` | 完全不腐烂 |
| `-0.25` | 反向回鲜 |

原版同类物品的参考值（`tuning.lua`）：熊皮袋 `0.05`、鱼箱 `-1/3`、食物保鲜盒 `.75`。

**已知行为**：背包里的**容器**（例如把冰箱/背包叠在里面）自身带 `preserver`
时会再次相乘，导致嵌套后接近不腐烂。单只背包、正常使用不受影响。

---

## 外观：原版背包 + 一朵鲜花印记

**当前状态：三处外观都带一朵同款花，其余与原版一致。**

| 用途 | 资源 | 来源 |
| --- | --- | --- |
| bank（动画） | `anim/backpack.zip` | 游戏内置 |
| build（地面/背上外观） | `anim/swap_backpack_flower.zip` | **本 mod 自带**，原版图集 + 一朵花 |
| 容器 UI | `anim/ui_backpack_2x4.zip` | 游戏内置 |
| 物品图标 | `images/flowerpack.tex` / `.xml`（64x64） | **本 mod 自带**，原版图标像素 + 一朵同款花 |

世界里的外观只做 `SetBuild("swap_backpack_flower")` +
`OverrideSymbol("swap_body", "swap_backpack_flower", "swap_body")`。
冰背包、背包皮肤等仍在用原版 `swap_backpack`，**完全不受影响**。

### 鲜花印记是怎么做的（三条链路）

花的画法只有一份实现：**`dev/flower_art.py`**。三处共用它，所以外观统一。

**样式**（按需求定）：五片花瓣填充**绿色** `(74,168,62)`，外围一圈**红色粗描边**
`(200,24,24)`，花心略深的绿 `(44,122,40)` 以保留层次。
描边粗细 `radius * 0.16`（最少 1.4px），所以小图标与大贴图上看起来一样粗。

| 目标 | 做法 | 脚本 |
| --- | --- | --- |
| 物品图标（物品栏/容器格子/配方） | 抠出原版 `backpack.tex` 图标 → 在背包右下角画花 → 重新打包成 `images/flowerpack.tex` | `dev/build_item_icon.py` |
| 背上 + 地面 | 解码原版 `swap_backpack` 图集 → 在背包主体右下角画花 → 封回 | `dev/build_world_flower.py` |
| ↑ 打包成独立 build | 把 `build.bin` 里的构建名改成 `swap_backpack_flower`，zip 一起改名 | `dev/build_world_build.py` |

**花的位置是自动搜出来的**，贴在背包的**右下角**：背包在贴图上是梯形/圆角团块，
直接用包围盒右下角会把花瓣放到轮廓外（实测有 64% 的像素落在透明区）。两个脚本都用
同一套判据 —— 在右下角附近枚举位置，取"花瓣压在背包上 ≥ 93%"里最靠右下的那个
（允许一点点探出轮廓，这样才像"贴"在角上）。最终：

| | 背包包围盒 | 花心 | 半径 | 压在背包上 |
| --- | --- | --- | --- | --- |
| 世界贴图 256x256 | x[9,116] y[150,250] | (82,236) | 13 | 95.5% |
| 物品图标 64x64 | x[2,61] y[1,59] | (41,51) | 7.6 | 94.8% |

图标的花半径按**背包高度等比换算**（`13 × 59 / 101 ≈ 7.6`），保证两处观感一致。

**背上与地面是同一份数据**：`swap_backpack` / 我们这份 `swap_backpack_flower`
同时服务两种显示（地面物品与角色身上都是 `SetBuild` + `swap_body` 符号），
所以改一次图集两处一起变 —— 这也是唯一能保证两者"统一"的做法。

### ★ 为什么 build 要改名为 `swap_backpack_flower`

`swap_backpack` 不只背包在用：

- `scripts/prefabs/backpack.lua`：`SetBuild("swap_backpack")`，而**冰背包**
  `params.icepack = params.backpack` 复用同一个预制体；
- `scripts/prefabskin.lua`：所有背包皮肤以 `"swap_backpack"` 作为基准 build。

mod 里的 `anim/` 资源优先级**高于**游戏内置资源，所以如果直接交一份同名的
`anim/swap_backpack.zip`，上面这些统统会被改掉 —— **冰背包身上也会长出一朵花**。
改名 + 改 zip 文件名就干净隔离了：只有本物品用这份贴图。

`build.bin` 里只改了**构建名字段**（`@20` 的 4 字节长度 + 字符串，`swap_backpack`
→ `swap_backpack_flower`，文件 4069 → 4076 字节），几何数据 4036 字节**逐字节未变**，
符号名 `swap_body` 也没动。`dev/build_world_build.py` 会校验这几点。

### ★ 世界贴图的 KTEX 布局（这次才算彻底搞对）

```
swap_backpack/atlas-0.tex = 87506 字节
    基准级 256x256 BC3   = 65536
    其余 8 级 mip 之和    = 21872
    87506 - 65536 - 21872 = 98      <- 头部长度, 精确无余数
布局 = [98 字节头][基准级 65536][8 级小 mip 21872]
```

**判断依据是"总和刚好用尽"**，不是肉眼猜的：三个数相加精确等于文件大小，
这种吻合不可能是巧合。`dev/decode_world_atlas.py` 会把这个关系断言一遍。

> 走过的弯路：`ktex.parse_ktex` 用的是"头长 = 文件长 − 基准级"，对**只存基准级**的
> 文件恰好成立（因为像素数据在末尾），但这里有完整的 mip 链，于是取到了小 mip，
> 解出来是噪声 —— 一度被误判成"平台 swizzle 格式"（这个误判也是物品图标一直
> 手绘的原因）。正确姿势见上。

### 为什么改世界贴图是安全的

`dev/verify_codec.py` 验证：解码 → 重新编码 → **重新解码**，像素误差
平均 0.13、最大 29（纯属 BC3 端点取整的自由度，肉眼不可见）。所以"改几个像素
再封回去"不会破坏背包观感。`build_world_flower.py` 另外会断言：

- 新旧文件**字节数完全相同**（布局不许被改变）；
- 花以外区域的像素变化 = 0（未修改的地方不引入任何改动）。

### 需求变更记录（避免以后误加回来）

### ★ 物品图标：三个必须同时满足的条件

**症状**：物品在所有界面上都是空白 —— 物品栏那一格、放进背包/箱子后的
**容器格子**（东西其实在里面，只是画不出来）、建造菜单的配方图标。

**日志特征**（`client_log.txt`）：

```
WARNING! Could not find region 'flowerpack.tex' from atlas 'images/inventoryimages4.xml'.
WARNING! Could not find region 'flowerpack.tex' from atlas 'images/inventoryimages1.xml'.
```

**原因链**（`scripts/simutil.lua` + `scripts/widgets/itemtile.lua`）：

1. `InventoryItem:GetImage()` 返回 `<预制体名>.tex`，即 `flowerpack.tex`；
2. `InventoryItem:GetAtlas()` → `GetInventoryItemAtlas("flowerpack.tex")`
   查 mod 注册表（`RegisterInventoryItemAtlas` 填的那张表），命中就返回那张图集；
3. `ItemTile:SetImageFromItem` 接着执行
   `im:SetTexture(atlas, "flowerpack.tex")` —— **引擎还要拿这个名字去图集里找真实的区域**；
4. 区域不存在 → 渲染空白。

**结论文档化一下，避免再走弯路**：

| 只做到这一步 | 结果 |
| --- | --- |
| 什么都不做 | 引擎回退到动态图集 `inventoryimages4.xml`，报错（第一条日志） |
| 把 `flowerpack.tex` 注册到原版 `inventoryimages1.xml`，想借用里面的 `backpack.tex` | **不行**，注册表只决定"用哪张图集"，**不能给区域改名**，于是改报 `inventoryimages1.xml`（第二条日志） |
| 自己提供图集，区域名恰好叫 `flowerpack.tex` | ✅ 三个条件齐了 |

所以正确做法是**同时**满足：

```lua
-- 1) 资源: 贴图 + 图集都要声明
Asset("ATLAS", "images/flowerpack.xml"),
Asset("IMAGE", "images/flowerpack.tex"),

-- 2) 登记: 键 = 引擎要查的名字, 值 = 我们自己那张图集
RegisterInventoryItemAtlas("images/flowerpack.xml", "flowerpack.tex")
```

```xml
<!-- 3) 区域名必须**恰好**是 flowerpack.tex, 不能是别的名字 -->
<Atlas><Texture filename="flowerpack.tex" /><Elements>
<Element name="flowerpack.tex" u1="0.0078125" u2="0.9921875" v1="0.0078125" v2="0.9921875" />
</Elements></Atlas>
```

UV 四周留**半像素内缩**（64px 时 = 0.5/64 = 0.0078125，正好让首/末像素中心落在
区域正中），原版图集就是这么做的。生成脚本：`dev/build_item_icon.py`。

> 参考：创意工坊里成熟 mod 的做法与此完全一致（如 `1909182187`：
> `RegisterInventoryItemAtlas("images/immortal_fruit.xml", "immortal_fruit.tex")`
> ＋ 同目录下同名的 tex/xml 各 5566 字节 = 64x64 BC3）。

### ★★ 原版图集其实**能**解开（修正一条错误的历史结论）

以前这里写着"原版 `inventoryimages1.tex` 是平台 swizzle 格式，线性解码是错乱的，
所以抠不出原版图标像素，只能手画"。**这个结论是错的**，错在取数据的偏移。

真相（见 `dev/probe_atlas1_layout.py`）：

```
文件大小        5592560
BC3 首级        4194304   (2048x2048)
整条 mip 链     5592432   (2048 一路到 1x1 之和)
5592560 - 5592432 = 128   <- 头部长度
```

也就是说这张图的布局是 **128 字节头 + 整条 mip 链，首级在最前面**；
而旧的解码器假设"首级 mip 在文件**末尾**"（用 `文件长 − 首级大小` 反推头长），
于是把 1024x1024 的 mip 当成了首级来解 —— 解出来当然是噪声，于是被误判成 swizzle。

按 `raw[128 : 128 + 4194304]` 取，解出来就是一张**整整齐齐的图标网格**
（`dev/art/atlas1_tryA_start.png`），1024 个区域全部对得上。附带确认：

- 排布 = 32x32 个 64x64 格，行主序；
- XML 的 `v` 轴原点在**上**（`row = int(v1 * 2048) / 64`），不是下；
- `backpack.tex` 在 `col=3 row=25`，旁边依次是 `backpack_babybeef`、
  `backpack_basic_blue_catcoon` … 与 XML 顺序一致；
- `dev/art/vanilla_backpack_icon_64.png` 现在是真的原版图标。

> 教训：`ktex.py` 里"头长 = 文件长 − 首级 mip"这条经验是从**单级 mip** 的
> 产物（modicon / swap_backpack）总结出来的，遇到**带完整 mip 链**的原版图集就不成立。
> 判断布局要先用尺寸关系验证，不要靠"以前都这样"。

### 需求变更记录（避免以后误加回来）

这个物品的外观方案改过好几轮，每一轮的原因都值得记下来：

| 曾经的方案 | 为什么废弃 |
| --- | --- |
| 复用原版贴图 + `colouradder` 染色 | 染色没有像素选择能力，会连角色一起染 |
| 自制带鲜花印记的贴图 | 需求改成"与原版一致" |
| 装满变红 / 未满变绿（`SetMultColour` + `SetAddColour`） | **两个致命问题**：① 引擎的染色 API 都没有像素选择能力，做不到"只染花不染包"；② 地面物品会把**整张图集的几何**都铺出来（用户截图确认），染色会把整片染红，外观直接坏掉；③ 加法染色对纯白像素会削顶，其实根本显不出色 |
| 背上用缩小一半的自制贴图 | 需求改成"与原版一致"，两套贴图一并删除 |

所以现在的结论很简单：**贴图全部用原版，不做任何缩放、染色或加花**。

如果以后还想做状态指示（比如"装满了"），正确做法是给**容器 UI 加覆盖层贴图**
（两张固定的贴图，按状态显示其一），而不是给世界里的物品染色。

### 自制贴图工具链（保留但当前未使用）

为了"改原版贴图"这件事，本项目写过一套完整的工具，现在虽然不用了，但留着以备将来
（想加花、改色、缩放时可以直接复用）：`dev/ktex.py`（编解码器）、
`dev/build_flowerpack_art.py`（原版图集 → 加花/缩放 → 重新打包）、
`dev/build_icons.py`（手绘图标 PNG）、`dev/find_flower_slot.py`（搜索不重叠的加花位置）
等等。完整清单见下面「自制贴图工具链（dev/ 目录）」。

### 图标

- **mod 列表图标**：`modicon.tex` / `modicon.xml`（128x128），自绘。
  由 `dev/build_icons.py` 生成 PNG、`dev/compile_modicon.ps1` 调官方
  TextureConverter 编译；一键脚本是 `dev/build_modicon.ps1`。
- **物品图标**：`images/flowerpack.tex` / `.xml`（64x64），**像素抠自原版图集**的
  `backpack.tex` 那一格。生成脚本 `dev/build_item_icon.py`，
  自检脚本 `dev/check_item_icon.py`（校验尺寸/格式/区域名/UV）。
  这是本 mod 唯一自带的贴图。

## 一键重建资源

```powershell
# 只需第一次(或游戏更新后)跑: 准备原版资源(解包出 inventoryimages*.tex/xml 等)
powershell -NoProfile -ExecutionPolicy Bypass -File dev\prepare_vanilla.ps1

# 重建物品图标(从原版图集抠出背包图标, 重新打包成本 mod 的图集)
& 'E:\app\Blender\5.2\python\bin\python.exe' dev\build_item_icon.py
& 'E:\app\Blender\5.2\python\bin\python.exe' dev\check_item_icon.py

# 重建 mod 列表图标(含 BOM 清理与 Lua 体检)
powershell -NoProfile -ExecutionPolicy Bypass -File dev\build_modicon.ps1
```

> `dev/build_all.ps1` 是"自制贴图"时代的旧脚本，**已经停用**：它会重新生成
> 已经删掉的 `anim/swap_backpack.zip` 与旧物品图标，把 mod 弄回旧方案。
> 留着只为参考编解码/编译流程。

## 自制贴图工具链（dev/ 目录）

| 文件 | 作用 |
| --- | --- |
| `ktex.py` | **KTEX 容器 + BC3/DXT5 + ARGB 编解码器**（本项目自写，官方工具只能单向 PNG→tex） |
| `build_item_icon.py` | **原版图集 → 抠出 backpack.tex → 打包成 images/flowerpack.tex/.xml** |
| `check_item_icon.py` | 物品图标图集自检（尺寸/格式/区域名/UV 全查一遍） |
| `probe_atlas1_layout.py` | 判定原版图集的字节布局（头长 + 首级 mip 在哪） |
| `find_backpack_cell.py` | 把解开的图集按 64x64 铺开，定位某个图标在第几行第几列 |
| `extract_vanilla_icon_exact.py` | 直接按 XML 的 u/v 抠出指定图标（v 原点在上） |
| `build_icons.py` | 画 mod 图标 PNG（手绘；物品图标已改为抠原版像素） |
| `build_modicon.ps1` | 一键重建 mod 图标 + BOM 清理 + Lua 体检（**当前用这个**） |
| `prepare_vanilla.ps1` | 从游戏目录复制并解包原版资源 |
| `lint_lua.py` | Lua 语法 + BOM 体检（**别直接传 `.`**，见下节） |
| `fix_bom.py` | 清除文本文件的 BOM（PowerShell 会写出带 BOM 的文件） |
| `check_po.py` | 按 DST 的解析规则预演 `.po`，确认译文能被正确读出 |
| `analyze_atlas.py` / `dump_components.py` / `inspect_body.py` | 图集/构建分析工具 |
| `probe_ktex.py` | 编解码器自检（解码 + 往返误差 + 封回验证） |
| `build_flowerpack_art.py` / `compile_item_icon.ps1` / `build_all.ps1` | 旧方案（加鲜花贴图），**已停用** |
| `art/`、`*_unzip/` | 中间产物与预览图（游戏不读） |

### KTEX 格式（逐字节 dump 逆出来的）

```
偏移  长度  含义
0     4     magic "KTEX"
4     1     固定 0x20
5     1     像素格式: 低半字节 2 = BC3/DXT5, 0x42 = ARGB; 高半字节是平台标志
6     1     标志位: 0xFC = premultiply(swizzle 位); 官方产物用 0xF0
7     1     固定 0xFF
8     2     宽度 (uint16 小端)
10    2     高度 (uint16 小端)
12    2     每行字节 (uint16 小端) = 宽/4*16 (BC3)
18/128 N    压缩像素数据 —— **偏移不固定, 见下**
```

**头长不固定，而且首级 mip 不一定在末尾**，必须先用尺寸关系判定是哪种排布：

| 排布 | 判定方法 | 实例 |
| --- | --- | --- |
| 头 + **单级** mip | `文件长 − 首级大小` = 头长(18~20 是小值) | `modicon.tex`(18)、`swap_backpack`(20)；`ui_backpack_2x4` 头 20 + 后面还有 21KB 附加数据 |
| 头 + **整条 mip 链**, 首级在**前** | `文件长 − 整条mip链之和` = 头长 | 原版 `inventoryimages1.tex`：`5592560 − 5592432 = 128`，故首级在 `[128, 128+4194304)` |

> 这里踩过一次大坑：`ktex.py` 早期把"头长 = 文件长 − 首级 mip"当成了通用规律，
> 那是从**单级 mip** 的产物总结出来的。用到带完整 mip 链的原版图集上，
> 它会去文件**末尾**取"首级"，实际取到的是 1024x1024 的 mip，解出来是噪声，
> 于是被误判成"平台 swizzle 格式"。详见"★★ 原版图集其实能解开"一节。

DXT5 每 4x4 块 16 字节：`alpha0 alpha1 + 6 字节 3bit 索引 + c0 c1 (RGB565) + 4 字节 2bit 索引`。
自检结果：解码原版 256x256 图集 → 重新编码 → 再解码，**平均误差 0.14、最大 29**，
封回后的头部与官方产物一致；物品图标(64x64)往返平均误差 0.10、最大 18。

---

## 调试流程

1. **先看日志**：进游戏加载 mod 后打开
   `C:\Users\wxj\Documents\Klei\DoNotStarveTogether\client_log.txt`，
   搜索 `flowerpack`，应能看到：
   ```
   [flowerpack] 物品图标已注册 -> images/flowerpack.xml
   [flowerpack] 语言 = zh, 已加载 scripts/languages/strings_zh.po
   [flowerpack] 保鲜背包已加载, 食物腐烂倍率 = 0.35
   ```
   有 `MOD ERROR` / `LUA ERROR` 就是加载失败，按堆栈修。
   **另外要搜 `Could not find region`** —— 出现 `flowerpack.tex` 就是图标图集/区域名
   有问题（见"★ 物品图标：三个必须同时满足的条件"）。
2. **控制台拿背包**：游戏中按 `~` 打开控制台：
   ```lua
   c_give("flowerpack")
   ```
3. **确认配方**：科学机器旁应能在「模组」分类里看到「保鲜背包」
   （材料：4 草 + 4 树枝，和原版背包相同）。
4. **确认没影响原版**：`c_give("backpack")` 拿原版背包，对比两者外观与腐烂速度。
5. **改代码后**：mod 代码只在加载时执行，必须重进世界/重启服务器；
   改 mod 图标资源要重新跑编译脚本。

## 运行环境（最容易踩坑的地方，务必先读）

DST 里 **modmain 和预制体/被 require 的模块根本不在同一个环境里**，本项目三个致命 bug 全部源于这里。

### modmain.lua —— 沙箱表（由 `setfenv(fn, env)` 执行）

`scripts/mods.lua` 的 `CreateEnvironment` 造了一张**纯表**（**没有 `__index` 回退**，
已确认 mods.lua 里没有任何 `setmetatable`），只有这些全局可用：

| 来源 | 名字 |
| --- | --- |
| CreateEnvironment 白名单 | `pairs` `ipairs` `print` `math` `table` `type` `string` `tostring` `require` `Class` `TUNING` `GROUND` `WORLD_TILES` `LOCKS` `KEYS` `LEVELCATEGORY` `LEVELTYPE` `CHARACTERLIST` `GLOBAL` `modname` `MODROOT` `env` `modimport` |
| modutil 注入的 mod API | `Prefab` `Asset` `Ingredient` `AddRecipe2` `AddRecipe` `AddComponentAction` `GetModConfigData`（包装版） `RegisterInventoryItemAtlas` `AddPrefabPostInit` 等 |

**`TECH` / `STRINGS` / `LOC` / `KnownModIndex` / `Vector3` 都不在这张表里**
（它们是 `_G` 的全局），所以沙箱里必须写 `GLOBAL.TECH`。直接写 `TECH` 得到 nil，
再索引就会报 `attempt to index a nil value`。

完整全局表通过 `GLOBAL` 暴露（`env.GLOBAL = _G`），本项目的写法是：
```lua
local G = GLOBAL
...
G.TECH.SCIENCE_ONE
G.STRINGS.NAMES.FLOWERPACK = "..."
G.Vector3(...)
```

### 预制体 / 被 require 的模块 —— 真正的 `_G`

`LoadPrefabFile` 用的是 `loadfile`，`require` 也是标准实现，所以
`scripts/prefabs/*.lua` 和 `scripts/*.lua` 跑在**真正的全局环境**里：
`TECH`、`STRINGS`、`KnownModIndex`、`GetModConfigData`、`pcall` 全都在。
但 DST 开了 **strict 模式**（`scripts/strict.lua`），读**未声明**的全局名会
`error("variable 'X' is not declared")` —— 连 `if X ~= nil` 这种探测都不允许。

所以配置读取放在 `scripts/flowerpack_config.lua` 里是**对的**（它在 `_G` 里，
可以显式带 `modname` 调 `GetModConfigData`），而不是放在 modmain 里。

### 三个致命坑（按踩到的顺序）

1. **`GetModConfigData` 在 modmain 之外必须自带 modname**：
   modmain 里的是包装版（自动补 `env.modname`），`_G` 里的是原始版，
   第二个参数必填，缺了直接 assert：
   ```
   modutil.lua:35: modname must be supplied manually if calling GetModConfigData
   from outside of modmain or modworldgenmain.
   ```
   正确写法：`GetModConfigData("PERISH_FACTOR", "hunger_mod")`。
2. **沙箱里没有 `pcall`**：写 `pcall(...)` 报
   `attempt to call global 'pcall' (a nil value)`。要用 `GLOBAL.pcall`。
3. **strict 模式下不能探测未声明的全局名**：`if GLOBAL ~= nil` 会报
   `variable 'GLOBAL' is not declared`。安全写法是表索引 `GLOBAL.X`
   （`GLOBAL` 在白名单里，`GLOBAL.X` 是普通表索引，不会触发 strict 的 `__index`）。
4. **沙箱里还没有 `softresolvefilepath`**：`type(softresolvefilepath) == "function"`
   这一句不但永远是 false，而且因为白名单里没这个名字，它其实是 `nil` ——
   靠它做"文件是否存在"的判断 → 那段代码**永远不会执行**。
   本项目就因为这个 bug，语言文件从来没被加载过（详见"本地化"一节）。
   沙箱里能用的只有白名单 + `env`/`GLOBAL`，**别假设任何 `_G` 函数存在**。

前两个坑的错误都发生在 **modmain 加载期** → 整个 mod 加载失败 →
**旧世界进不去、新世界也生成不了**。第三个坑发生在被 require 的模块里，同样致命。
第四个坑不会报错，只会**静默失效** —— 这种最难查。

### 第五个坑：文件编码（BOM）

**`.lua` 和 `.xml` 必须是无 BOM 的 UTF-8。** DST 的 Lua 加载器不认字节顺序标记：

```
error loading module 'flowerpack_config' from file '...':
  unexpected symbol near '<EF BB BF>'
```

这个坑是**编辑器/命令造成的**，不是代码写错：PowerShell 的
`Set-Content -Encoding UTF8` 会写出**带 BOM** 的文件（PS 5.1 的行为）。
我在用 PowerShell 做字符串替换时就把配置文件写成了带 BOM 的版本。

- 改 Lua 文件请用能写无 BOM UTF-8 的编辑器/工具；
- 唯一的例外是 `dev/*.ps1`：那两个脚本**必须**带 BOM，
  否则 Windows PowerShell 5.1 会按 GBK 解析，中文提示全变乱码；
- `dev/lint_lua.py` 现在会检查 BOM，跑一次就能发现（见下节）。

### 由此得到的写法约定

- modmain 里：每个可能出错的**模块级**调用都包在 `RunStep(name, fn)` 里，
  最坏情况只是那项功能不生效并打一行日志，而不是拖垮整个世界。
- 取引擎全局一律走 `G.xxx`，不要裸写。
- 读一个可能不存在的名字前，先用 `type(...)` 或表索引，不要裸探测。

### 常见坑（其他）

- **排查错误只需要一个文件**：`1069397715\Cluster_N\Master\backup\server_log\` 下
  最新的日志。游戏内世界起不来时，服务端会把自己的启动日志写在这里，
  `MOD ERROR` + `LUA ERROR stack traceback` 会直接给出文件名和行号。
  注意主目录下的 `master_server_log.txt` 可能只是**上一次成功会话**的日志。
- **`AddRecipe2` 只有 4 个参数**：`(name, ingredients, tech, config)`。
  `config.image` 才是配方图标；多传第 5 个参数会被静默忽略，
  配方统一归入「模组」分类。
- **客户端也要装吗**：不需要。逻辑全在服务端（`preserver`、容器内容都由服务端同步），
  所以 `all_clients_require_mod = false`。但**房主/开服的人必须装**。
- **本地 mod 要手动启用**：游戏主菜单 → Mods → 勾选 Preserving Backpack。
- **改 `modinfo.lua` 的配置项**后，游戏内的旧配置会失效并回落到默认值，需要重新在
  Mods 设置里选一次。
- **`prefabs` 表 vs `PrefabFiles`**：`PrefabFiles`（modmain）只负责加载文件；
  `Prefab("flowerpack", fn, assets, prefabs)` 的第四个参数是"依赖的其他预制体"，
  这里列了 `ash`（烧毁时生成）。
- **改过 `modmain.lua` 后客户端要重启**：客户端在 `DoLuaFile scripts/main.lua`
  阶段加载 mod，游戏中途改文件不会生效；另注意日志里 mod 会被加载两遍
  （frontend 一次、进世界一次），这是正常的。

---

## 本地化（名字随游戏语言变化）

**机制**（`scripts/main.lua` + `scripts/translator.lua`）：

1. `main.lua` 在 `ModManager:LoadMods()` 之后会再调一次 `TranslateStringTable(STRINGS)`；
2. 它遍历 `STRINGS` 的每个字符串，用 `"STRINGS.NAMES.FLOWERPACK"` 这样的**完整路径**
   去查当前语言表，命中就**直接覆盖**那个字符串。

所以正确做法是：

- 在 modmain 里写一份**英文默认值**（`G.STRINGS.NAMES.FLOWERPACK = "..."`）；
- 用官方 API `LoadPOFile(path, code)` 给当前语言装一份 `.po`；
- `code` 用 `LOC.GetLocaleCode(LOC.GetLanguage())` 取，取值与
  `scripts/languages/loc.lua` 里的 `code` 一致：`zh` / `zht` / `zhr` / `en` / `ru` …

`.po` 必须是 **gettext 格式且带 `msgctxt`**（解析器按 `^msgctxt%s*"(%S*)"` 取 key，
空白行分隔条目），例如：

```
#: STRINGS.NAMES.FLOWERPACK
msgctxt "STRINGS.NAMES.FLOWERPACK"
msgstr "保鲜背包"
```

**踩过的坑**：原来用 `softresolvefilepath` 判断语言文件在不在，但那个函数
**不在 modmain 沙箱里**（见"第四个坑"），所以整段判断永远为假，语言文件从来没被加载 ——
不管什么语言都显示英文。现在改成直接调 `LoadPOFile`（用 `MODROOT` 拼路径，
相对路径再试一次），不依赖文件系统探测。

### 改完代码怎么自查（没有 Lua 解释器也能做）

```powershell
# 语法体检: 括号/块关键字配平(能拦住少一个 end、括号不配对这类致命错误)
# 注意别直接传 "." —— 会连 upload_tmp2 里的原版脚本一起扫, 慢且会碰到非 UTF-8 文件
& 'E:\app\Blender\5.2\python\bin\python.exe' dev\lint_lua.py `
    modmain.lua modinfo.lua scripts\prefabs\flowerpack.lua scripts\flowerpack_config.lua
```

它不是编译器，但比肉眼看强得多；真正的验证仍然要在游戏里跑。

### 离线自测（不依赖开游戏）

理想情况下可以先用独立服务端跑一遍只看日志，但**本机这条路没走通**：
独立服务端（`bin64\dontstarve_dedicated_server_nullrenderer_x64.exe`）在挂载
base game 的 `data/databundles` 阶段就失败（日志里 7 个 `Mounting file system ... skipped`），
`main.lua` 根本没加载。换 32/64 位、换工作目录、把 data 解包到旁边都无效，
属于启动参数/环境问题，与 mod 无关。所以**改完代码务必在游戏里实测**。

---

## 下一步可做（按价值排序）

1. **平衡调整**：确认默认 `0.35` 是否合适；配方要不要比原版背包贵一点
   （现在是草 x4 + 树枝 x4，和原版完全一样）。
2. **容量可调**：把槽位数量也做成 modinfo 配置项（`containers.params.flowerpack`
   已在 modmain 里集中定义，改起来只动一处）。
3. **防嵌套保鲜**：`SetPerishRateMultiplier` 支持传函数，可检测背包自身是否在容器里，
   避免倍率叠乘。
4. **状态指示**（如果还想要"装满了"之类的提示）：给**容器 UI 加覆盖层贴图**
   （两张固定贴图按状态显示其一），不要给世界里的物品染色 —— 详见"需求变更记录"。
5. **创意工坊发布**：`ModUploader.exe`（同在 Mod Tools 目录），发布前补
   `forumthread`、确认 `version`，并再评估 `priority = -1` 是否必要。
   **注意**：发布前建议把目录名从 `hunger_mod` 改成 `flowerpack` 之类的名字，
   更贴合 mod 内容（改目录名要一起重建 junction，见文件顶部说明）。
