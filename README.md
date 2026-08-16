# roosting-robos-skill

A Claude skill for building, debugging, and reviewing [Rewst](https://rewst.io) automations —
workflows, forms, Crates, org variables, Jinja — over a Rewst MCP server, without re-discovering
the same tenant IDs every session or firing a write at the wrong customer.

> **Not affiliated with, endorsed by, or supported by Rewst.** This is a community project. It
> drives a multi-tenant MSP automation platform that sits upstream of real customer
> environments — read section 6 before pointing it at production.

**Short version.** Install the plugin if you want updates in place; install the release asset if
you want bytes that CI has verified. Either way, keep your `house-style.md` and tenant manifest
outside the skill directory, because a plugin update replaces it. Sections 3 and 4 cover both
paths.

## 1. Why this exists

Driving Rewst through an MCP server from a Claude session has four failure modes, and the skill
is built around them:

1. **Token burn.** Every session re-discovering the same org IDs, integration IDs, and PSA lookup
   values costs tens of thousands of tokens. The skill caches those in a **tenant manifest** — a
   file read instead of a discovery sweep — with per-entry freshness stamps, and re-verifies only
   the specific IDs a write touches.
2. **Stale trained knowledge.** Rewst is mid-platform-rebuild, so what a model remembers about
   the platform is unreliable. The skill enforces *fetch, don't recall*: a routing table maps
   topics to live doc URLs, with cheap mechanics (`.md` suffix for raw markdown, `?ask=` for
   targeted answers, `llms.txt` as the index).
3. **Inconsistent output.** A user-owned `house-style.md` carries naming, structure, error
   handling, and documentation conventions. A fixed build procedure — scope → research → propose
   → confirm → build → verify → update manifest — keeps sessions from improvising.
4. **Costly mistakes.** One tenant holds the MSP owner org plus every customer sub-org, so a
   wrong org ID fires at someone's production environment. Guardrails are ordered by blast
   radius: org confirmation **by ID**, read-only dry runs before destructive identity or license
   actions, and never touching Crate-managed content.

## 2. What's inside

| File | Purpose | Owner |
|---|---|---|
| `skills/rewst/SKILL.md` | Routing, constants policy, build procedure, always-active hard rules | skill |
| `skills/rewst/references/guardrails.md` | Full guardrail list, read before any write or execute | skill |
| `skills/rewst/references/house-style.md` | **Your** build conventions — defaults to overwrite | you |
| `skills/rewst/references/doc-map.md` | Topic → live doc URL routing table, plus fetch mechanics | skill |
| `skills/rewst/references/manifest.md` | Tenant manifest schema, refresh procedure, persistence | skill |
| `skills/rewst/references/jinja-gotchas.md` | Jinja traps the docs don't lead with | skill |
| `skills/rewst/references/tenant-manifest.json` | Empty starter cache — populate via the refresh procedure | generated |
| `skills/rewst/scripts/validate_manifest.py` | Checks manifest shape, staleness, and accidental secrets | skill |

## 3. Install

You need a Rewst MCP server connected to your Claude surface — Rewst's own MCP endpoint, or a
community server exposing your tenant. Without one the skill degrades to advisory mode: design
and review still work, but nothing is verified against a live tenant.

**Claude Code — plugin (recommended).** Installs and updates in place:

```
/plugin marketplace add TechLuddite/roosting-robos-skill
/plugin install roosting-robos@techluddite-skills
```

The skill then answers to `/roosting-robos:rewst`, and Claude loads it on its own when a task
looks like Rewst.

**Claude Code — manual.** Copy `skills/rewst/` into your project's `.claude/skills/`, or into
`~/.claude/skills/` for every project. Keep the folder named `rewst`; the folder name is the
command name.

**claude.ai / desktop.** Download `rewst.skill` from the
[latest release](https://github.com/TechLuddite/roosting-robos-skill/releases/latest) and upload
it under Settings → Capabilities → Skills. It's a zip with the `rewst/` folder at its root. If
the uploader refuses the extension, rename it to `rewst.zip` — same bytes.

## 4. First-run setup

> **Plugin installs:** a plugin update replaces the skill directory and takes any in-tree edits
> with it. Keep your live `house-style.md` and tenant manifest outside the plugin — a path you
> name, or a connected doc store (see `references/manifest.md`, "Where the manifest lives").
> Editing the files in place is only durable on a manual install.

1. **Claim `house-style.md`.** Search it for `[SET THIS]` markers — your MSP's naming prefix,
   org-variable casing, notification targets, tag taxonomy. Until those are set, sessions drive
   toward the documented defaults.
2. **Build the tenant manifest.** Ask Claude to run the refresh procedure in
   `references/manifest.md`. It sweeps breadth-first — orgs, then integrations, then org variable
   *names* — stamps every entry, and never stores variable values or secrets.
3. **Validate:** `python skills/rewst/scripts/validate_manifest.py <path-to-your-live-manifest>`
   (exit 0 clean, 1 warnings, 2 errors). On a manual install where the manifest lives in-tree,
   that path is `skills/rewst/references/tenant-manifest.json`. The shipped starter reports an
   error until it's populated — that's the `UNCONFIGURED` guard, not a broken validator.

## 5. Recommended org instructions

Skills under-trigger on symptom-phrased requests — "the offboarding workflow didn't fire" never
says "Rewst." I recommend dropping the block below into org or project instructions. It costs
about 200 tokens and makes sessions mount the skill earlier and more reliably:

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

## 6. The safety model, honestly

**The guardrails are behavioral, not enforcement.** They make a Claude session confirm targets by
ID, show dry runs, and re-propose on scope changes — but nothing in a prompt can physically stop
a write. Real enforcement is the scope of the MCP token and the RBAC attached to it. If routine
build work is running on a token that can write to every customer org, fix the token first; the
skill is a second layer, not the first one.

**The manifest holds names, types, and IDs — never org-variable values, credentials, or customer
PII.** The validator backstops part of that. It hard-errors on value and default fields at any
depth, and on strings shaped like known credentials: JWTs, vendor key prefixes, AWS keys, PEM
blocks, URL-embedded passwords, `key=value` assignments, webhook URLs, and long hex tokens. It
cannot recognize an arbitrary password or PII, so those exclusions are procedural — kept by the
refresh rules, not by code. The file is designed to be committed; the validator narrows the ways
that can go wrong, but it does not close them.

**Install channels have different trust models.** The release asset is the verified path: CI
leak-checks, smoke-tests, and checksums the exact bytes it attaches, and a `.sha256` ships next
to the asset. The plugin marketplace ships whatever the repo's default branch holds when a
version bump lands, so none of the release gates apply at install or update time. For
high-assurance use, install the release asset, or fork and pin.

**"Designed to be committed" means *your* repo, not a public one.** A populated manifest holds no
secrets, but it does hold your customer org names and IDs, integration IDs, PSA
board/queue/status IDs, and org variable names — a readable map of your client base and how it's
wired. A filled-in `house-style.md` adds your naming prefix and notification targets. If you fork
this repo, keep the fork private.

Adding the paths to `.gitignore` is **not** enough on its own. Both files are already tracked, and
Git ignores `.gitignore` for tracked files, so the next `git add .` after a refresh commits the
populated manifest anyway. If the fork must be public, untrack them first:

```bash
git rm --cached skills/rewst/references/tenant-manifest.json \
                skills/rewst/references/house-style.md
printf '%s\n' skills/rewst/references/tenant-manifest.json \
              skills/rewst/references/house-style.md >> .gitignore
git add .gitignore
git commit -m "Keep tenant manifest and house style out of the public fork"
```

That protects the future, not the past. If a populated version was **ever committed**, the fork's
history still contains it — rewrite history with `git filter-repo`, or start the public fork from
a fresh clone of upstream, before publishing. Watch for stray copies too
(`tenant-manifest.backup.json`, editor `.bak` files); the recipe only untracks those two exact
paths.

Upstream ships both files at their empty or default state on purpose, which is why they're
tracked here.

## 7. Building and releasing

The `.skill` is **not committed** — it's a zip of `skills/rewst/`, and a committed copy drifts
from the source it duplicates. CI builds it on every PR and push to `main`, leak-checks the
manifest, smoke-tests the archive, and on a `v*` tag attaches that same verified artifact to the
GitHub Release along with its `.sha256`. The published bytes always come from a clean checkout,
and downloads can be verified. The build is reproducible: packaging the same source twice yields
byte-identical archives — timestamps, modes, entry order, compression level, and zip metadata are
all pinned — so release checksums only change when content does.

To build one locally:

```bash
python scripts/package.py skills/rewst dist
```

The packager refuses to build if the folder name and the `name:` in `SKILL.md` frontmatter
disagree, which is the most common upload rejection. It skips dotfiles, `__pycache__`, and
`node_modules`, and it refuses to package a populated `tenant-manifest.json` unless you pass
`--allow-populated`. It can't inspect everything you may have edited, though — a filled-in
`house-style.md` ships as-is. **Build from a clean checkout before sharing a `.skill`.**

To cut a release:

1. Bump `version` in `.claude-plugin/plugin.json`. Marketplace-installed plugins only see updates
   when that value changes.
2. Commit, then `git tag v<version> && git push origin v<version>`. The tag must match the bumped
   `plugin.json` exactly; the workflow refuses one that doesn't.
3. The workflow creates the release if it doesn't exist and attaches the exact `rewst.skill` bytes
   the build job checked, verified against that job's checksum.

Publishing a release from the GitHub UI on an existing `v*` tag attaches the asset too. A `v*` tag
is what ships bytes: without one for the current version, pushes to `main` only produce the
workflow artifact on the Actions run page, and CI prints a notice when `plugin.json`'s version has
no matching tag.

## 8. Assumptions and dependencies

- A Rewst MCP server is connected to the Claude surface you're using. Without one, treat every
  platform claim as unverified.
- The MCP token's RBAC is scoped to what the work actually needs. The skill assumes it, and
  cannot check it.
- The tenant manifest is yours to maintain. It's a cache with a TTL, not a source of truth, and
  entries past the TTL are treated as hints.
- Rewst is mid-platform-rebuild. Where a doc and the MCP server disagree, the server wins for
  tenant state, and the generation question ("legacy or new builders?") is worth answering before
  a build rather than during one.

## 9. Out of scope

- **Enforcement.** See section 6. The guardrails shape a session's behavior; they don't restrict
  the token.
- **Standing up or hosting an MCP server.** The skill consumes one; it doesn't provide one.
- **Rewst platform support.** This is a community project. Platform bugs and licensing questions
  go to Rewst.
- **Secret storage.** Nothing here holds credentials, and the manifest is explicitly designed not
  to.

## 10. License

MIT — see [`LICENSE`](LICENSE).
