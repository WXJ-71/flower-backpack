-- 保鲜背包 / Preserving Backpack -- modmain.lua
-- 注册预制体、资源、物品图标、容器 UI、配方与本地化。
--
-- 设计原则: 这是一个**独立的新物品**, 外观与原版背包完全一致。
--   - 不覆盖任何原版预制体, 不用 AddPrefabPostInit 去改原版背包;
--   - 所有内部 ID 都带 flowerpack 前缀(预制体/配方/容器 widget),
--     不会和原版或其他 mod 撞名;
--   - 容器 UI 用自己的一份参数, 不复用原版 "backpack" 那份;
--   - 贴图直接用游戏自带的原版资源, 本 mod 不含任何自定义贴图。

--[[==========================================================================
    ★ 运行环境说明(本项目踩过四个坑, 全在这一段)
    modmain.lua 由 setfenv(fn, env) 在**沙箱表**里执行(scripts/mods.lua),
    这个沙箱表没有 __index 回退, 里面的全局只有:
      · CreateEnvironment 白名单:
          pairs ipairs print math table type string tostring require Class
          TUNING CHARACTERLIST GROUND WORLD_TILES LOCKS KEYS LEVELCATEGORY LEVELTYPE
          GLOBAL modname MODROOT env modimport
      · modutil.InsertPostInitFunctions 注入的 mod API:
          Prefab Asset Ingredient AddRecipe2 AddRecipe AddComponentAction
          GetModConfigData(包装版, 自动补 modname) RegisterInventoryItemAtlas
          LoadPOFile 等等
    注意 **TECH / STRINGS / LOC / KnownModIndex / Vector3 都不在沙箱里**,
    它们是 _G 的全局。所以在沙箱里必须写 GLOBAL.TECH, 直接写 TECH 会得到 nil
    (索引 nil 会报 attempt to index a nil value)。
    完整全局表通过 GLOBAL 暴露: env.GLOBAL = _G。

    坑 1: 在 modmain 之外调用 GetModConfigData 必须自带 modname, 否则 assert。
    坑 2: 沙箱里没有 pcall, 要用 GLOBAL.pcall。
    坑 3: 读一个不存在的全局名会被 strict 模式报 "variable 'X' is not declared"
          —— 所以连 `if X ~= nil` 探测都不行。安全写法是表索引: GLOBAL.X。
          同理 softresolvefilepath 也**不在沙箱里**, 用它做"文件是否存在"的
          判断会直接报 attempt to call a nil value(见下面"本地化"一节)。
    坑 4: 物品图标必须注册! 见下面"物品图标"一节, 这是"格子显示为空"的元凶。

    另外: 预制体(scripts/prefabs/*.lua)和被 require 的模块走 loadfile,
    跑在**真正的 _G** 里, 那里 TECH/STRINGS 等本来就在, 但也受 strict 约束。
==========================================================================]]--

local G = GLOBAL

--[[--------------------------------------------------------------------------
    0. 错误隔离
    沙箱里没有 pcall, 必须走 GLOBAL.pcall。目的是把每个可能失败的模块级调用
    隔离开: 最坏情况只是该项功能不生效并打一行日志, 而不是整个 mod 加载失败
    (modmain 里任何一处抛错都会导致 mod 加载失败 -> 世界打不开)。
    注意: 图标注册那一项**不能**静默失败, 所以另外补了一次校验(见下)。
--------------------------------------------------------------------------]]--

local function SafeCall(fn)
    if type(G.pcall) == "function" then
        return G.pcall(fn)
    end
    return true, fn()
end

local function RunStep(name, fn)
    local ok, reason = SafeCall(fn)
    if not ok then
        print("[flowerpack] " .. name .. " 失败: " .. tostring(reason))
    end
    return ok
end

--[[--------------------------------------------------------------------------
    1. 预制体
--------------------------------------------------------------------------]]--

PrefabFiles = {
    "flowerpack",
}

--[[--------------------------------------------------------------------------
    2. 资源
    背包本体(bank / 容器 UI)用游戏内置的原版资源:
        anim/backpack.zip         (bank)
        anim/ui_backpack_2x4.zip  (容器 UI)
    而"背上 + 地面"共用的那套外观本 mod **自己带一份**, 只加了一朵花:
        anim/swap_backpack_flower.zip   (build 名 = swap_backpack_flower)
    贴图是把原版图集解码后在背包正面右下角重画了一朵花; 几何数据(build.bin 里
    除构建名之外的部分)与原版**逐字节相同**, 所以除了那朵花外观与原版一致。

    ★ 为什么 build 名不叫 swap_backpack:
      原版那个 build 不只背包在用 —— 冰背包(icepack 复用背包预制体)、
      prefabskin.lua 的背包皮肤都以 "swap_backpack" 为基准。mod 资源优先级高于
      游戏内置资源, 如果直接交一份同名的 anim/swap_backpack.zip,
      冰背包身上也会长出一朵花。所以这里改了构建名与文件名做隔离。

    物品图标 images/flowerpack.tex/.xml 同样是"原版像素 + 一朵同款花"。
--------------------------------------------------------------------------]]--

Assets = {
    Asset("ANIM", "anim/backpack.zip"),
    Asset("ANIM", "anim/swap_backpack_flower.zip"),
    Asset("ANIM", "anim/ui_backpack_2x4.zip"),

    -- 物品图标: 唯一的自定义贴图, 内容就是原版背包图标(见第 3 节)
    Asset("ATLAS", "images/flowerpack.xml"),
    Asset("IMAGE", "images/flowerpack.tex"),
}

--[[--------------------------------------------------------------------------
    3. 物品图标 —— ★ 这一节是"物品图标显示为空白"的修复

    【症状】物品在所有界面上都是空白: 物品栏那一格、**容器格子**(东西放进去后
    格子看着像空的)、建造菜单的配方图标。
    【日志】WARNING! Could not find region 'flowerpack.tex' from atlas '...'

    【引擎的查找顺序】(scripts/simutil.lua + widgets/itemtile.lua)
        InventoryItem:GetImage()   -> "<预制体名>.tex" 即 "flowerpack.tex"
        InventoryItem:GetAtlas()   -> GetInventoryItemAtlas(GetImage())
          GetInventoryItemAtlas 先查 mod 注册表(RegisterInventoryItemAtlas),
          命中就直接返回那张图集 —— **但这只决定"用哪张图集"**,
          之后引擎仍然要拿 "flowerpack.tex" 这个名字去图集里找**真实的区域**。
          区域不存在 -> 渲染空白。

    【踩过的两个错】
      1. 什么都不注册 -> 引擎回退到动态图集 images/inventoryimages4.xml 找, 报
         "Could not find region 'flowerpack.tex' from atlas 'images/inventoryimages4.xml'"。
      2. 只把 flowerpack.tex 注册到原版图集 images/inventoryimages1.xml,
         想让引擎借用里面的 backpack.tex 区域 —— 不行! 区域名必须真实存在,
         于是改报 "... from atlas 'images/inventoryimages1.xml'"。
         注册表**不能**给区域改名。

    【正解】自己提供一张 64x64 的图标图集, 区域名恰好叫 flowerpack.tex:
        images/flowerpack.tex  <- 像素直接来自原版图集里 backpack.tex 那一格
        images/flowerpack.xml  <- <Element name="flowerpack.tex" .../>
      图标与原版背包**像素级一致**(不是手画的相似品)。
      生成脚本: dev/build_item_icon.py

    参考: 创意工坊里成熟 mod 的做法与此完全一致
    (例如 1909182187 的 RegisterInventoryItemAtlas("images/immortal_fruit.xml",
    "immortal_fruit.tex") + 同目录下的同名 tex/xml)。
--------------------------------------------------------------------------]]--

local FLOWERPACK_ICON_ATLAS = "images/flowerpack.xml"

local function RegisterItemIcon()
    if type(RegisterInventoryItemAtlas) ~= "function" then
        return false, "RegisterInventoryItemAtlas 不可用"
    end

    -- 键就是引擎要查的名字: <预制体名>.tex
    RegisterInventoryItemAtlas(FLOWERPACK_ICON_ATLAS, "flowerpack.tex")
    -- 裸预制体名也登记一份, 防止别处用不带后缀的名字来查
    RegisterInventoryItemAtlas(FLOWERPACK_ICON_ATLAS, "flowerpack")
    return true
end

RunStep("物品图标注册", RegisterItemIcon)

-- 图标缺失会让物品在所有界面上变成空白, 属于必须吼出来的问题。
if G.GetInventoryItemAtlas ~= nil then
    local atlas = G.GetInventoryItemAtlas("flowerpack.tex")
    if atlas == nil then
        print("[flowerpack] 警告: 物品图标未注册成功, 游戏里物品会显示为空白!")
    else
        print(string.format("[flowerpack] 物品图标已注册 -> %s", tostring(atlas)))
    end
end

--[[--------------------------------------------------------------------------
    4. 容器 UI
    用自己的一份参数注册 "flowerpack" 布局, 而不是复用原版 "backpack" 那份,
    这样以后调整槽位数量/位置时不会影响原版参数和其他 mod。
    2 列 x 4 行 = 8 格, 位置与原版背包一致。
--------------------------------------------------------------------------]]--

local SLOT_COUNT = 8
local SLOT_COLUMNS = 2

local function SetupContainerWidget()
    local containers = require("containers")
    if containers == nil or containers.params == nil then
        return false, "containers.params 不可用"
    end

    local slotpos = {}
    for index = 0, SLOT_COUNT - 1 do
        local column = index % SLOT_COLUMNS
        local row = math.floor(index / SLOT_COLUMNS)
        -- 起始点 (-162, 114) 取自原版背包布局, 每格间距 75
        table.insert(slotpos, G.Vector3(-162 + column * 75, -75 * row + 114, 0))
    end

    containers.params.flowerpack =
    {
        widget =
        {
            slotpos = slotpos,
            numslots = SLOT_COUNT,
            animbank = "ui_backpack_2x4",
            animbuild = "ui_backpack_2x4",
            pos = G.Vector3(-5, -80, 0),
        },
        issidewidget = true,
        type = "pack",
        openlimit = 1,
    }

    return true
end

RunStep("容器 UI 注册", SetupContainerWidget)

--[[--------------------------------------------------------------------------
    5. 配方
    科技等级与材料都跟原版背包一致(科学机器一级: 草 x4 + 树枝 x4),
    配方图标直接用原版背包的图标(物品图标也是原版的, 见第 3 节)。
    配方会自动归入"模组"分类(见 modutil.lua 里 env.AddRecipe2 的实现)。
--------------------------------------------------------------------------]]--

RunStep("配方注册", function()
    AddRecipe2(
        "flowerpack",
        {
            Ingredient("cutgrass", 4),
            Ingredient("twigs", 4),
        },
        G.TECH.SCIENCE_ONE
    )
end)

--[[--------------------------------------------------------------------------
    6. 本地化(名字/描述随游戏内语言变化)

    机制(scripts/translator.lua + scripts/main.lua):
      1. main.lua 在 ModManager:LoadMods() 之后会调用
         TranslateStringTable(STRINGS) 再刷一遍全表;
      2. 它会遍历 STRINGS 的每一个字符串, 用 "STRINGS.NAMES.FLOWERPACK"
         这样的完整路径去查当前语言表, 命中就**覆盖**该字符串。
    所以只要给当前语言装一份 .po 就行, 英文写在这里当默认值:
       - 中文玩家  -> 加载 strings_zh.po  -> "保鲜背包"
       - 繁体玩家  -> 加载 strings_zht.po -> "保鮮背包"
       - 其他语言  -> 不加载           -> 保持下面的英文

    ★ 这里曾经有个 bug: 用 softresolvefilepath 判断语言文件是否存在。
      它**不在 modmain 沙箱里**(沙箱白名单见文件开头), 所以那行永远不执行,
      语言文件从来没被加载过 -> 不管什么语言都只显示英文。
      LoadPOFile 是官方 API(modutil 注入), 不依赖文件系统探测, 才可靠。

    语言代码由 LOC.GetLocaleCode 给出, 与 scripts/languages/loc.lua 里的
    code 一致: zh=简中, zht=繁中, en=英文, ru=俄文 ... 没有对应文件就退回英文。
--------------------------------------------------------------------------]]--

-- 默认英文(也是其他语言玩家看到的兜底)
-- 名字刻意用 Flower Backpack / 鲜花背包: 原版保温背包(icepack, Insulated Pack)
-- 的官方中文名就是"保鲜背包", 用同名会让玩家分不清两个功能相近的背包。
G.STRINGS.NAMES.FLOWERPACK = "Flower Backpack"
G.STRINGS.RECIPE_DESC.FLOWERPACK = "A flower on the flap. Keeps food fresh inside."
G.STRINGS.CHARACTERS.GENERIC.DESCRIBE.FLOWERPACK = "Same as a Backpack, but the food inside lasts longer."

local function LocalizeStrings()
    if type(LoadPOFile) ~= "function" then
        return false, "LoadPOFile 不可用"
    end

    local lang_id = (G.LOC ~= nil and G.LOC.GetLanguage ~= nil) and G.LOC.GetLanguage() or nil
    local locale_code = (G.LOC ~= nil and G.LOC.GetLocaleCode ~= nil)
        and G.LOC.GetLocaleCode(lang_id)
        or "en"

    if locale_code == "en" then
        -- 英文就是上面写死的默认值, 不用再装一份
        return true
    end

    -- 本 mod 只维护简体/繁体两份翻译, 英文就是上面写死的默认值。
    -- zhr(简中铁路版)的文字与 zh 相同, 直接复用那份。
    -- 没有对应文件时 LoadPOFile 只会打一行 "not found" 并把空表登记进去,
    -- 不会报错, 也**不会**覆盖已有的英文, 所以可以放心尝试。
    local pofile_for_code =
    {
        zh = "strings_zh.po",
        zhr = "strings_zh.po",
        zht = "strings_zht.po",
    }

    local pofile = pofile_for_code[locale_code]
    if pofile == nil then
        print(string.format("[flowerpack] 语言 = %s, 无对应翻译, 使用英文", tostring(locale_code)))
        return true
    end

    -- MODROOT 是沙箱白名单里的变量(形如 "../mods/hunger_mod/"), 用它能拼出
    -- 引擎一定找得到的路径; 相对路径也试一次作为兼容(modimport 那类接口就是
    -- 这么被别的 mod 用来读自己目录里的文件的)。
    local fullpath = "scripts/languages/" .. pofile
    SafeCall(function() LoadPOFile(MODROOT .. fullpath, locale_code) end)
    SafeCall(function() LoadPOFile(fullpath, locale_code) end)
    print(string.format("[flowerpack] 语言 = %s, 已加载 %s", tostring(locale_code), fullpath))
    return true
end

RunStep("本地化", LocalizeStrings)

-- 启动时打一行日志, 方便在 client_log.txt / server_log.txt 里确认 mod 生效
local FlowerPackConfig = require("flowerpack_config")
print(string.format("[flowerpack] 保鲜背包已加载, 食物腐烂倍率 = %s", tostring(FlowerPackConfig.GetPerishFactor())))
