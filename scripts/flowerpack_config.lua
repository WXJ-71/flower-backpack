-- 鲜花背包 / Flower Backpack -- 模组设置
--
-- 这个文件被 modmain.lua 和预制体(scripts/prefabs/flowerpack.lua)共同 require。
--
-- 【运行环境】(这一点很容易搞错, 是本项目踩坑的根源)
--   - modmain.lua 跑在 mod 沙箱里: 只有 scripts/mods.lua 白名单里的全局,
--     完整全局表在 GLOBAL 上。沙箱表**没有** __index 回退, 所以沙箱里读不到
--     TECH / STRINGS / modinfo 这些引擎全局。
--   - 而被 require 的模块(modmain 里 require、预制体里 require)走的是标准
--     loadfile, 跑在**真正的全局环境 _G** 里: 引擎全局都在, 但 DST 开了 strict
--     模式(scripts/strict.lua), 读**未声明**的全局名会 error 而不是返回 nil。
--   本文件因此遵循两条规则: 只用 _G 里确实存在的名字; 不写 `if X ~= nil` 这种
--   对可能存在、也可能不存在的名字做探测的代码。
--
-- 【为什么可以在这里读配置】
-- GetModConfigData 的正确签名是 (optionname, modname, get_local_config),
-- 其中 modname 是**必填**的。modmain 里那个包装版本(env.GetModConfigData)会自动
-- 补上 modname, 而裸函数不会 —— 缺了就直接 assert:
--     modname must be supplied manually if calling GetModConfigData from
--     outside of modmain or modworldgenmain.
-- 所以这里显式传入 mod 目录名, 就和在 modmain 里读等价了。
-- 用 mod 目录名而不是 modinfo 里的显示名, 改显示名也不会失效。
--
-- 【文件编码】必须是无 BOM 的 UTF-8!
-- DST 的 Lua 加载器不认字节顺序标记, 有 BOM 会报:
--     error loading module 'xxx': unexpected symbol near '<EF BB BF>'
-- 用 PowerShell 的 Set-Content -Encoding UTF8 会写出带 BOM 的文件, 别用它改
-- Lua 文件。

local MOD_NAME = "hunger_mod"

local FlowerPackConfig = {}

-- 读取玩家实际选择的保鲜倍率。
-- 三道防线: 显式 modname 读设置 -> modinfo 里的 default -> 写死的兜底值。
-- 保证任何情况下都返回一个数字, 不会把 nil 当倍率用。
local function ResolvePerishFactor()
    local value = GetModConfigData("PERISH_FACTOR", MOD_NAME)
    if type(value) == "number" then
        return value
    end

    local ok, info = pcall(KnownModIndex.GetModInfo, KnownModIndex, MOD_NAME)
    if ok and type(info) == "table" and type(info.configuration_options) == "table" then
        for _, option in ipairs(info.configuration_options) do
            if option.name == "PERISH_FACTOR" and type(option.default) == "number" then
                return option.default
            end
        end
    end

    return 0.35
end

local PERISH_FACTOR = ResolvePerishFactor()

-- 背包内食物的腐烂速度倍率:
--   1     -> 和原版一样
--   0.35  -> 腐烂速度降到 35%(默认)
--   0     -> 完全不腐烂
--   负数  -> 反向回鲜
function FlowerPackConfig.GetPerishFactor()
    return PERISH_FACTOR
end

return FlowerPackConfig
