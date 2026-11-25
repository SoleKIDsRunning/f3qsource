#!/usr/bin/env python3
"""Generate the static QSource site from the JSON in content/.

    python3 scripts/build.py          # writes into the repo root

Each edition gets /<edition>/ (table of contents) and /<edition>/<slug>/ (one
page per section). Every page is labelled with the edition it comes from and
links to the same section in the other editions.
"""
import html
import json
import os
import re
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
SITE_NAME = "QSource"
BASE_URL = "https://f3qsource.web.app"

EDITIONS = [
    dict(id="2017", file="2017-handbook.json",
         title="QSource: The F3 Leadership Handbook",
         short="2017 Handbook",
         note="Original, unedited text of the complete handbook (all four quadrants), saved January 2017. "
              "The earliest version on this site.",
         groups=[("I", "StartEx"), ("Q1", "The First Quadrant: DRP"),
                 ("Q2", "The Second Quadrant: IMPACT"),
                 ("Q3", "The Third Quadrant: Group Leadership"),
                 ("Q4", "The Fourth Quadrant: Legacy"), ("EndEx", "EndEx")]),
    dict(id="2018", file="2018-manual.json",
         title="QSource: The F3 Manual Of Leadership",
         short="2018 Manual",
         note="Original, unedited text of the May 2018 manual (Foundation, Quadrant 1 and Quadrant 2), a rework of the 2017 Handbook. "
              "New terms appear in red, as in the original.",
         groups=[("F", "Foundation"), ("Q1", "The First Quadrant: Get Right"),
                 ("Q2", "The Second Quadrant: Live Right")],
         lexicon="2018-lexicon.json"),
]

# Section names that differ between editions but are the same QPoint.
ALIASES = {
    "GROUPS": "GROUP", "THE VIRTUOUS LEADER": "VIRTUOUS LEADER",
    "DEVELOPING TEAMS": "TEAM DEVELOPMENT", "SUA SPONTE LEADERSHIP": "SUA SPONTE LEADER",
    "LEADERSHIP DEVELOPMENT PROCESS": "LDP", "MAMMOM": "MAMMON",
}

PART_TITLES = [("scripture", "Scripture"), ("socratic", "Socratic"),
               ("synthesis", "Synthesis"), ("spur", "Spur")]


def esc(s):
    return html.escape(s, quote=True)


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def match_key(name):
    n = re.sub(r"\s+", " ", name.upper().replace("§", "")).strip()
    return ALIASES.get(n, n)


def display_name(name):
    if name in ("EndEx",):
        return name
    small = {"and", "of", "the", "a", "to"}
    words = name.replace("(TEAM)", "(Team)").split()
    out = []
    for i, w in enumerate(words):
        if w.isupper() and len(w) > 1 and w not in ("DRP", "LDP", "IMPACT", "M"):
            w = w.capitalize() if not (i and w.lower() in small) else w.lower()
        out.append(w)
    return " ".join(out)


def group_of(code):
    if code == "EndEx":
        return "EndEx"
    if code.startswith("I."):
        return "I"
    if code.startswith("F"):
        return "F"
    return code.split(".")[0]


def load_editions():
    eds = []
    for e in EDITIONS:
        secs = json.load(open(os.path.join(CONTENT, e["file"]), encoding="utf-8"))
        for s in secs:
            s["slug"] = slugify(f'{s["code"]} {s["name"]}') if s["code"] != "EndEx" else "endex"
            s["title"] = display_name(s["name"])
            s["key"] = match_key(s["name"])
            s["group_id"] = group_of(s["code"])
        e = dict(e, sections=secs)
        if e.get("lexicon"):
            e["lexicon_rows"] = json.load(open(os.path.join(CONTENT, e["lexicon"]), encoding="utf-8"))
        eds.append(e)
    return eds


def page(title, body, desc, path, crumbs=""):
    url = BASE_URL + path
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>Q</text></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,600;0,700;1,400&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/style.css">
</head>
<body>
<header class="site-header">
  <div class="wrap">
    <a class="brand" href="/"><b>QSource</b><span>The F3 leadership manual</span></a>
    <nav class="top-nav">
      <a href="/2017/">2017 Handbook</a>
      <a href="/2018/">2018 Manual</a>
      <a href="/versions/">Versions</a>
    </nav>
  </div>
</header>
{crumbs}
<main>
{body}
</main>
<footer class="site-footer">
  <div class="wrap">
    <p>QSource is the leadership manual of <a href="https://f3nation.com/">F3 Nation</a>. Text is reproduced exactly as it appears in each version; see <a href="/versions/">About these versions</a>.</p>
  </div>
