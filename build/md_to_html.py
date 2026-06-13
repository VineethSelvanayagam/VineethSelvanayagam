#!/usr/bin/env python3
"""
Zero-dependency Markdown -> styled HTML converter for the Tamil parenting ebook.

Why this exists:
  - The standard toolchain (pandoc / LaTeX / weasyprint) was not available, and the
    build environment had no internet access to install it.
  - This script uses ONLY the Python standard library, so it runs anywhere Python 3 exists.
  - The produced HTML is fully self-contained, renders Tamil correctly (Noto Sans Tamil via
    Google Fonts with a robust system-font fallback), and exports to PDF directly from any
    browser via  File -> Print -> Save as PDF.

Usage:
    python3 md_to_html.py ../Kuzhandhaigal-Urimai-Pesa-Thayangugiraargal.md ../Kuzhandhaigal-Urimai-Pesa-Thayangugiraargal.html

It deliberately supports the subset of Markdown used by the ebook:
  headings, bold/italic/inline-code/links, blockquotes (incl. [[VISUAL]] designer boxes),
  pipe tables, ordered/unordered lists (incl. checkbox glyphs), horizontal rules,
  raw <div>/<br> passthrough, HTML comments, and the \\newpage page-break marker.
"""
import sys
import re
import html

# ---------- inline formatting ----------

def fmt_inline(text: str) -> str:
    """Apply inline markdown to a single run of text (already a text node, not raw HTML)."""
    text = html.escape(text, quote=False)
    # inline code
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    # links [t](u)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    # bold then italic
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    return text


def is_raw_html_line(line: str) -> bool:
    s = line.strip()
    return s.startswith("<div") or s.startswith("</div") or s.startswith("<br")


# ---------- block parsing ----------

