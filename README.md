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
| `skills/rewst/SKILL.md` | Routing, constants policy, build procedure, always-active hard rules | skill |
| `skills/rewst/references/guardrails.md` | Full guardrail list, read before any write/execute | skill |
| `skills/rewst/references/house-style.md` | **Your** build conventions — defaults to overwrite | you |
| `skills/rewst/references/doc-map.md` | Topic → live doc URL routing table + fetch mechanics | skill |
| `skills/rewst/references/manifest.md` | Tenant manifest schema, refresh procedure, persistence | skill |
| `skills/rewst/references/jinja-gotchas.md` | Jinja traps the docs don't lead with | skill |
| `skills/rewst/references/tenant-manifest.json` | Empty starter cache — populate via the refresh procedure | generated |
| `skills/rewst/scripts/validate_manifest.py` | Checks manifest shape, staleness, and accidental secrets | skill |

## Install

You need a Rewst MCP server connected to your Claude surface (Rewst's own MCP endpoint or a
community server exposing your tenant). The skill degrades to advisory mode without one.

**Claude Code — plugin (recommended).** Installs and updates in place:

```
/plugin marketplace add TechLuddite/roosting-robos-skill
/plugin install roosting-robos@techluddite-skills
```

The skill then answers to `/roosting-robos:rewst`, and Claude loads it on its own when a task
looks like Rewst.

**Claude Code — manual.** Copy `skills/rewst/` into your project's `.claude/skills/` (or
`~/.claude/skills/` for every project). Keep the folder named `rewst`; the folder name is the
command name.

**claude.ai / desktop.** Download `rewst.skill` from the
[latest release](https://github.com/TechLuddite/roosting-robos-skill/releases/latest) and upload
it under Settings → Capabilities → Skills. It's a zip with the `rewst/` folder at its root; if
the uploader refuses the extension, rename it to `rewst.zip` — same bytes.

## First-run setup

> **Plugin installs:** a plugin update replaces the skill directory, taking in-tree edits with
> it. Keep your live `house-style.md` and tenant manifest outside the plugin — a path you name,
> or a connected doc store (see `references/manifest.md`, "Where the manifest lives"). Editing
> the files in place is only durable on a manual install.

1. **Claim `house-style.md`.** Search it for `[SET THIS]` markers — your MSP's naming prefix,
   org-variable casing, notification targets, tag taxonomy. Until set, sessions drive toward
   the documented defaults.
2. **Build the tenant manifest.** Ask Claude to run the refresh procedure in
   `references/manifest.md`. It sweeps breadth-first (orgs → integrations → org variable
   *names*), stamps every entry, and never stores variable values or secrets.
3. **Validate:** `python skills/rewst/scripts/validate_manifest.py <path-to-your-live-manifest>`
   (exit 0 clean / 1 warnings / 2 errors). On a manual install where the manifest lives
   in-tree, that path is `skills/rewst/references/tenant-manifest.json`. The shipped starter
   reports an error until it's populated — that's the `UNCONFIGURED` guard, not a broken
   validator.

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
and IDs only. The validator backstops part of that: it hard-errors on value/default fields at
any depth and on strings shaped like known credentials (JWTs, vendor key prefixes, AWS keys,
PEM blocks, URL-embedded passwords, `key=value` assignments, webhook URLs, long hex tokens).
It cannot recognize an arbitrary password or PII — those exclusions are procedural, kept by the
refresh rules, not by code. The file is designed to be committed; the validator narrows, but
does not close, the ways that can go wrong.

**Install channels have different trust models.** The release asset is the verified path: CI
leak-checks, smoke-tests, and checksums the exact bytes it attaches (a `.sha256` ships next to
the asset). The plugin marketplace ships whatever the repo's default branch holds when a
version bump lands — none of the release gates apply at install or update time. For
high-assurance use, install the release asset, or fork and pin.

**"Designed to be committed" means *your* repo, not a public one.** A populated manifest holds no
secrets, but it does hold your customer org names and IDs, integration IDs, PSA board/queue/status
IDs, and org variable names — a readable map of your client base and how it's wired. A filled-in
`house-style.md` adds your naming prefix and notification targets. If you fork this repo, keep the
fork private. Adding the paths to `.gitignore` is **not** enough on its own — both files are
already tracked, and Git ignores `.gitignore` for tracked files, so the next `git add .` after a
refresh commits the populated manifest anyway. If the fork must be public, untrack them first:

```bash
git rm --cached skills/rewst/references/tenant-manifest.json \
                skills/rewst/references/house-style.md
printf '%s\n' skills/rewst/references/tenant-manifest.json \
              skills/rewst/references/house-style.md >> .gitignore
git add .gitignore
git commit -m "Keep tenant manifest and house style out of the public fork"
```

This protects the future, not the past: if a populated version was **ever committed**, the
fork's history still contains it — rewrite history with `git filter-repo` (or start the public
fork from a fresh clone of upstream) before publishing. Watch for stray copies too
(`tenant-manifest.backup.json`, editor `.bak` files); the recipe only untracks the two exact
paths.

Upstream ships them at their empty/default state on purpose, so they're tracked here.

## Building the package

The `.skill` is **not committed** — it's a zip of `skills/rewst/`, and a committed copy drifts
from the source it duplicates. CI builds it on every PR and push to `main`, leak-checks the
manifest, smoke-tests the archive, and on a `v*` tag attaches that same verified artifact to
the GitHub Release along with its `.sha256`, so the published bytes always come from a clean
checkout and downloads can be verified. The build is reproducible: packaging the same source
twice yields byte-identical archives (timestamps, modes, entry order, compression level, and
zip metadata are all pinned), so release checksums only change when content does.

To build one locally:

```bash
python scripts/package.py skills/rewst dist
```

The packager refuses to build if the folder name and the `name:` in `SKILL.md` frontmatter
disagree, which is the most common upload rejection. It skips dotfiles, `__pycache__`, and
`node_modules`, and it refuses to package a populated `tenant-manifest.json` unless you pass
`--allow-populated` — but it can't inspect everything you may have edited (a filled-in
`house-style.md` ships as-is). **Build from a clean checkout before sharing a `.skill`.**

To cut a release: bump `version` in `.claude-plugin/plugin.json` — marketplace-installed plugins
only see updates when that value changes — commit, then `git tag v<version> && git push origin
v<version>` (the tag must match the bumped `plugin.json` exactly). The workflow refuses a tag
that doesn't match `plugin.json`, creates the release if it doesn't exist, and attaches the
exact `rewst.skill` bytes the build job checked, verified against the build job's checksum.
Publishing a release from the GitHub UI on an existing `v*` tag attaches the asset too.

A `v*` tag is what ships bytes: without one for the current version, pushes to `main` only
produce the workflow artifact on the Actions run page, and CI prints a notice when
`plugin.json`'s version has no matching tag.

## License

MIT — see [`LICENSE`](LICENSE).