</footer>
</body>
</html>
"""


def crumbs_html(items):
    parts = [f'<a href="{esc(h)}">{esc(t)}</a>' if h else f"<span>{esc(t)}</span>" for t, h in items]
    return '<nav class="crumbs wrap">' + " &rsaquo; ".join(parts) + "</nav>"


def tidy(text):
    """Merge formatting runs split across PDF text items (e.g. <dfn>P</dfn><dfn>urpose</dfn>)."""
    for tag in ("dfn", "em"):
        text = re.sub(rf"</{tag}>(\s*)<{tag}>", r"\1", text)
    return text


def render_part(items):
    out, in_list = [], False
    for kind, text in items:
        text = tidy(text)
        if kind == "li":
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{text}</li>")
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        if kind == "h":
            out.append(f"<h3>{text}</h3>")
        elif kind == "cite":
            out.append(f'<p class="cite">{text}</p>')
        else:
            out.append(f"<p>{text}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def edition_badge(e):
    return (f'<div class="edition-badge"><span class="tag">{esc(e["short"])}</span>'
            f'<span>From <i>{esc(e["title"])}</i>. {esc(e["note"])}</span></div>')


def section_page(e, idx, eds):
    s = e["sections"][idx]
    secs = e["sections"]
    others = []
    for o in eds:
        if o is e:
            continue
        for t in o["sections"]:
            if t["key"] == s["key"]:
                others.append(f'<a href="/{o["id"]}/{t["slug"]}/">{esc(o["short"])}: {esc(t["code"])} {esc(t["title"])}</a>')
    other_html = ('<aside class="other-versions"><b>This section in other versions</b>'
                  + "".join(others) + "</aside>") if others else ""
    body = [f'<article class="qpoint">', edition_badge(e),
            f'<p class="code">{esc(s["code"]) if s["code"] != "EndEx" else ""}</p>',
            f'<h1>{esc(s["title"])}</h1>']
    if s["statement"]:
        body.append(f'<p class="statement"><span>Statement</span>{esc(s["statement"])}</p>')
    body.append(other_html)
    for key, label in PART_TITLES:
        items = s["parts"].get(key)
        if not items:
            continue
        if key == "synthesis" and len(s["parts"]) == 1:
            body.append(f'<section class="part part-{key}">{render_part(items)}</section>')
        else:
            body.append(f'<section class="part part-{key}"><h2>{label}</h2>{render_part(items)}</section>')
    if s["footnotes"]:
        fns = "".join(f'<li id="fn{esc(n)}" value="{esc(n)}">{t} <a href="#r{esc(n)}" class="back" aria-label="Back to text">&#8617;</a></li>'
                      for n, t in s["footnotes"])
        body.append(f'<section class="footnotes"><h2>Notes</h2><ol>{fns}</ol></section>')
    prev_l = f'<a class="prev" href="/{e["id"]}/{secs[idx-1]["slug"]}/"><small>Previous</small>{esc(secs[idx-1]["code"])} {esc(secs[idx-1]["title"])}</a>' if idx > 0 else "<span></span>"
    next_l = f'<a class="next" href="/{e["id"]}/{secs[idx+1]["slug"]}/"><small>Next</small>{esc(secs[idx+1]["code"])} {esc(secs[idx+1]["title"])}</a>' if idx + 1 < len(secs) else "<span></span>"
    body.append(f'<nav class="pager">{prev_l}{next_l}</nav></article>')
    title = f'{s["code"]} {s["title"]} — {e["short"]} — QSource' if s["code"] != "EndEx" else f'EndEx — {e["short"]} — QSource'
    desc = s["statement"] or f'{s["title"]} from {e["title"]}.'
    path = f'/{e["id"]}/{s["slug"]}/'
    cr = crumbs_html([("QSource", "/"), (e["short"], f'/{e["id"]}/'), (f'{s["code"]} {s["title"]}' if s["code"] != "EndEx" else "EndEx", None)])
    return path, page(title, "\n".join(body), desc, path, cr)


def toc_page(e):
    groups = []
    for gid, gname in e["groups"]:
        items = [s for s in e["sections"] if s["group_id"] == gid]
        if not items:
            continue
        lis = "".join(
            f'<li><a href="/{e["id"]}/{s["slug"]}/"><span class="c">{esc(s["code"]) if s["code"] != "EndEx" else ""}</span>'
            f'<span class="t">{esc(s["title"])}</span>'
            f'{"<span class=s>" + esc(s["statement"]) + "</span>" if s["statement"] else ""}</a></li>'
            for s in items)
        groups.append(f'<section class="toc-group"><h2>{esc(gname)}</h2><ul class="toc">{lis}</ul></section>')
    if e.get("lexicon_rows"):
        groups.append(f'<section class="toc-group"><h2>Appendix</h2><ul class="toc"><li><a href="/{e["id"]}/lexicon/"><span class="c">A</span><span class="t">Lexicon</span><span class="s">Every defined term and the QPoint where it first appears</span></a></li></ul></section>')
    body = f'<div class="wrap narrow">{edition_badge(e)}<h1>{esc(e["title"])}</h1>{"".join(groups)}</div>'
    path = f'/{e["id"]}/'
    return path, page(f'{e["short"]} — QSource', body, e["note"], path,
                      crumbs_html([("QSource", "/"), (e["short"], None)]))


def lexicon_page(e, eds):
    by_code = {s["code"]: s for s in e["sections"]}
    def code_link(c):
        k = c if c in by_code else c.replace("F", "F") if False else c
        s = by_code.get(k)
        return f'<a href="/{e["id"]}/{s["slug"]}/">{esc(c)}</a>' if s else esc(c)
    rows = "".join(f'<tr><th scope="row">{esc(w)}</th><td>{code_link(c)}</td><td>{esc(d)}</td></tr>'
                   for w, c, d in e["lexicon_rows"])
    body = (f'<div class="wrap">{edition_badge(e)}<h1>Lexicon</h1>'
            f'<p class="lede">Appendix A of the 2018 manual: each word, the QPoint where it is first defined, and its definition.</p>'
            f'<div class="table-wrap"><table class="lexicon"><thead><tr><th>Word</th><th>First QPoint</th><th>Definition</th></tr></thead><tbody>{rows}</tbody></table></div></div>')
    path = f'/{e["id"]}/lexicon/'
    return path, page(f'Lexicon — {e["short"]} — QSource', body, "The QSource lexicon of defined terms.", path,
                      crumbs_html([("QSource", "/"), (e["short"], f'/{e["id"]}/'), ("Lexicon", None)]))


def home_page(eds):
    cards = "".join(
        f'<a class="ed-card" href="/{e["id"]}/"><span class="tag">{esc(e["short"])}</span>'
        f'<b>{esc(e["title"])}</b><span>{esc(e["note"])}</span>'
        f'<span class="count">{len(e["sections"])} sections</span></a>' for e in eds)
    body = f"""<header class="hero"><div class="wrap">
