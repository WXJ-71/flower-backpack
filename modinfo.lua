-- 鲜花背包 -- 饥荒联机版 mod
-- 开发目录: E:\ds h\hunger_mod
-- 游戏内 mod 目录通过 junction 指向本目录, 详见 dev_notes.md
--
-- 显示名 = "Flower Backpack" / 中文 "鲜花背包"。
-- 内部 ID 一律保持 flowerpack、mod 目录名保持 hunger_mod —— 这两个是存档与
-- GetModConfigData 的标识, 改了会让旧存档里的物品失联。

name = "Flower Backpack"
description =
[[一只带鲜花印记的保鲜背包。

【怎么造】
· 需要科学机器（科技一级）
· 材料：草 x4、树枝 x4（与原版背包相同）
· 在建造菜单的「模组」分类里找到它

【有什么用】
· 和原版背包一样：背在身体栏、8 个格子
· 外观 = 原版背包 + 右下角一朵绿花红边的鲜花印记
  （物品栏、背在身上、丢在地上三处都有，方便和原版背包区分）
· 放进去的食物腐烂速度大幅降低，保鲜强度可在模组设置里调

这是一个独立的新物品，不会替换、也不会改动原版背包，和其他 mod 互不影响。
房主装了这个 mod 就能用，客机不需要安装。]]
author = "哦鲸鲸"
version = "0.6.1"

icon = "modicon.tex"
icon_atlas = "modicon.xml"

-- 当前游戏版本 756039 对应的 mod API 版本
api_version = 10

dst_compatible = true
dont_starve_compatible = false
reign_of_giants_compatible = false
shipwrecked_compatible = false

-- 逻辑全在服务端运行(保鲜、容器内容都由服务端同步), 客机无需安装
all_clients_require_mod = false
client_only_mod = false

server_filter_tags = { "storage", "food" }

-- 让本 mod 在其他 mod 之前加载, 便于后续做兼容补丁
priority = -1

forumthread = ""

configuration_options =
{
    {
        name = "PERISH_FACTOR",
        label = "食物保鲜 / Food freshness",
        hover = "背包内食物的腐烂速度倍率。0 = 完全不腐烂，1 = 和原版一样，负数 = 反向恢复新鲜度。",
        options =
        {
            { description = "关闭 (原版速度)", data = 1 },
            { description = "轻微 (0.6x)",      data = 0.6 },
            { description = "保鲜 (0.35x)",     data = 0.35 },
            { description = "强效 (0.15x)",     data = 0.15 },
            { description = "接近永鲜 (0.05x)", data = 0.05 },
            { description = "完全不腐烂 (0)",   data = 0 },
            { description = "逆向回鲜 (-0.25x)", data = -0.25 },
        },
        default = 0.35,
    },
}
