#!/usr/bin/env python3
"""Cross-check release, citation, repository, and theorem metadata surfaces."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

from strict_json import StrictJSONError, load_canonical as load_json

ROOT = Path(__file__).resolve().parents[1]


def _json_file(root: Path, relative: str, errors: list[str]) -> dict[str, Any]:
    try:
        value = load_json(root / relative)
    except StrictJSONError as exc:
        errors.append(f"cannot read {relative}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{relative} must contain a JSON object")
        return {}
    return value


def _text_file(root: Path, relative: str, errors: list[str]) -> str:
    try:
        return (root / relative).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"cannot read {relative}: {exc}")
        return ""


def _cff_scalar(text: str, key: str, errors: list[str]) -> str | None:
    matches = re.findall(rf"(?m)^{re.escape(key)}:\s*(.*?)\s*$", text)
    if len(matches) != 1:
        errors.append(f"CITATION.cff must define {key!r} exactly once")
        return None
    raw = matches[0]
    if not raw:
        errors.append(f"CITATION.cff has an empty {key!r}")
        return None
    if raw[0] in {'"', "'"}:
        try:
            parsed = ast.literal_eval(raw)
        except (SyntaxError, ValueError) as exc:
            errors.append(f"CITATION.cff has an invalid quoted {key!r}: {exc}")
            return None
        if not isinstance(parsed, str):
            errors.append(f"CITATION.cff {key!r} is not a string")
            return None
        return parsed
    return raw


def _bib_field(text: str, field: str, errors: list[str]) -> str | None:
    matches = re.findall(
        rf"(?im)^\s*{re.escape(field)}\s*=\s*[{{\"]([^}}\"]*)[}}\"]\s*,?\s*$",
        text,
    )
    if len(matches) != 1:
        errors.append(f"CITATION.bib must define {field!r} exactly once")
        return None
    return matches[0].strip()


def _expect(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def check_metadata_consistency(root: Path = ROOT) -> list[str]:
    """Return deterministic diagnostics for metadata drift across repository surfaces."""
    root = root.resolve()
    errors: list[str] = []
    project = _json_file(root, "project.json", errors)
    if not project:
        return errors
    _expect(errors, project.get("schema_version") == 6, "project.json schema-version drift")
    _expect(errors, project.get("recovery_generation") == 9, "project.json recovery-generation drift")

    version = project.get("version")
    release_date = project.get("release_date")
    repository = project.get("repository")
    _expect(errors, isinstance(version, str) and re.fullmatch(r"\d+\.\d+\.\d+", version) is not None, "project.json has an invalid semantic version")
    try:
        parsed_date = date.fromisoformat(str(release_date))
    except ValueError:
        parsed_date = None
        errors.append("project.json has an invalid release_date")
    _expect(errors, isinstance(repository, str) and repository.startswith("https://github.com/"), "project.json has an invalid repository URL")
    if not isinstance(version, str) or parsed_date is None or not isinstance(repository, str):
        return errors

    cff = _text_file(root, "CITATION.cff", errors)
    cff_title = _cff_scalar(cff, "title", errors)
    _expect(errors, _cff_scalar(cff, "version", errors) == version, "CITATION.cff version drift")
    _expect(errors, _cff_scalar(cff, "date-released", errors) == release_date, "CITATION.cff release-date drift")
    _expect(errors, _cff_scalar(cff, "repository-code", errors) == repository, "CITATION.cff repository drift")
    _expect(errors, _cff_scalar(cff, "license", errors) == project.get("licenses", {}).get("code_and_tooling"), "CITATION.cff license drift")

    bib = _text_file(root, "CITATION.bib", errors)
    _expect(errors, _bib_field(bib, "version", errors) == version, "CITATION.bib version drift")
    _expect(errors, _bib_field(bib, "year", errors) == str(parsed_date.year), "CITATION.bib year drift")
    _expect(errors, _bib_field(bib, "url", errors) == repository, "CITATION.bib repository drift")
    if cff_title is not None:
        _expect(errors, _bib_field(bib, "title", errors) == cff_title, "citation title drift between CFF and BibTeX")

    codemeta = _json_file(root, "codemeta.json", errors)
    _expect(errors, codemeta.get("version") == version, "CodeMeta version drift")
    _expect(errors, codemeta.get("datePublished") == release_date, "CodeMeta publication-date drift")
    _expect(errors, codemeta.get("codeRepository") == repository, "CodeMeta repository drift")

    zenodo = _json_file(root, ".zenodo.json", errors)
    _expect(errors, zenodo.get("version") == version, "Zenodo version drift")
    _expect(errors, zenodo.get("publication_date") == release_date, "Zenodo publication-date drift")
    _expect(errors, zenodo.get("license") == project.get("licenses", {}).get("code_and_tooling"), "Zenodo license drift")

    theorem = _json_file(root, "archive/theorem-manifest.json", errors)
    _expect(errors, theorem.get("artifact_version") == version, "theorem-manifest artifact-version drift")
    _expect(errors, theorem.get("upstream") == project.get("upstream"), "theorem-manifest upstream pins drift")
    boundary = project.get("claim_boundary", {})
    theorem_boundary = theorem.get("formal_boundary", {})
    for key in ("closed_exact_catalan_identity", "conditional_downstream_adapter"):
        _expect(errors, theorem_boundary.get(key) == boundary.get(key), f"theorem-manifest claim boundary drift for {key}")
    open_identity = next(
        (
            entry
            for entry in theorem.get("declarations", [])
            if isinstance(entry, dict)
            and entry.get("name") == "YangMills.KP.RootedChildFactorialCatalanIdentity"
        ),
        None,
    )
    _expect(errors, isinstance(open_identity, dict) and open_identity.get("status") == "open_general_lean_proof", "theorem manifest no longer records the open general Catalan identity")

    changelog = _text_file(root, "CHANGELOG.md", errors)
    _expect(errors, f"## {version} - {release_date}" in changelog, "CHANGELOG.md lacks the current version/date heading")
    release_notes = _text_file(root, "RELEASE_NOTES.md", errors)
    _expect(errors, f"v{version}" in release_notes, "RELEASE_NOTES.md lacks the current version")

    release_policy = project.get("release_policy", {})
    for key in (
        "clean_git_worktree_required",
        "complete_release_checksums",
        "non_destructive_powershell_build",
        "portable_archive_paths",
        "release_output_exact_inventory",
        "source_archive_repackaging",
        "source_manifest_self_check",
        "spdx_2_3_conformant_checksums",
        "standalone_source_zip_verifier",
        "strict_json_metadata",
        "tracked_git_files_only",
        "history_bundle_exact_head_inventory",
        "archive_resource_limits",
        "canonical_json_encoding",
        "canonical_zip_utf8_flags",
        "history_bundle_deep_fsck",
        "history_release_tag_binding",
        "passive_single_revision_pdf",
        "producer_source_zip_self_verification",
        "zip_regular_file_type_bits",
    ):
        _expect(errors, release_policy.get(key) is True, f"project release policy does not enable {key}")
    _expect(
        errors,
        project.get("release_outputs")
        == [
            "rooted-tree-catalan-closure-v{version}.zip",
            "rooted-tree-catalan-closure-v{version}.zip.sha256",
            "rooted-tree-catalan-closure-v{version}.spdx.json",
            "rooted-tree-catalan-closure-v{version}.release.json",
            "rooted-tree-catalan-closure-v{version}.SHA256SUMS",
        ],
        "project release output inventory drift",
    )
    required_checks = project.get("required_checks", [])
    _expect(errors, any("metadata consistency" in str(item).lower() for item in required_checks), "project required checks omit metadata consistency")
    _expect(errors, any("source manifest" in str(item).lower() for item in required_checks), "project required checks omit extracted source-manifest verification")
    _expect(errors, any("standalone source zip" in str(item).lower() for item in required_checks), "project required checks omit standalone source ZIP verification")
    _expect(errors, any("exact git bundle head" in str(item).lower() for item in required_checks), "project required checks omit exact Git bundle head verification")
    _expect(errors, any("tracked git files only" in str(item).lower() for item in required_checks), "project required checks omit tracked-only clean-worktree packaging")
    _expect(errors, any("complete release sha256sums" in str(item).lower() for item in required_checks), "project required checks omit the complete release checksum inventory")
    _expect(errors, any("spdx 2.3 file sha1" in str(item).lower() for item in required_checks), "project required checks omit SPDX 2.3 verification data")
    _expect(errors, any("non-destructive powershell" in str(item).lower() for item in required_checks), "project required checks omit the non-destructive PowerShell build")
    _expect(errors, any("canonical json encoding" in str(item).lower() for item in required_checks), "project required checks omit canonical JSON encoding")
    _expect(errors, any("regular-file type bits" in str(item).lower() for item in required_checks), "project required checks omit canonical ZIP regular-file metadata")
    _expect(errors, any("producer-side source zip self-verification" in str(item).lower() for item in required_checks), "project required checks omit producer ZIP self-verification")
    _expect(errors, any("git fsck --full --strict" in str(item).lower() for item in required_checks), "project required checks omit deep Git bundle fsck")
    _expect(errors, any("annotated v<version> release tag" in str(item).lower() for item in required_checks), "project required checks omit release-tag binding")
    _expect(errors, any("passive single-revision" in str(item).lower() for item in required_checks), "project required checks omit the manuscript PDF safety contract")
    _expect(errors, any("rebuild pdf-version allowlist" in str(item).lower() for item in required_checks), "project required checks omit the rebuild PDF-version contract")
    _expect(errors, project.get("history_inventory_schema") == 3, "project history inventory schema drift")
    manuscript = project.get("manuscript_pdf", {})
    _expect(
        errors,
        manuscript == {
            "active_content": False,
            "author": "Lluis Eriksson",
            "embedded_files": False,
            "encrypted": False,
            "file": "Rooted_tree_Catalan_closure.pdf",
            "forms": False,
            "incremental_updates": False,
            "javascript": False,
            "page_size": "A4",
            "pages": 17,
            "pdf_version": "1.5",
            "rebuild_pdf_versions": ["1.5", "1.7"],
            "title": "Rooted-tree summation and Catalan closure for polymer cluster expansions with holes",
        },
        "project manuscript PDF contract drift",
    )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    errors = check_metadata_consistency(args.root)
    if args.as_json:
        print(json.dumps({"errors": errors, "ok": not errors}, indent=2, sort_keys=True))
    else:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        if not errors:
            print("metadata consistency check passed")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
