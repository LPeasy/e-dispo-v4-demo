#!/usr/bin/env python3
"""Build DOCX reviewer deliverables from Markdown source files."""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
REVIEWER_DIR = ROOT / "docs" / "reviewer"
OUTPUT_DIR = ROOT / "output" / "doc"

ACCENT = "1F4E79"
ACCENT_DARK = RGBColor(31, 78, 121)
LIGHT_BLUE = "D9EAF7"
LIGHT_GRAY = "F2F2F2"


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    build_docx(
        REVIEWER_DIR / "model-review-report.md",
        OUTPUT_DIR / "Model_Review_Report.docx",
        subtitle="Plain-English review guide for the current pooled empirical v2 educational app",
    )
    build_docx(
        REVIEWER_DIR / "model-reviewer-checklist.md",
        OUTPUT_DIR / "Model_Reviewer_Checklist.docx",
        subtitle="Structured feedback form for current model, evidence, and documentation review",
    )
    build_docx(
        REVIEWER_DIR / "current-model-glossary.md",
        OUTPUT_DIR / "Current_Model_Glossary.docx",
        subtitle="Plain-language glossary for the current E-Dispo review package",
    )
    return 0


def build_docx(source: Path, destination: Path, subtitle: str) -> None:
    doc = Document()
    setup_document(doc)
    lines = source.read_text(encoding="utf-8").splitlines()
    title = lines[0].lstrip("# ").strip()
    add_cover(doc, title, subtitle)
    doc.add_section(WD_SECTION.NEW_PAGE)
    parse_markdown(doc, lines[1:])
    set_core_properties(doc, title)
    doc.save(destination)


def setup_document(doc: Document) -> None:
    section = doc.sections[0]
    section.top_margin = Inches(0.65)
    section.bottom_margin = Inches(0.65)
    section.left_margin = Inches(0.72)
    section.right_margin = Inches(0.72)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Aptos"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Aptos")
    normal.font.size = Pt(10.5)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.08

    for style_name, size in [("Heading 1", 18), ("Heading 2", 14), ("Heading 3", 12)]:
        style = styles[style_name]
        style.font.name = "Aptos Display"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Aptos Display")
        style.font.color.rgb = ACCENT_DARK
        style.font.size = Pt(size)
        style.font.bold = True
        style.paragraph_format.space_before = Pt(10)
        style.paragraph_format.space_after = Pt(5)
        style.paragraph_format.keep_with_next = True

    styles["List Bullet"].font.name = "Aptos"
    styles["List Bullet"].font.size = Pt(10.5)


