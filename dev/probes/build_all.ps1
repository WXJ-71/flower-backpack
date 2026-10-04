# ⚠⚠ 已停用 —— 请改用 dev\build_modicon.ps1 ⚠⚠
#
# 这个脚本是"自制贴图"时代的产物: 它会重新生成 anim/swap_backpack.zip 与
# images/inventoryimages/flowerpack.tex, 也就是**把已经删掉的自定义贴图又造回来**,
# 与当前"外观完全用原版资源"的方案冲突。留着只为日后参考编解码/编译流程。
#
# 当前 mod 只需要重建 mod 列表图标 -> dev\build_modicon.ps1
#
# ---------------------------------------------------------------------------
# 一键重建鲜花背包的全部资源(旧方案, 勿跑)。
#
# 用法 (Windows PowerShell):
#     powershell -NoProfile -ExecutionPolicy Bypass -File dev\build_all.ps1
#
# 做四件事:
#     1. 解码原版背包图集 -> 画上鲜花印记 -> 重新编码打包成 anim/swap_backpack.zip
#     2. 画物品图标(64x64)与 mod 图标(128x128)
#     3. 用官方 TextureConverter 把物品图标编译成 images/inventoryimages/flowerpack.tex
#     4. 用官方 TextureConverter 把 mod 图标编译成 modicon.tex
#
# 前置: 需要 dev/swap_backpack_unzip/ 下有原版图集(由 dev/prepare_vanilla.ps1 准备)
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

Write-Host "=== 1/4 生成背包贴图(原版图集 + 鲜花印记) ===" -ForegroundColor Cyan
& $python (Join-Path $dev 'build_flowerpack_art.py')
if ($LASTEXITCODE -ne 0) { throw "build_flowerpack_art.py 失败" }

Write-Host "=== 2/4 生成图标 PNG ===" -ForegroundColor Cyan
& $python (Join-Path $dev 'build_icons.py')
if ($LASTEXITCODE -ne 0) { throw "build_icons.py 失败" }

Write-Host "=== 3/4 编译物品图标 ===" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $dev 'compile_item_icon.ps1')

Write-Host "=== 4/4 编译 mod 图标 ===" -ForegroundColor Cyan
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $dev 'compile_modicon.ps1')

Write-Host "`n=== 清理 BOM 并做语法体检 ===" -ForegroundColor Cyan
& $python (Join-Path $dev 'fix_bom.py') $modRoot
& $python (Join-Path $dev 'lint_lua.py') $modRoot

Write-Host "`n全部完成。" -ForegroundColor Green
