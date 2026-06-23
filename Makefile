TEX := main.tex
PDF := Rooted_tree_Catalan_closure.pdf
PACKAGE := rooted-tree-catalan-closure-source.zip

.PHONY: all paper tectonic audit package clean

all: audit paper

paper:
	pdflatex -interaction=nonstopmode -halt-on-error $(TEX)
	pdflatex -interaction=nonstopmode -halt-on-error $(TEX)
	pdflatex -interaction=nonstopmode -halt-on-error $(TEX)
	cp main.pdf $(PDF)

tectonic:
	mkdir -p build
	tectonic -X compile $(TEX) --outdir build
	cp build/main.pdf $(PDF)

audit:
	python3 scripts/audit_artifact.py

package: audit
	python3 scripts/package_release.py

clean:
	rm -rf build release
	rm -f main.aux main.log main.out main.toc main.pdf main.fls main.fdb_latexmk $(PDF)
