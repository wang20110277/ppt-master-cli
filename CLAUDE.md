# CLAUDE.md

## Project Overview

PPT Master is an AI-driven presentation generation engine (CLI + scripts). Through multi-role collaboration (Strategist → Image_Generator → Executor), it converts source documents (PDF/DOCX/URL/Markdown) into natively editable PPTX with real PowerPoint shapes (DrawingML).

**Core Pipeline**: `Source Document → Create Project → Template Option → Strategist Eight Confirmations → [Image_Generator] → Executor → Post-processing → Export PPTX`

**Skill repo**: AI role definitions, templates, and the SKILL.md workflow live in the sibling `ppt-master-skill` repo (`../ppt-master-skill/`). The `ppm` CLI reads templates/references from there automatically.

## Common Commands

```bash
# Source content conversion
python3 src/pptmaster/scripts/source_to_md/pdf_to_md.py <PDF_file>
python3 src/pptmaster/scripts/source_to_md/doc_to_md.py <DOCX_or_other_file>
python3 src/pptmaster/scripts/source_to_md/ppt_to_md.py <PPTX_file>
python3 src/pptmaster/scripts/source_to_md/web_to_md.py <URL>
node src/pptmaster/scripts/source_to_md/web_to_md.cjs <URL>       # fallback only

# Project management
ppm create <input_file_or_url> [--format ppt169] [-o output_dir]   # One-step: hidden .project dir
ppm init <project_name> --format ppt169
ppm import <project_path> <source_files...> --move
ppm validate <project_path>

# Image tools
python3 src/pptmaster/scripts/image_gen.py "prompt" --aspect_ratio 16:9 --image_size 1K -o <project_path>/images

# SVG quality check
python3 src/pptmaster/scripts/svg_quality_checker.py <project_path>

# Post-processing pipeline (MUST run sequentially, one at a time — NEVER batch)
python3 src/pptmaster/scripts/total_md_split.py <project_path>
# ✅ Confirm no errors before running the next command
python3 src/pptmaster/scripts/finalize_svg.py <project_path>
# ✅ Confirm no errors before running the next command
python3 src/pptmaster/scripts/svg_to_pptx.py <project_path> -s final
```

## Architecture

- `src/pptmaster/scripts/` — Runnable tool scripts (converters, finalizer, exporter, etc.)
- `src/pptmaster/scripts/docs/` — Topic-focused script docs
- `../ppt-master-skill/` — Skill definitions, references, templates, icons (sibling repo)
- `examples/` — Example projects
- `projects/` — User project workspace

## SVG Technical Constraints (Non-negotiable)

**Banned features**: `mask` | `<style>` | `class` | external CSS | `<foreignObject>` | `textPath` | `@font-face` | `<animate*>` | `<script>` | `<iframe>` | `<symbol>`+`<use>` (`id` inside `<defs>` is a legitimate reference and is NOT banned)

**Conditionally allowed**: `marker-start` / `marker-end` — the referenced `<marker>` must live in `<defs>`, use `orient="auto"`, and its shape must be a triangle (3-vertex closed path/polygon), diamond (4-vertex), or circle/ellipse. The converter maps these to native DrawingML `<a:headEnd>` / `<a:tailEnd>`. See `shared-standards.md` §1.1 for full constraints.

**Conditionally allowed**: `clipPath` on `<image>` — the referenced `<clipPath>` must live in `<defs>` and contain a single shape child (circle, ellipse, rect with rx/ry, path, or polygon). The converter maps these to native DrawingML picture geometry (`<a:prstGeom>` or `<a:custGeom>`). Only supported on `<image>` elements. See `shared-standards.md` §1.2 for full constraints.

**PPT compatibility alternatives**:

| Banned | Alternative |
|--------|-------------|
| `rgba()` | `fill-opacity` / `stroke-opacity` |
| `<g opacity>` | Set opacity on each child element individually |
| `<image opacity>` | Overlay with a mask layer |

## Canvas Format Quick Reference

| Format | viewBox |
|--------|---------|
| PPT 16:9 | `0 0 1280 720` |
| PPT 4:3 | `0 0 1024 768` |
| Xiaohongshu (RED) | `0 0 1242 1660` |
| WeChat Moments | `0 0 1080 1080` |
| Story | `0 0 1080 1920` |

## Post-processing Notes

- **NEVER** use `cp` as a substitute for `finalize_svg.py`
- **NEVER** export directly from `svg_output/` — MUST export from `svg_final/` (use `-s final`)
- Do NOT add extra flags like `--only` to the post-processing commands
- **NEVER** run the three post-processing steps in a single code block or single shell invocation