def add_cover(doc: Document, title: str, subtitle: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(90)
    run = p.add_run(title)
    run.font.name = "Aptos Display"
    run.font.size = Pt(25)
    run.font.bold = True
    run.font.color.rgb = ACCENT_DARK

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(18)
    run = p.add_run(subtitle)
    run.font.size = Pt(12.5)
    run.font.color.rgb = RGBColor(89, 89, 89)

    table = doc.add_table(rows=3, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    table.columns[0].width = Inches(1.8)
    table.columns[1].width = Inches(4.6)
    rows = [
        ("Project", "ED Disposition Personal Risk Model"),
        ("Version", "Endpoint-refined v3"),
        ("Date", "2026-04-28"),
    ]
    for idx, (label, value) in enumerate(rows):
        row = table.rows[idx]
        shade_cell(row.cells[0], LIGHT_BLUE)
        set_cell_text(row.cells[0], label, bold=True)
        set_cell_text(row.cells[1], value)

    doc.add_paragraph()
    add_callout(
        doc,
        "Review boundary",
        "This is an educational/statistical model. It is not a clinical decision tool, and it does not diagnose, triage, recommend treatment, recommend discharge, or tell anyone whether to seek emergency care.",
    )


def parse_markdown(doc: Document, lines: list[str]) -> None:
    idx = 0
    while idx < len(lines):
        line = lines[idx].rstrip()
        if not line:
            idx += 1
            continue
        if line.startswith("## "):
            doc.add_heading(line[3:].strip(), level=1)
            idx += 1
            continue
        if line.startswith("### "):
            doc.add_heading(line[4:].strip(), level=2)
            idx += 1
            continue
        if line.startswith("|") and idx + 1 < len(lines) and lines[idx + 1].startswith("|"):
            table_lines = []
            while idx < len(lines) and lines[idx].startswith("|"):
                table_lines.append(lines[idx])
                idx += 1
            add_markdown_table(doc, table_lines)
            continue
        if line.startswith("- "):
            while idx < len(lines) and lines[idx].startswith("- "):
                add_inline_paragraph(doc, lines[idx][2:].strip(), style="List Bullet")
                idx += 1
            continue
        if line.startswith("```"):
            code_lines = []
            idx += 1
            while idx < len(lines) and not lines[idx].startswith("```"):
                code_lines.append(lines[idx])
                idx += 1
            idx += 1
            add_code_block(doc, "\n".join(code_lines))
            continue
        if line.startswith("Plain-English translation:"):
            add_callout(
                doc,
                "Plain-English translation",
                line.replace("Plain-English translation:", "").strip(),
            )
            idx += 1
            continue
        add_inline_paragraph(doc, line)
        idx += 1


def add_inline_paragraph(doc: Document, text: str, style: str | None = None) -> None:
    p = doc.add_paragraph(style=style)
    add_runs_with_code(p, text)


def add_runs_with_code(paragraph, text: str) -> None:
    parts = re.split(r"(`[^`]+`)", text)
    for part in parts:
        if not part:
            continue
        if part.startswith("`") and part.endswith("`"):
            run = paragraph.add_run(part[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(9.5)
            run.font.color.rgb = RGBColor(64, 64, 64)
        else:
            paragraph.add_run(part)


def add_callout(doc: Document, label: str, text: str) -> None:
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    cell = table.cell(0, 0)
    shade_cell(cell, LIGHT_BLUE)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    label_run = p.add_run(f"{label}: ")
    label_run.bold = True
    label_run.font.color.rgb = ACCENT_DARK
    p.add_run(text)
    set_cell_margins(cell, top=120, bottom=120, start=160, end=160)


def add_code_block(doc: Document, text: str) -> None:
    table = doc.add_table(rows=1, cols=1)
    table.style = "Table Grid"
    cell = table.cell(0, 0)
    shade_cell(cell, LIGHT_GRAY)
    p = cell.paragraphs[0]
    for idx, line in enumerate(text.splitlines()):
        if idx:
            p.add_run().add_break()
        run = p.add_run(line)
        run.font.name = "Consolas"
        run.font.size = Pt(9.5)
    set_cell_margins(cell, top=100, bottom=100, start=140, end=140)


def add_markdown_table(doc: Document, table_lines: list[str]) -> None:
    rows = [split_table_row(line) for line in table_lines if not is_separator(line)]
    if not rows:
        return
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    for row_idx, row_values in enumerate(rows):
        row = table.rows[row_idx]
        for col_idx, value in enumerate(row_values):
            cell = row.cells[col_idx]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell, top=90, bottom=90, start=95, end=95)
            if row_idx == 0:
                shade_cell(cell, ACCENT)
                set_cell_text(cell, value, bold=True, color=RGBColor(255, 255, 255))
            else:
                if row_idx % 2 == 0:
                    shade_cell(cell, "F7FBFE")
                set_cell_text(cell, value)
    doc.add_paragraph()


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_separator(line: str) -> bool:
    cells = split_table_row(line)
    return all(set(cell.replace(":", "").strip()) <= {"-"} for cell in cells)


def set_cell_text(cell, text: str, bold: bool = False, color: RGBColor | None = None) -> None:
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    add_runs_with_code(p, text)
    for run in p.runs:
        run.bold = bold
        if color is not None:
            run.font.color.rgb = color


def shade_cell(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=80, start=80, bottom=80, end=80) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in {"top": top, "start": start, "bottom": bottom, "end": end}.items():
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_core_properties(doc: Document, title: str) -> None:
    props = doc.core_properties
    props.title = title
    props.subject = "ED Disposition Model reviewer documentation"
    props.author = "Codex"
    props.comments = "Generated reviewer package for the current pooled empirical v2 educational app."


if __name__ == "__main__":
    raise SystemExit(main())
