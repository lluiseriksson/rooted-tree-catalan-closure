TEX := main.tex
TRACKED_PDF := Rooted_tree_Catalan_closure.pdf
PYTHON ?= python3
RELEASE_DIR ?= release
HISTORY_DIR ?= history-release
BUILD_DIR ?= build
BUILT_PDF := $(BUILD_DIR)/Rooted_tree_Catalan_closure.pdf
LATEX_FLAGS ?= -interaction=nonstopmode -halt-on-error -file-line-error

.PHONY: help static audit ci test finite-check finite-refresh paper paper-refresh paper-check tectonic package package-determinism verify-release history-bundle verify-history recovery verify release upstream-replay clean

help:
	@printf '%s\n' \
	  'make static              - audit pins, blobs, Lean boundary, evidence, workflows, metadata' \
	  'make ci                  - static audit, unit tests, and finite Catalan evidence' \
	  'make test                - run repository-tool unit tests' \
	  'make finite-check        - exact finite tree/Prüfer/profile checks through n=8' \
	  'make finite-refresh      - intentionally regenerate tracked finite evidence' \
	  'make paper               - rebuild manuscript into build/ without changing tracked PDF' \
	  'make paper-refresh       - intentionally replace tracked PDF with rebuilt PDF' \
	  'make paper-check         - rebuild and inspect the build PDF' \
	  'make package             - deterministic stored ZIP, checksum, source manifest, and SPDX SBOM' \
	  'make package-determinism - build the release twice and compare every output byte' \
	  'make verify-release      - independently validate all release outputs' \
	  'make history-bundle      - preserve complete Git history and refs in a verified bundle' \
	  'make verify-history      - validate history bundle checksums, refs, and Git structure' \
	  'make recovery            - build and verify source plus full-history recovery artifacts' \
	  'make verify              - non-TeX publication gate' \
	  'make release             - verify, rebuild/inspect paper, and package' \
	  'make upstream-replay     - apply and compile the adapter in a pinned upstream checkout'

static audit:
	$(PYTHON) scripts/check_repository.py

ci: static test finite-check

test:
	$(PYTHON) -m unittest discover -s tests -v

finite-check:
	$(PYTHON) scripts/check_finite_catalan.py

finite-refresh:
	$(PYTHON) scripts/check_finite_catalan.py --write

paper:
	mkdir -p $(BUILD_DIR)
	pdflatex $(LATEX_FLAGS) -output-directory=$(BUILD_DIR) $(TEX)
	pdflatex $(LATEX_FLAGS) -output-directory=$(BUILD_DIR) $(TEX)
	pdflatex $(LATEX_FLAGS) -output-directory=$(BUILD_DIR) $(TEX)
	cp $(BUILD_DIR)/main.pdf $(BUILT_PDF)

paper-refresh: paper
	cp $(BUILT_PDF) $(TRACKED_PDF)

paper-check: paper
	$(PYTHON) scripts/check_pdf.py $(BUILT_PDF)

tectonic:
	mkdir -p $(BUILD_DIR)
	tectonic -X compile $(TEX) --outdir $(BUILD_DIR)
	cp $(BUILD_DIR)/main.pdf $(BUILT_PDF)
	$(PYTHON) scripts/check_pdf.py $(BUILT_PDF)

package: static test finite-check
	$(PYTHON) scripts/package_release.py --output-dir $(RELEASE_DIR)

package-determinism: static test finite-check
	$(PYTHON) scripts/check_determinism.py

verify-release: package
	$(PYTHON) scripts/verify_release.py --release-dir $(RELEASE_DIR)

history-bundle: static
	$(PYTHON) scripts/create_history_bundle.py --output-dir $(HISTORY_DIR)

verify-history: history-bundle
	$(PYTHON) scripts/verify_history_bundle.py --release-dir $(HISTORY_DIR)

recovery: package-determinism verify-release verify-history

verify: static test finite-check package-determinism

release: verify paper-check package verify-release

upstream-replay:
	bash scripts/bootstrap_upstream_patch.sh

clean:
	rm -rf $(BUILD_DIR) $(RELEASE_DIR) $(HISTORY_DIR)