def split_row(line: str):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def is_table_sep(line: str) -> bool:
    return bool(re.match(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$", line))


def render_table(rows):
    head = rows[0]
    body = rows[2:]
    out = ['<table>', '<thead><tr>']
    for c in head:
        out.append(f"<th>{fmt_inline(c)}</th>")
    out.append('</tr></thead>')
    out.append('<tbody>')
    for r in body:
        out.append('<tr>')
        # pad/truncate to header width
        cells = (r + [""] * len(head))[: len(head)]
        for c in cells:
            out.append(f"<td>{fmt_inline(c)}</td>")
        out.append('</tr>')
    out.append('</tbody></table>')
    return "\n".join(out)


def render_blockquote(lines):
    # lines: content lines with leading '> ' already stripped
    joined = " ".join(l.strip() for l in lines if l.strip())
    if joined.startswith("[[VISUAL"):
        # Designer visual specification box
        out = ['<div class="visual-spec">']
        out.append('<div class="visual-spec-label">\U0001F3A8 Designer Visual Spec</div>')
        for l in lines:
            s = l.strip()
            if not s:
                continue
            out.append(f"<p>{fmt_inline(s)}</p>")
        out.append('</div>')
        return "\n".join(out)
    # normal blockquote: keep line breaks (used for quotes + sample dialogues)
    parts = []
    for l in lines:
        s = l.strip()
        if s:
            parts.append(fmt_inline(s))
    inner = "<br>\n".join(parts)
    return f"<blockquote><p>{inner}</p></blockquote>"


def convert(md: str) -> str:
    # strip HTML comments (incl. multiline)
    md = re.sub(r"<!--.*?-->", "", md, flags=re.DOTALL)
    lines = md.split("\n")
    out = []
    i = 0
    n = len(lines)

    def flush_para(buf):
        if buf:
            out.append(f"<p>{fmt_inline(' '.join(buf))}</p>")
            buf.clear()

    para = []

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # blank line
        if stripped == "":
            flush_para(para)
            i += 1
            continue

        # page break marker
        if stripped == "\\newpage":
            flush_para(para)
            out.append('<div class="page-break"></div>')
            i += 1
            continue

        # horizontal rule (not a table sep)
        if stripped == "---":
            flush_para(para)
            out.append("<hr>")
            i += 1
            continue

        # raw html passthrough
        if is_raw_html_line(line):
            flush_para(para)
            out.append(stripped)
            i += 1
            continue

        # headings
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush_para(para)
            level = len(m.group(1))
            out.append(f"<h{level}>{fmt_inline(m.group(2))}</h{level}>")
            i += 1
            continue

        # blockquote block
        if stripped.startswith(">"):
            flush_para(para)
            bq = []
            while i < n and lines[i].strip().startswith(">"):
                content = re.sub(r"^\s*>\s?", "", lines[i])
                bq.append(content)
                i += 1
            out.append(render_blockquote(bq))
            continue

        # table block
        if "|" in line and i + 1 < n and is_table_sep(lines[i + 1]):
            flush_para(para)
            tbl = [split_row(line), None]
            i += 2  # skip header + sep
            rows = [tbl[0], []]
            data = []
            while i < n and "|" in lines[i] and lines[i].strip() != "":
                data.append(split_row(lines[i]))
                i += 1
            full = [tbl[0], []] + data
            out.append(render_table(full))
            continue

        # unordered list (incl. checkbox glyphs that begin with '- ')
        if re.match(r"^\s*[-*]\s+", line):
            flush_para(para)
            items = []
            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(re.sub(r"^\s*[-*]\s+", "", lines[i]))
                i += 1
            out.append("<ul>" + "".join(f"<li>{fmt_inline(it)}</li>" for it in items) + "</ul>")
            continue

        # ordered list
        if re.match(r"^\s*\d+\.\s+", line):
            flush_para(para)
            items = []
            while i < n and re.match(r"^\s*\d+\.\s+", lines[i]):
                items.append(re.sub(r"^\s*\d+\.\s+", "", lines[i]))
                i += 1
            out.append("<ol>" + "".join(f"<li>{fmt_inline(it)}</li>" for it in items) + "</ol>")
            continue

        # default: paragraph text
        para.append(stripped)
        i += 1

    flush_para(para)
    return "\n".join(out)


# ---------- HTML shell with print/PDF-friendly styling ----------

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Tamil:wght@400;500;700&family=Noto+Serif+Tamil:wght@400;600;700&display=swap');

:root{
  --ink:#1f2933; --muted:#52606d; --accent:#1d4e89; --accent2:#e8843c;
  --soft:#f4f6fa; --line:#d9e2ec; --green:#2f8f5b; --red:#c0392b;
}
*{box-sizing:border-box;}
body{
  font-family:'Noto Serif Tamil','Latha','Nirmala UI',serif;
  color:var(--ink); line-height:1.75; margin:0;
  background:#e9edf2;
}
.page{
  max-width:820px; margin:24px auto; background:#fff; padding:64px 72px;
  box-shadow:0 2px 18px rgba(0,0,0,.08); border-radius:4px;
}
h1,h2,h3,h4{font-family:'Noto Sans Tamil','Nirmala UI',sans-serif; line-height:1.4; color:var(--accent);}
h1{font-size:2.0rem; text-align:center; margin:.2em 0 .6em;}
h2{font-size:1.5rem; border-bottom:3px solid var(--accent2); padding-bottom:.25em; margin-top:1.8em;}
h3{font-size:1.2rem; color:var(--accent2);}
h4{font-size:1.05rem; color:var(--muted);}
p{margin:.6em 0;}
hr{border:0; border-top:1px solid var(--line); margin:1.6em 0;}
strong{color:var(--ink);}
code{background:var(--soft); padding:.1em .4em; border-radius:4px; font-size:.95em;}
a{color:var(--accent);}

blockquote{
  margin:1.2em 0; padding:.8em 1.2em; background:var(--soft);
  border-left:5px solid var(--accent2); border-radius:0 6px 6px 0; font-style:italic;
}
blockquote p{margin:0;}

.visual-spec{
  margin:1.4em 0; padding:1em 1.2em; background:#fff8f0;
  border:1px dashed var(--accent2); border-radius:8px; font-size:.9rem; color:var(--muted);
}
.visual-spec-label{
  font-family:'Noto Sans Tamil',sans-serif; font-weight:700; color:var(--accent2);
  font-style:normal; margin-bottom:.4em; letter-spacing:.02em;
}
.visual-spec p{margin:.25em 0;}

table{border-collapse:collapse; width:100%; margin:1.2em 0; font-size:.95rem;}
th,td{border:1px solid var(--line); padding:.55em .7em; text-align:left; vertical-align:top;}
th{background:var(--accent); color:#fff; font-family:'Noto Sans Tamil',sans-serif;}
tbody tr:nth-child(even){background:var(--soft);}

ul,ol{margin:.6em 0 .6em 1.2em;}
li{margin:.25em 0;}

.page-break{break-after:page; page-break-after:always; height:0;}

@media print{
  body{background:#fff;}
  .page{box-shadow:none; margin:0; max-width:none; padding:0 12mm; border-radius:0;}
  h2{break-before:auto;}
  .visual-spec,blockquote,table{break-inside:avoid;}
  @page{ size:A5; margin:16mm 14mm; }
}
"""

SHELL = """<!DOCTYPE html>
<html lang="ta">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<main class="page">
{body}
</main>
</body>
</html>
"""


def main():
    if len(sys.argv) != 3:
        print("usage: python3 md_to_html.py <input.md> <output.html>", file=sys.stderr)
        sys.exit(1)
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, encoding="utf-8") as f:
        md = f.read()
    body = convert(md)
    title = "\u0b95\u0bc1\u0bb4\u0ba8\u0bcd\u0ba4\u0bc8\u0b95\u0bb3\u0bcd \u0b89\u0bb0\u0bbf\u0bae\u0bc8 \u2014 \u0baa\u0bc6\u0bb1\u0bcd\u0bb1\u0bcb\u0bb0\u0bcd \u0bb5\u0bb4\u0bbf\u0b95\u0bbe\u0b9f\u0bcd\u0b9f\u0bbf"
    out = SHELL.format(title=title, css=CSS, body=body)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"Wrote {dst} ({len(out):,} bytes)")


if __name__ == "__main__":
    main()
