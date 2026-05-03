# Portable Reviewer Package README

## What Is In This Package

This package contains a portable review copy of the `e-dispo-v4.0` ED Disposition Model class project.

Main files:

- `Model_Review_Report.docx`: reviewer-facing report in plain English with technical detail.
- `Model_Reviewer_Checklist.docx`: checklist for structured reviewer feedback.
- `Model_Review_Report.md`: Markdown copy of the report.
- `Model_Reviewer_Checklist.md`: Markdown copy of the checklist.
- `app_dist/`: production static build of the web app.
- `documentation/`: model card, endpoint decision log, NHAMCS appendix, class deliverable map, source index, and QA screenshots.
- `sources/source-index.md`: source links and what they support.

## How To Open The App

Best option:

1. Open a terminal in the `app_dist` folder.
2. Run:

   ```powershell
   python -m http.server 8000
   ```

3. Open this address in a browser:

   ```text
   http://127.0.0.1:8000/
   ```

If Python is not available, the reviewer can still read the DOCX and Markdown files without running the app.

## What To Review First

1. Read `Model_Review_Report.docx`.
2. Open the app and inspect the Model Demo and Documentation areas.
3. Complete `Model_Reviewer_Checklist.docx`.
4. Return the completed checklist and any comments.

## Important Boundary

This is an educational/statistical model package. It is not a clinical tool. It does not diagnose, triage, recommend treatment, recommend discharge, predict death, or tell anyone whether to seek emergency care.
