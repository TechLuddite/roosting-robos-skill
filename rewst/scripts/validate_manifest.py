#!/usr/bin/env python3
"""Validate a Rewst tenant manifest: shape, staleness, and accidental secrets.

Usage:
    python validate_manifest.py references/tenant-manifest.json
    python validate_manifest.py references/tenant-manifest.json --ttl 7

Exit codes: 0 = clean, 1 = warnings, 2 = errors (including validator crashes).
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone

REQUIRED_TOP = ["schema_version", "tenant", "generated_at", "ttl_days"]

GENERATION_VALUES = {"legacy", "new", "mixed", "unknown"}

# Keys that should never hold a value in a manifest. Names and types are fine;
# values are not, because this file gets committed and uploaded.
SECRET_KEY_PATTERN = re.compile(
    r"(secret|password|passwd|api_?key|token|credential|client_?secret|bearer|private_?key)",
    re.I,
)

# String values that look like credentials regardless of what key they sit under.
# Kept to well-known prefixes on purpose: generic entropy checks would flag the
# UUIDs a manifest is made of.
SECRET_VALUE_PATTERN = re.compile(
    r"^(eyJ[A-Za-z0-9_-]{10,}"          # JWT
    r"|sk-[A-Za-z0-9_-]{8,}"            # sk- API keys
    r"|(ghp|gho|ghu|ghs)_[A-Za-z0-9]{8,}"  # GitHub tokens
    r"|github_pat_[A-Za-z0-9_]{8,}"
    r"|xox[baprs]-"                     # Slack tokens
    r"|AKIA[0-9A-Z]{16}"                # AWS access key id
    r"|-----BEGIN\s)"                   # PEM material
)

# Keys that must not exist at all inside org_variables entries: the schema
# stores names and types, never values or defaults.
FORBIDDEN_ORG_VAR_KEYS = ("value", "default")

COLLECTIONS_WITH_STAMPS = [
    "orgs",
    "integrations",
    "org_variables",
    "workflows",
    "forms",
]


def parse_ts(value):
    if not isinstance(value, str):
        return None
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    # A stamp without an offset is assumed UTC rather than crashing the
    # staleness math against an aware `now`.
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def age_days(ts, now):
    return (now - ts).total_seconds() / 86400.0


def walk_for_secrets(node, path, findings):
    """Flag secret-named keys with values, and secret-shaped values under any key."""
    if isinstance(node, dict):
        for key, val in node.items():
            here = f"{path}.{key}" if path else key
            if (SECRET_KEY_PATTERN.search(key) and isinstance(val, (str, int, float))
                    and str(val).strip()):
                findings.append(here)
            elif isinstance(val, str) and SECRET_VALUE_PATTERN.match(val.strip()):
                findings.append(here)
            walk_for_secrets(val, here, findings)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            if isinstance(item, str) and SECRET_VALUE_PATTERN.match(item.strip()):
                findings.append(f"{path}[{i}]")
            walk_for_secrets(item, f"{path}[{i}]", findings)


def main():
    # Piped output on Windows defaults to the locale codec with strict errors;
    # an org name outside that codepage must degrade, not crash the report.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--ttl", type=int, default=None,
                    help="Override ttl_days from the manifest.")
    args = ap.parse_args()

    errors, warnings = [], []

    try:
        with open(args.path, encoding="utf-8") as fh:
            m = json.load(fh)
    except FileNotFoundError:
        print(f"ERROR: no manifest at {args.path}")
        return 2
    except UnicodeDecodeError as exc:
        print(f"ERROR: manifest is not valid UTF-8 — {exc}")
        return 2
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON — {exc}")
        return 2

    if not isinstance(m, dict):
        print("ERROR: manifest root must be an object")
        return 2

    for key in REQUIRED_TOP:
        if key not in m:
            errors.append(f"missing required top-level key: {key}")

    if m.get("tenant") == "UNCONFIGURED":
        errors.append(
            "tenant is UNCONFIGURED — this is the empty starter; run the refresh "
            "procedure in references/manifest.md before relying on it"
        )

    gen_value = m.get("platform_generation")
    if gen_value is not None and gen_value not in GENERATION_VALUES:
        warnings.append(
            f"platform_generation '{gen_value}' is not one of {sorted(GENERATION_VALUES)}"
        )

    now = datetime.now(timezone.utc)
    ttl = args.ttl if args.ttl is not None else m.get("ttl_days", 14)
    try:
        ttl = int(ttl)
    except (TypeError, ValueError):
        errors.append(f"ttl_days is not a number: {ttl!r}")
        ttl = 14

    gen = parse_ts(m.get("generated_at", ""))
    if m.get("generated_at") and gen is None:
        errors.append("generated_at is not a valid ISO-8601 timestamp")

    if not m.get("mcp_tools"):
        warnings.append(
            "mcp_tools is empty — record discovered tool names as draft-time hints "
            "(every session still re-enumerates before its first live call)"
        )

    stale, unstamped, total = [], [], 0
    for coll in COLLECTIONS_WITH_STAMPS:
        items = m.get(coll, [])
        if not isinstance(items, list):
            errors.append(f"{coll} must be a list")
            continue
        for i, item in enumerate(items):
            total += 1
            if not isinstance(item, dict):
                errors.append(f"{coll}[{i}] must be an object")
                continue
            ts = parse_ts(item.get("captured_at", ""))
            label = item.get("name") or item.get("id") or f"{coll}[{i}]"
            if ts is None:
                unstamped.append(f"{coll}: {label}")
            elif age_days(ts, now) > ttl:
                stale.append(f"{coll}: {label} ({age_days(ts, now):.0f}d)")

    # org_variables must hold names and types only — a literal value/default
    # field is the canonical secret leak this validator exists to catch.
    org_vars = m.get("org_variables", [])
    if isinstance(org_vars, list):
        for i, item in enumerate(org_vars):
            if not isinstance(item, dict):
                continue
            for bad in FORBIDDEN_ORG_VAR_KEYS:
                if bad in item:
                    label = item.get("name") or f"org_variables[{i}]"
                    errors.append(
                        f"org_variables entry '{label}' carries a '{bad}' field — "
                        "manifests hold names and types, never values"
                    )

    # psa_lookups is keyed by org id rather than being a list
    psa = m.get("psa_lookups", {})
    if not isinstance(psa, dict):
        errors.append("psa_lookups must be an object keyed by org id")
    else:
        for org_id, block in psa.items():
            total += 1
            if not isinstance(block, dict):
                errors.append(f"psa_lookups[{org_id}] must be an object")
                continue
            ts = parse_ts(block.get("captured_at", ""))
            if ts is None:
                unstamped.append(f"psa_lookups: {org_id}")
            elif age_days(ts, now) > ttl:
                stale.append(f"psa_lookups: {org_id} ({age_days(ts, now):.0f}d)")

    secrets = []
    walk_for_secrets(m, "", secrets)
    for hit in secrets:
        errors.append(f"possible secret value at {hit} — manifests hold names, not values")

    orgs = m.get("orgs", [])
    if isinstance(orgs, list) and orgs:
        if not any(o.get("role") == "owner" for o in orgs if isinstance(o, dict)):
            warnings.append("no org marked role=owner — owner-level writes cascade to all customers")
        if not any(o.get("role") == "test" for o in orgs if isinstance(o, dict)):
            warnings.append("no org marked role=test — nowhere safe to test against")

    if unstamped:
        warnings.append(f"{len(unstamped)} entries missing captured_at")
    if stale:
        warnings.append(f"{len(stale)} entries older than {ttl}d — treat as hints, verify before writing")

    print(f"manifest: {args.path}")
    print(f"tenant:   {m.get('tenant', '?')}   generation: {m.get('platform_generation', '?')}")
    print(f"entries:  {total}   ttl: {ttl}d")
    print()

    for e in errors:
        print(f"  ERROR  {e}")
    for w in warnings:
        print(f"  WARN   {w}")

    if stale:
        print("\n  stale:")
        for s in stale[:20]:
            print(f"    - {s}")
        if len(stale) > 20:
            print(f"    ... and {len(stale) - 20} more")

    if unstamped:
        print("\n  unstamped:")
        for u in unstamped[:20]:
            print(f"    - {u}")
        if len(unstamped) > 20:
            print(f"    ... and {len(unstamped) - 20} more")

    if not errors and not warnings:
        print("  clean")

    return 2 if errors else (1 if warnings else 0)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # crashes must not masquerade as warnings
        print(f"ERROR: validator crashed — {type(exc).__name__}: {exc}")
        sys.exit(2)
