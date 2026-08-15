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

# Documented upload limits for SKILL.md frontmatter.
MAX_NAME_LEN = 64
MAX_DESCRIPTION_LEN = 1024
NAME_SHAPE = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")

# Fixed timestamp for zip entries: rebuilding the same source must produce the
# same bytes, so a release checksum only changes when the content does.
ZIP_DATE = (1980, 1, 1, 0, 0, 0)


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


def frontmatter_fields(skill_md):
    """Read `name:` and `description:` out of the SKILL.md YAML frontmatter."""
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    fields = {}
    for key in ("name", "description"):
        match = re.search(rf"^{key}:\s*(.+?)\s*$", text[3:end], re.M)
        if not match:
            continue
        val = match.group(1)
        # A quoted scalar keeps everything inside the quotes; a plain scalar
        # drops any trailing YAML comment.
        if val[0] in "'\"" and val.find(val[0], 1) != -1:
            val = val[1:val.find(val[0], 1)]
        else:
            val = val.split(" #")[0].strip()
        fields[key] = val
    return fields


def collect(skill_path):
    """The files that will be packaged, as (path, rel-to-parent) pairs."""
    root = skill_path.parent
    out = []
    for path in sorted(skill_path.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        rel = path.relative_to(root)
        if should_exclude(rel):
            continue
        out.append((path, rel))
    return out


def validate(skill_path, packed):
    """Checks that map to the documented skill-upload failures.

    `packed` is the set of skill-relative paths that will land in the archive.
    """
    errors = []
    skill_md = skill_path / "SKILL.md"

    if not skill_path.is_dir():
        return [f"not a directory: {skill_path}"]
    if not skill_md.exists():
        return [f"no SKILL.md in {skill_path}"]

    # Uploads don't support symlinks, a link would be packaged under its own
    # name with the target's content (out-of-tree files included), and broken
    # or directory links vanish from the archive without a message.
    for path in sorted(skill_path.rglob("*")):
        if path.is_symlink():
            errors.append(
                f"symlink not allowed in a skill: {path.relative_to(skill_path)}"
            )

    fields = frontmatter_fields(skill_md)
    if fields is None:
        errors.append("SKILL.md has no YAML frontmatter block")
        return errors

    name = fields.get("name")
    if name is None:
        errors.append("SKILL.md frontmatter has no parseable `name:` field")
    elif name != skill_path.name:
        # "Skill folder name doesn't match the skill name" is a documented
        # upload rejection, so catch it at build time instead.
        errors.append(
            f"folder name '{skill_path.name}' does not match SKILL.md name '{name}' — "
            "uploads reject this"
        )
    elif len(name) > MAX_NAME_LEN:
        errors.append(f"name is {len(name)} chars — uploads cap it at {MAX_NAME_LEN}")
    elif not NAME_SHAPE.fullmatch(name):
        errors.append(f"name '{name}' must be lowercase letters, digits, and hyphens")

    desc = fields.get("description")
    if not desc:
        errors.append("SKILL.md frontmatter has no `description:` — uploads reject this")
    elif len(desc) > MAX_DESCRIPTION_LEN:
        errors.append(
            f"description is {len(desc)} chars — uploads cap it at {MAX_DESCRIPTION_LEN}"
        )

    # SKILL.md routes by literal path; a renamed or excluded file would ship
    # instructions pointing at files the archive doesn't carry.
    text = skill_md.read_text(encoding="utf-8")
    for ref in sorted(set(re.findall(r"`((?:references|scripts)/[A-Za-z0-9._/-]+)`", text))):
        if ref not in packed:
            errors.append(f"SKILL.md references `{ref}` but it is not in the package")

    return errors


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    skill_path = Path(sys.argv[1]).resolve()
    out_dir = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else Path.cwd()

    files = collect(skill_path) if skill_path.is_dir() else []
    packed = {rel.as_posix().split("/", 1)[1] for _, rel in files}
    errors = validate(skill_path, packed)
    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{skill_path.name}.skill"

    # Paths inside the archive are relative to the skill's parent, so the skill
    # folder itself is the archive root — which is what an upload expects.
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, rel in files:
            info = zipfile.ZipInfo(rel.as_posix(), date_time=ZIP_DATE)
            # Git only tracks the executable bit, so normalize to 644/755
            # rather than inheriting the checkout's umask.
            mode = 0o755 if path.stat().st_mode & 0o100 else 0o644
            info.external_attr = (0o100000 | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, path.read_bytes())

    for _, rel in files:
        print(f"  + {rel.as_posix()}")
    print(f"\npackaged {len(files)} files -> {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
