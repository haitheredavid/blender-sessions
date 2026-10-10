# Writing Workflows

How to distill a technique from a session into `workflows/`. `/wrap` runs this.

## What qualifies

- A technique that would save a future session real time: a construction method, a fix for a recurring failure, a reusable param scheme.
- Not a model-specific fact (that goes in the model's session note) and not an operating rule (that goes in a `.context/` guide).

## Update before create

1. Search `workflows/README.md` for a doc that covers it. If one exists, update it: add steps, gotchas, a bpy snippet, and the model under **Models**.
2. Only if nothing fits, create `workflows/<kebab-name>.md` from `_template.md` and add a row to the README table.

## Writing rules

- Lead with one sentence: what it builds and when to use it.
- Steps are numbered and concrete: names, sizes, node types, not "set it up".
- Gotchas state cause → fix ("bevel before boolean → artifacts; apply booleans first").
- Snippets are short, runnable over MCP, and use `kit`/`patterns` where they exist.
- Point at a reference implementation path (`models/<m>/builders/...` or `lib/patterns/...`).
- If a snippet proves generic, move it into `lib/` and have the doc point there instead.
