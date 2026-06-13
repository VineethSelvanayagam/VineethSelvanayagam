#!/usr/bin/env python3
"""
Zero-dependency Markdown -> Word (.docx) converter for the Tamil parenting ebook.

A .docx file is an Office Open XML (OOXML) package: a ZIP archive of XML parts.
This script builds that package using ONLY the Python standard library (zipfile),
so it runs anywhere Python 3 exists - no python-docx, no pandoc, no internet.

It maps the Markdown subset used by the ebook to Word constructs:
  headings -> Heading1..4 styles      tables -> bordered w:tbl
  **bold** / *italic* / `code`        blockquotes -> Quote style (shaded)
  [[VISUAL]] -> shaded "designer" box lists -> bulleted / numbered paragraphs
  \\newpage -> hard page break         --- -> bottom-border rule
A Tamil-capable font (Nirmala UI, with Latha/Noto fallbacks via the OS) is set as
the document default, including the complex-script (w:cs) slot Tamil requires.

Usage:
    python3 md_to_docx.py ../<input>.md ../<output>.docx
"""
import sys
import re
import zipfile
from xml.sax.saxutils import escape

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

# ---------------- inline parsing ----------------

TOKEN = re.compile(r"\*\*(.+?)\*\*|(?<!\*)\*([^*]+?)\*(?!\*)|`(.+?)`|\[(.+?)\]\((.+?)\)")


def inline_runs(text):
    """Return list of (text, props) where props subset of {b,i,code,link}."""
    runs = []
    pos = 0
    for m in TOKEN.finditer(text):
        if m.start() > pos:
            runs.append((text[pos:m.start()], {}))
        if m.group(1) is not None:
            runs.append((m.group(1), {"b": True}))
        elif m.group(2) is not None:
            runs.append((m.group(2), {"i": True}))
        elif m.group(3) is not None:
            runs.append((m.group(3), {"code": True}))
        elif m.group(4) is not None:
            runs.append((m.group(4), {"i": True}))  # render link text (URL dropped in docx)
        pos = m.end()
    if pos < len(text):
        runs.append((text[pos:], {}))
    if not runs:
        runs.append(("", {}))
    return runs


def run_xml(text, props, base_color=None):
    rpr = ["<w:rPr>"]
    if props.get("b"):
        rpr.append("<w:b/><w:bCs/>")
    if props.get("i"):
        rpr.append("<w:i/><w:iCs/>")
    if props.get("code"):
        rpr.append('<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/>')
    if base_color:
        rpr.append(f'<w:color w:val="{base_color}"/>')
    rpr.append("</w:rPr>")
    rpr_s = "".join(rpr)
    if rpr_s == "<w:rPr></w:rPr>":
        rpr_s = ""
    return f'<w:r>{rpr_s}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def runs_xml(text, color=None):
    return "".join(run_xml(t, p, color) for t, p in inline_runs(text))


# ---------------- block helpers ----------------

def para(content_runs, *, style=None, jc=None, shade=None, border=False, indent=None):
    ppr = ["<w:pPr>"]
    if style:
        ppr.append(f'<w:pStyle w:val="{style}"/>')
    if shade:
        ppr.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{shade}"/>')
    if border:
        ppr.append('<w:pBdr><w:bottom w:val="single" w:sz="6" w:space="1" w:color="C9C9C9"/></w:pBdr>')
    if indent:
        ppr.append(f'<w:ind w:left="{indent}"/>')
    if jc:
        ppr.append(f'<w:jc w:val="{jc}"/>')
    ppr.append("</w:pPr>")
    ppr_s = "".join(ppr)
    if ppr_s == "<w:pPr></w:pPr>":
        ppr_s = ""
    return f"<w:p>{ppr_s}{content_runs}</w:p>"


def page_break():
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'


