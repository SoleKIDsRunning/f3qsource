#!/usr/bin/env python3
"""Convert a QSource PDF into one JSON record per section.

Usage:
    pdftohtml -xml -i -q SOURCE.pdf out      # writes out.xml
    python3 pdf_to_sections.py out.xml EDITION > sections.json

The PDFs were laid out in Word, so structure is recovered from fonts:
  - section titles:  large (>=24pt) Noteworthy, e.g. "Foundation/DISRUPTION (F1)"
  - part labels:     Noteworthy "Statement:", "Scripture:", "Socratic", "Synthesis", "Spur"
  - subheadings:     bold body-size Calibri
  - new terms:       red (#c00000) body text (2018 only)
  - footnotes:       smaller text at the bottom of each page
  - footnote marks:  tiny (<=12pt) digits inline in the body
Text is kept verbatim; only layout (line breaks, page numbers) is removed.
"""
import html
import json
import re
import sys

LABELS = {"statement": "statement", "scripture": "scripture", "socratic": "socratic",
          "synthesis": "synthesis", "spur": "spur"}
BULLET_GLYPHS = {"§", "ü", "•", "o", "", ""}


def load(path):
    x = open(path, encoding="utf-8").read()
    specs = {}
    for m in re.finditer(r'<fontspec id="(\d+)" size="(\d+)" family="([^"]+)" color="([^"]+)"', x):
        specs[m[1]] = (int(m[2]), m[3].split("+")[-1], m[4])
    items = []
    for pm in re.finditer(r'<page number="(\d+)"(.*?)</page>', x, re.S):
        page = int(pm[1])
        for m in re.finditer(r'<text top="(\d+)" left="(\d+)" width="(\d+)" height="(\d+)" font="(\d+)">(.*?)</text>', pm[2]):
            raw = m[6]
            size, fam, color = specs[m[5]]
            items.append(dict(page=page, top=int(m[1]), left=int(m[2]), width=int(m[3]),
                              size=size, fam=fam, color=color, bold="<b>" in raw,
                              italic="<i>" in raw,
                              text=html.unescape(re.sub(r"<[^>]+>", "", raw))))
    return items


def lines_of(items):
    """Group text items into visual lines (same page, tops within 6px)."""
    out = []
    for it in sorted(items, key=lambda i: (i["page"], i["top"], i["left"])):
        if out and out[-1][0]["page"] == it["page"] and abs(out[-1][0]["top"] - it["top"]) <= 6:
            out[-1].append(it)
        else:
            out.append([it])
    for ln in out:
        ln.sort(key=lambda i: i["left"])
    return out


def is_blank(ln):
    return all(not i["text"].strip() for i in ln)


def esc(s):
    return html.escape(s, quote=False)


def render_inline(ln, body_size):
    """Render a line's items to HTML: red terms -> <dfn>, tiny digits -> footnote refs."""
    parts = []
    for i in ln:
        t = i["text"]
        if not t:
            continue
        if i["size"] <= 12 and t.strip().isdigit() and i["fam"] != "Wingdings":
            n = t.strip()
            parts.append(f'<sup class="fn-ref"><a href="#fn{n}" id="r{n}">{n}</a></sup>')
            continue
        e = esc(t)
        if i["color"].lower() == "#c00000" and i["size"] >= body_size - 1 and t.strip():
            e = f"<dfn>{e.strip()}</dfn>" + (" " if t.endswith(" ") else "")
        elif i["italic"] and t.strip():
            e = f"<em>{e}</em>"
        parts.append(e)
    s = "".join(parts)
    return re.sub(r"\s+", " ", s)


def text_of(ln):
    return re.sub(r"\s+", " ", "".join(i["text"] for i in ln)).strip()


TITLE_RE = re.compile(r"^(?:§\s*)?(?:(Foundation|StartEx)\s*/\s*)?(.+?)\s*\(\s*([A-Z]+\d*(?:\.\d+)?)\s*\)\s*$")


