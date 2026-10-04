# 把 dev/item_icon_src/images/flowerpack.png 编译成 mod 里的物品图标:
#     images/inventoryimages/flowerpack.tex
#     images/inventoryimages/flowerpack.xml
#
# 用法 (Windows PowerShell):
#     powershell -NoProfile -ExecutionPolicy Bypass -File dev\compile_item_icon.ps1
#
# 背景与坑(和 compile_modicon.ps1 同源, 差别在于输出目录和图集条目名):
# 1. 游戏只认 KTEX 格式的 .tex, 转换器在 mod_tools\tools\bin\TextureConverter.exe。
# 2. 必须 --premultiply: DST 贴图是预乘 alpha 的。
# 3. 物品图标要 64x64 且是 2 的幂, 转换后应是 18 字节头 + 64*64 的 BC3 数据 = 4114 字节。
# 4. .xml 里 Texture filename 与 Element name 都必须是 "flowerpack.tex"(相对路径),
#    引擎按这个名字在图集里查贴图; modmain 里用
#    RegisterInventoryItemAtlas("images/inventoryimages/flowerpack.xml", "flowerpack") 注册。

$ErrorActionPreference = 'Stop'

$modRoot = Split-Path -Parent $PSScriptRoot
$modTools = 'E:\app\steam\steamapps\common\Don''t Starve Mod Tools\mod_tools'
$textureConverter = Join-Path $modTools 'tools\bin\TextureConverter.exe'

$png = Join-Path $modRoot 'dev\item_icon_src\images\flowerpack.png'
$outDir = Join-Path $modRoot 'images\inventoryimages'
$tex = Join-Path $outDir 'flowerpack.tex'
$xml = Join-Path $outDir 'flowerpack.xml'

foreach ($required in @($textureConverter, $png)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "缺少文件: $required" }
}

New-Item -ItemType Directory -Path $outDir -Force | Out-Null
Remove-Item -LiteralPath $tex, $xml -Force -ErrorAction SilentlyContinue

& $textureConverter --swizzle --format bc3 --platform opengl --premultiply -i $png -o $tex
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $tex)) {
    throw "TextureConverter 失败, 退出码 $LASTEXITCODE"
}

# 单图图集: 一个元素铺满整张图, uv 用 0..1(与原版 modicon.xml 一致)
$atlasXml = '<?xml version="1.0" encoding="utf-8"?>' +
    '<Atlas><Texture filename="flowerpack.tex" />' +
    '<Elements><Element name="flowerpack.tex" u1="0" u2="1" v2="1" v1="0" /></Elements></Atlas>'
$atlasXml | Set-Content -LiteralPath $xml -Encoding UTF8 -NoNewline

$size = (Get-Item -LiteralPath $tex).Length
$header = ([System.IO.File]::ReadAllBytes($tex)[0..17] | ForEach-Object { $_.ToString('X2') }) -join ' '
Write-Host "flowerpack.tex: $size 字节"
Write-Host "header:         $header"
if ($size -ne 4114) {
    Write-Warning "大小不是 4114(64x64 BC3 无 mip), 请检查输入图尺寸和参数"
}
Write-Host "完成: $tex"