<p class="eyebrow">F3 Nation</p>
<h1>QSource</h1>
<p class="sub">The F3 manual of leadership: getting right, living right, leading right and leaving right.</p>
</div></header>
<div class="wrap">
<section class="home-section"><h2>Choose a version</h2>
<p class="lede">QSource has been published in more than one version. Each is reproduced here exactly as written and clearly labelled, so you can read the original and compare.</p>
<div class="ed-grid">{cards}</div>
<p class="more"><a href="/versions/">About these versions &rarr;</a></p>
</section></div>"""
    return "/", page("QSource — The F3 Manual Of Leadership", body,
                     "QSource, the F3 leadership manual, in its original 2017 and 2018 versions.", "/")


def versions_page(eds):
    rows = []
    for e in eds:
        rows.append(f'<tr><th scope="row"><a href="/{e["id"]}/">{esc(e["short"])}</a></th><td><i>{esc(e["title"])}</i></td><td>{len(e["sections"])}</td><td>{esc(e["note"])}</td></tr>')
    body = f"""<div class="wrap narrow"><h1>About these versions</h1>
<p>Every page on this site says which version its text comes from. The text is reproduced exactly as it appears in that version: wording, capitalization and punctuation are unchanged. Only page layout (line breaks and page numbers) has been removed.</p>
<div class="table-wrap"><table class="versions"><thead><tr><th>Version</th><th>Title</th><th>Sections</th><th>Notes</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<h2>How the versions differ</h2>
<p>The <b>2017 Handbook</b> came first (the PDF was saved in January 2017). It opens with a StartEx introduction (QSource, Groups, Leadership Development Process, Four Quadrants), begins Quadrant 1 with a QPoint on the Q himself, and covers all four quadrants, including <i>Group Leadership</i> and <i>Legacy</i>. Each QPoint has a Statement, Scripture, Socratic questions, a Synthesis and a Spur.</p>
<p>The <b>2018 Manual</b> (May 2018) reworks the opening into a five-part Foundation (Disruption, Language, Group, LDP, Preparedness), renames the first two quadrants <i>Get Right</i> and <i>Live Right</i>, and covers those two quadrants only. It adds red highlighting for new terms and an appendix lexicon. The 2025 web edits on f3nation.com were made from this text.</p>
<p>Where the same QPoint appears in more than one version, its page links to the others under <i>This section in other versions</i>.</p>
</div>"""
    return "/versions/", page("About these versions — QSource", body, "Which versions of QSource are on this site and how they differ.", "/versions/",
                              crumbs_html([("QSource", "/"), ("Versions", None)]))


def write(path, text):
    out = os.path.join(ROOT, path.strip("/"), "index.html") if path != "/" else os.path.join(ROOT, "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    eds = load_editions()
    for e in eds:
        d = os.path.join(ROOT, e["id"])
        if os.path.isdir(d):
            shutil.rmtree(d)
    pages = [home_page(eds), versions_page(eds)]
    for e in eds:
        pages.append(toc_page(e))
        if e.get("lexicon_rows"):
            pages.append(lexicon_page(e, eds))
        for i in range(len(e["sections"])):
            pages.append(section_page(e, i, eds))
    for path, text in pages:
        write(path, text)
    urls = "".join(f"<url><loc>{BASE_URL}{p}</loc></url>" for p, _ in pages)
    with open(os.path.join(ROOT, "sitemap.xml"), "w") as f:
        f.write(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    print(f"wrote {len(pages)} pages")


if __name__ == "__main__":
    main()