def parse(path, edition):
    items = load(path)
    body_size = 18
    lines = lines_of(items)
    sections = []
    cur = None
    para = None      # current paragraph buffer (list of html strings)
    block = None     # current part name
    fn_cur = None
    prev = None      # (left, right) of previous body line
    bullet_left = None
    min_left = min(i["left"] for i in items if i["text"].strip() and i["size"] >= body_size)
    max_right = max(i["left"] + i["width"] for i in items if i["text"].strip() and i["size"] >= body_size)

    def flush():
        nonlocal para
        if para and cur is not None:
            s = re.sub(r"\s+", " ", " ".join(para)).strip()
            if s:
                cur["parts"].setdefault(block or "synthesis", []).append(("p", s))
        para = None

    for ln in lines:
        if is_blank(ln):
            continue
        txt = text_of(ln)
        sizes = [i["size"] for i in ln if i["text"].strip()]
        maxsize = max(sizes)
        first = next(i for i in ln if i["text"].strip())

        # page numbers / running footer
        if first["top"] > 1080 and re.fullmatch(r"\d+", txt):
            continue

        # 2018 Appendix A glossary table: stop (parsed separately)
        if "DEFINITION" in txt and "WORD" in txt:
            break
        if txt == "EndEx" and cur is not None:
            flush()
            cur = dict(edition=edition, code="EndEx", name="EndEx", group="", statement="",
                       parts={}, footnotes=[])
            sections.append(cur)
            block = "synthesis"
            prev = None
            continue

        # section title
        if maxsize >= 24 and any(i["fam"].startswith("Noteworthy") for i in ln):
            m = TITLE_RE.match(txt)
            if m:
                flush()
                cur = dict(edition=edition, code=m[3], name=m[2].strip(" §"), group=m[1] or "",
                           statement="", parts={}, footnotes=[])
                sections.append(cur)
                block = None
                fn_cur = None
                prev = None
                continue
        if cur is None:
            continue

        # footnotes: smaller-than-body text in the lower part of a page
        if maxsize < body_size - 2 and first["fam"] != "Wingdings":
            flush()
            m = re.match(r"^(\d+)\s*(.*)$", txt)
            if m and first["size"] <= 12:
                rest = render_inline(ln[1:], body_size).strip() if len(ln) > 1 else m[2]
                fn_cur = [m[1], rest]
                cur["footnotes"].append(fn_cur)
            elif fn_cur is not None:
                fn_cur[1] += " " + render_inline(ln, body_size).strip()
            continue
        fn_cur = None
        if first["text"].strip() not in BULLET_GLYPHS:
            bullet_left = None if not (para is None and first["left"] > (bullet_left or 9999)) else bullet_left

        # part labels
        if first["fam"].startswith("Noteworthy"):
            word = first["text"].strip().rstrip(":").lower()
            if word in LABELS:
                flush()
                block = LABELS[word]
                rest = [i for i in ln if i is not first and not i["fam"].startswith("Noteworthy")]
                if block == "statement":
                    cur["statement"] = text_of(rest)
                elif rest and text_of(rest):
                    para = [render_inline(rest, body_size)]
                continue

        # bullets
        if first["text"].strip() in BULLET_GLYPHS and first["fam"] in ("Wingdings", "SymbolMT", "CourierNewPSMT", "Symbol"):
            flush()
            bullet_left = first["left"]
            prev = None
            rest = [i for i in ln if i is not first]
            s = render_inline(rest, body_size).strip()
            if s:
                cur["parts"].setdefault(block or "synthesis", []).append(("li", s))
            continue

        # continuation of a bullet that wraps onto the next line (deep indent, no glyph)
        lst = cur["parts"].get(block or "synthesis")
        if (para is None and lst and lst[-1][0] == "li" and bullet_left is not None
                and first["left"] > bullet_left + 5 and not first["bold"]):
            lst[-1] = ("li", lst[-1][1] + " " + render_inline(ln, body_size).strip())
            continue

        # subheading: whole line bold at body size
        if all(i["bold"] for i in ln if i["text"].strip()) and maxsize >= body_size - 1:
            flush()
            cur["parts"].setdefault(block or "synthesis", []).append(("h", esc(txt)))
            prev = None
            continue

        # scripture reference line (Gabriola)
        if first["fam"] == "Gabriola":
            flush()
            cur["parts"].setdefault(block or "scripture", []).append(("cite", esc(txt)))
            continue

        if block == "statement":
            cur["statement"] = (cur["statement"] + " " + txt).strip()
            continue

        # body text: a new paragraph starts after a short (paragraph-ending) line,
        # or when the first line is indented relative to the line before it
        s = render_inline(ln, body_size)
        left = first["left"]
        right = max(i["left"] + i["width"] for i in ln if i["text"].strip())
        if prev is not None and prev[2] != first["page"]:
            # paragraph continuing across a page break: only an indent starts a new one
            new = para is None or left > prev[0] + 20
        else:
            new = (para is None or prev is None or prev[1] < max_right - 90
                   or left > prev[0] + 20)
        if new:
            flush()
            para = [s]
        else:
            para.append(s)
        prev = (left, right, first["page"])
    flush()
    for sec in sections:
        sec["parts"] = {k: [list(x) for x in v] for k, v in sec["parts"].items()}
    return sections


def parse_glossary(layout_txt):
    """Parse the 2018 Appendix A table from `pdftotext -layout` output."""
    lines = open(layout_txt, encoding="utf-8").read().split("\n")
    start = next(i for i, l in enumerate(lines) if "DEFINITION" in l and "WORD" in l)
    rows = []
    row_re = re.compile(r"^(\S.*?)\s{2,}((?:Q\d|F)\d*(?:\.\d+)?)\s+(.*)$")
    for l in lines[start + 1:]:
        if not l.strip() or re.fullmatch(r"\s*\d+\s*", l) or ("DEFINITION" in l and "WORD" in l) \
                or l.strip() in ("FIRST", "QPoint"):
            continue
        m = row_re.match(l)
        if m:
            rows.append([m[1].strip(), m[2], m[3].strip()])
        elif rows:
            rows[-1][2] += " " + l.strip()
    return rows


if __name__ == "__main__":
    if sys.argv[1] == "--glossary":
        json.dump(parse_glossary(sys.argv[2]), sys.stdout, ensure_ascii=False, indent=1)
    else:
        json.dump(parse(sys.argv[1], sys.argv[2]), sys.stdout, ensure_ascii=False, indent=1)
