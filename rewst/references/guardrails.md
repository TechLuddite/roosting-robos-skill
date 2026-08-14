# Guardrails

Read this before the first write, publish, delete, or execution of a session — including
re-running a workflow while debugging. Read-only work can't violate most of it and doesn't need
it in context.

Rewst sits upstream of real customer environments — M365 tenants, AD, PSA, RMM. A mistake here
isn't a broken build, it's a customer incident. These rules are ordered roughly by how much
damage the mistake causes.

## Blast radius

**Confirm the target org by ID before any write, publish, or execution.** Customer names collide,
sub-orgs shadow each other, and the MSP owner org looks like just another entry in a list. If the
user says "do it for Acme," resolve Acme to an org ID, state the ID back, and get agreement. If
two orgs match the name, stop and ask.

**Treat the MSP owner org as production for everyone.** Org variables, tags, and workflows at the
owner level cascade. A change there that looks like a small config edit can alter behavior for
every customer simultaneously.

**Never run a workflow against "all organizations" to test something.** If a test needs a real
org, use a designated test/sandbox org. Ask which one; don't pick.

## Destructive actions

Require an explicit read-only dry run, shown to the user, before executing any of:

- Disabling, deleting, or deprovisioning users or devices
- Removing or reassigning licenses
- Password rotation or session invalidation
- Mailbox permission, forwarding, or delegation changes
- Group membership removal
- Conditional Access or security policy changes
- Bulk operations of any kind, including `with_items` over a list you didn't count first

The dry run means: resolve the exact set of objects that would be affected, show the count and a
sample, and confirm. "This will disable 1 user" and "this will disable 340 users" look identical
in a workflow definition and very different in a PSA queue the next morning.

## Crate-managed content

**Don't edit workflows, forms, or variables that came from a Crate.** The next Crate upgrade
overwrites them without warning and the customization vanishes — often noticed weeks later when
behavior silently reverts. Clone into your own namespace and modify the clone, or use the Crate's
supported extension points if it has them.

If you're unsure whether something is Crate-managed, check before editing rather than after.

## Secrets and data

- **Never hardcode credentials, API keys, tokens, or passwords** in Jinja, in a workflow field,
  in a PowerShell script body, or in a form default. Use integration credentials and org
  variables.
- **Never put a secret anywhere it lands in a run log.** Task results are stored and visible.
  Rewst supports JSONPath-based redaction — use it for anything sensitive passing through
  context.
- **Don't paste customer PII into chat** when a count or an ID would do.
- **Don't email, ticket, or message out** as part of a build test. Test notification steps against
  an internal address, and say which one you used.

## Reusability

- **Don't hardcode tenant-specific IDs into a workflow** intended for multiple orgs. Parameterize
  through org variables. A hardcoded board ID is the single most common reason a workflow works
  for one customer and silently mis-routes for the next.
- **Don't hardcode integration instance IDs** where the org's own integration should be resolved
  at runtime.

## Execution safety

- **Bound your loops.** `with_items` over an unpaged API result is how you discover the rate limit
  in production. Page explicitly and know the count.
- **Respect webhook trigger rate limits.** Don't design a fan-out that self-triggers.
- **Don't enable a production trigger to test a workflow.** Run it manually with test input, or
  use a trigger scoped to a test org.
- **Check for existing automation before adding new.** Duplicate offboarding workflows both firing
  is a real and common failure.

## Scope discipline

- **One approval covers one proposal.** If the org changes, the scope grows, or you discover the
  build needs a second workflow, re-propose. Don't chain "while I'm here" edits onto an approval.
- **Don't build around a permissions error.** If the MCP token can't do something, surface it.
  Working around a permission boundary defeats the control that boundary exists to provide.
- **Report what you actually did**, with IDs, including anything that partially completed. A
  half-built workflow the user doesn't know about is worse than a failed build.

## What these rules are not

These are behavioral guardrails inside one Claude session. They are not enforcement. Real
enforcement is the scope of the Rewst MCP token and the RBAC attached to it. If someone is doing
routine build work with a token that can write to every customer org, the token is the thing to
fix.
