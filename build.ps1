param(
    [string]$Tectonic = "tectonic"
)

$ErrorActionPreference = "Stop"
$buildDir = Join-Path $PSScriptRoot "build"
New-Item -ItemType Directory -Force -Path $buildDir | Out-Null

& $Tectonic -X compile (Join-Path $PSScriptRoot "main.tex") --outdir $buildDir
Copy-Item -LiteralPath (Join-Path $buildDir "main.pdf") `
    -Destination (Join-Path $PSScriptRoot "Rooted_tree_Catalan_closure.pdf") -Force
