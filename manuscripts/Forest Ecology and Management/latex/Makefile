# Makefile for LaTeX manuscript build
# Requires: pdflatex, bibtex (or texlive-full)

MAIN    = main
FIGS    = figs
BLDDIR  = build

.PHONY: all clean view

all: $(MAIN).pdf

$(MAIN).pdf: $(MAIN).tex references.bib
	mkdir -p $(BLDDIR)
	pdflatex -output-directory=$(BLDDIR) $(MAIN).tex
	bibtex $(BLDDIR)/$(MAIN)
	pdflatex -output-directory=$(BLDDIR) $(MAIN).tex
	pdflatex -output-directory=$(BLDDIR) $(MAIN).tex
	cp $(BLDDIR)/$(MAIN).pdf .

clean:
	rm -rf $(BLDDIR) $(MAIN).pdf

view: $(MAIN).pdf
	xdg-open $(MAIN).pdf 2>/dev/null || open $(MAIN).pdf 2>/dev/null || start $(MAIN).pdf
