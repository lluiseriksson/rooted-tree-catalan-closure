#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    'README.md',
    'main.tex',
    'Rooted_tree_Catalan_closure.pdf',
    'LEAN_PATCH_MANIFEST.md',
    'project.json',
    'lean-patch/CATALAN_PATCH_STATUS.md',
    'lean-patch/YangMills/KP/RootedCatalan.lean',
    'lean-patch/YangMills/RG/AppendixFHsharpCatalanClosure.lean',
    'lean-patch/YangMills/RG/AppendixFHsharpCatalanSource.lean',
    'lean-patch/catalan-conditional-adapter.patch',
    'lean-patch/oracle_check_catalan.lean',
    'lean-patch/verification/catalan-build.log',
    'lean-patch/verification/oracle_check_catalan.log',
    'docs/CLAIMS_BOUNDARY.md',
    'docs/RECOVERY.md',
    'docs/REPRODUCIBILITY.md',
]
FORBIDDEN_OVERCLAIMS = [
    'mass gap is proved',
    'continuum limit is proved',
    'osterwalder--schrader reconstruction is proved',
    'RootedChildFactorialCatalanIdentity n is proved for every n',
]

def fail(msg: str) -> None:
    print(f'audit failed: {msg}', file=sys.stderr)
    raise SystemExit(1)

def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding='utf-8')

def main() -> None:
    missing = [p for p in REQUIRED if not (ROOT / p).exists()]
    if missing:
        fail('missing required files: ' + ', '.join(missing))

    meta = json.loads(read('project.json'))
    if meta.get('status') != 'recovered_conditional_publication_artifact':
        fail('project.json status must remain conditional and recovered')
    if 'RootedChildFactorialCatalanIdentity' not in meta.get('unresolved_obligation', ''):
        fail('project.json must record the unresolved Catalan identity obligation')

    status = read('lean-patch/CATALAN_PATCH_STATUS.md')
    if 'not a closed formal proof' not in status:
        fail('CATALAN_PATCH_STATUS.md must explicitly deny closed-proof status')

    oracle = read('lean-patch/verification/oracle_check_catalan.log')
    if 'sorryAx' in oracle:
        fail('oracle log mentions sorryAx')
    if 'Classical.choice' not in oracle or 'Quot.sound' not in oracle:
        fail('oracle log does not contain the expected axiom boundary')

    all_text = '\n'.join(
        p.read_text(encoding='utf-8', errors='ignore')
        for p in ROOT.rglob('*')
        if p.is_file()
        and p.relative_to(ROOT).as_posix() != 'scripts/audit_artifact.py'
        and p.suffix.lower() not in {'.pdf', '.png', '.zip'}
    ).lower()
    for phrase in FORBIDDEN_OVERCLAIMS:
        if phrase.lower() in all_text:
            fail(f'forbidden overclaim: {phrase}')

    print('artifact audit passed')

if __name__ == '__main__':
    main()
