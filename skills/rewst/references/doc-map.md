# Doc map

Routing table only — no doc content lives here on purpose. Rewst is mid-platform-rebuild and
cached prose goes stale silently, which is worse than a fetch.

## How to fetch

- Append `.md` to any URL for raw markdown: `https://docs.rewst.help/documentation/jinja.md`
- For a specific question, don't pull the whole page:
  ```
  GET https://docs.rewst.help/<page>.md?ask=<specific question>&goal=<what you're building>
  ```
  Returns a direct answer plus excerpts and sources. Use this by default; fetch full pages only
  when you need to read an entire procedure end to end.
- Keep `?ask`/`&goal` values generic — platform concepts only, never customer names, org IDs, or
  other tenant specifics. Query strings land in external logs.
- Full page index: `https://docs.rewst.help/llms.txt` — use when nothing below matches. It's
  large, so prefer the `?ask=` route against a plausible page first.

Base: `https://docs.rewst.help`

## Platform generation

| Topic | Path |
|---|---|
| New platform overview (Rewst Agent, new builders) | `/flow-2026-announcement/coming-soon-to-rewst` |
| AI basics | `/flow-2026-announcement/ai-basics` |
| Recent dev changes | `/updates/development-updates/2026-dev-updates` |

Check the first of these when tenant behavior contradicts older docs.

## Workflows

| Topic | Path |
|---|---|
| Workflows overview | `/documentation/automations/workflows` |
| Workflow builder setup | `/documentation/automations/workflows/workflow-builder-how-to-set-up-a-workflow` |
| Task transitions | `/documentation/automations/workflows/task-transitions` |
| Data aliases | `/documentation/automations/workflows/data-aliases` |
| Input vs context variables | `/documentation/automations/workflows/data-input-and-output-input-variables-and-context-variables` |
| Design best practices | `/documentation/automations/workflows/best-practices-for-designing-workflows` |
| Troubleshooting executions | `/documentation/automations/workflows/troubleshoot-workflow-executions-and-task-results` |
| Boolean logic | `/documentation/automations/workflows/boolean-logic-in-rewst-workflows` |
| Subworkflows (prebuilt catalog) | `/documentation/automations/subworkflows` |

## Actions

| Topic | Path |
|---|---|
| Actions overview | `/documentation/automations/actions-in-rewst` |
| Core actions | `/documentation/automations/actions-in-rewst/core-actions` |
| Rewst actions | `/documentation/automations/actions-in-rewst/rewst-actions` |
| Transform actions index | `/documentation/automations/actions-in-rewst/transform-actions` |
| Generic GraphQL request | `/documentation/automations/actions-in-rewst/generic-graphql-request-action` |

Individual transform actions live under `/transform-actions/<name>-transform-action`. Query the
index with `?ask=` rather than guessing a slug.

## Triggers and forms

| Topic | Path |
|---|---|
| Triggers | `/documentation/automations/intro-to-triggers` |
| Trigger criteria | `/documentation/automations/intro-to-triggers/trigger-criteria` |
| Webhook triggers | `/documentation/automations/intro-to-triggers/use-cases-and-examples/using-webhook-triggers` |
| Webhook rate limits | `/security/webhook-trigger-rate-limits` |
| Forms | `/documentation/automations/forms` |
| Form building | `/documentation/automations/forms/intro-to-forms` |
| Options filter (legacy) | `/documentation/automations/forms/options-filter-filtering-in-forms` |
| Option generator workflows (legacy) | `/documentation/automations/workflows/option-generator-workflows` |
| Form org variables | `/documentation/automations/forms/form-organizational-variables` |

Options Generator and Options Filter are replaced by the Options Builder in the new platform —
confirm generation before following the legacy pages.

## Jinja

| Topic | Path |
|---|---|
| Jinja index | `/documentation/jinja` |
| Essentials | `/documentation/jinja/jinja-essentials` |
| Data types | `/documentation/jinja/data-types` |
| Filter list | `/documentation/jinja/list-of-jinja-filters` |
| Common examples | `/documentation/jinja/common-jinja-examples` |
| Conditionals | `/documentation/jinja/common-jinja-examples/conditional-statements-and-logical-operators` |
| Loops | `/documentation/jinja/common-jinja-examples/loops-in-jinja` |
| Try/catch | `/documentation/jinja/common-jinja-examples/understanding-try-catch-blocks` |
| Reserved keywords | `/documentation/jinja/use-cases-and-best-practices/jinja-reserved-keywords` |
| Nested data extraction | `/documentation/jinja/use-cases-and-best-practices/efficiently-extracting-nested-data` |
| Collect CTX dynamically | `/documentation/jinja/use-cases-and-best-practices/collecting-ctx-variables-dynamically-using-jinja` |
| Context viewer | `/documentation/jinja/context-viewer` |
| PowerShell in Rewst | `/documentation/jinja/use-powershell-scripts-in-rewst` |
| JSONPath redaction | `/documentation/jinja/jsonpath-for-data-redaction-in-rewst` |

## Orgs, integrations, settings

| Topic | Path |
|---|---|
| Orgs and org variables | `/documentation/integrations/organization-variables` |
| Integrations index | `/documentation/integrations` |
| Integration guides | `/documentation/integrations/integration-guides` |
| Custom integrations v2 | `/documentation/integrations/custom-integrations/custom-integrations-v2` |
| Multi-instance integrations | `/documentation/integrations/multi-instance-integration` |
| Microsoft Cloud bundle | `/documentation/integrations/integration-guides/microsoft-cloud-integration-bundle` |
| Microsoft Cloud permissions | `/documentation/integrations/integration-guides/microsoft-cloud-integration-bundle/microsoft-cloud-permissions` |
| MS Cloud troubleshooting | `/documentation/integrations/integration-guides/microsoft-cloud-integration-bundle/microsoft-cloud-integration-bundle-troubleshooting-guide` |
| Permissions and roles | `/documentation/settings/roles` |
| Tags | `/documentation/settings/tags-in-rewst` |
| PowerShell interpreter | `/documentation/settings/powershell-interpreter` |

Per-integration guides follow `/documentation/integrations/integration-guides/<vendor>-integration`
but slugs are inconsistent (Autotask lives under `datto-psa-integration-setup`, OpenText under
`webroot-integration-setup`). Check `llms.txt` rather than guessing.

## Crates

| Topic | Path |
|---|---|
| Crates overview | `/documentation/crates` |
| Crate guides index | `/documentation/crates/existing-crate-documentation` |
| Version migration | `/documentation/crates/migrating-between-crate-versions` |
| Deprecation FAQ | `/documentation/crates/crate-deprecation-faq` |
| Crate with custom integration | `/documentation/crates/use-a-crate-with-a-custom-integration` |

## Other

| Topic | Path |
|---|---|
| Glossary | `/terms-and-definitions/glossary-of-terms` |
| Security policy / IPs | `/security/security-policy` |
| Agent Smith | `/documentation/agent-smith` |
| App Builder | `/documentation/app-builder` |
