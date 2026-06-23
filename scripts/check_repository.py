#!/usr/bin/env python3
"""Audit the recovered rooted-tree Catalan closure artifact without network access."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

from check_actions_pins import audit_workflows, load_policy

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = (
    "README.md",
    "AGENTS.md",
    "main.tex",
    "Rooted_tree_Catalan_closure.pdf",
    "Makefile",
    "project.json",
    "LEAN_PATCH_MANIFEST.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "LICENSE",
    "CITATION.cff",
    "CITATION.bib",
    "codemeta.json",
    ".zenodo.json",
    "archive/theorem-manifest.json",
    "archive/github-actions-policy.json",
    "evidence/README.md",
    "evidence/finite-catalan-checks.json",
    "docs/CLAIMS_BOUNDARY.md",
    "docs/PROVENANCE.md",
    "docs/RECOVERY.md",
    "docs/REPRODUCIBILITY.md",
    "docs/RELEASE_CHECKLIST.md",
    "docs/PRUFER_PROFILE_REDUCTION.md",
    "docs/DISASTER_RECOVERY.md",
    "docs/CI_PORTABILITY.md",
    "docs/SUPPLY_CHAIN.md",
    "schema/project.schema.json",
    "lean-patch/CATALAN_PATCH_STATUS.md",
    "lean-patch/catalan-conditional-adapter.patch",
    "lean-patch/oracle_check_catalan.lean",
    "lean-patch/verification/catalan-build.log",
    "lean-patch/verification/oracle_check_catalan.log",
    "lean-patch/YangMills/KP/RootedCatalan.lean",
    "lean-patch/YangMills/RG/AppendixFHsharpCatalanClosure.lean",
    "lean-patch/YangMills/RG/AppendixFHsharpCatalanSource.lean",
    "scripts/bootstrap_upstream_patch.sh",
    "scripts/bootstrap_upstream_patch.ps1",
    "scripts/check_finite_catalan.py",
    "scripts/check_actions_pins.py",
    "scripts/check_pdf.py",
    "scripts/check_repository.py",
    "scripts/package_release.py",
    "scripts/verify_release.py",
    "scripts/check_determinism.py",
    "scripts/verify_replay_logs.py",
    "scripts/create_history_bundle.py",
    "scripts/verify_history_bundle.py",
    "tests/test_artifact_tools.py",
    "tests/test_actions_pins.py",
    "tests/test_finite_catalan.py",
    "tests/test_replay_logs.py",
    "tests/test_history_bundle.py",
    ".github/workflows/artifact-ci.yml",
    ".github/workflows/dependency-review.yml",
    ".github/workflows/full-lean-replay.yml",
    ".github/workflows/release.yml",
    ".github/workflows/history-backup.yml",
    ".github/dependabot.yml",
)
FORBIDDEN_FILES = ("apply_improvements.py", ".github/workflows/artifact.yml")
LEAN_FILES = (
    "lean-patch/YangMills/KP/RootedCatalan.lean",
    "lean-patch/YangMills/RG/AppendixFHsharpCatalanClosure.lean",
    "lean-patch/YangMills/RG/AppendixFHsharpCatalanSource.lean",
    "lean-patch/oracle_check_catalan.lean",
)
EXPECTED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
EXPECTED_VERIFIED_DECLARATIONS = {
    "YangMills.KP.rootedChildCount_factorialTreeSum_normalized_le_catalan_of_identity",
    "YangMills.RG.catalanClosure_fixedPoint",
    "YangMills.RG.appendixFHoleHsharpWeightedTreeMarkedRootSum_le_catalan_of_expWeight",
}
BINARY_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".zip"}


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
    """Compute the canonical Git blob object ID (SHA-1 repositories)."""
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()  # noqa: S324


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def strip_lean_comments_and_strings(source: str) -> str:
    """Blank nested Lean comments and strings while preserving line structure."""
    out: list[str] = []
    index = 0
    depth = 0
    in_string = False
    escaped = False
    while index < len(source):
        char = source[index]
        nxt = source[index + 1] if index + 1 < len(source) else ""
        if depth:
            if char == "/" and nxt == "-":
                depth += 1
                out.extend("  ")
                index += 2
            elif char == "-" and nxt == "/":
                depth -= 1
                out.extend("  ")
                index += 2
            else:
                out.append("\n" if char == "\n" else " ")
                index += 1
            continue
        if in_string:
            out.append("\n" if char == "\n" else " ")
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"' or char == "\n":
                in_string = False
            index += 1
            continue
        if char == "/" and nxt == "-":
            depth = 1
            out.extend("  ")
            index += 2
        elif char == "-" and nxt == "-":
            while index < len(source) and source[index] != "\n":
                out.append(" ")
                index += 1
        elif char == '"':
            in_string = True
            out.append(" ")
            index += 1
        else:
            out.append(char)
            index += 1
    return "".join(out)


def parse_oracle_axioms(text: str) -> list[set[str]]:
    groups = re.findall(r"depends on axioms:\s*\[([^\]]*)\]", text, flags=re.S)
    return [
        {part.strip() for part in group.replace("\n", " ").split(",") if part.strip()}
        for group in groups
    ]


def repository_files() -> list[str]:
    """Return tracked plus not-ignored working-tree files when Git is available."""
    if (ROOT / ".git").exists():
        proc = subprocess.run(
            ["git", "ls-files", "-co", "--exclude-standard", "-z"],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        if proc.returncode == 0:
            return sorted(item.decode("utf-8") for item in proc.stdout.split(b"\0") if item)
    excluded = {".git", "release", "history-release", "build", ".work", "__pycache__"}
    return sorted(
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file() and not any(part in excluded for part in path.relative_to(ROOT).parts)
    )


def check_text_files(audit: Audit, files: Iterable[str]) -> None:
    for rel in files:
        path = ROOT / rel
        if not path.is_file() or path.suffix.lower() in BINARY_SUFFIXES:
            continue
        data = path.read_bytes()
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as exc:
            audit.errors.append(f"{rel} is not valid UTF-8: {exc}")
            continue
        audit.require(b"\r\n" not in data, f"{rel} contains CRLF line endings")
        audit.require(not data or data.endswith(b"\n"), f"{rel} lacks a final newline")


def check_python_sources(audit: Audit, files: Iterable[str]) -> None:
    for rel in files:
        if not rel.endswith(".py"):
            continue
        try:
            ast.parse(read_text(rel), filename=rel)
        except SyntaxError as exc:
            audit.errors.append(f"invalid Python syntax in {rel}: {exc}")


def check_json_files(audit: Audit, files: Iterable[str]) -> None:
    for rel in files:
        if not rel.endswith(".json"):
            continue
        try:
            json.loads(read_text(rel))
        except json.JSONDecodeError as exc:
            audit.errors.append(f"invalid JSON in {rel}: {exc}")


def check_local_markdown_links(audit: Audit, files: Iterable[str]) -> None:
    pattern = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    for rel in files:
        if not rel.endswith(".md"):
            continue
        parent = (ROOT / rel).parent
        for target in pattern.findall(read_text(rel)):
            target = target.strip().split()[0].strip("<>")
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            target_path = target.split("#", 1)[0]
            if not target_path:
                continue
            resolved = (parent / target_path).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                audit.errors.append(f"{rel} has a link escaping the repository: {target}")
                continue
            audit.require(resolved.exists(), f"{rel} has a broken local link: {target}")


def check_git(audit: Audit) -> None:
    if not (ROOT / ".git").exists():
        audit.note("git worktree checks skipped outside a checkout")
        return
    proc = subprocess.run(["git", "diff", "--check"], cwd=ROOT, text=True, capture_output=True)
    audit.require(proc.returncode == 0, f"git diff --check failed:\n{proc.stdout}{proc.stderr}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accept-rebuilt-pdf", action="store_true")
    args = parser.parse_args()
    audit = Audit()

    for rel in REQUIRED_FILES:
        audit.require((ROOT / rel).is_file(), f"missing required file: {rel}")
    for rel in FORBIDDEN_FILES:
        audit.require(not (ROOT / rel).exists(), f"obsolete repository file still present: {rel}")
    if audit.errors:
        for error in audit.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    files = repository_files()
    project = json.loads(read_text("project.json"))
    audit.require(project.get("schema_version") == 4, "unsupported project.json schema")
    audit.require(project.get("name") == "rooted-tree-catalan-closure", "wrong project name")
    audit.require(project.get("default_branch") == "master", "default branch record is not master")
    audit.require(
        project.get("status") == "recovered_conditional_publication_artifact",
        "formal status drift",
    )
    audit.require(bool(re.fullmatch(r"\d+\.\d+\.\d+", project.get("version", ""))), "bad version")
    schema = json.loads(read_text("schema/project.schema.json"))
    audit.require(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "project schema draft drift")
    audit.require("history_backup_outputs" in schema.get("required", []), "project schema omits history outputs")
    audit.require("actions_policy" in schema.get("required", []), "project schema omits actions policy")
    audit.require(
        project.get("tooling_python_versions") == ["3.11", "3.12", "3.13"],
        "tooling Python matrix drift",
    )
    audit.require(
        project.get("unresolved_obligation")
        == "YangMills.KP.RootedChildFactorialCatalanIdentity n for every n",
        "unresolved obligation was changed or removed",
    )
    audit.require(
        set(project.get("verified_declarations", [])) == EXPECTED_VERIFIED_DECLARATIONS,
        "verified declaration set drift",
    )
    audit.require(set(project.get("expected_axioms", [])) == EXPECTED_AXIOMS, "project axiom set drift")
    audit.require(len(project.get("release_outputs", [])) >= 4, "release output inventory is incomplete")
    audit.require(len(project.get("history_backup_outputs", [])) == 3, "history output inventory is incomplete")
    recovery_policy = project.get("recovery_policy", {})
    audit.require(recovery_policy.get("off_site_storage_recommended") is True, "off-site recovery policy drift")
    audit.require(recovery_policy.get("history_bundle_byte_reproducibility_claim") is False, "history bundle overclaims byte reproducibility")
    actions_policy_rel = project.get("actions_policy")
    audit.require(actions_policy_rel == "archive/github-actions-policy.json", "actions-policy path drift")
    boundary = project.get("claim_boundary", {})
    audit.require(boundary.get("closed_exact_catalan_identity") is False, "closed-proof flag drift")
    audit.require(boundary.get("conditional_downstream_adapter") is True, "adapter status drift")

    upstream = project["upstream"]
    pins = {
        "base": upstream["base_commit"],
        "patch": upstream["checked_patch_commit"],
        "lean": upstream["lean_toolchain"],
        "mathlib": upstream["mathlib_commit"],
    }
    for label, value in pins.items():
        audit.require(bool(value), f"empty {label} pin")
    for rel in (
        "README.md",
        "AGENTS.md",
        "LEAN_PATCH_MANIFEST.md",
        "lean-patch/CATALAN_PATCH_STATUS.md",
        "docs/PROVENANCE.md",
        "docs/PRUFER_PROFILE_REDUCTION.md",
        "archive/theorem-manifest.json",
    ):
        text = read_text(rel)
        for label, value in pins.items():
            if rel in {"docs/PROVENANCE.md", "docs/PRUFER_PROFILE_REDUCTION.md"} and label in {
                "lean",
                "mathlib",
            }:
                continue
            if rel == "docs/PRUFER_PROFILE_REDUCTION.md" and label in {"base", "patch"}:
                continue
            audit.require(value in text, f"{rel} does not contain {label} pin {value}")

    main_tex = read_text("main.tex")
    for label in ("base", "lean", "mathlib"):
        audit.require(pins[label] in main_tex, f"main.tex lost the {label} pin")

    for rel in project["critical_git_blobs"]:
        audit.require(
            not rel.startswith(".github/workflows/"),
            f"workflow file must be governed semantically rather than frozen as a critical blob: {rel}",
        )

    for rel, expected in project["critical_git_blobs"].items():
        path = ROOT / rel
        audit.require(path.is_file(), f"critical file missing: {rel}")
        if path.is_file() and not (
            args.accept_rebuilt_pdf and rel == "Rooted_tree_Catalan_closure.pdf"
        ):
            actual = git_blob_sha(path.read_bytes())
            audit.require(actual == expected, f"critical blob mismatch for {rel}: {actual} != {expected}")

    pdf = (ROOT / "Rooted_tree_Catalan_closure.pdf").read_bytes()
    audit.require(pdf.startswith(b"%PDF-"), "compiled manuscript is not a PDF")
    audit.require(len(pdf) >= 50_000, "compiled manuscript is unexpectedly small")
    audit.require(b"%%EOF" in pdf[-4096:], "compiled manuscript has no terminal EOF marker")

    for rel in LEAN_FILES:
        stripped = strip_lean_comments_and_strings(read_text(rel))
        for token in ("sorry", "admit", "sorryAx"):
            audit.require(
                re.search(rf"\b{token}\b", stripped) is None,
                f"active Lean placeholder {token!r} found in {rel}",
            )
        audit.require(
            re.search(r"(?m)^\s*axiom\b", stripped) is None,
            f"project-local axiom declaration found in {rel}",
        )

    rooted = read_text("lean-patch/YangMills/KP/RootedCatalan.lean")
    audit.require("def RootedChildFactorialCatalanIdentity" in rooted, "identity interface missing")
    audit.require(
        "rootedChildCount_factorialTreeSum_normalized_le_catalan_of_identity" in rooted,
        "conditional Catalan consumer missing",
    )
    audit.require(
        "theorem rootedChildCount_factorialTreeSum_normalized_eq_catalan" not in rooted,
        "closed identity theorem appeared without status/evidence migration",
    )
    source = read_text("lean-patch/YangMills/RG/AppendixFHsharpCatalanSource.lean")
    audit.require(
        "(hcat : YangMills.KP.RootedChildFactorialCatalanIdentity n)" in source,
        "Appendix-F adapter no longer exposes the Catalan hypothesis",
    )

    patch = read_text("lean-patch/catalan-conditional-adapter.patch")
    audit.require(patch.startswith(f"From {pins['patch']} "), "mailbox patch header mismatch")
    for rel in (
        "YangMills/KP/RootedCatalan.lean",
        "YangMills/RG/AppendixFHsharpCatalanClosure.lean",
        "YangMills/RG/AppendixFHsharpCatalanSource.lean",
        "oracle_check_catalan.lean",
    ):
        audit.require(rel in patch, f"mailbox patch does not mention {rel}")

    build_log = read_text("lean-patch/verification/catalan-build.log")
    audit.require(project["archived_build_marker"] in build_log, "build success marker missing")
    oracle_log = read_text("lean-patch/verification/oracle_check_catalan.log")
    groups = parse_oracle_axioms(oracle_log)
    audit.require(len(groups) == 3, "expected three oracle reports")
    for index, names in enumerate(groups, 1):
        audit.require(names == EXPECTED_AXIOMS, f"oracle report {index} has unexpected axioms: {names}")
    audit.require("sorryAx" not in oracle_log, "oracle log contains sorryAx")

    evidence = json.loads(read_text("evidence/finite-catalan-checks.json"))
    audit.require(evidence.get("schema_version") == 1, "finite evidence schema drift")
    audit.require(
        evidence.get("status") == "finite_exact_computational_evidence_not_formal_proof",
        "finite evidence status overclaims",
    )
    audit.require(evidence.get("max_n") == 8 and evidence.get("graph_max_n") == 7, "finite evidence range drift")
    audit.require(
        set(evidence.get("methods", []))
        == {
            "exhaustive_prufer_words",
            "exhaustive_edge_subset_trees",
            "prufer_occurrence_profiles",
        },
        "finite evidence method set drift",
    )
    result_bytes = json.dumps(
        evidence.get("results", []), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    audit.require(evidence.get("results_sha256") == sha256(result_bytes), "finite evidence result digest mismatch")
    results = evidence.get("results", [])
    audit.require(len(results) == 9, "finite evidence should contain n=0 through n=8")
    if results:
        audit.require(results[-1].get("n") == 8, "finite evidence final order drift")
        audit.require(results[-1].get("expected_weighted_sum") == 57_657_600, "finite evidence n=8 value drift")

    theorem_manifest = json.loads(read_text("archive/theorem-manifest.json"))
    audit.require(theorem_manifest.get("schema_version") == 1, "theorem manifest schema drift")
    audit.require(theorem_manifest.get("artifact_version") == project["version"], "theorem manifest version drift")
    declarations = theorem_manifest.get("declarations", [])
    declaration_names = {entry.get("name") for entry in declarations}
    audit.require(EXPECTED_VERIFIED_DECLARATIONS <= declaration_names, "theorem manifest omits verified declarations")
    audit.require(
        "YangMills.KP.RootedChildFactorialCatalanIdentity" in declaration_names,
        "theorem manifest omits the open identity",
    )
    for entry in declarations:
        source_path = entry.get("source")
        if source_path:
            audit.require((ROOT / source_path).is_file(), f"theorem manifest source missing: {source_path}")
        evidence_path = entry.get("evidence")
        if evidence_path:
            audit.require((ROOT / evidence_path).is_file(), f"theorem evidence missing: {evidence_path}")
    audit.require(
        theorem_manifest.get("formal_boundary", {}).get("closed_exact_catalan_identity") is False,
        "theorem manifest overclaims closure",
    )

    for rel in (
        "README.md",
        "AGENTS.md",
        "lean-patch/CATALAN_PATCH_STATUS.md",
        "docs/CLAIMS_BOUNDARY.md",
        "evidence/README.md",
        "docs/PRUFER_PROFILE_REDUCTION.md",
    ):
        text = read_text(rel).lower()
        audit.require(
            "conditional" in text or "not a proof" in text,
            f"{rel} hides the conditional/evidence boundary",
        )
        audit.require(
            "still open" in text
            or "not certified" in text
            or "remains open" in text
            or "not a substitute" in text,
            f"{rel} hides the unresolved identity",
        )

    version = project["version"]
    date = project["release_date"]
    audit.require(f"version: {version}" in read_text("CITATION.cff"), "CITATION.cff version drift")
    audit.require(f"date-released: {date}" in read_text("CITATION.cff"), "CITATION.cff date drift")
    audit.require(json.loads(read_text("codemeta.json"))["version"] == version, "CodeMeta version drift")
    audit.require(json.loads(read_text(".zenodo.json"))["version"] == version, "Zenodo version drift")
    audit.require(f"## {version} - {date}" in read_text("CHANGELOG.md"), "changelog version/date missing")

    makefile = read_text("Makefile")
    audit.require(
        re.search(r"(?m)^TEX := main\.tex$", makefile) is not None,
        "Makefile must hard-pin TEX := main.tex",
    )
    audit.require(
        re.search(r"(?m)^TRACKED_PDF := Rooted_tree_Catalan_closure\.pdf$", makefile) is not None,
        "Makefile must hard-pin the tracked PDF name",
    )
    audit.require("TEX ?=" not in makefile, "Makefile reintroduced environment-sensitive TEX ?=")
    for target in (
        "actions-check:",
        "finite-check:",
        "paper-refresh:",
        "package-determinism:",
        "verify-release:",
        "history-bundle:",
        "verify-history:",
        "recovery:",
    ):
        audit.require(target in makefile, f"Makefile lacks target {target}")
    package_source = read_text("scripts/package_release.py")
    audit.require("ZIP_STORED" in package_source, "release ZIP is not cross-runtime stored")
    audit.require("ARCHIVED_EVIDENCE_LOGS" in package_source, "source package does not preserve archived Lean evidence logs")
    verifier_source = read_text("scripts/verify_release.py")
    audit.require("run_extracted_self_audit" in verifier_source, "release verifier does not audit the extracted source archive")

    try:
        action_policy = load_policy(ROOT / actions_policy_rel)
        action_errors, action_counts = audit_workflows(ROOT, action_policy)
        for error in action_errors:
            audit.errors.append(f"GitHub Actions policy: {error}")
        audit.require(sum(action_counts.values()) >= 10, "unexpectedly small GitHub Actions reference inventory")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        audit.errors.append(f"invalid GitHub Actions policy: {exc}")

    ci = read_text(".github/workflows/artifact-ci.yml")
    for python_version in project["tooling_python_versions"]:
        audit.require(
            f'"{python_version}"' in ci,
            f"CI tooling matrix omits Python {python_version}",
        )
    audit.require("tooling-matrix:" in ci, "CI tooling portability matrix is missing")
    audit.require("persist-credentials: false" in ci, "CI checkout credentials are persisted")
    audit.require(
        ("make ci" in ci or "make finite-check" in ci)
        and "make package-determinism" in ci
        and "make verify-release" in ci,
        "CI does not enforce finite evidence and deterministic verified releases",
    )
    replay = read_text(".github/workflows/full-lean-replay.yml")
    audit.require(
        "workflow_dispatch:" in replay
        and "Verify immutable upstream pins" in replay
        and "verify_replay_logs.py" in replay,
        "manual full Lean replay workflow is incomplete",
    )
    for value in pins.values():
        audit.require(value in replay, f"full Lean replay workflow lacks pin {value}")
    history = read_text(".github/workflows/history-backup.yml")
    audit.require(
        "git bundle" in history.lower()
        and "create_history_bundle.py" in history
        and "verify_history_bundle.py" in history
        and "fetch-depth: 0" in history,
        "history-backup workflow is incomplete",
    )
    release = read_text(".github/workflows/release.yml")
    audit.require("tags: [\"v*\"]" in release and "gh release create" in release, "tagged release workflow is incomplete")
    audit.require("actions/attest-build-provenance@" in release, "tagged release lacks provenance attestations")
    audit.require("history-release/*" in release, "tagged release omits full-history recovery artifacts")
    dependabot = read_text(".github/dependabot.yml")
    audit.require("groups:" in dependabot and "github-actions:" in dependabot, "Dependabot action updates are not grouped")
    audit.require("open-pull-requests-limit: 1" in dependabot, "Dependabot may open parallel action-update PRs")
    dependency_review = read_text(".github/workflows/dependency-review.yml")
    audit.require("fail-on-severity: high" in dependency_review, "dependency review severity policy drift")
    audit.require("retry-on-snapshot-warnings: true" in dependency_review, "dependency review snapshot retry is disabled")
    audit.require(
        release.count("if: startsWith(github.ref, 'refs/tags/')") >= 3,
        "tag-only release/attestation guards are incomplete",
    )

    check_text_files(audit, files)
    check_python_sources(audit, files)
    check_json_files(audit, files)
    check_local_markdown_links(audit, files)
    check_git(audit)
    for note in audit.notes:
        print(f"NOTE: {note}")
    if audit.errors:
        for error in audit.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"repository audit failed with {len(audit.errors)} error(s)", file=sys.stderr)
        return 1
    print(
        "repository audit passed: provenance, critical blobs, conditional Lean boundary, "
        "finite evidence, theorem manifest, source/history recovery, workflows, PDF, tooling, links, and metadata are consistent"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
