#!/usr/bin/env python3
"""PPT Master — Quick project creation from a source document.

Creates a hidden .project directory alongside the input file, converts the
source to Markdown, and records a path reference (no copy / no move).

Usage:
    ppm create <input_path> [--format ppt169] [-o output_dir]
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

try:
    from project_utils import normalize_canvas_format, CANVAS_FORMATS
except ImportError:
    _tools = Path(__file__).resolve().parent
    if str(_tools) not in sys.path:
        sys.path.insert(0, str(_tools))
    from project_utils import normalize_canvas_format, CANVAS_FORMATS  # type: ignore

try:
    from pptmaster._paths import get_scripts_dir, PKG_ROOT
    TOOLS_DIR = get_scripts_dir()
    SKILL_DIR = PKG_ROOT
except ImportError:
    TOOLS_DIR = Path(__file__).resolve().parent
    SKILL_DIR = TOOLS_DIR.parent

from project_manager import (
    ProjectManager,
    is_url,
    sanitize_name,
    derive_url_basename,
    PDF_SUFFIXES,
    DOC_SUFFIXES,
    PRESENTATION_SUFFIXES,
    TEXT_SOURCE_SUFFIXES,
)

SOURCE_REF_FILE = "source_ref.json"


def _resolve_source_type(input_path: str) -> tuple[str, str]:
    """Return (source_type, stem) from an input path or URL."""
    if is_url(input_path):
        return "url", sanitize_name(derive_url_basename(input_path))

    path = Path(input_path).resolve()
    stem = path.stem
    suffix = path.suffix.lower()

    if suffix in PDF_SUFFIXES:
        return "pdf", stem
    if suffix in DOC_SUFFIXES:
        return "doc", stem
    if suffix in PRESENTATION_SUFFIXES:
        return "presentation", stem
    if suffix in TEXT_SOURCE_SUFFIXES:
        return "text", stem
    return "unknown", stem


def create(
    input_path: str,
    canvas_format: str = "ppt169",
    output_dir: str | None = None,
) -> str:
    """Create a hidden project from an input document.

    Returns the project directory path.
    """
    normalized_format = normalize_canvas_format(canvas_format)
    if normalized_format not in CANVAS_FORMATS:
        available = ", ".join(sorted(CANVAS_FORMATS.keys()))
        raise ValueError(
            f"Unsupported canvas format: {canvas_format} "
            f"(available: {available})"
        )

    source_type, stem = _resolve_source_type(input_path)

    if source_type == "unknown" and not is_url(input_path):
        suffix = Path(input_path).suffix.lower()
        print(f"[WARN] Unrecognized file type: {suffix}")

    # Determine parent directory (where the source file lives)
    if is_url(input_path):
        parent_dir = Path.cwd()
    else:
        source = Path(input_path).resolve()
        if not source.exists():
            raise FileNotFoundError(f"Input file not found: {source}")
        parent_dir = source.parent

    # Build hidden project directory name
    date_str = datetime.now().strftime("%Y%m%d")
    dir_name = f".{stem}_{normalized_format}_{date_str}"
    project_path = parent_dir / dir_name

    if project_path.exists():
        raise FileExistsError(f"Project directory already exists: {project_path}")

    # Create subdirectory structure
    for rel in (
        "svg_output", "svg_final", "images", "notes",
        "templates", "sources", "exports",
    ):
        (project_path / rel).mkdir(parents=True, exist_ok=True)

    # Write source reference
    ref_data = {
        "type": "create_mode",
        "source_path": str(Path(input_path).resolve()) if not is_url(input_path) else input_path,
        "source_type": source_type,
        "format": normalized_format,
        "created": datetime.now().isoformat(timespec="seconds"),
        "output_dir": str(output_dir) if output_dir else str(parent_dir),
    }
    (project_path / SOURCE_REF_FILE).write_text(
        json.dumps(ref_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Convert source to Markdown inside sources/
    pm = ProjectManager()
    sources_dir = project_path / "sources"
    md_path = sources_dir / f"{stem}.md"

    if source_type == "url":
        pm._import_url(input_path, md_path)
    elif source_type == "pdf":
        pm._import_pdf(Path(input_path).resolve(), md_path)
    elif source_type == "doc":
        pm._import_doc(Path(input_path).resolve(), md_path)
    elif source_type == "presentation":
        pm._import_presentation(Path(input_path).resolve(), md_path)
    elif source_type == "text":
        pm._normalize_text_source(Path(input_path).resolve(), sources_dir)
    else:
        # Unknown: just copy the file into sources/ as-is
        import shutil
        shutil.copy2(str(Path(input_path).resolve()), str(sources_dir / Path(input_path).name))

    # Write README
    canvas_info = CANVAS_FORMATS[normalized_format]
    out_dir = ref_data["output_dir"]
    (project_path / "README.md").write_text(
        f"# {stem}\n\n"
        f"- Source: {ref_data['source_path']}\n"
        f"- Canvas: {normalized_format} ({canvas_info['dimensions']})\n"
        f"- Created: {date_str}\n"
        f"- Mode: create (source referenced in-place)\n\n"
        "## Directories\n\n"
        "- `svg_output/`: raw SVG output\n"
        "- `svg_final/`: finalized SVG output\n"
        "- `images/`: presentation assets\n"
        "- `notes/`: speaker notes\n"
        "- `templates/`: project templates\n"
        "- `sources/`: converted markdown\n"
        "- `exports/`: generated PPTX files\n",
        encoding="utf-8",
    )

    # Print result
    print(f"Project created: {project_path}")
    print(f"  Source: {ref_data['source_path']}")
    print(f"  Canvas: {canvas_info['name']} ({canvas_info['dimensions']})")
    print(f"  Output: {out_dir}")
    print()
    print("Next steps:")
    print(f"  1. Generate SVG pages (use Claude Code with ppt-master skill)")
    print(f"  2. ppm finalize \"{project_path}\"")
    print(f'  3. ppm export "{project_path}" -s final -o "{out_dir}/{stem}.pptx"')

    return str(project_path)


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="create_project",
        description="Create a hidden project from a source document",
    )
    parser.add_argument("input_path", help="Input file path or URL")
    parser.add_argument("--format", default="ppt169", help="Canvas format (default: ppt169)")
    parser.add_argument("-o", "--output", default=None, help="Output directory for PPTX")

    args = parser.parse_args()

    try:
        create(args.input_path, args.format, args.output)
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
