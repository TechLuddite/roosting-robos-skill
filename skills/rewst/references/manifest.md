# Tenant manifest

The manifest is the token lever — a cache, not a source of truth. The constants policy and
cache/verify rule in SKILL.md govern it; this file covers what goes in, how to refresh, and
where it lives.

## What goes in

Tier 2 constants only — stable for weeks, expensive to discover:

- Org IDs and names (owner + sub-orgs), with any tags used for routing
- Integration IDs and instance names per org
- Org variable names, types, and which orgs have them set (names and shapes, **not values**)
- PSA lookup values: boards, queues, statuses, priorities, types, subtypes, member IDs
- Workflow and form IDs for things you build against repeatedly
- The MCP tool names you actually found — draft-time hints only; every session still
  re-enumerates before its first live call, because the server is beta and names change

## What stays out

- **Any secret, credential, token, or org variable *value*.** Names and types only. The manifest
  is a plain file that may end up in a repo or a project upload.
- Customer PII of any kind.
- Run results, execution history, current status — Tier 3, always live.
- Doc content — Tier 1, always fetched.

## Schema

```json
{
  "schema_version": 1,
  "tenant": "<owner org ID as reported by the server>",
  "region": "us-east",
  "generated_at": "2026-08-14T00:00:00Z",
  "ttl_days": 14,
  "platform_generation": "legacy | new | mixed | unknown",
  "mcp_tools": ["<actual tool names discovered, not assumed>"],
  "orgs": [
    {
      "id": "<org-id>",
      "name": "Acme Corp",
      "role": "owner | customer | test",
      "tags": ["psa-connectwise", "m365"],
      "captured_at": "2026-08-14T00:00:00Z"
    }
  ],
  "integrations": [
    {
      "org_id": "<org-id>",
      "type": "connectwise_psa",
      "instance_name": "Primary",
      "id": "<integration-id>",
      "captured_at": "2026-08-14T00:00:00Z"
    }
  ],
  "org_variables": [
    {
      "name": "psa_default_board_id",
      "type": "string",
      "set_for": ["<org-id>", "<org-id>"],
      "notes": "board tickets route to by default",
      "captured_at": "2026-08-14T00:00:00Z"
    }
  ],
  "psa_lookups": {
    "<org-id>": {
      "boards": [{"id": 12, "name": "Service Board"}],
      "statuses": [{"id": 3, "name": "New"}],
      "priorities": [{"id": 2, "name": "Medium"}],
      "captured_at": "2026-08-14T00:00:00Z"
    }
  },
  "workflows": [
    {
      "id": "<workflow-id>",
      "name": "[ACME - TASK] M365: Assign License Bundle",
      "crate_managed": false,
      "captured_at": "2026-08-14T00:00:00Z"
    }
  ],
  "forms": [
    {
      "id": "<form-id>",
      "name": "New User Request",
      "bound_workflow_id": "<workflow-id>",
      "captured_at": "2026-08-14T00:00:00Z"
    }
  ]
}
```

Every entry carries `captured_at` individually — refreshes are usually partial, and a single
top-level timestamp would make a two-month-old org list look as fresh as this morning's PSA
lookup.

Mark `crate_managed` on anything that came from a Crate. That flag is what stops a later session
editing something the next Crate upgrade will overwrite.

## Refresh procedure

Refreshing is a Claude procedure, not a script — the MCP tools are called by Claude, not by
Python. Don't look for a refresh script; there isn't one and there can't be.

1. **Discover the tool surface.** List available Rewst MCP tools. Record the real names. The
   server is beta; do not assume names from a previous session or from memory.
2. **Sweep breadth-first, not depth-first.** Orgs, then integrations, then org variable names.
   Stop there for a first pass. PSA lookups are per-org and expensive — pull them only for orgs
   the user actually works in, and ask which those are rather than fetching all of them.
   Re-verify `role` labels (owner/customer/test) whenever a refresh touches orgs.
3. **Compact as you go.** Store IDs, names, and types. Drop descriptions, timestamps you don't
   need, nested metadata, and anything you'd never reference. A manifest that reproduces the API
   response verbatim defeats its own purpose.
4. **Strip values.** Org variable names and types, never values.
5. **Stamp** each entry with `captured_at`, and set the top-level fields: `tenant` (the owner
   org ID as reported by the server — the identifier the first-use binding check compares),
   `region`, `platform_generation`, and a fresh `generated_at`.
6. **Validate**: `python scripts/validate_manifest.py <path>`
7. **Report** what was captured and what was deliberately skipped, so the user knows the shape of
   the cache rather than assuming it's complete.

### Partial refresh

Most refreshes should be partial. If a build needs one customer's PSA lookups, refresh that org's
entry alone and leave the rest. Full sweeps are for initial setup or after a major tenant change
(new PSA, migration, bulk onboarding).

## Where the manifest lives

Resolution order — use the first available (the shipped UNCONFIGURED starter counts as absent;
continue down the list):

1. **A path the user names.** Always wins.
2. **`references/tenant-manifest.json` inside this skill.** Readable on both surfaces; writable
   only in Claude Code, where the skill lives in an editable repo and manifest changes show up
   in diffs. A refresh written here on claude.ai never reaches the uploaded skill — use option
   1 or 3 there.
3. **A connected document/memory store MCP server**, under a stable title such as
   `rewst-tenant-manifest`. Best cross-surface option: one refresh in Claude Code serves
   claude.ai sessions too.
4. **A local working file in Claude Code.** Fast, but a scratch cache — offer to promote it to
   option 2 or 3.

**Claude Code** — files persist; if the skill lives in a repo, manifest changes show up in diffs,
which is a feature.

**claude.ai** — the sandbox filesystem resets between sessions. A file written to `/home/claude`
is gone next time; never tell the user a manifest is cached when it's sitting in a sandbox about
to be wiped. On claude.ai, persistence means option 1 or 3.

## When the manifest is wrong

If a verification step finds a cached ID no longer exists or has changed:

1. Stop the build. Don't substitute a similar-looking ID.
2. Tell the user what changed.
3. Fix that manifest entry.
4. Consider whether related entries are also stale — IDs rarely change alone. A removed
   integration usually means the org variables pointing at it are stale too.
