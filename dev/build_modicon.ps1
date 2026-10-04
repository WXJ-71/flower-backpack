# 重建 mod 图标（mod 列表里显示的那张）。
#
# 用法 (Windows PowerShell):
#     powershell -NoProfile -ExecutionPolicy Bypass -File dev\build_modicon.ps1
#
# 做两件事:
#     1. 用 dev/build_icons.py 画出 mod 图标 PNG (128x128)
#     2. 用官方 TextureConverter 编译成 modicon.tex / modicon.xml
#     3. 顺手清理 BOM 并做 Lua 语法体检
#
# 【这个脚本管什么】
#   世界里的外观(地面/背上)全部用游戏内置的原版背包资源, 不需要重建。
#   物品图标(物品栏/容器格子/配方里的那张 64x64)由 dev\build_item_icon.py 生成 ——
#   它是从**原版图集**里抠出来的像素, 手绘流程用不上, 所以不在本脚本里。
#   本脚本只负责 mod 列表里显示的那张 modicon。
#
#   改造之前那套"生成背包贴图 + 手绘物品图标"的脚本(build_flowerpack_art.py /
#   compile_item_icon.ps1 / build_all.ps1)还留在 dev/ 里当参考, 但**不要再跑** ——
#   它们会重新生成已经删掉的 anim/ 与 images/inventoryimages/, 反而把 mod 弄回旧方案。
#
# 注意: 本文件必须保存为 UTF-8 with BOM, 否则 Windows PowerShell 5.1 会按 GBK 解析。

$ErrorActionPreference = 'Stop'

$dev = $PSScriptRoot
$modRoot = Split-Path -Parent $dev
$python = 'E:\app\Blender\5.2\python\bin\python.exe'

if (-not (Test-Path -LiteralPath $python)) {
    $python = (Get-Command python -ErrorAction SilentlyContinue).Source
}
if (-not $python) { throw "找不到可用的 python" }

Write-Host "=== 1/3 画 mod 图标 PNG ===" -ForegroundColor Cyan
& $python (Join-Path $dev 'build_icons.py')
if ($LASTEXITCODE -ne 0) { throw "build_icons.py 失败" }

Write-Host "=== 2/3 编译 mod 图标 ===" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $dev 'compile_modicon.ps1')

Write-Host "`n=== 3/3 清理 BOM 并做语法体检 ===" -ForegroundColor Cyan
& $python (Join-Path $dev 'fix_bom.py') $modRoot
if ($LASTEXITCODE -ne 0) { throw "fix_bom.py 失败" }

# 只检查 mod 自己的 lua 文件: 直接传目录会把 upload_tmp2 里的原版脚本一起扫,
# 又慢又会撞上非 UTF-8 文件。
& $python (Join-Path $dev 'lint_lua.py') `
    (Join-Path $modRoot 'modmain.lua') `
    (Join-Path $modRoot 'modinfo.lua') `
    (Join-Path $modRoot 'scripts\prefabs\flowerpack.lua') `
    (Join-Path $modRoot 'scripts\flowerpack_config.lua')

Write-Host "`n全部完成。" -ForegroundColor Green
