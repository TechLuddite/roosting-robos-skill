#!/usr/bin/env python3
"""Package a skill folder into a distributable .skill file (a zip).

Usage:
    python scripts/package.py skills/rewst [output-dir]

Build tooling, not part of the skill. The output is not committed — CI builds it
on a tag and attaches it to the GitHub Release, so the artifact always comes from
a clean checkout rather than from someone's working tree.

Exit codes: 0 = packaged, 1 = validation failed.
"""

import fnmatch
import re
import sys
import zipfile
from pathlib import Path

# Mirrors the exclusions in Anthropic's skill-creator packager.
EXCLUDE_DIRS = {"__pycache__", "node_modules"}
EXCLUDE_GLOBS = {"*.pyc", "*.skill"}
EXCLUDE_FILES = {".DS_Store"}
ROOT_EXCLUDE_DIRS = {"evals"}


def should_exclude(rel_path):
    parts = rel_path.parts
    if any(part in EXCLUDE_DIRS or part.startswith(".") for part in parts):
        return True
    # parts[0] is the skill folder name; parts[1] is its first subdirectory.
    if len(parts) > 1 and parts[1] in ROOT_EXCLUDE_DIRS:
        return True
    if rel_path.name in EXCLUDE_FILES:
        return True
    return any(fnmatch.fnmatch(rel_path.name, pat) for pat in EXCLUDE_GLOBS)


def frontmatter_name(skill_md):
    """Read `name:` out of the SKILL.md YAML frontmatter."""
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    match = re.search(r"^name:\s*(\S+)\s*$", text[3:end], re.M)
    return match.group(1) if match else None


def validate(skill_path):
    """Checks that map to the documented skill-upload failures."""
    errors = []
    skill_md = skill_path / "SKILL.md"

    if not skill_path.is_dir():
        return [f"not a directory: {skill_path}"]
    if not skill_md.exists():
        return [f"no SKILL.md in {skill_path}"]

    name = frontmatter_name(skill_md)
    if name is None:
        errors.append("SKILL.md frontmatter has no `name:` field")
    elif name != skill_path.name:
        # "Skill folder name doesn't match the skill name" is a documented
        # upload rejection, so catch it at build time instead.
        errors.append(
            f"folder name '{skill_path.name}' does not match SKILL.md name '{name}' — "
            "uploads reject this"
        )
    return errors


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    skill_path = Path(sys.argv[1]).resolve()
    out_dir = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else Path.cwd()

    errors = validate(skill_path)
    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{skill_path.name}.skill"

    # Paths inside the archive are relative to the skill's parent, so the skill
    # folder itself is the archive root — which is what an upload expects.
    root = skill_path.parent
    packed = []
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(skill_path.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(root)
            if should_exclude(rel):
                continue
            zf.write(path, rel.as_posix())
            packed.append(rel.as_posix())

    for name in packed:
        print(f"  + {name}")
    print(f"\npackaged {len(packed)} files -> {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
