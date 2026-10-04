# 准备原版背包资源(只需跑一次, 或游戏更新后重跑)。
#
# 把游戏里的 data/anim/swap_backpack.zip 复制并解包到 dev/swap_backpack_unzip/,
# 供 build_flowerpack_art.py 解码使用。
#
# 用法 (Windows PowerShell):
#     powershell -NoProfile -ExecutionPolicy Bypass -File dev\prepare_vanilla.ps1
#
# 注意: 本文件必须保存为 UTF-8 with BOM, 否则 Windows PowerShell 5.1 会按 GBK 解析。

$ErrorActionPreference = 'Stop'

$dev = $PSScriptRoot
$game = "E:\app\steam\steamapps\common\Don't Starve Together\data\anim"

$sources = @{
    'swap_backpack' = "$game\swap_backpack.zip"
    'backpack'      = "$game\backpack.zip"
}

foreach ($name in $sources.Keys) {
    $zip = $sources[$name]
    if (-not (Test-Path -LiteralPath $zip)) { throw "找不到 $zip" }

    $dstZip = Join-Path $dev "$name.zip"
    $dstDir = Join-Path $dev "${name}_unzip"
    Copy-Item -LiteralPath $zip -Destination $dstZip -Force
    Remove-Item -LiteralPath $dstDir -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
    Expand-Archive -LiteralPath $dstZip -DestinationPath $dstDir -Force
    Write-Host "$name.zip -> $dstDir"
    Get-ChildItem -LiteralPath $dstDir | ForEach-Object { "    $($_.Name)  $($_.Length) 字节" }
}

Write-Host "`n准备完成。接下来可以跑 dev\build_all.ps1" -ForegroundColor Green
