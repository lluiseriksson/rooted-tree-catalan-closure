param(
    [string]$WorkDir = (Join-Path (Split-Path -Parent $PSScriptRoot) ".work/upstream-catalan"),
    [switch]$Build,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$UpstreamUrl = "https://github.com/lluiseriksson/THE-ERIKSSON-PROGRAMME.git"
$UpstreamSha = "1d044a353ac2b69ddca732dd851fb0ab4a94d7af"
$LeanToolchain = "leanprover/lean4:v4.29.0-rc6"
$MathlibSha = "07642720480157414db592fa85b626dafb71355b"

if ($Clean -and (Test-Path -LiteralPath $WorkDir)) {
    Remove-Item -LiteralPath $WorkDir -Recurse -Force
}
if (Test-Path -LiteralPath $WorkDir) {
    throw "Work directory already exists: $WorkDir (use -Clean to recreate it)"
}
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $WorkDir) | Out-Null

git clone --no-checkout $UpstreamUrl $WorkDir
if ($LASTEXITCODE -ne 0) { throw "git clone failed" }
git -C $WorkDir checkout --detach $UpstreamSha
if ($LASTEXITCODE -ne 0) { throw "git checkout failed" }
$ActualSha = (git -C $WorkDir rev-parse HEAD).Trim()
if ($ActualSha -ne $UpstreamSha) { throw "Unexpected upstream SHA: $ActualSha" }
$ActualToolchain = (Get-Content -LiteralPath (Join-Path $WorkDir "lean-toolchain") -Raw).Trim()
if ($ActualToolchain -ne $LeanToolchain) { throw "Unexpected Lean toolchain: $ActualToolchain" }
if (-not (Select-String -LiteralPath (Join-Path $WorkDir "lake-manifest.json") -SimpleMatch $MathlibSha -Quiet)) {
    throw "Pinned Mathlib SHA not found"
}

$Patch = Join-Path $Root "lean-patch/catalan-conditional-adapter.patch"
git -C $WorkDir apply --check $Patch
if ($LASTEXITCODE -ne 0) { throw "patch preflight failed" }
git -C $WorkDir apply $Patch
if ($LASTEXITCODE -ne 0) { throw "patch application failed" }
git -C $WorkDir diff --check
if ($LASTEXITCODE -ne 0) { throw "git diff --check failed" }

$Pairs = @(
    @("YangMills/KP/RootedCatalan.lean", "lean-patch/YangMills/KP/RootedCatalan.lean"),
    @("YangMills/RG/AppendixFHsharpCatalanClosure.lean", "lean-patch/YangMills/RG/AppendixFHsharpCatalanClosure.lean"),
    @("YangMills/RG/AppendixFHsharpCatalanSource.lean", "lean-patch/YangMills/RG/AppendixFHsharpCatalanSource.lean"),
    @("oracle_check_catalan.lean", "lean-patch/oracle_check_catalan.lean")
)
foreach ($Pair in $Pairs) {
    $Left = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $WorkDir $Pair[0])).Hash
    $Right = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $Root $Pair[1])).Hash
    if ($Left -ne $Right) { throw "Recovered source mismatch: $($Pair[0])" }
}
Write-Host "Patch application and recovered-source comparison passed"

if ($Build) {
    Push-Location $WorkDir
    try {
        lake exe cache get
        lake build YangMillsCore 2>&1 | Tee-Object -FilePath (Join-Path $Root "replay-build.log")
        lake build YangMills.KP.RootedCatalan YangMills.RG.AppendixFHsharpCatalanClosure 2>&1 | Tee-Object -FilePath (Join-Path $Root "replay-build.log") -Append
        lake build YangMills.RG.AppendixFHsharpCatalanSource 2>&1 | Tee-Object -FilePath (Join-Path $Root "replay-build.log") -Append
        lake env lean oracle_check_catalan.lean 2>&1 | Tee-Object -FilePath (Join-Path $Root "replay-oracle.log")
    } finally {
        Pop-Location
    }
    $ArtifactSha = (git -C $Root rev-parse HEAD 2>$null)
    if (-not $ArtifactSha) { $ArtifactSha = "uncommitted-local-checkout" }
    python (Join-Path $Root "scripts/verify_replay_logs.py") `
        --build-log (Join-Path $Root "replay-build.log") `
        --oracle-log (Join-Path $Root "replay-oracle.log") `
        --output (Join-Path $Root "replay-report.json") `
        --artifact-sha $ArtifactSha.Trim() `
        --upstream-sha $UpstreamSha `
        --lean-toolchain $LeanToolchain `
        --mathlib-sha $MathlibSha
}
