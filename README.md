# roosting-robos-skill

A Claude skill for building, debugging, and reviewing [Rewst](https://rewst.io) automations —
workflows, forms, Crates, org variables, Jinja — over a Rewst MCP server, without burning tokens
on re-discovery or firing a write at the wrong customer.

> **Not affiliated with, endorsed by, or supported by Rewst.** Community project. It drives a
> multi-tenant MSP automation platform that sits upstream of real customer environments — read
> the safety model below before pointing it at production.

## Why this exists

Driving Rewst through an MCP server from a Claude session has four failure modes this skill is
built around:

1. **Token burn.** Every session re-discovering the same org IDs, integration IDs, and PSA
   lookup values costs tens of thousands of tokens. The skill caches those in a **tenant
   manifest** (a file read instead of a discovery sweep) with per-entry freshness stamps, and
   re-verifies only the specific IDs a write touches.
2. **Stale trained knowledge.** Rewst is mid-platform-rebuild; what a model remembers about the
   platform is unreliable. The skill enforces *fetch, don't recall*: a routing table maps topics
   to live doc URLs, with cheap mechanics (`.md` suffix for raw markdown, `?ask=` for targeted
   answers, `llms.txt` as the index).
3. **Inconsistent output.** A user-owned `house-style.md` carries naming, structure, error
   handling, and documentation conventions; a fixed build procedure (scope → research →
   propose → confirm → build → verify → update manifest) keeps sessions from improvising.
4. **Costly mistakes.** One tenant holds the MSP owner org plus every customer sub-org, so a
   wrong org ID fires at someone's production environment. Blast-radius-ordered guardrails
   require org confirmation **by ID**, read-only dry runs before destructive identity/license
   actions, and never touching Crate-managed content.

## What's inside

| File | Purpose | Owner |
|---|---|---|
| `rewst/SKILL.md` | Routing, constants policy, build procedure, always-active hard rules | skill |
| `rewst/references/guardrails.md` | Full guardrail list, read before any write/execute | skill |
| `rewst/references/house-style.md` | **Your** build conventions — defaults to overwrite | you |
| `rewst/references/doc-map.md` | Topic → live doc URL routing table + fetch mechanics | skill |
| `rewst/references/manifest.md` | Tenant manifest schema, refresh procedure, persistence | skill |
| `rewst/references/jinja-gotchas.md` | Jinja traps the docs don't lead with | skill |
| `rewst/references/tenant-manifest.json` | Empty starter cache — populate via the refresh procedure | generated |
| `rewst/scripts/validate_manifest.py` | Checks manifest shape, staleness, and accidental secrets | skill |

## Install

You need a Rewst MCP server connected to your Claude surface (Rewst's own MCP endpoint or a
community server exposing your tenant). The skill degrades to advisory mode without one.

- **Claude Code:** copy the `rewst/` folder into your project's `.claude/skills/` directory
  (or a personal skills directory), or install the packaged `roosting-robos.skill`.
- **claude.ai / desktop:** upload `roosting-robos.skill` under Settings → Capabilities →
  Skills.

## First-run setup

1. **Claim `house-style.md`.** Search it for `[SET THIS]` markers — your MSP's naming prefix,
   org-variable casing, notification targets, tag taxonomy. Until set, sessions drive toward
   the documented defaults.
2. **Build the tenant manifest.** Ask Claude to run the refresh procedure in
   `references/manifest.md`. It sweeps breadth-first (orgs → integrations → org variable
   *names*), stamps every entry, and never stores variable values or secrets.
3. **Validate:** `python rewst/scripts/validate_manifest.py rewst/references/tenant-manifest.json`
   (exit 0 clean / 1 warnings / 2 errors).

## Recommended org instructions

Skills under-trigger on symptom-phrased requests ("the offboarding workflow didn't fire") that
never say "Rewst." Dropping this into org or project instructions makes sessions mount the skill
earlier and more reliably (~200 tokens):

```
## Rewst
If a task touches Rewst in any way — workflows, forms, Crates, org variables, the Rewst MCP
server, or Jinja/PowerShell in MSP automation — load the `rewst` skill before your first answer
or tool call, even for quick questions, read-only look-ups, code review, or debugging. Symptom
reports count: "the offboarding workflow didn't fire," "the form options are empty," "CTX.x is
blank" are Rewst tasks even when Rewst isn't named. Never answer Rewst platform questions from
trained knowledge — the platform is mid-rebuild and memory is stale; the skill routes to live
docs and a cached tenant manifest, which is also far cheaper than re-discovering tenant IDs. Any
tenant write, publish, delete, or execution goes through the skill's guardrails and org-ID
confirmation. If you realize mid-task that Rewst is involved, mount the skill then rather than
finishing without it.
```

## The safety model, honestly

The guardrails are **behavioral, not enforcement**. They make a Claude session confirm targets
by ID, show dry runs, and re-propose on scope changes — but nothing in a prompt can physically
stop a write. Real enforcement is the scope of the MCP token and the RBAC attached to it. If
routine build work is running on a token that can write to every customer org, fix the token.

The manifest never stores org-variable *values*, credentials, or customer PII — names, types,
and IDs only — and the validator hard-errors on value fields and secret-shaped strings, because
this file is designed to be committed.

**"Designed to be committed" means *your* repo, not a public one.** A populated manifest holds no
secrets, but it does hold your customer org names and IDs, integration IDs, PSA board/queue/status
IDs, and org variable names — a readable map of your client base and how it's wired. A filled-in
`house-style.md` adds your naming prefix and notification targets. If you fork this repo, keep the
fork private, or add these two paths to `.gitignore` before your first refresh:

```
rewst/references/tenant-manifest.json
rewst/references/house-style.md
```

Upstream ships them at their empty/default state on purpose, so they're tracked here.

## Rebuilding the package

After editing the source, rebuild the `.skill` (it's a zip with the `rewst/` folder at the root):

```bash
python -c "import zipfile, pathlib; skip = lambda p: any(part.startswith('.') or part == '__pycache__' for part in p.parts); z = zipfile.ZipFile('roosting-robos.skill', 'w', zipfile.ZIP_DEFLATED); [z.write(p, p.as_posix()) for p in sorted(pathlib.Path('rewst').rglob('*')) if p.is_file() and not skip(p)]; z.close()"
```

The rebuild packages whatever is on disk under `rewst/`. If you've populated
`tenant-manifest.json` or filled in `house-style.md`, that content goes into the `.skill` —
rebuild from a clean checkout before sharing the package.

## License

MIT — see [`LICENSE`](LICENSE).
