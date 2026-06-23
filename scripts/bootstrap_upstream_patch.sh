#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM_URL="https://github.com/lluiseriksson/THE-ERIKSSON-PROGRAMME.git"
UPSTREAM_SHA="1d044a353ac2b69ddca732dd851fb0ab4a94d7af"
LEAN_TOOLCHAIN="leanprover/lean4:v4.29.0-rc6"
MATHLIB_SHA="07642720480157414db592fa85b626dafb71355b"
WORKDIR="${ROOT}/.work/upstream-catalan"
BUILD=0
CLEAN=0

usage() {
  cat <<'EOF'
usage: scripts/bootstrap_upstream_patch.sh [--workdir PATH] [--build] [--clean]

Clone the immutable upstream base, verify its pins, apply the recovered adapter,
and compare the applied files with the repository copies.  --build additionally
runs the pinned Lean build and oracle check.  --clean removes an existing workdir.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workdir)
      [[ $# -ge 2 ]] || { echo "missing value for --workdir" >&2; exit 2; }
      WORKDIR="$2"; shift 2 ;;
    --build) BUILD=1; shift ;;
    --clean) CLEAN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ $CLEAN -eq 1 && -e "$WORKDIR" ]]; then
  rm -rf -- "$WORKDIR"
fi
if [[ -e "$WORKDIR" ]]; then
  echo "workdir already exists: $WORKDIR" >&2
  echo "use --clean to recreate it" >&2
  exit 1
fi
mkdir -p "$(dirname "$WORKDIR")"
git clone --no-checkout "$UPSTREAM_URL" "$WORKDIR"
git -C "$WORKDIR" checkout --detach "$UPSTREAM_SHA"
[[ "$(git -C "$WORKDIR" rev-parse HEAD)" == "$UPSTREAM_SHA" ]]
[[ "$(tr -d '\r\n' < "$WORKDIR/lean-toolchain")" == "$LEAN_TOOLCHAIN" ]]
grep -Fq "$MATHLIB_SHA" "$WORKDIR/lake-manifest.json"

git -C "$WORKDIR" apply --check "$ROOT/lean-patch/catalan-conditional-adapter.patch"
git -C "$WORKDIR" apply "$ROOT/lean-patch/catalan-conditional-adapter.patch"
git -C "$WORKDIR" diff --check
cmp "$WORKDIR/YangMills/KP/RootedCatalan.lean" "$ROOT/lean-patch/YangMills/KP/RootedCatalan.lean"
cmp "$WORKDIR/YangMills/RG/AppendixFHsharpCatalanClosure.lean" "$ROOT/lean-patch/YangMills/RG/AppendixFHsharpCatalanClosure.lean"
cmp "$WORKDIR/YangMills/RG/AppendixFHsharpCatalanSource.lean" "$ROOT/lean-patch/YangMills/RG/AppendixFHsharpCatalanSource.lean"
cmp "$WORKDIR/oracle_check_catalan.lean" "$ROOT/lean-patch/oracle_check_catalan.lean"

echo "patch application and recovered-source comparison passed"
if [[ $BUILD -eq 1 ]]; then
  command -v lake >/dev/null || { echo "lake is required for --build" >&2; exit 1; }
  (
    cd "$WORKDIR"
    lake exe cache get
    lake build YangMillsCore 2>&1 | tee "$ROOT/replay-build.log"
    lake build YangMills.KP.RootedCatalan YangMills.RG.AppendixFHsharpCatalanClosure 2>&1 | tee -a "$ROOT/replay-build.log"
    lake build YangMills.RG.AppendixFHsharpCatalanSource 2>&1 | tee -a "$ROOT/replay-build.log"
    lake env lean oracle_check_catalan.lean 2>&1 | tee "$ROOT/replay-oracle.log"
  )
  python3 "$ROOT/scripts/verify_replay_logs.py" \
    --build-log "$ROOT/replay-build.log" \
    --oracle-log "$ROOT/replay-oracle.log" \
    --output "$ROOT/replay-report.json" \
    --artifact-sha "$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || printf 'uncommitted-local-checkout')" \
    --upstream-sha "$UPSTREAM_SHA" \
    --lean-toolchain "$LEAN_TOOLCHAIN" \
    --mathlib-sha "$MATHLIB_SHA"
fi
