# QSource

Static site for QSource, the F3 leadership manual, published at
https://f3qsource.web.app. It presents each version of the text unedited and
clearly labelled, so readers can compare versions. Plain HTML/CSS, deployed with
Firebase Hosting.

## The text must not be edited

The original wording is the point of this site. Misspellings, typos and slips
in the source PDFs (e.g. "Ecclesiastics 4:12", "TGalations 5:22-23",
"12Timothy 2:4") are kept deliberately: they are part of the author's voice.
Do not correct, normalise or "clean up" anything in `content/`. Only layout
(line breaks, page numbers, page headers) is removed during conversion.

## Versions on the site

| Path    | Source                                                       |
|---------|--------------------------------------------------------------|
| `/2017/` | *QSource: The F3 Leadership Handbook* (PDF saved Jan 2017): StartEx, Q1–Q4, EndEx |
| `/2018/` | *QSource: The F3 Manual Of Leadership* (PDF created May 2018): Foundation, Q1, Q2, plus the Appendix A lexicon |

Every section page names its version and links to the same QPoint in the other
versions (matched by name; see `ALIASES` in `scripts/build.py`).

## Layout

- `content/*.json`: the text, one record per section, extracted from the PDFs.
  This is the source of truth for the pages.
- `scripts/pdf_to_sections.py`: PDF → JSON converter (uses font size, colour and
  boldness to find titles, Statement/Scripture/Socratic/Synthesis/Spur,
  subheadings, red new terms and footnotes). Text is kept verbatim.
- `scripts/build.py`: JSON → HTML. Regenerates `index.html`, `versions/`,
  `2017/`, `2018/` and `sitemap.xml`. Old `/2021/` URLs redirect to
  `/2017/` (see `firebase.json`); the Handbook was first labelled 2021 from its
  Drive upload date before its PDF metadata showed January 2017.
- `assets/style.css`: the one stylesheet.

## Regenerating

```
pdftohtml -xml -i -q "QSource The F3 Leadership Handbook.pdf" h21   # poppler-utils
python3 scripts/pdf_to_sections.py h21.xml 2017 > content/2017-handbook.json
pdftotext -layout "QSource.Quadrants 1+2 (2018).pdf" q18.txt
python3 scripts/pdf_to_sections.py --glossary q18.txt > content/2018-lexicon.json
python3 scripts/build.py
```

## Deploying

Every push to `main` deploys via `.github/workflows/firebase-hosting-merge.yml`,
which needs a `FIREBASE_SERVICE_ACCOUNT` repository secret. The site is the
`f3qsource` Hosting site inside the `bills-crossroads` Firebase project
(`"site"` in `firebase.json` keeps deploys off that project's default site).
