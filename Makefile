TEX := main.tex
PDF := Rooted_tree_Catalan_closure.pdf

.PHONY: paper tectonic clean

paper:
	pdflatex -interaction=nonstopmode -halt-on-error $(TEX)
	pdflatex -interaction=nonstopmode -halt-on-error $(TEX)
	pdflatex -interaction=nonstopmode -halt-on-error $(TEX)
	cp main.pdf $(PDF)

tectonic:
	mkdir -p build
	tectonic -X compile $(TEX) --outdir build
	cp build/main.pdf $(PDF)

clean:
	rm -rf build
	rm -f main.aux main.log main.out main.toc main.pdf main.fls main.fdb_latexmk $(PDF)