def split_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def is_table_sep(line):
    return bool(re.match(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$", line))


def table_xml(header, body):
    cols = len(header)
    borders = (
        "<w:tblBorders>"
        '<w:top w:val="single" w:sz="4" w:color="BFC9D4"/>'
        '<w:left w:val="single" w:sz="4" w:color="BFC9D4"/>'
        '<w:bottom w:val="single" w:sz="4" w:color="BFC9D4"/>'
        '<w:right w:val="single" w:sz="4" w:color="BFC9D4"/>'
        '<w:insideH w:val="single" w:sz="4" w:color="BFC9D4"/>'
        '<w:insideV w:val="single" w:sz="4" w:color="BFC9D4"/>'
        "</w:tblBorders>"
    )
    out = [
        "<w:tbl><w:tblPr><w:tblW w:w=\"0\" w:type=\"auto\"/>",
        borders,
        '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="0" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/>',
        "</w:tblPr>",
    ]
    out.append("<w:tblGrid>" + "<w:gridCol/>" * cols + "</w:tblGrid>")

    # header row
    out.append("<w:tr>")
    for c in header:
        cell_p = para(runs_xml(c, color="FFFFFF"), shade="1D4E89")
        # make header bold by wrapping: simpler -> rebuild runs as bold
        cell_p = (
            '<w:p><w:pPr><w:shd w:val="clear" w:color="auto" w:fill="1D4E89"/></w:pPr>'
            + "".join(run_xml(t, {**p, "b": True}, "FFFFFF") for t, p in inline_runs(c))
            + "</w:p>"
        )
        out.append(f'<w:tc><w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="1D4E89"/></w:tcPr>{cell_p}</w:tc>')
    out.append("</w:tr>")

    # body rows
    for ri, row in enumerate(body):
        cells = (row + [""] * cols)[:cols]
        shade = "F4F6FA" if ri % 2 == 1 else None
        out.append("<w:tr>")
        for c in cells:
            tcpr = f'<w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="{shade}"/></w:tcPr>' if shade else "<w:tcPr/>"
            out.append(f"<w:tc>{tcpr}{para(runs_xml(c))}</w:tc>")
        out.append("</w:tr>")
    out.append("</w:tbl>")
    # a blank paragraph after table (Word requires a p after tbl in many viewers)
    out.append("<w:p/>")
    return "".join(out)


def is_raw_html_line(line):
    s = line.strip()
    return s.startswith("<div") or s.startswith("</div") or s.startswith("<br")


# ---------------- main conversion ----------------

def convert_body(md):
    md = re.sub(r"<!--.*?-->", "", md, flags=re.DOTALL)
    lines = md.split("\n")
    out = []
    i, n = 0, len(lines)
    center = False

    while i < n:
        line = lines[i]
        s = line.strip()

        if s == "":
            i += 1
            continue

        if s == "\\newpage":
            out.append(page_break())
            i += 1
            continue

        if s == "---":
            out.append(para("", border=True))
            i += 1
            continue

        if is_raw_html_line(line):
            if s.startswith("<div align=\"center\"") or s.startswith("<div align='center'"):
                center = True
            elif s.startswith("</div"):
                center = False
            # <br> -> ignored
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            level = min(len(m.group(1)), 4)
            jc = "center" if (center or level == 1) else None
            out.append(para(runs_xml(m.group(2)), style=f"Heading{level}", jc=jc))
            i += 1
            continue

        if s.startswith(">"):
            bq = []
            while i < n and lines[i].strip().startswith(">"):
                bq.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            joined = " ".join(x.strip() for x in bq if x.strip())
            if joined.startswith("[[VISUAL"):
                out.append(para(runs_xml("Designer Visual Spec"), style="VisualLabel", shade="FFF1E0"))
                for bl in bq:
                    if bl.strip():
                        out.append(para(runs_xml(bl.strip()), style="VisualBody", shade="FFF8F0"))
            else:
                for bl in bq:
                    if bl.strip():
                        out.append(para(runs_xml(bl.strip()), style="Quote"))
            continue

        if "|" in line and i + 1 < n and is_table_sep(lines[i + 1]):
            header = split_row(line)
            i += 2
            body = []
            while i < n and "|" in lines[i] and lines[i].strip() != "":
                body.append(split_row(lines[i]))
                i += 1
            out.append(table_xml(header, body))
            continue

        if re.match(r"^\s*[-*]\s+", line):
            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                item = re.sub(r"^\s*[-*]\s+", "", lines[i])
                out.append(para(runs_xml("\u2022\u2002" + item), indent=360))
                i += 1
            continue

        if re.match(r"^\s*\d+\.\s+", line):
            num = 1
            while i < n and re.match(r"^\s*\d+\.\s+", lines[i]):
                item = re.sub(r"^\s*\d+\.\s+", "", lines[i])
                out.append(para(runs_xml(f"{num}.\u2002" + item), indent=360))
                num += 1
                i += 1
            continue

        # paragraph (gather until blank)
        buf = [s]
        i += 1
        while i < n and lines[i].strip() != "" and not re.match(r"^(#{1,6}\s|>|\s*[-*]\s|\s*\d+\.\s)", lines[i]) \
                and "|" not in lines[i] and lines[i].strip() not in ("---", "\\newpage") \
                and not is_raw_html_line(lines[i]):
            buf.append(lines[i].strip())
            i += 1
        out.append(para(runs_xml(" ".join(buf)), jc=("center" if center else None)))

    return "".join(out)


STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr>
<w:rFonts w:ascii="Nirmala UI" w:hAnsi="Nirmala UI" w:cs="Nirmala UI" w:eastAsia="Nirmala UI"/>
<w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="288" w:lineRule="auto"/></w:pPr></w:pPrDefault>
</w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/>
<w:pPr><w:keepNext/><w:spacing w:before="240" w:after="120"/><w:jc w:val="center"/></w:pPr>
<w:rPr><w:b/><w:bCs/><w:color w:val="1D4E89"/><w:sz w:val="40"/><w:szCs w:val="40"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/>
<w:pPr><w:keepNext/><w:spacing w:before="280" w:after="120"/><w:pBdr><w:bottom w:val="single" w:sz="12" w:space="2" w:color="E8843C"/></w:pBdr></w:pPr>
<w:rPr><w:b/><w:bCs/><w:color w:val="1D4E89"/><w:sz w:val="30"/><w:szCs w:val="30"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/>
<w:pPr><w:keepNext/><w:spacing w:before="200" w:after="80"/></w:pPr>
<w:rPr><w:b/><w:bCs/><w:color w:val="E8843C"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading4"><w:name w:val="heading 4"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/>
<w:pPr><w:keepNext/><w:spacing w:before="160" w:after="60"/></w:pPr>
<w:rPr><w:b/><w:bCs/><w:color w:val="52606D"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Quote"><w:name w:val="Quote"/><w:basedOn w:val="Normal"/>
<w:pPr><w:ind w:left="360"/><w:shd w:val="clear" w:color="auto" w:fill="F4F6FA"/><w:pBdr><w:left w:val="single" w:sz="18" w:space="6" w:color="E8843C"/></w:pBdr></w:pPr>
<w:rPr><w:i/><w:iCs/><w:color w:val="334155"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="VisualLabel"><w:name w:val="Visual Label"/><w:basedOn w:val="Normal"/>
<w:pPr><w:spacing w:before="120" w:after="0"/></w:pPr>
<w:rPr><w:b/><w:bCs/><w:color w:val="E8843C"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="VisualBody"><w:name w:val="Visual Body"/><w:basedOn w:val="Normal"/>
<w:pPr><w:spacing w:after="0"/></w:pPr>
<w:rPr><w:color w:val="52606D"/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:style>
</w:styles>"""

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

# A5 page: 148mm x 210mm in twips (1mm = 56.6929 twips)
SECTPR = ('<w:sectPr><w:pgSz w:w="8391" w:h="11906"/>'
          '<w:pgMar w:top="1080" w:right="1000" w:bottom="1080" w:left="1000" '
          'w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>')


def build_document(body):
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document {W}><w:body>{body}{SECTPR}</w:body></w:document>'
    )


def main():
    if len(sys.argv) != 3:
        print("usage: python3 md_to_docx.py <input.md> <output.docx>", file=sys.stderr)
        sys.exit(1)
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, encoding="utf-8") as f:
        md = f.read()
    body = convert_body(md)
    document = build_document(body)

    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", document)
        z.writestr("word/styles.xml", STYLES)
        z.writestr("word/_rels/document.xml.rels", DOC_RELS)
    print(f"Wrote {dst}")


if __name__ == "__main__":
    main()
