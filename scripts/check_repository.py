#!/usr/bin/env python3
"""Audit the recovered rooted-tree Catalan closure artifact without network access."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    'README.md', 'main.tex', 'Rooted_tree_Catalan_closure.pdf', 'Makefile',
    'project.json', 'LEAN_PATCH_MANIFEST.md', 'CHANGELOG.md', 'CONTRIBUTING.md',
    'SECURITY.md', 'LICENSE', 'CITATION.cff', 'CITATION.bib', 'codemeta.json',
    '.zenodo.json', 'docs/CLAIMS_BOUNDARY.md', 'docs/PROVENANCE.md',
    'docs/RECOVERY.md', 'docs/REPRODUCIBILITY.md', 'docs/RELEASE_CHECKLIST.md',
    'lean-patch/CATALAN_PATCH_STATUS.md',
    'lean-patch/catalan-conditional-adapter.patch',
    'lean-patch/oracle_check_catalan.lean',
    'lean-patch/verification/catalan-build.log',
    'lean-patch/verification/oracle_check_catalan.log',
    'lean-patch/YangMills/KP/RootedCatalan.lean',
    'lean-patch/YangMills/RG/AppendixFHsharpCatalanClosure.lean',
    'lean-patch/YangMills/RG/AppendixFHsharpCatalanSource.lean',
    'scripts/package_release.py', 'scripts/verify_release.py',
    'scripts/check_determinism.py', '.github/workflows/artifact-ci.yml',
    '.github/workflows/full-lean-replay.yml', '.github/workflows/release.yml',
)
FORBIDDEN_FILES = ('apply_improvements.py', '.github/workflows/artifact.yml')
LEAN_FILES = (
    'lean-patch/YangMills/KP/RootedCatalan.lean',
    'lean-patch/YangMills/RG/AppendixFHsharpCatalanClosure.lean',
    'lean-patch/YangMills/RG/AppendixFHsharpCatalanSource.lean',
    'lean-patch/oracle_check_catalan.lean',
)
EXPECTED_AXIOMS = {'propext', 'Classical.choice', 'Quot.sound'}

class Audit:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.notes: list[str] = []
    def require(self, condition: bool, message: str) -> None:
        if not condition:
            self.errors.append(message)
    def note(self, message: str) -> None:
        self.notes.append(message)

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f'blob {len(data)}\0'.encode('ascii') + data).hexdigest()  # noqa: S324

def read_text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding='utf-8')

def strip_lean_comments_and_strings(source: str) -> str:
    out: list[str] = []
    i = 0
    depth = 0
    in_string = False
    escaped = False
    while i < len(source):
        c = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ''
        if depth:
            if c == '/' and nxt == '-':
                depth += 1; out.extend('  '); i += 2
            elif c == '-' and nxt == '/':
                depth -= 1; out.extend('  '); i += 2
            else:
                out.append('\n' if c == '\n' else ' '); i += 1
            continue
        if in_string:
            out.append('\n' if c == '\n' else ' ')
            if escaped:
                escaped = False
            elif c == '\\':
                escaped = True
            elif c == '"' or c == '\n':
                in_string = False
            i += 1
            continue
        if c == '/' and nxt == '-':
            depth = 1; out.extend('  '); i += 2
        elif c == '-' and nxt == '-':
            while i < len(source) and source[i] != '\n':
                out.append(' '); i += 1
        elif c == '"':
            in_string = True; out.append(' '); i += 1
        else:
            out.append(c); i += 1
    return ''.join(out)

def parse_oracle_axioms(text: str) -> list[set[str]]:
    groups = re.findall(r'depends on axioms:\s*\[([^\]]*)\]', text, flags=re.S)
    return [{part.strip() for part in group.replace('\n', ' ').split(',') if part.strip()} for group in groups]

def check_text_files(audit: Audit, files: Iterable[str]) -> None:
    for rel in files:
        path = ROOT / rel
        if not path.is_file() or path.suffix.lower() in {'.pdf', '.png', '.zip'}:
            continue
        data = path.read_bytes()
        try:
            data.decode('utf-8')
        except UnicodeDecodeError as exc:
            audit.errors.append(f'{rel} is not valid UTF-8: {exc}')
            continue
        audit.require(b'\r\n' not in data, f'{rel} contains CRLF line endings')
        audit.require(not data or data.endswith(b'\n'), f'{rel} lacks a final newline')

def check_git(audit: Audit) -> None:
    if not (ROOT / '.git').exists():
        audit.note('git worktree checks skipped outside a checkout')
        return
    proc = subprocess.run(['git', 'diff', '--check'], cwd=ROOT, text=True, capture_output=True)
    audit.require(proc.returncode == 0, f'git diff --check failed:\n{proc.stdout}{proc.stderr}')

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--accept-rebuilt-pdf', action='store_true')
    args = parser.parse_args()
    audit = Audit()

    for rel in REQUIRED_FILES:
        audit.require((ROOT / rel).is_file(), f'missing required file: {rel}')
    for rel in FORBIDDEN_FILES:
        audit.require(not (ROOT / rel).exists(), f'obsolete repository file still present: {rel}')
    if audit.errors:
        for error in audit.errors:
            print(f'ERROR: {error}', file=sys.stderr)
        return 1

    project = json.loads(read_text('project.json'))
    audit.require(project.get('schema_version') == 2, 'unsupported project.json schema')
    audit.require(project.get('name') == 'rooted-tree-catalan-closure', 'wrong project name')
    audit.require(project.get('default_branch') == 'master', 'default branch record is not master')
    audit.require(project.get('status') == 'recovered_conditional_publication_artifact', 'formal status drift')
    audit.require(bool(re.fullmatch(r'\d+\.\d+\.\d+', project.get('version', ''))), 'bad version')
    audit.require(project.get('unresolved_obligation') ==
        'YangMills.KP.RootedChildFactorialCatalanIdentity n for every n',
        'unresolved obligation was changed or removed')

    upstream = project['upstream']
    pins = {'base': upstream['base_commit'], 'patch': upstream['checked_patch_commit'],
            'lean': upstream['lean_toolchain'], 'mathlib': upstream['mathlib_commit']}
    for label, value in pins.items():
        audit.require(bool(value), f'empty {label} pin')
    for rel in ('README.md', 'LEAN_PATCH_MANIFEST.md', 'lean-patch/CATALAN_PATCH_STATUS.md', 'docs/PROVENANCE.md'):
        text = read_text(rel)
        for label, value in pins.items():
            if rel == 'docs/PROVENANCE.md' and label in {'lean', 'mathlib'}:
                continue
            audit.require(value in text, f'{rel} does not contain {label} pin {value}')

    main_tex = read_text('main.tex')
    for label in ('base', 'lean', 'mathlib'):
        audit.require(pins[label] in main_tex, f'main.tex lost the {label} pin')

    for rel, expected in project['critical_git_blobs'].items():
        path = ROOT / rel
        audit.require(path.is_file(), f'critical file missing: {rel}')
        if path.is_file() and not (args.accept_rebuilt_pdf and rel == 'Rooted_tree_Catalan_closure.pdf'):
            actual = git_blob_sha(path.read_bytes())
            audit.require(actual == expected, f'critical blob mismatch for {rel}: {actual} != {expected}')

    pdf = (ROOT / 'Rooted_tree_Catalan_closure.pdf').read_bytes()
    audit.require(pdf.startswith(b'%PDF-'), 'compiled manuscript is not a PDF')
    audit.require(len(pdf) >= 50_000, 'compiled manuscript is unexpectedly small')
    audit.require(b'%%EOF' in pdf[-2048:], 'compiled manuscript has no terminal EOF marker')

    for rel in LEAN_FILES:
        stripped = strip_lean_comments_and_strings(read_text(rel))
        for token in ('sorry', 'admit', 'sorryAx'):
            audit.require(re.search(rf'\b{token}\b', stripped) is None,
                          f'active Lean placeholder {token!r} found in {rel}')
        audit.require(re.search(r'(?m)^\s*axiom\b', stripped) is None,
                      f'project-local axiom declaration found in {rel}')

    rooted = read_text('lean-patch/YangMills/KP/RootedCatalan.lean')
    audit.require('def RootedChildFactorialCatalanIdentity' in rooted, 'identity interface missing')
    audit.require('rootedChildCount_factorialTreeSum_normalized_le_catalan_of_identity' in rooted,
                  'conditional Catalan consumer missing')
    audit.require('theorem rootedChildCount_factorialTreeSum_normalized_eq_catalan' not in rooted,
                  'closed identity theorem appeared without status/evidence migration')
    source = read_text('lean-patch/YangMills/RG/AppendixFHsharpCatalanSource.lean')
    audit.require('(hcat : YangMills.KP.RootedChildFactorialCatalanIdentity n)' in source,
                  'Appendix-F adapter no longer exposes the Catalan hypothesis')

    patch = read_text('lean-patch/catalan-conditional-adapter.patch')
    audit.require(patch.startswith(f"From {pins['patch']} "), 'mailbox patch header mismatch')
    for rel in ('YangMills/KP/RootedCatalan.lean',
                'YangMills/RG/AppendixFHsharpCatalanClosure.lean',
                'YangMills/RG/AppendixFHsharpCatalanSource.lean', 'oracle_check_catalan.lean'):
        audit.require(rel in patch, f'mailbox patch does not mention {rel}')

    build_log = read_text('lean-patch/verification/catalan-build.log')
    audit.require(project['archived_build_marker'] in build_log, 'build success marker missing')
    oracle_log = read_text('lean-patch/verification/oracle_check_catalan.log')
    groups = parse_oracle_axioms(oracle_log)
    audit.require(len(groups) == 3, 'expected three oracle reports')
    for i, names in enumerate(groups, 1):
        audit.require(names == EXPECTED_AXIOMS, f'oracle report {i} has unexpected axioms: {names}')
    audit.require('sorryAx' not in oracle_log, 'oracle log contains sorryAx')

    for rel in ('README.md', 'lean-patch/CATALAN_PATCH_STATUS.md', 'docs/CLAIMS_BOUNDARY.md'):
        text = read_text(rel).lower()
        audit.require('conditional' in text, f'{rel} hides the conditional boundary')
        audit.require('still open' in text or 'not certified' in text or 'remains open' in text,
                      f'{rel} hides the unresolved identity')

    version, date = project['version'], project['release_date']
    audit.require(f'version: {version}' in read_text('CITATION.cff'), 'CITATION.cff version drift')
    audit.require(f'date-released: {date}' in read_text('CITATION.cff'), 'CITATION.cff date drift')
    audit.require(json.loads(read_text('codemeta.json'))['version'] == version, 'CodeMeta version drift')
    audit.require(json.loads(read_text('.zenodo.json'))['version'] == version, 'Zenodo version drift')
    audit.require(f'## {version} - {date}' in read_text('CHANGELOG.md'), 'changelog version/date missing')

    ci = read_text('.github/workflows/artifact-ci.yml')
    audit.require('persist-credentials: false' in ci, 'CI checkout credentials are persisted')
    audit.require('make package-determinism' in ci and 'make verify-release' in ci,
                  'CI does not enforce deterministic verified releases')
    replay = read_text('.github/workflows/full-lean-replay.yml')
    audit.require('workflow_dispatch:' in replay and 'lake env lean oracle_check_catalan.lean' in replay,
                  'manual full Lean replay workflow is incomplete')
    release = read_text('.github/workflows/release.yml')
    audit.require('tags: ["v*"]' in release and 'gh release create' in release,
                  'tagged release workflow is incomplete')

    check_text_files(audit, REQUIRED_FILES)
    check_git(audit)
    for note in audit.notes:
        print(f'NOTE: {note}')
    if audit.errors:
        for error in audit.errors:
            print(f'ERROR: {error}', file=sys.stderr)
        print(f'repository audit failed with {len(audit.errors)} error(s)', file=sys.stderr)
        return 1
    print('repository audit passed: provenance, critical blobs, conditional Lean boundary, '
          'evidence, workflows, PDF, and metadata are consistent')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
