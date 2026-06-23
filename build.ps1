param(
    [string]$Tectonic = "tectonic",
    [string]$Python = "python",
    [switch]$RequirePdfTools,
    [switch]$RefreshTrackedPdf
)

$ErrorActionPreference = "Stop"
$buildDir = Join-Path $PSScriptRoot "build"
$sourcePdf = Join-Path $buildDir "main.pdf"
$builtPdf = Join-Path $buildDir "Rooted_tree_Catalan_closure.pdf"
$trackedPdf = Join-Path $PSScriptRoot "Rooted_tree_Catalan_closure.pdf"
$checker = Join-Path $PSScriptRoot "scripts/check_pdf.py"

New-Item -ItemType Directory -Force -Path $buildDir | Out-Null

& $Tectonic -X compile (Join-Path $PSScriptRoot "main.tex") --outdir $buildDir
if ($LASTEXITCODE -ne 0) {
    throw "Tectonic failed with exit code $LASTEXITCODE"
}

Copy-Item -LiteralPath $sourcePdf -Destination $builtPdf -Force
$checkerArgs = @($checker, $builtPdf, "--rebuilt")
if ($RequirePdfTools) {
    $checkerArgs += "--require-tools"
}
& $Python @checkerArgs
if ($LASTEXITCODE -ne 0) {
    throw "PDF inspection failed with exit code $LASTEXITCODE"
}

if ($RefreshTrackedPdf) {
    Copy-Item -LiteralPath $builtPdf -Destination $trackedPdf -Force
    Write-Host "Refreshed tracked PDF: $trackedPdf"
} else {
    Write-Host "Built and inspected PDF without modifying the tracked artifact: $builtPdf"
}
