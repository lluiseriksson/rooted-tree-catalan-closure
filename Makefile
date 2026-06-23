TEX := main.tex
PDF := Rooted_tree_Catalan_closure.pdf
PYTHON ?= python3
RELEASE_DIR ?= release
LATEX_FLAGS ?= -interaction=nonstopmode -halt-on-error -file-line-error

.PHONY: help audit static paper tectonic verify package package-determinism verify-release release clean

help:
	@printf '%s\n' \
	  'make static              - audit pins, critical blobs, Lean boundary, logs, metadata' \
	  'make paper               - rebuild the PDF with pdflatex' \
	  'make tectonic            - rebuild the PDF with tectonic' \
	  'make verify              - static audit, rebuild paper, then structural recheck' \
	  'make package             - deterministic ZIP, checksum, SPDX SBOM, release metadata' \
	  'make package-determinism - build the release twice and compare every output byte' \
	  'make verify-release      - build and independently verify release outputs' \
	  'make release             - complete local publication gate' \
	  'make clean               - remove generated build and release files'

audit static:
	$(PYTHON) scripts/check_repository.py

paper:
	pdflatex $(LATEX_FLAGS) $(TEX)
	pdflatex $(LATEX_FLAGS) $(TEX)
	pdflatex $(LATEX_FLAGS) $(TEX)
	cp main.pdf $(PDF)

tectonic:
	mkdir -p build
	tectonic -X compile $(TEX) --outdir build
	cp build/main.pdf $(PDF)

verify: static paper
	$(PYTHON) scripts/check_repository.py --accept-rebuilt-pdf

package: static
	$(PYTHON) scripts/package_release.py --output-dir $(RELEASE_DIR)

package-determinism: static
	$(PYTHON) scripts/check_determinism.py

verify-release: package
	$(PYTHON) scripts/verify_release.py --release-dir $(RELEASE_DIR)

release: verify package-determinism verify-release

clean:
	rm -rf build $(RELEASE_DIR)
	rm -f main.aux main.log main.out main.toc main.pdf main.fls main.fdb_latexmk main.synctex.gz
