-- 保鲜背包 / Preserving Backpack -- 预制体本体
--
-- 结构参考原版 scripts/prefabs/backpack.lua, 但做成**完全独立**的新物品:
--   1. 自己的预制体名(flowerpack)、配方、容器 UI, 不覆盖也不修改原版背包;
--   2. 内部 ID 全部带 flowerpack 前缀, 不会和其他 mod 的物品撞名;
--   3. 去掉皮肤系统(自定义物品没有官方皮肤, 那些代码在这里是死代码);
--   4. 加上官方 preserver 组件 -> 容器内食物腐烂变慢;
--   5. **外观与原版背包完全一致** —— 直接使用游戏自带的原版资源,
--      不带任何自定义贴图、不做缩放、不做任何染色。
--
-- 需求变更记录(避免以后误加回来):
--   · 曾做过"装满变红/未满变绿"的染色 -> 已删除。引擎的 SetAddColour/SetMultColour
--     没有像素选择能力, 染色会作用到整个物品; 而且地面物品会把整张图集的几何都
--     铺出来, 染色会把整片都染红, 外观直接坏掉。
--   · 曾做过"背上缩小一半"的自制贴图 -> 已删除, 现在背上也是原版尺寸。

local FlowerPackConfig = require("flowerpack_config")

--------------------------------------------------------------------------
-- 资源
--------------------------------------------------------------------------
-- 只用游戏自带的原版资源(都是 data/anim 下的内置文件, 不是本 mod 打包的),
-- 显式声明的原因: 引擎需要把这几张图加进加载清单, 物品才能显示出来。
--   bank  "backpack1"        <- anim/backpack.zip (游戏内置)
--   build "swap_backpack_flower" <- anim/swap_backpack_flower.zip (本 mod 自带, 加了花)
--   UI    "ui_backpack_2x4"  <- anim/ui_backpack_2x4.zip (游戏内置)
-- build 名带 _flower 后缀是为了和原版 swap_backpack 隔离:
-- 冰背包与背包皮肤都用原版那个 build, 同名会连它们一起改掉。
local assets =
{
    Asset("ANIM", "anim/backpack.zip"),
    Asset("ANIM", "anim/swap_backpack_flower.zip"),
    Asset("ANIM", "anim/ui_backpack_2x4.zip"),
}

local prefabs =
{
    "ash",
}

--------------------------------------------------------------------------
-- 保鲜倍率
--------------------------------------------------------------------------
local FLOWERPACK_MOD_NAME = "hunger_mod"

-- 优先问 FlowerPackConfig(它在 _G 环境里带 modname 读 GetModConfigData, 是唯一
-- 正确的读法); 拿不到再退回 modinfo 默认值, 绝不把 nil 交给 preserver
-- (那样 preserver 会按 1 处理, 保鲜静默失效)。
local function GetPerishFactor()
    local value = FlowerPackConfig.GetPerishFactor()
    if type(value) == "number" then
        return value
    end

    local info = KnownModIndex:GetModInfo(FLOWERPACK_MOD_NAME)
    if type(info) == "table" and type(info.configuration_options) == "table" then
        for _, option in ipairs(info.configuration_options) do
            if option.name == "PERISH_FACTOR" and type(option.default) == "number" then
                return option.default
            end
        end
    end

    return 0.35
end

--------------------------------------------------------------------------
-- 装备 / 卸下 (与原版背包完全一致的写法)
--------------------------------------------------------------------------

local function onequip(inst, owner)
    -- 把背包画到角色身上的 swap_body 位置, 和原版行为一致
    owner.AnimState:OverrideSymbol("swap_body", "swap_backpack_flower", "swap_body")

    if inst.components.container ~= nil then
        inst.components.container:Open(owner)
    end
end

local function onunequip(inst, owner)
    owner.AnimState:ClearOverrideSymbol("swap_body")
    owner.AnimState:ClearOverrideSymbol("backpack")

    if inst.components.container ~= nil then
        inst.components.container:Close(owner)
    end
end

-- 被摆到人偶/雕像上时不能开着容器
local function onequiptomodel(inst, owner, from_ground)
    if inst.components.container ~= nil then
        inst.components.container:Close(owner)
    end
end

--------------------------------------------------------------------------
-- 烧毁
--------------------------------------------------------------------------

local function onburnt(inst)
    if inst.components.container ~= nil then
        inst.components.container:DropEverything()
        inst.components.container:Close()
    end

    SpawnPrefab("ash").Transform:SetPosition(inst.Transform:GetWorldPosition())

    inst:Remove()
end

local function onignite(inst)
    if inst.components.container ~= nil then
        inst.components.container.canbeopened = false
    end
end

local function onextinguish(inst)
    if inst.components.container ~= nil then
        inst.components.container.canbeopened = true
    end
end

--------------------------------------------------------------------------
-- 主函数 (结构照抄原版 scripts/prefabs/backpack.lua, 去掉皮肤相关)
--------------------------------------------------------------------------

local function fn()
    local inst = CreateEntity()

    inst.entity:AddTransform()
    inst.entity:AddAnimState()
    inst.entity:AddSoundEmitter()
    inst.entity:AddMiniMapEntity()
    inst.entity:AddNetwork()

    MakeInventoryPhysics(inst)

    inst.AnimState:SetBank("backpack1")
    inst.AnimState:SetBuild("swap_backpack_flower")
    inst.AnimState:PlayAnimation("anim")

    -- 打上原版背包标签, 让熊獾偷吃、浣猫翻包等原版行为仍然认得它。
    -- 另外加一个专属标签, 方便自己或别人的 mod 精确识别这个物品。
    inst:AddTag("backpack")
    inst:AddTag("flowerpack")

    inst.MiniMapEntity:SetIcon("backpack.png")

    inst.foleysound = "dontstarve/movement/foley/backpack"

    -- 掉进水里漂浮时用的展示动画
    MakeInventoryFloatable(inst, "small", 0.2, nil, nil, nil, { bank = "backpack1", anim = "anim" })

    inst.entity:SetPristine()

    -- 客机在此处返回, 容器内容由服务端同步
    if not TheWorld.ismastersim then
        return inst
    end

    inst:AddComponent("inspectable")

    inst:AddComponent("inventoryitem")
    inst.components.inventoryitem.cangoincontainer = false

    inst:AddComponent("equippable")
    inst.components.equippable.equipslot = EQUIPSLOTS.BODY
    inst.components.equippable:SetOnEquip(onequip)
    inst.components.equippable:SetOnUnequip(onunequip)
    inst.components.equippable:SetOnEquipToModel(onequiptomodel)

    inst:AddComponent("container")
    inst.components.container:WidgetSetup("flowerpack")

    -- 本 mod 的核心: preserver 组件会把容器内物品的腐烂速度乘以给定倍率。
    -- perishable 组件在更新时会向 owner(也就是这只背包)查询该倍率:
    --   0      -> 完全不腐烂
    --   0.35   -> 腐烂速度降到 35%
    --   -0.25  -> 反向回鲜
    inst:AddComponent("preserver")
    inst.components.preserver:SetPerishRateMultiplier(GetPerishFactor())

    MakeSmallBurnable(inst)
    MakeSmallPropagator(inst)
    inst.components.burnable:SetOnBurntFn(onburnt)
    inst.components.burnable:SetOnIgniteFn(onignite)
    inst.components.burnable:SetOnExtinguishFn(onextinguish)

    MakeHauntableLaunchAndDropFirstItem(inst)

    return inst
end

return Prefab("flowerpack", fn, assets, prefabs)
