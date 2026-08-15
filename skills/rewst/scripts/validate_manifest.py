#!/usr/bin/env python3
"""Validate a Rewst tenant manifest: shape, staleness, and accidental secrets.

Usage (from the skill root, skills/rewst/):
    python scripts/validate_manifest.py references/tenant-manifest.json
    python scripts/validate_manifest.py references/tenant-manifest.json --ttl 7
    python scripts/validate_manifest.py references/tenant-manifest.json --allow-unconfigured

Exit codes: 0 = clean, 1 = warnings, 2 = errors (including validator crashes).
--allow-unconfigured downgrades the shipped UNCONFIGURED starter's error to a
warning, so CI can gate on the exit code while still packaging the starter.
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
    r"(secret|password|passwd|pwd|api_?key|access_?key|token|credential"
    r"|client_?secret|bearer|private_?key|auth(orization|entication)?(?![a-z])"
    r"|conn(ection)?[-_]?str(ing)?|dsn(?![a-z]))",
    re.I,
)

# String values that look like credentials regardless of what key they sit
# under, searched anywhere inside the value — a JWT pasted as "Bearer eyJ…"
# must not pass because of its prefix. Patterns stay specific (known prefixes,
# URL userinfo, key=value assignments, webhook URLs, 40+ contiguous hex — a
# dashed UUID never exceeds 12) because generic entropy checks would flag the
# UUIDs a manifest is made of; unmarked base64 blobs remain out of scope for
# the same reason.
_SECRET_VALUE = (
    r"(eyJ[A-Za-z0-9_-]{10,}"           # JWT
    r"|sk-[A-Za-z0-9_-]{8,}"            # sk- API keys
    r"|(ghp|gho|ghu|ghs)_[A-Za-z0-9]{8,}"  # GitHub tokens
    r"|github_pat_[A-Za-z0-9_]{8,}"
    r"|xox[baprs]-"                     # Slack tokens
    r"|AKIA[0-9A-Z]{16}"                # AWS access key id
    r"|-----BEGIN\s"                    # PEM material
    r"|://[^/\s@:]+:[^/\s@]+@"          # URL userinfo credentials (scheme://user:pass@)
    r"|(?i:\b(password|passwd|pwd|secret|api_?key|token)\s*=\s*[^\s;,&\"']{2,})"
    r"|hooks\.slack\.com/services/"     # capability-bearing webhook URLs
    r"|webhook\.office\.com/"
    r"|outlook\.office\.com/webhook"
    r"|discord(app)?\.com/api/webhooks/"
    r"|\b[0-9a-fA-F]{40,}\b)"           # long contiguous hex token
)
SECRET_VALUE_ANYWHERE = re.compile(_SECRET_VALUE)

# Keys that must not exist anywhere in a manifest: the schema stores names
# and types, never values or defaults, so a value-like key at any depth is
# the canonical leak this validator exists to catch.
FORBIDDEN_VALUE_KEYS = ("value", "values", "default", "defaults")

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
    # Truncate 7+-digit fractional seconds (.NET/PowerShell `-Format o` emits
    # them) so parsing behaves the same on every supported Python version.
    value = re.sub(r"\.(\d{6})\d+", r".\1", value.replace("Z", "+00:00"))
    try:
        ts = datetime.fromisoformat(value)
    except ValueError:
        return None
    # A stamp without an offset is assumed UTC rather than crashing the
    # staleness math against an aware `now`.
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def age_days(ts, now):
    return (now - ts).total_seconds() / 86400.0


def raw_secret_scan(path):
    """Fallback for unparseable manifests: report secret-shaped lines anyway."""
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            for n, line in enumerate(fh, 1):
                if SECRET_VALUE_ANYWHERE.search(line):
                    print(f"ERROR: possible secret value at line {n} — "
                          "manifests hold names, not values")
    except OSError:
        pass


def walk_for_secrets(node, path, findings):
    """Flag secret-named keys with values, and secret-shaped values under any key."""
    if isinstance(node, dict):
        for key, val in node.items():
            here = f"{path}.{key}" if path else key
            # bool is excluded: an `is_secret: true` flag is names-and-types
            # metadata, not a leaked value.
            if SECRET_KEY_PATTERN.search(key) and not isinstance(val, bool):
                if isinstance(val, str) and val.strip():
                    findings.append(here)
                elif (isinstance(val, (int, float))
                        and len(re.sub(r"\D", "", str(val))) >= 6):
                    # Small numbers under secret-ish names are metadata
                    # (token_count: 512); six or more digits is
                    # credential-shaped.
                    findings.append(here)
                elif isinstance(val, (dict, list)) and val:
                    # A populated container under a secret-named key
                    # ("passwords": [...]) has no place in a names-and-types
                    # manifest, whatever its leaves look like.
                    findings.append(here)
            if (isinstance(val, str) and SECRET_VALUE_ANYWHERE.search(val)
                    and here not in findings):
                findings.append(here)
            walk_for_secrets(val, here, findings)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            if isinstance(item, str) and SECRET_VALUE_ANYWHERE.search(item):
                findings.append(f"{path}[{i}]")
            walk_for_secrets(item, f"{path}[{i}]", findings)


def walk_for_forbidden_keys(node, path, hits):
    """Find value/default-style keys at any depth — they never belong here."""
    if isinstance(node, dict):
        for key, val in node.items():
            here = f"{path}.{key}" if path else key
            if key in FORBIDDEN_VALUE_KEYS:
                hits.append(here)
            walk_for_forbidden_keys(val, here, hits)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            walk_for_forbidden_keys(item, f"{path}[{i}]", hits)


def main():
    # Piped output on Windows defaults to the locale codec with strict errors;
    # an org name outside that codepage must degrade, not crash the report.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--ttl", type=int, default=None,
                    help="Override ttl_days from the manifest.")
    ap.add_argument("--allow-unconfigured", action="store_true",
                    help="Report the UNCONFIGURED starter as a warning instead of "
                         "an error (CI validates the shipped starter this way).")
    args = ap.parse_args()

    errors, warnings = [], []

    try:
        # utf-8-sig decodes plain UTF-8 identically and tolerates the BOM some
        # Windows editors prepend.
        with open(args.path, encoding="utf-8-sig") as fh:
            m = json.load(fh)
    except FileNotFoundError:
        print(f"ERROR: no manifest at {args.path}")
        return 2
    except UnicodeDecodeError as exc:
        print(f"ERROR: manifest is not valid UTF-8 — {exc}")
        raw_secret_scan(args.path)
        return 2
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON — {exc}")
        raw_secret_scan(args.path)
        return 2

    if not isinstance(m, dict):
        print("ERROR: manifest root must be an object")
        return 2

    for key in REQUIRED_TOP:
        if key not in m:
            errors.append(f"missing required top-level key: {key}")

    # tenant anchors both the UNCONFIGURED guard and the wrong-tenant binding
    # check, so its shape is an error, not a nuance.
    tenant = m.get("tenant")
    if "tenant" in m and (not isinstance(tenant, str) or not tenant.strip()):
        errors.append(
            f"tenant must be a non-empty string (the owner org ID as reported "
            f"by the server), got: {tenant!r}"
        )
    elif isinstance(tenant, str) and tenant.strip().upper() == "UNCONFIGURED":
        msg = ("tenant is UNCONFIGURED — this is the empty starter; run the refresh "
               "procedure in references/manifest.md before relying on it")
        (warnings if args.allow_unconfigured else errors).append(msg)

    gen_value = m.get("platform_generation")
    if gen_value is not None and (
            not isinstance(gen_value, str) or gen_value not in GENERATION_VALUES):
        warnings.append(
            f"platform_generation {gen_value!r} is not one of {sorted(GENERATION_VALUES)}"
        )

    now = datetime.now(timezone.utc)
    ttl = args.ttl if args.ttl is not None else m.get("ttl_days", 14)
    if isinstance(ttl, bool):
        # int(True) is 1 — a shape mistake must not silently become a 1-day TTL.
        errors.append(f"ttl_days is not a number: {ttl!r}")
        ttl = 14
    try:
        ttl = int(ttl)
    except (TypeError, ValueError):
        errors.append(f"ttl_days is not a number: {ttl!r}")
        ttl = 14

    gen = parse_ts(m.get("generated_at", ""))
    if m.get("generated_at") and gen is None:
        errors.append("generated_at is not a valid ISO-8601 timestamp")
    elif gen is not None and age_days(gen, now) < -1:
        warnings.append("generated_at is in the future — check the clock or "
                        "timezone that wrote it")

    if not m.get("mcp_tools"):
        warnings.append(
            "mcp_tools is empty — record discovered tool names as draft-time hints "
            "(every session still re-enumerates before its first live call)"
        )

    stale, unstamped, future, total = [], [], [], 0
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
            elif age_days(ts, now) < -1:
                # A future stamp can never go stale, which silently disables
                # the one check that guards against acting on outdated IDs.
                future.append(f"{coll}: {label}")
            elif age_days(ts, now) > ttl:
                stale.append(f"{coll}: {label} ({age_days(ts, now):.0f}d)")

    # Value/default-style keys never belong in a manifest at any depth — the
    # schema stores names and types only, and this is the canonical secret
    # leak the validator exists to catch.
    forbidden = []
    walk_for_forbidden_keys(m, "", forbidden)
    for hit in forbidden:
        errors.append(
            f"value-like field at {hit} — manifests hold names and types, "
            "never values or defaults"
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
            elif age_days(ts, now) < -1:
                future.append(f"psa_lookups: {org_id}")
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
    if future:
        warnings.append(f"{len(future)} entries stamped in the future — a wrong "
                        "clock or timezone disables staleness checks; fix the stamps")
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
