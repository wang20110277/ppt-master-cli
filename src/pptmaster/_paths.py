"""Dual-mode resource path resolver.

Works correctly whether pptmaster is installed via pip (site-packages) or
used directly from a git clone (src/pptmaster/).

Skill assets (references, workflows, templates, icons) are resolved from
the sibling ppt-master-skill repo when available, falling back to bundled assets.
"""

import os
from pathlib import Path

# Package root = src/pptmaster/ (resolves correctly in both modes)
PKG_ROOT = Path(__file__).resolve().parent


def _skill_assets_root() -> Path:
    """Locate the ppt-master-skill directory for templates/references.

    Search order:
    1. PPM_SKILL_DIR environment variable
    2. Sibling directory ../ppt-master-skill (relative to repo root)
    3. PKG_ROOT fallback
    """
    env_dir = os.environ.get("PPM_SKILL_DIR")
    if env_dir:
        p = Path(env_dir).resolve()
        if p.is_dir():
            return p

    repo_root = PKG_ROOT.parent.parent
    sibling = repo_root.parent / "ppt-master-skill"
    if sibling.is_dir():
        return sibling

    return PKG_ROOT


_ASSETS_ROOT = _skill_assets_root()


def get_templates_dir() -> Path:
    return _ASSETS_ROOT / "templates"


def get_icons_dir() -> Path:
    return _ASSETS_ROOT / "templates" / "icons"


def get_references_dir() -> Path:
    return _ASSETS_ROOT / "references"


def get_scripts_dir() -> Path:
    return PKG_ROOT / "scripts"


def get_workflows_dir() -> Path:
    return _ASSETS_ROOT / "workflows"


def find_env_file() -> Path | None:
    """Locate .env file: cwd first, then repo root."""
    cwd_env = Path.cwd() / ".env"
    if cwd_env.exists():
        return cwd_env
    pkg_env = PKG_ROOT.parent.parent / ".env"
    if pkg_env.exists():
        return pkg_env
    return None
