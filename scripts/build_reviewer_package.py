#!/usr/bin/env python3
"""Assemble the current-model portable reviewer package."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
LEGACY_APP_ROOT = WORKSPACE / "ed-disposition-web-v3"
PACKAGE_ROOT = ROOT / "output" / "reviewer_package" / "current_model_review"
ZIP_PATH = ROOT / "output" / "ED_Disposition_Current_Model_Review_Package_2026-05-01.zip"

ACTIVE_MODEL_ID = "e-dispo-v4.0"

COMBINED_ARTIFACTS: list[str] = []

POOLED_NHAMCS_ARTIFACTS = [
    "e_dispo_v4_pain_severe_calibration.csv",
    "e_dispo_v4_pain_severe_cell_counts.csv",
    "e_dispo_v4_pain_severe_coefficients.csv",
    "e_dispo_v4_pain_severe_covariance.csv",
    "e_dispo_v4_pain_severe_draws.csv",
    "e_dispo_v4_pain_severe_leave_one_year_out.csv",
    "e_dispo_v4_pain_severe_validation_report.md",
]

SUPPORTING_NHAMCS_ARTIFACTS = [
    "nausea_mapping_audit.csv",
    "nausea_model_comparison_metadata.csv",
    "nausea_cell_counts_by_year.csv",
    "nausea_missingness_by_endpoint.csv",
    "nausea_model_comparison_coefficients.csv",
    "nausea_model_comparison_covariance.csv",
    "nausea_model_comparison_draws.csv",
    "nausea_model_comparison_calibration.csv",
    "nausea_leave_one_year_out_validation.csv",
    "nausea_candidate_gate_decision.csv",
    "nausea_candidate_ranked_decision.csv",
    "nausea_candidate_screen_report.md",
]

HISTORICAL_CONTEXT_ARTIFACTS = [
    ("artifacts/nhamcs/endpoint-audit-2022.json", "endpoint-audit-2022.json"),
    ("artifacts/nhamcs/endpoint-audit-2022.csv", "endpoint-audit-2022.csv"),
    ("artifacts/nhamcs/model-fit-2022.json", "model-fit-2022.json"),
    ("artifacts/nhamcs/model-fit-2022-coefficients.csv", "model-fit-2022-coefficients.csv"),
]

REVIEW_DOCS = [
    ("docs/reviewer/model-review-report.md", "Model_Review_Report.md"),
    ("docs/reviewer/model-reviewer-checklist.md", "Model_Reviewer_Checklist.md"),
    ("docs/reviewer/current-model-glossary.md", "Current_Model_Glossary.md"),
    ("docs/reviewer/source-index.md", "source-index.md"),
    ("docs/reviewer/verification-summary.md", "verification-summary.md"),
]

DOCUMENTATION_FILES = [
    ("docs/model-card.md", "model-card.md"),
    ("docs/endpoint-refinement-decision-log.md", "endpoint-refinement-decision-log.md"),
    ("docs/nhamcs-pipeline.md", "nhamcs-pipeline.md"),
    ("docs/class-deliverable-package.md", "class-deliverable-package.md"),
    ("docs/validation/performance-report.md", "performance-report.md"),
    ("docs/validation/predictive-power-usability-review.md", "predictive-power-usability-review.md"),
    ("docs/validation/nausea-candidate-screen.md", "nausea-candidate-screen.md"),
    ("docs/validation/uncertainty-simulation-method.md", "uncertainty-simulation-method.md"),
    ("docs/validation/validation-dossier-readme.md", "validation-dossier-readme.md"),
    ("docs/validation/pas5-acuity-candidate-screen.md", "pas5-acuity-candidate-screen.md"),
    ("docs/validation/deficiency-review-next-phase.md", "deficiency-review-next-phase.md"),
    ("README.md", "app-readme.md"),
]

STALE_REVIEW_PHRASES = [
    "The current coefficients are " + "prototype assumptions",
    "current coefficients are " + "prototype assumptions",
    "The current class model uses " + "seven inputs",
    "The app does not claim " + "NHAMCS-derived coefficients are active",
    "the current app has not yet " + "completed that path",
]


def main() -> int:
    validate_review_copy()
    run_command(["npm", "run", "test"])
    run_command(["npm", "run", "lint"])
    run_command(["npm", "run", "build"])
    run_command(["npm", "run", "check:dist"])
    run_command([str(python_with_module("docx")), "scripts/build_reviewer_docs.py"])

    validate_active_model_matches_app()

    if PACKAGE_ROOT.exists():
        shutil.rmtree(PACKAGE_ROOT)
    PACKAGE_ROOT.mkdir(parents=True)

    copy_file(ROOT / "docs" / "reviewer" / "portable-package-readme.md", PACKAGE_ROOT / "README_FIRST.md")
    copy_docx_outputs()
    copy_review_docs()
    copy_documentation()
    copy_app_dist()
    copy_current_model_artifacts()
    copy_historical_context()
    copy_qa_evidence()
    copy_technical_source_extract()

    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    zip_dir(PACKAGE_ROOT, ZIP_PATH)
    print(ZIP_PATH)
    return 0


def validate_review_copy() -> None:
    paths = [
        ROOT / "README.md",
        ROOT / "docs" / "reviewer" / "model-review-report.md",
        ROOT / "docs" / "reviewer" / "model-reviewer-checklist.md",
        ROOT / "docs" / "reviewer" / "portable-package-readme.md",
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for phrase in STALE_REVIEW_PHRASES:
            if phrase in text:
                raise RuntimeError(f"Stale review phrase in {path}: {phrase}")


def validate_active_model_matches_app() -> None:
    model_source = (ROOT / "src" / "data" / "eDispoV4Model.ts").read_text(encoding="utf-8")
    if ACTIVE_MODEL_ID not in model_source:
        raise RuntimeError("Active model ID is not present in eDispoV4Model.ts.")
    draw_metadata = (ROOT / "src" / "data" / "pooledEmpiricalCoefficientDraws.ts").read_text(encoding="utf-8")
    if ACTIVE_MODEL_ID not in draw_metadata:
        raise RuntimeError("Active app export model ID is not present in coefficient draw metadata.")


def run_command(command: list[str]) -> None:
    command_text = " ".join(command)
    completed = subprocess.run(
        command_text if os.name == "nt" else command,
        cwd=ROOT,
        shell=os.name == "nt",
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed: {command_text}")


def python_with_module(module_name: str) -> Path:
    candidates = [
        Path(sys.executable),
        Path.home()
        / ".cache"
        / "codex-runtimes"
        / "codex-primary-runtime"
        / "dependencies"
        / "python"
        / ("python.exe" if os.name == "nt" else "python"),
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        completed = subprocess.run(
            [str(candidate), "-c", f"import {module_name}"],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if completed.returncode == 0:
            return candidate
    raise RuntimeError(
        f"Could not find a Python runtime with required module: {module_name}"
    )


def copy_docx_outputs() -> None:
    for source_name, dest_name in [
        ("Model_Review_Report.docx", "Model_Review_Report.docx"),
        ("Model_Reviewer_Checklist.docx", "Model_Reviewer_Checklist.docx"),
        ("Current_Model_Glossary.docx", "Current_Model_Glossary.docx"),
    ]:
        copy_file(ROOT / "output" / "doc" / source_name, PACKAGE_ROOT / dest_name)


def copy_review_docs() -> None:
    docs_dir = PACKAGE_ROOT / "review_docs"
    docs_dir.mkdir()
    for source, dest_name in REVIEW_DOCS:
        copy_file(ROOT / source, docs_dir / dest_name)


def copy_documentation() -> None:
    docs_dir = PACKAGE_ROOT / "documentation"
    docs_dir.mkdir()
    for source, dest_name in DOCUMENTATION_FILES:
        copy_file(ROOT / source, docs_dir / dest_name)


def copy_app_dist() -> None:
    app_dist = ROOT / "dist"
    copy_tree(app_dist, PACKAGE_ROOT / "app_dist")
    write_launcher(PACKAGE_ROOT / "app_dist" / "START_LOCAL_SERVER.cmd")


def copy_current_model_artifacts() -> None:
    artifact_root = PACKAGE_ROOT / "current_model_artifacts"
    pooled_source = current_source_dir("outputs/nhamcs_pooled")

    combined_dest = artifact_root / "combined"
    combined_dest.mkdir(parents=True)
    if COMBINED_ARTIFACTS:
        combined_source = current_source_dir("outputs/combined")
        for name in COMBINED_ARTIFACTS:
            copy_file(combined_source / name, combined_dest / name)

    pooled_dest = artifact_root / "nhamcs_pooled"
    pooled_dest.mkdir()
    for name in POOLED_NHAMCS_ARTIFACTS:
        copy_file(pooled_source / name, pooled_dest / name)

    supporting_dest = artifact_root / "supporting_not_active"
    supporting_dest.mkdir()
    for name in SUPPORTING_NHAMCS_ARTIFACTS:
        copy_file(pooled_source / name, supporting_dest / name)

    draws_dest = artifact_root / "app_draws"
    draws_dest.mkdir()
    copy_file(
        ROOT / "src" / "data" / "pooled-empirical-coefficient-draws.csv",
        draws_dest / "pooled-empirical-coefficient-draws.csv",
    )

    write_current_artifact_readme(artifact_root)


def copy_historical_context() -> None:
    historical_root = PACKAGE_ROOT / "historical_context_optional" / "nhamcs_2022_baseline"
    historical_root.mkdir(parents=True)
    copied = []
    for source_relative, dest_name in HISTORICAL_CONTEXT_ARTIFACTS:
        source = LEGACY_APP_ROOT / source_relative
        if source.exists():
            copy_file(source, historical_root / dest_name)
            copied.append(dest_name)
    write_historical_readme(historical_root, copied)


def copy_qa_evidence() -> None:
    qa_root = PACKAGE_ROOT / "qa_evidence"
    qa_root.mkdir()
    source_dir = ROOT / "output" / "playwright"
    if source_dir.exists():
        for path in sorted(source_dir.iterdir()):
            if not path.is_file():
                continue
            if path.name.startswith("current-model-") or path.name.startswith("prompt7-") or path.name.startswith("prompt8-"):
                copy_file(path, qa_root / path.name)
    png_count = len(list(qa_root.glob("*.png")))
    qa_md_count = len(list(qa_root.glob("*.md")))
    if png_count < 2:
        raise RuntimeError("Current reviewer package requires at least two QA screenshots in output/playwright.")
    if qa_md_count < 1:
        write_qa_summary(qa_root / "current-model-static-qa.md")


def copy_technical_source_extract() -> None:
    source_extract = PACKAGE_ROOT / "technical_source_extract"
    copy_tree(ROOT / "src" / "model", source_extract / "src" / "model")
    copy_tree(ROOT / "src" / "data", source_extract / "src" / "data")
    copy_tree(ROOT / "scripts" / "nhamcs", source_extract / "scripts" / "nhamcs")
    copy_tree(ROOT / "scripts" / "modeling", source_extract / "scripts" / "modeling")
    copy_file(ROOT / "src" / "App.tsx", source_extract / "src" / "App.tsx")
    copy_file(ROOT / "package.json", source_extract / "package.json")
    copy_file(ROOT / "vite.config.ts", source_extract / "vite.config.ts")
    copy_file(ROOT / "scripts" / "build_reviewer_docs.py", source_extract / "scripts" / "build_reviewer_docs.py")
    copy_file(ROOT / "scripts" / "build_reviewer_package.py", source_extract / "scripts" / "build_reviewer_package.py")
    copy_file(ROOT / "scripts" / "check_dist_portability.mjs", source_extract / "scripts" / "check_dist_portability.mjs")


def current_source_dir(relative: str) -> Path:
    candidates = [ROOT / relative, LEGACY_APP_ROOT / relative]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Missing current-model artifact directory: {relative}")


def copy_file(source: Path, destination: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_tree(source: Path, destination: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(source)
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".playwright-cli", "node_modules"))


def write_launcher(path: Path) -> None:
    path.write_text(
        "@echo off\n"
        "cd /d \"%~dp0\"\n"
        "echo Starting local server for the E-Dispo current model reviewer app...\n"
        "echo Open http://127.0.0.1:8000/ in your browser.\n"
        "python -m http.server 8000\n",
        encoding="utf-8",
    )


def write_current_artifact_readme(path: Path) -> None:
    (path / "README.md").write_text(
        "# Current Model Artifacts\n\n"
        "These files support the active reduced pooled NHAMCS 2018-2022 e-dispo-v4.0 model.\n\n"
        f"Active model ID: `{ACTIVE_MODEL_ID}`.\n\n"
        "What this is: evidence and metadata for the model currently used by the app.\n\n"
        "Why it matters: reviewers can inspect the exported model, coefficient evidence, calibration outputs, and uncertainty assets without reading source code first.\n\n"
        "What it does not prove: these files do not establish clinical validity or transportability to other settings.\n\n"
        "Raw NHAMCS public-use data is not included.\n",
        encoding="utf-8",
    )


def write_historical_readme(path: Path, copied: list[str]) -> None:
    files = "\n".join(f"- `{name}`" for name in copied) or "- No historical files were available."
    (path / "README.md").write_text(
        "# Historical 2022 NHAMCS Baseline Context\n\n"
        "These files are optional context only.\n\n"
        "They are not the active app model. The active model is the pooled NHAMCS 2018-2022 e-dispo-v4.0 export.\n\n"
        "Included files:\n\n"
        f"{files}\n\n"
        "Use these files only to understand earlier endpoint and validation work.\n",
        encoding="utf-8",
    )


def write_qa_summary(path: Path) -> None:
    path.write_text(
        "# Current Model QA Evidence\n\n"
        "The package build runs `npm run test`, `npm run lint`, `npm run build`, and `npm run check:dist` before copying files.\n\n"
        "The app build includes the coefficient draw CSV under `app_dist/assets` and is intended to be served by a static HTTP server.\n",
        encoding="utf-8",
    )


def zip_dir(source_dir: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(source_dir.parent))


if __name__ == "__main__":
    raise SystemExit(main())
