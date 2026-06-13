# Ebook Build Setup

This folder builds the Tamil parenting ebook
(`../Kuzhandhaigal-Urimai-Pesa-Thayangugiraargal.md`) into shareable formats.

There are two paths depending on what is installed on your machine.

---

## Option A — HTML (no installs, recommended for a quick PDF)

Works with **only Python 3** — no extra packages, no internet.

```bash
make html
# or:
python3 md_to_html.py ../Kuzhandhaigal-Urimai-Pesa-Thayangugiraargal.md \
                      ../Kuzhandhaigal-Urimai-Pesa-Thayangugiraargal.html
```

Then:
1. Open the generated `Kuzhandhaigal-Urimai-Pesa-Thayangugiraargal.html` in any browser
   (Chrome/Edge/Firefox).
2. Tamil text renders via **Noto Tamil** web fonts (with a system-font fallback, so it
   also works offline if the fonts are installed locally).
3. To make a PDF: **File → Print → Destination: Save as PDF**.
   - The stylesheet is print-aware: it uses A5 page size, avoids breaking tables/visual
     boxes across pages, and honours the `\newpage` markers as real page breaks.

The `[[VISUAL]]` blocks render as dashed "Designer Visual Spec" boxes so a designer can
replace each one with the described artwork.

---

## Option B — Word .docx (no installs)

Also needs **only Python 3** — no extra packages, no internet. Produces a real Word
document that opens in Microsoft Word, Google Docs, and LibreOffice Writer.

```bash
make docx
# or:
python3 md_to_docx.py ../Kuzhandhaigal-Urimai-Pesa-Thayangugiraargal.md \
                      ../Kuzhandhaigal-Urimai-Pesa-Thayangugiraargal.docx
```

What you get:
- Proper Word heading styles (Heading 1-4) -> usable for an auto Table of Contents
  (in Word: References -> Table of Contents).
- Bordered tables, shaded quote blocks, dashed "Designer Visual Spec" boxes.
- Hard page breaks at every `\newpage`, A5 page size.
- Tamil text set in **Nirmala UI** (a Tamil-capable font shipped with Windows). On macOS
  or Linux, if Nirmala UI is absent, the app falls back to another installed Tamil font
  (e.g. Latha, Noto Sans Tamil). The text itself is Unicode, so it is never lost — only
  the typeface may differ. To force a specific font, edit the `w:rFonts` line in
  `md_to_docx.py` (search for `Nirmala UI`).

---

## Option C — True PDF / EPUB via pandoc

Produces a typeset PDF and a reflowable EPUB. Requires a toolchain:

**Install (one time):**

| Platform | Command |
|---|---|
| macOS | `brew install pandoc && brew install --cask mactex` then `brew install font-noto-sans-tamil font-noto-serif-tamil` (via `homebrew/cask-fonts`) |
| Ubuntu/Debian | `sudo apt install pandoc texlive-xetex fonts-noto fonts-noto-extra` |
| Windows | Install [pandoc](https://pandoc.org/installing.html), [MiKTeX](https://miktex.org/), and the Noto Tamil fonts from Google Fonts |

**Build:**

```bash
make pdf     # -> ../Kuzhandhaigal-Urimai-Pesa-Thayangugiraargal.pdf
make epub    # -> ../Kuzhandhaigal-Urimai-Pesa-Thayangugiraargal.epub
```

Equivalent raw commands (if you prefer not to use make):

```bash
pandoc ../Kuzhandhaigal-Urimai-Pesa-Thayangugiraargal.md \
  -o ../Kuzhandhaigal-Urimai-Pesa-Thayangugiraargal.pdf \
  --pdf-engine=xelatex \
  -V mainfont="Noto Serif Tamil" -V sansfont="Noto Sans Tamil" \
  -V papersize=a5 -V geometry:margin=16mm \
  --toc --toc-depth=2
```

> **Tamil font note:** XeLaTeX (not pdfLaTeX) is required for correct Tamil shaping.
> The `--pdf-engine=xelatex` flag handles this. If you see boxes instead of letters,
> the Noto Tamil fonts are not installed/visible to the engine.

---

## Files

| File | Purpose |
|---|---|
| `md_to_html.py` | Dependency-free Markdown → styled HTML converter (stdlib only) |
| `md_to_docx.py` | Dependency-free Markdown → Word .docx converter (stdlib only) |
| `Makefile` | `make html` / `make docx` / `make pdf` / `make epub` / `make clean` |
| `README.md` | This file |

## Notes for the designer

Every illustration is specified inline in the source as a `[[VISUAL]]` block with three
parts: a **title**, a **description**, and **layout instructions**. In the HTML output
these appear as dashed orange boxes. Replace each box with the final artwork before
publishing.
