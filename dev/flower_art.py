"""鲜花印记的统一画法 —— 全项目共用这一个实现, 保证三处外观一致。

样式(按需求调整过):
    · 五片花瓣, 填充**绿色**
    · 外围一圈**红色粗描边**(包住整朵花的外轮廓)
    · 花心略深一点的绿, 让五瓣的层次还能看出来

调用方:
    dev/build_item_icon.py    -> 物品图标 64x64
    dev/build_world_flower.py -> 世界贴图 256x256 (背上 + 地面共用)
"""

import math

import numpy as np

# 红色粗描边 —— 需求指定
OUTLINE = (200, 24, 24, 255)
# 花瓣填充 —— 需求指定为绿色
PETAL = (74, 168, 62, 255)
# 花心: 比花瓣略深的绿, 保留层次
PETAL_CORE = (44, 122, 40, 255)

# 描边粗细(像素), 会按半径缩放
OUTLINE_WIDTH = 2.2

# 花瓣布局: 5 片均匀分布, 花瓣中心离花心 0.66R, 花瓣半径 0.47R
PETAL_ORBIT = 0.66
PETAL_RADIUS = 0.47
CORE_RADIUS = 0.30


def draw_flower(rgba, cx, cy, radius):
    """在 rgba 上就地画一朵花。cx/cy 为花心, radius 为整朵花的半径(像素)。

    返回被改动的像素掩码(布尔数组), 便于调用方统计/校验。
    """
    height, width = rgba.shape[0], rgba.shape[1]
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float64)

    petal_centres = []
    for index in range(5):
        angle = math.pi * 2.0 * index / 5.0 - math.pi / 2.0
        petal_centres.append((cx + math.cos(angle) * radius * PETAL_ORBIT,
                              cy + math.sin(angle) * radius * PETAL_ORBIT))
    petal_r = radius * PETAL_RADIUS

    # 描边宽度按半径缩放, 保证图标(小)与贴图(大)上看起来一样粗
    outline_w = max(1.4, radius * 0.16)

    petal_mask = np.zeros((height, width), dtype=bool)
    for px, py in petal_centres:
        petal_mask |= ((xx - px) ** 2 + (yy - py) ** 2) <= petal_r ** 2
    petal_mask |= ((xx - cx) ** 2 + (yy - cy) ** 2) <= (radius * CORE_RADIUS) ** 2

    # 描边 = 把花瓣整体向外"膨胀" outline_w 像素
    outline_mask = np.zeros((height, width), dtype=bool)
    for px, py in petal_centres:
        outline_mask |= ((xx - px) ** 2 + (yy - py) ** 2) <= (petal_r + outline_w) ** 2
    outline_mask |= ((xx - cx) ** 2 + (yy - cy) ** 2) <= (radius * CORE_RADIUS + outline_w) ** 2

    rgba[outline_mask] = OUTLINE
    rgba[petal_mask] = PETAL
    core_mask = ((xx - cx) ** 2 + (yy - cy) ** 2) <= (radius * CORE_RADIUS) ** 2
    rgba[core_mask] = PETAL_CORE

    return outline_mask | petal_mask | core_mask
