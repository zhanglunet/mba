# Published Artifacts

This directory contains public report sources that are safe to publish.

- `published/reports/<brand>/report.html` is copied to
  `site/reports/<brand>/index.html` by `site/build.sh`.
- `metric-brand-auditor/reports/` remains the local runtime output directory and
  is ignored by Git by default.
- Add a brand slug to `site/published-reports.txt` to publish it.
