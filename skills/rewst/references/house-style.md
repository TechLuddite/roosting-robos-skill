# House style

**This file belongs to you, not to the skill.** Everything else here describes Rewst or Claude's
procedure; this describes your team, and no one else can write it. The defaults below are modeled
on Rewst's own naming — overwrite them freely.

Three rules: (1) where this file contradicts anything else in the skill, this file wins — only
`references/guardrails.md` outranks it; (2) carry this file forward across skill updates, never
clobber it — on a plugin-marketplace install that means keeping your live copy outside the
plugin directory, because updates replace it; (3) anything marked `[SET THIS]` is an unmade
decision, and until it's made the skill drives consistency toward a guess.

---

## Naming

Rewst's own prebuilt content uses a bracketed-prefix convention that's worth matching so your
workflows sort alongside theirs rather than in a separate pile:

```
[SCOPE - TYPE] System: Action
```

- **SCOPE** — who owns it. Rewst ships `REWST` and `PROD`. Suggested for your own:
  - `[SET THIS]` — your MSP's prefix for owned production content
  - `DEV` — in progress, not safe to trigger
  - `TEST` — scratch, safe to delete
- **TYPE** — `PROCESS` for orchestrators that call other workflows, `TASK` for single-purpose
  leaf workflows, `SUB` for reusable subworkflows.
- **System** — the integration or domain: `M365`, `PSA-CW`, `PSA-Halo`, `RMM-Ninja`, `General`.
- **Action** — verb-first and specific. `Get User Licenses`, not `User License Stuff`.

Examples:
```
[ACME - PROCESS] Onboarding: Full User Create
[ACME - TASK] M365: Assign License Bundle
[DEV - TASK] PSA-CW: Upsert Contact
```

Forms: `Customer-facing name` — end users see these, so no prefixes or internal jargon.

Org variables: `[SET THIS: snake_case or camelCase]`, prefixed by domain —
`psa_default_board_id`, `m365_license_sku_standard`. Never abbreviate to the point of ambiguity;
these get read by people six months later with no context.

## Structure

**One workflow, one job.** If a workflow needs a paragraph to describe, it should be a PROCESS
that calls TASKs. Deep single workflows are the hardest thing in Rewst to debug because the
context viewer gets unwieldy and a failure at step 40 makes you re-run steps 1–39.

**Parameterize anything org-specific.** Board IDs, queue IDs, license SKUs, notification
addresses, approval recipients — org variables, not literals. A workflow that only works for one
customer should be the exception and should say so in its description.

**Name your tasks meaningfully.** Task names become the keys in `CTX` and in run logs. `get_user`
is findable; `task_7` is not. Use `snake_case` for task names regardless of the variable
convention above, since that's what reads cleanly in Jinja references.

**Set data aliases deliberately** rather than reaching deep into raw task output everywhere. One
alias near the source beats fifteen copies of a nested path that breaks when the API adds a
wrapper.

## Error handling

Every workflow that touches a customer system should answer three questions in its structure:

1. **What happens if the lookup returns nothing?** Not an error — an empty list is a normal
   result and the most common cause of a workflow that "worked" but did nothing. Branch on it
   explicitly.
2. **What happens if the write fails?** At minimum, don't continue as if it succeeded. Preferably
   surface it: PSA note, ticket, or notification.
3. **How does a human find out?** Silent failure is the default in automation and the reason
   nobody trusts it. `[SET THIS: your notification target — PSA ticket, Teams channel, email]`

Use transitions on failure, not just on success. A workflow with only success transitions has no
error handling; it just stops.

## Documentation

Fill in the workflow description field. It costs thirty seconds and it's the only thing standing
between the next person and reverse-engineering forty tasks. Include: what it does, what triggers
it, what org variables it depends on, and anything non-obvious about why.

Tag consistently — `[SET THIS: your tag taxonomy]`. Tags are how anything gets found once the
tenant has a few hundred workflows.

## Jinja

- Keep it short, and prefer explicit filters over clever comprehensions — the next person
  debugging it at 2am is the audience.
- The traps themselves (undefined propagation, empty results, type coercion) live in
  `references/jinja-gotchas.md`; treat that file, not memory, as the checklist.

## PowerShell

- Return structured objects, not formatted text. `ConvertTo-Json` at the boundary.
- No credentials in the script body — pass them in.
- Fail loudly with a non-zero exit or a clear error object; a script that swallows errors makes
  the workflow think it succeeded.

## Before you call it done

- Does it work for a second org, or only the one you tested?
- Does it do the right thing when the input list is empty?
- Would someone else understand it from the description alone?
- Is anything in it Crate-managed and about to be overwritten?
