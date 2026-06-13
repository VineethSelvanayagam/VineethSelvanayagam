# Build targets for the Tamil parenting ebook.
#
# Quick start (no tools needed except Python 3):
#   make html        # -> styled, self-contained HTML (open in a browser, Print -> Save as PDF)
#
# Full e-book output (requires pandoc + a XeLaTeX engine + Noto Tamil fonts installed):
#   make pdf         # -> A5 PDF via pandoc + xelatex
#   make epub        # -> EPUB3
#
# See README.md in this folder for install instructions.

MD     := ../Kuzhandhaigal-Urimai-Pesa-Thayangugiraargal.md
HTML   := ../Kuzhandhaigal-Urimai-Pesa-Thayangugiraargal.html
PDF    := ../Kuzhandhaigal-Urimai-Pesa-Thayangugiraargal.pdf
EPUB   := ../Kuzhandhaigal-Urimai-Pesa-Thayangugiraargal.epub

MAINFONT  := Noto Serif Tamil
SANSFONT  := Noto Sans Tamil

.PHONY: all html pdf epub clean

all: html

html: $(MD)
	python3 md_to_html.py $(MD) $(HTML)

pdf: $(MD)
	pandoc $(MD) -o $(PDF) \
	  --pdf-engine=xelatex \
	  -V mainfont="$(MAINFONT)" \
	  -V sansfont="$(SANSFONT)" \
	  -V monofont="$(SANSFONT)" \
	  -V papersize=a5 \
	  -V geometry:margin=16mm \
	  -V linkcolor=blue \
	  --toc --toc-depth=2

epub: $(MD)
	pandoc $(MD) -o $(EPUB) \
	  --metadata title="குழந்தைகள் உரிமை" \
	  --metadata author="விழிப்புணர்வு வினீத்" \
	  --metadata lang=ta \
	  --toc --toc-depth=2

clean:
	rm -f $(HTML) $(PDF) $(EPUB)
