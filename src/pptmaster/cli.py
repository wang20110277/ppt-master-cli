#!/usr/bin/env python3
"""PPT Master CLI — unified command-line interface.

Usage:
    ppm create <input_path> [--format ppt169] [-o dir]
    ppm init <name> [--format ppt169] [--dir projects]
    ppm import <project> <sources...> [--move]
    ppm validate <project>
    ppm info <project>
    ppm convert <file_or_url> [-o output.md]
    ppm finalize <project> [--dry-run] [--only ...]
    ppm export <project> [-s final] [--only native|legacy] [-o output]
    ppm split <project>
    ppm check <project>
    ppm config list-formats|list-colors|list-industries
    ppm image <prompt> [--aspect-ratio 16:9] [-o dir]
    ppm <input_path> <output_path>     # auto pipeline
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


def _scripts_dir() -> Path:
    """Locate the scripts directory."""
    try:
        from pptmaster._paths import get_scripts_dir
        return get_scripts_dir()
    except ImportError:
        return Path(__file__).resolve().parent / "scripts"


def _run_script(module_path: str, argv: list[str]) -> int:
    """Run a script module with the given argv."""
    # Try package import first
    try:
        parts = module_path.replace("/", ".").replace("\\", ".")
        mod = __import__(f"pptmaster.scripts.{parts}", fromlist=["main"])
        old_argv = sys.argv
        sys.argv = [module_path] + argv
        try:
            mod.main()
        except SystemExit as e:
            return e.code if isinstance(e.code, int) else 0
        finally:
            sys.argv = old_argv
        return 0
    except (ImportError, AttributeError):
        pass

    # Fallback: run as standalone script via subprocess
    script = _scripts_dir() / module_path
    result = subprocess.run(
        [sys.executable, str(script)] + argv,
        cwd=Path.cwd(),
    )
    return result.returncode


# ── Subcommand handlers ─────────────────────────────────────

def cmd_create(args: argparse.Namespace) -> None:
    argv = [args.input_document, "--format", args.format]
    if args.output:
        argv += ["-o", args.output]
    sys.exit(_run_script("create_project", argv))


def cmd_init(args: argparse.Namespace) -> None:
    argv = ["init", args.name, "--format", args.format]
    if args.dir:
        argv += ["--dir", args.dir]
    sys.exit(_run_script("project_manager", argv))


def cmd_import(args: argparse.Namespace) -> None:
    argv = ["import-sources", args.project] + args.sources
    if args.move:
        argv.append("--move")
    elif args.copy:
        argv.append("--copy")
    sys.exit(_run_script("project_manager", argv))


def cmd_validate(args: argparse.Namespace) -> None:
    sys.exit(_run_script("project_manager", ["validate", args.project]))


def cmd_info(args: argparse.Namespace) -> None:
    sys.exit(_run_script("project_manager", ["info", args.project]))


def cmd_convert(args: argparse.Namespace) -> None:
    input_path = args.file
    # Detect URL
    if urlparse(input_path).scheme in ("http", "https"):
        argv = [input_path]
        if args.output:
            argv += ["-o", args.output]
        sys.exit(_run_script("source_to_md/web_to_md", argv))

    ext = Path(input_path).suffix.lower()
    converter_map = {
        ".pdf": "source_to_md/pdf_to_md",
        ".docx": "source_to_md/doc_to_md",
        ".doc": "source_to_md/doc_to_md",
        ".odt": "source_to_md/doc_to_md",
        ".rtf": "source_to_md/doc_to_md",
        ".epub": "source_to_md/doc_to_md",
        ".ipynb": "source_to_md/doc_to_md",
        ".html": "source_to_md/doc_to_md",
        ".pptx": "source_to_md/ppt_to_md",
        ".ppt": "source_to_md/ppt_to_md",
        ".pptm": "source_to_md/ppt_to_md",
    }
    converter = converter_map.get(ext)
    if not converter:
        print(f"[ERROR] Unsupported file type: {ext}")
        print(f"   Supported: .pdf .docx .doc .odt .rtf .epub .ipynb .html .pptx")
        sys.exit(1)

    argv = [input_path]
    if args.output:
        argv += ["-o", args.output]
    sys.exit(_run_script(converter, argv))


def cmd_finalize(args: argparse.Namespace) -> None:
    argv = [args.project]
    if args.dry_run:
        argv.append("--dry-run")
    if args.quiet:
        argv.append("--quiet")
    if args.only:
        argv += ["--only"] + args.only
    sys.exit(_run_script("finalize_svg", argv))


def cmd_export(args: argparse.Namespace) -> None:
    argv = [args.project, "-s", args.source]
    if args.only:
        argv += ["--only", args.only]
    if args.output:
        argv += ["-o", args.output]
    sys.exit(_run_script("svg_to_pptx", argv))


def cmd_split(args: argparse.Namespace) -> None:
    argv = [args.project]
    if args.quiet:
        argv.append("-q")
    sys.exit(_run_script("total_md_split", argv))


def cmd_check(args: argparse.Namespace) -> None:
    argv = [args.project]
    if args.format:
        argv += ["--format", args.format]
    sys.exit(_run_script("svg_quality_checker", argv))


def cmd_config(args: argparse.Namespace) -> None:
    if args.action == "export" and args.output:
        sys.exit(_run_script("config", ["export", args.output]))
    sys.exit(_run_script("config", [args.action]))


def cmd_image(args: argparse.Namespace) -> None:
    argv = [args.prompt or ""]
    if args.aspect_ratio:
        argv += ["--aspect_ratio", args.aspect_ratio]
    if args.image_size:
        argv += ["--image_size", args.image_size]
    if args.output:
        argv += ["-o", args.output]
    if args.backend:
        argv += ["-b", args.backend]
    sys.exit(_run_script("image_gen", argv))


def cmd_update(args: argparse.Namespace) -> None:
    sys.exit(_run_script("update_repo", []))


def auto_pipeline(args: argparse.Namespace) -> None:
    """Simplified: ppm <input> <output> — auto-detect and convert."""
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists() and not urlparse(str(input_path)).scheme:
        print(f"[ERROR] Input not found: {input_path}")
        sys.exit(1)

    # Determine project name
    if input_path.is_file():
        name = input_path.stem
    else:
        name = input_path.name or "presentation"

    print(f"[ppm] Auto pipeline: {input_path} → {output_path}")

    # Step 1: Convert to markdown
    import tempfile
    tmp = tempfile.mkdtemp(prefix="ppm_")
    md_out = os.path.join(tmp, "content.md")
    ext = input_path.suffix.lower() if input_path.is_file() else ""

    if urlparse(str(input_path)).scheme in ("http", "https"):
        rc = _run_script("source_to_md/web_to_md", [str(input_path), "-o", md_out])
    elif ext == ".pdf":
        rc = _run_script("source_to_md/pdf_to_md", [str(input_path), "-o", md_out])
    elif ext in (".docx", ".doc", ".odt", ".epub", ".html"):
        rc = _run_script("source_to_md/doc_to_md", [str(input_path), "-o", md_out])
    elif ext in (".pptx", ".ppt"):
        rc = _run_script("source_to_md/ppt_to_md", [str(input_path), "-o", md_out])
    elif ext in (".md", ".markdown", ".txt"):
        import shutil
        shutil.copy2(str(input_path), md_out)
        rc = 0
    else:
        print(f"[ERROR] Unsupported input type: {ext}")
        sys.exit(1)

    if rc != 0:
        print("[ERROR] Conversion failed")
        sys.exit(rc)

    # Step 2: Init project
    from pptmaster._paths import get_scripts_dir
    scripts = get_scripts_dir()
    project_dir = os.path.join(tmp, f"{name}_ppt169")

    rc = _run_script("project_manager", ["init", name, "--format", "ppt169", "--dir", tmp])
    if rc != 0:
        print("[ERROR] Project init failed")
        sys.exit(rc)

    # Step 3: Import source
    rc = _run_script("project_manager", ["import-sources", project_dir, md_out, "--move"])
    if rc != 0:
        print("[ERROR] Import failed")
        sys.exit(rc)

    print(f"\n[ppm] Project created: {project_dir}")
    print(f"[ppm] Source content imported. Next steps:")
    print(f"  1. Generate SVG pages (use Claude Code with ppt-master skill)")
    print(f"  2. ppm finalize {project_dir}")
    print(f"  3. ppm export {project_dir} -o {output_path}")

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


# ── Argument parser ──────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ppm",
        description="PPT Master CLI — AI-driven presentation generation",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # create
    p = sub.add_parser("create", help="Create project from input document")
    p.add_argument("input_document", help="Input file path or URL")
    p.add_argument("--format", default="ppt169", help="Canvas format (default: ppt169)")
    p.add_argument("-o", "--output", default=None, help="Output directory for PPTX")

    # init
    p = sub.add_parser("init", help="Initialize a new project")
    p.add_argument("name", help="Project name")
    p.add_argument("--format", default="ppt169", help="Canvas format (default: ppt169)")
    p.add_argument("--dir", default=None, help="Base directory (default: projects)")

    # import
    p = sub.add_parser("import", help="Import sources into project")
    p.add_argument("project", help="Project path")
    p.add_argument("sources", nargs="+", help="Source files or URLs")
    p.add_argument("--move", action="store_true", help="Move files into project")
    p.add_argument("--copy", action="store_true", help="Copy files into project")

    # validate
    p = sub.add_parser("validate", help="Validate project structure and SVGs")
    p.add_argument("project", help="Project path")

    # info
    p = sub.add_parser("info", help="Show project info")
    p.add_argument("project", help="Project path")

    # convert
    p = sub.add_parser("convert", help="Convert file/URL to markdown")
    p.add_argument("file", help="Input file path or URL")
    p.add_argument("-o", "--output", help="Output markdown path")

    # finalize
    p = sub.add_parser("finalize", help="Post-process SVG files")
    p.add_argument("project", help="Project path")
    p.add_argument("--dry-run", "-n", action="store_true")
    p.add_argument("--quiet", "-q", action="store_true")
    p.add_argument("--only", nargs="+", help="Run specific steps only")

    # export
    p = sub.add_parser("export", help="Export project to PPTX")
    p.add_argument("project", help="Project path")
    p.add_argument("-s", "--source", default="final", help="Source dir (default: final)")
    p.add_argument("--only", choices=["native", "legacy"], help="Export only one version")
    p.add_argument("-o", "--output", help="Output PPTX path")

    # split
    p = sub.add_parser("split", help="Split speaker notes")
    p.add_argument("project", help="Project path")
    p.add_argument("-q", "--quiet", action="store_true")

    # check
    p = sub.add_parser("check", help="SVG quality check")
    p.add_argument("project", help="Project path or SVG file")
    p.add_argument("--format", default=None, help="Expected canvas format")

    # config
    p = sub.add_parser("config", help="Show configuration")
    p.add_argument("action", choices=["list-formats", "list-colors", "list-industries", "export", "format"])
    p.add_argument("output", nargs="?", default=None, help="Output file (for export)")

    # image
    p = sub.add_parser("image", help="Generate AI image")
    p.add_argument("prompt", nargs="?", default=None, help="Image prompt")
    p.add_argument("--aspect-ratio", default="16:9")
    p.add_argument("--image-size", default="1K")
    p.add_argument("-o", "--output", help="Output directory")
    p.add_argument("--backend", "-b", help="Image backend")

    # update
    sub.add_parser("update", help="Update pptmaster")

    # version
    parser.add_argument("-v", "--version", action="store_true", help="Show version")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.version:
        try:
            from pptmaster import __version__
            print(f"pptmaster-cli {__version__}")
        except ImportError:
            print("pptmaster-cli (unknown version)")
        return

    if args.command is None:
        # Check for positional <input> <output> auto-pipeline
        if len(sys.argv) == 3:
            args.input = sys.argv[1]
            args.output = sys.argv[2]
            auto_pipeline(args)
            return
        parser.print_help()
        return

    dispatch = {
        "create": cmd_create,
        "init": cmd_init,
        "import": cmd_import,
        "validate": cmd_validate,
        "info": cmd_info,
        "convert": cmd_convert,
        "finalize": cmd_finalize,
        "export": cmd_export,
        "split": cmd_split,
        "check": cmd_check,
        "config": cmd_config,
        "image": cmd_image,
        "update": cmd_update,
    }
    handler = dispatch.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
