# Jinja gotchas

Traps only. For filter reference and syntax, fetch the docs — see `references/doc-map.md` under
Jinja. This file exists because the docs tell you what works and these are the things that
quietly don't.
The traps below are core Jinja2 engine semantics (verified 2026-08), not rebuild-sensitive
platform surface.

## Empty is not an error

The single most common Rewst failure mode: a lookup returns `[]`, the workflow continues happily,
and nothing happens. No error, no alert, ticket sits closed. Branch explicitly on empty results
rather than assuming a non-error means data.

```jinja
{{ CTX.users | default([]) | length > 0 }}
```

## Undefined propagates silently

An undefined value rendered into a string becomes empty rather than raising. `{{ CTX.typo_here }}`
produces `""` and the API call goes out with a blank field. Default anything sourced from a form,
an API, or another workflow:

```jinja
{{ CTX.department | default('Unassigned') }}
```

Chained attribute access is worse — `CTX.user.manager.email` fails differently depending on which
link is missing. Guard the whole chain, not the last hop.

## Type coercion at boundaries

Form inputs arrive as strings. A form field that looks like a number is `"12"`, and `"12" == 12`
is false. Comparisons against PSA IDs, license counts, and booleans are the usual casualties.
Cast at the boundary: `| int`, `| float`, and for booleans be explicit — `"false"` is a truthy
string.

## Whitespace in multi-line output

Jinja control blocks leave newlines behind. In anything where format matters — CSV generation,
JSON assembly, PowerShell script bodies — use whitespace control (`{%-` / `-%}`) or you'll ship
a file with blank lines between every row.

## Building JSON by string concatenation

Don't. A quote or backslash in a customer name breaks it, usually months later and only for one
customer. Build a dict and let the platform serialize it, or use `| tojson`.

## Loop scope

Variables set inside a `{% for %}` don't survive it. Accumulate with a namespace or use a filter
that does the aggregation directly. See the block scope doc if you need the mechanics.

## Reserved keywords

Rewst reserves certain names in Jinja context. Naming a task or variable one of them produces
confusing failures that don't look like naming collisions. The list is in the docs — check it
when a reference behaves impossibly.

## Deep extraction

For pulling nested values out of API responses, filters usually beat list comprehensions for both
readability and performance, and the docs have a page specifically comparing them. A comprehension
three levels deep is a sign the logic belongs in a transform action.

## Debugging

Use the Context Viewer rather than adding logging tasks. It shows actual runtime shape, which is
usually the answer — most Jinja "bugs" are the data being one level deeper than assumed, or a
single-item result arriving as an object rather than a list.

When an expression fails, evaluate the innermost piece first against real context. Debugging a
whole expression at once tells you it's broken, not where.

## When to stop using Jinja

If an expression needs a comment to be understandable, move it into a transform action or a
PowerShell step. Jinja that only its author can read is a maintenance liability in a platform
where someone else debugs it at 2am.
