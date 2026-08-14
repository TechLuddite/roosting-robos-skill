---
name: rewst
description: Build, edit, debug and review Rewst automations (workflows, forms, apps, Crates, org variables, Jinja, integrations) via the Rewst MCP server. Use this skill whenever the user mentions Rewst, Crates, RoboRewsty, org variables, or Rewst workflows/forms; asks to build, fix, or inspect anything in their Rewst tenant; mentions Jinja in an MSP automation context; or reports MSP automation symptoms even without naming Rewst — an onboarding/offboarding workflow that broke or misfired, a workflow that ran but did nothing, empty form options, blank CTX variables, misrouted PSA tickets. Enforces multi-tenant write guardrails and house build conventions.
---

# Rewst

Rewst is a multi-tenant MSP automation platform: one tenant holds the MSP owner org plus many
customer sub-orgs, so a wrong org ID fires at a real customer's production environment.

## Route by task

- **Read-only** (explain, inspect, debug, review): work from the manifest and docs. No extra
  reads required — except `references/jinja-gotchas.md` whenever Jinja is being written or
  debugged.
- **Creating or editing** anything: read `references/house-style.md` first. Where files disagree,
  the order is `guardrails.md` > `house-style.md` > this file > other references.
- **Any write, publish, delete, or execution** — including re-running a workflow while debugging:
  read `references/guardrails.md` before the first such action, and follow the Build procedure.
  Re-read it before any destructive or bulk execution if the earlier read is no longer reliably
  in context (long sessions, compaction) — the rules only work while they're resident.

The Rewst MCP server is beta and tool names change: enumerate the tools once per session rather
than assuming names, and record what you find in the manifest. If the server isn't connected,
say so and fall back to advisory mode — design and review are fine, but flag that nothing is
verified against the live tenant instead of guessing at IDs.

## Constants policy

Three tiers, three rules. Mixing them up is what makes Rewst sessions expensive.

- **Platform constants** (transform action behavior, Jinja filters, core action shapes, trigger
  types): fetch from docs via `references/doc-map.md`. Never cache — the docs are the source of
  truth and a copy just goes stale.
- **Tenant constants** (org IDs, integration IDs, workflow/form IDs, org variable names, PSA
  boards/statuses/priorities/queues, tags): read from `references/tenant-manifest.json`. This is
  the token lever — a live discovery sweep costs tens of thousands of tokens; the manifest costs
  a file read. If no manifest exists, say so and offer to build one (`references/manifest.md`)
  rather than silently sweeping.
- **Live state** (run results, execution status, recent modifications): always query, never
  cache — and query narrow. One execution, one task result, one object; pull full run histories
  or whole workflow exports only when a targeted read genuinely can't answer the question.
  Freshness means re-querying state, not re-pulling payloads at full width.

**Cache/verify rule:** cached tenant constants are good enough to reason and draft with, not to
write with. Before any create/update/publish/delete/execute, re-verify the specific IDs that
operation touches against the live server — verifying three IDs costs almost nothing, and in a
multi-tenant platform a stale ID can mean a write that *succeeds*, against the wrong thing.
Treat entries older than the manifest TTL as hints, and say so when relying on one. On first
manifest use in a session, check the manifest's `tenant` against the connected server — a
manifest from a different tenant is worse than none; treat it as absent and offer a refresh.

## Doc lookups

Fetch, don't recall — the platform is mid-rebuild. `references/doc-map.md` routes topics to URLs
and documents the cheap fetch mechanics (`.md` suffix, `?ask=` queries, `llms.txt`). Never paste
doc prose into the manifest or notes as a permanent record. If a doc fetch fails or fetching is
unavailable on this surface, say so, label any platform-behavior claim as unverified trained
knowledge, and prefer pointing the user at the doc URL over asserting from memory.

Rewst is transitioning between platform generations (Rewst Agent, new Form/Options/Integration
Builders). Where a doc contradicts what the MCP server reports, trust the server for tenant state
and ask which generation the tenant is on rather than averaging the two.

## Build procedure

For anything that creates or modifies. The in-product Rewst Agent runs enforced playbooks before
authoring; driving the tenant over MCP bypasses them, so this procedure is the replacement.

1. **Scope.** Restate what will be built and which org it targets — by ID, not name. Names
   collide.
2. **Research.** Manifest first, docs second, live MCP only for what neither has.
3. **Propose.** Show nodes/tasks in order, field mappings, the specific IDs, the failure path,
   and the doc pages consulted for any non-trivial Jinja or action configuration. Name anything
   taken on trust from a stale manifest entry.
4. **Confirm and wait.** Restate the guardrails that apply to this build (dry run, owner-org
   cascade, bulk bounds) in the proposal, so they're resident at the moment of the write. One
   approval covers the proposal as stated; if the org or scope changes, re-propose.
5. **Build** to `references/house-style.md`.
6. **Verify.** Re-read the created objects from the tenant, confirm they match the proposal, and
   report what was built with IDs.
7. **Update the manifest** with new IDs, fresh `captured_at` stamps.

Debugging starts at 2 (research) and verifies by re-reading whatever it touched; a debug fix
that modifies anything still gets a brief propose-and-confirm (3–4), and org confirmation
always applies before re-running anything.

## Capturing house style

When the user corrects a name, structure, or pattern, ask once: "general rule, or just here?" If
general, offer the exact wording to add to `references/house-style.md` — never edit it silently.
`[SET THIS]` markers are unmade decisions; ask when one blocks a build, since a concrete case is
the cheapest moment to get an answer. If the user corrects the same class of thing twice across
sessions, the first correction failed to land — fix the file, not just the build. On claude.ai
the skill's copy of `house-style.md` isn't writable across sessions: put the exact wording in
front of the user to add to their copy (or the shared doc store), and never claim the file was
updated when it wasn't.

## Hard rules (always active)

- **Never write, publish, or execute against an org the user hasn't confirmed by ID.**
- **Never run a destructive identity or license action** (disable, delete, deprovision, license
  removal, password rotation, mailbox changes) without a read-only dry run shown to the user.
- **Never edit a Crate-managed workflow or form** — the next Crate upgrade silently overwrites
  it. Clone and modify the clone.
- **Treat any write to the MSP owner org as a change to every customer** — name the cascade
  explicitly before asking for confirmation.
- **Never execute against "all organizations."** Tests run only in a user-designated test org.

The full list is `references/guardrails.md` (when to read it: Route by task). These rules are
behavioral, not enforced — real enforcement is the MCP token's scope and RBAC, worth mentioning
once if the user runs high-risk work on a broad token.

## Reference files

| File | Read it when | Owner |
|---|---|---|
| `references/guardrails.md` | Before any write, publish, delete, or execution | skill |
| `references/house-style.md` | Creating or editing anything | **the user** |
| `references/doc-map.md` | You need a Rewst doc | skill |
| `references/manifest.md` | Building, refreshing, or resolving the tenant manifest | skill |
| `references/jinja-gotchas.md` | Writing or debugging Jinja | skill |
| `references/tenant-manifest.json` | The cached tenant constants themselves | generated |

`house-style.md` and `tenant-manifest.json` must survive skill updates; everything skill-owned
can be regenerated. `scripts/validate_manifest.py <path>` checks manifest shape and staleness
after a refresh.
