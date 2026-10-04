# 用 Mod Tools 自带的贴图编译链, 把 dev/modicon_src/images/modicon.png
# 编译成 mod 根目录下的 modicon.tex / modicon.xml
#
# 用法 (Windows PowerShell):
#     powershell -NoProfile -ExecutionPolicy Bypass -File dev\compile_modicon.ps1
#
# 背景与坑:
# 1. 游戏只认 KTEX 格式的 .tex, 不能直接用 PNG。转换器在
#    mod_tools\tools\bin\TextureConverter.exe, 由 32 位 Python 2.7 的 klei 包调用,
#    所以别换其他 python。
# 2. 不用 mod_tools\compiler_scripts\image_build.py, 因为它内部走
#    atlas.Atlas(minimize_num_textures=True) 会强制生成 mip, 产出 21960 字节;
#    而 modicon 只有 128x128, 官方 modicon.tex 是无 mip 的 16402 字节
#    (= 18 字节头 + 128*128 的 BC3 数据)。这里直接调转换器更贴合官方产物。
# 3. 必须 --premultiply: DST 贴图是预乘 alpha 的, 漏掉会在游戏里显示异常。
# 4. xml 里必须是相对 mod 根目录的文件名, 不能有绝对路径。
# 5. 本文件必须以 UTF-8 with BOM 保存, 否则 Windows PowerShell 5.1 会按 GBK 解析导致中文乱码。

$ErrorActionPreference = 'Stop'

$modRoot = Split-Path -Parent $PSScriptRoot
$modTools = 'E:\app\steam\steamapps\common\Don''t Starve Mod Tools\mod_tools'
$textureConverter = Join-Path $modTools 'tools\bin\TextureConverter.exe'

$png = Join-Path $modRoot 'dev\modicon_src\images\modicon.png'
$tex = Join-Path $modRoot 'modicon.tex'
$xml = Join-Path $modRoot 'modicon.xml'

foreach ($required in @($textureConverter, $png)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "缺少文件: $required" }
}

Remove-Item -LiteralPath $tex, $xml -Force -ErrorAction SilentlyContinue

& $textureConverter --swizzle --format bc3 --platform opengl --premultiply -i $png -o $tex
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $tex)) {
    throw "TextureConverter 失败, 退出码 $LASTEXITCODE"
}

$atlasXml = '<?xml version="1.0" encoding="utf-8"?>' +
    '<Atlas><Texture filename="modicon.tex" />' +
    '<Elements><Element name="modicon.tex" u1="0" u2="1" v2="1" v1="0" /></Elements></Atlas>'
$atlasXml | Set-Content -LiteralPath $xml -Encoding UTF8 -NoNewline

$size = (Get-Item -LiteralPath $tex).Length
$header = ([System.IO.File]::ReadAllBytes($tex)[0..17] | ForEach-Object { $_.ToString('X2') }) -join ' '
Write-Host "modicon.tex: $size 字节"
Write-Host "header:      $header"
if ($size -ne 16402) {
    Write-Warning "大小不是 16402(128x128 BC3 无 mip), 请检查参数"
}
Write-Host "完成: $tex"
