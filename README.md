# QSource

Static site for QSource, the F3 leadership manual, published at
https://f3qsource.web.app. It presents each version of the text unedited and
clearly labelled, so readers can compare versions. Plain HTML/CSS, deployed with
Firebase Hosting.

## Versions on the site

| Path    | Source                                                       |
|---------|--------------------------------------------------------------|
| `/2018/` | *QSource: The F3 Manual Of Leadership* (2018 PDF): Foundation, Q1, Q2, plus the Appendix A lexicon |
| `/2021/` | *QSource: The F3 Leadership Handbook* (2021 PDF): StartEx, Q1–Q4, EndEx |

Every section page names its version and links to the same QPoint in the other
versions (matched by name; see `ALIASES` in `scripts/build.py`).

## Layout

- `content/*.json`: the text, one record per section, extracted from the PDFs.
  This is the source of truth for the pages.
- `scripts/pdf_to_sections.py`: PDF → JSON converter (uses font size, colour and
  boldness to find titles, Statement/Scripture/Socratic/Synthesis/Spur,
  subheadings, red new terms and footnotes). Text is kept verbatim.
- `scripts/build.py`: JSON → HTML. Regenerates `index.html`, `versions/`,
  `2018/`, `2021/` and `sitemap.xml`.
- `assets/style.css`: the one stylesheet.

## Regenerating

```
pdftohtml -xml -i -q "QSource The F3 Leadership Handbook.pdf" h21   # poppler-utils
python3 scripts/pdf_to_sections.py h21.xml 2021 > content/2021-handbook.json
pdftotext -layout "QSource.Quadrants 1+2 (2018).pdf" q18.txt
python3 scripts/pdf_to_sections.py --glossary q18.txt > content/2018-lexicon.json
python3 scripts/build.py
```

## Deploying

Every push to `main` deploys via `.github/workflows/firebase-hosting-merge.yml`,
which needs a `FIREBASE_SERVICE_ACCOUNT` repository secret. The site is the
`f3qsource` Hosting site inside the `bills-crossroads` Firebase project
(`"site"` in `firebase.json` keeps deploys off that project's default site).
key JSON from Firebase console → Project settings → Service accounts).
