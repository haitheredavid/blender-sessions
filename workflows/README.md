# Workflows

Reusable Blender techniques distilled from sessions. Read the relevant ones before modeling (`/make` does this). Write new ones or update existing ones when a session ends (`/done` does this). Start each new doc from `_template.md`.

`just workflows` lists each doc with the sessions that use it, read from `workflows = [...]` in each `session.toml`.

| workflow | summary |
|---|---|
| [mcp-modeling-loop](mcp-modeling-loop.md) | The base loop: small MCP code steps, `look` often, persist in builders/, save before `just` |
| [ring-sweep-frame](ring-sweep-frame.md) | Watertight profiled frame/bezel from same-count rings bridged in a loop; freeform outline, parametric profile |
| [variant-grid-exploration](variant-grid-exploration.md) | Lay param variants side by side via a non-NN `explore.py`, `look`, and let the user pick |
| [print-fit-and-sectioning](print-fit-and-sectioning.md) | Rabbet stacks (glazing/art/board), turn-clip pockets, skin asserts, splitting for the printer bed |
| [photo-to-texture](photo-to-texture.md) | Perspective-crop a handheld photo of flat art to a real-size texture; show it in Solid and Material views |
| [render-views-and-sections](render-views-and-sections.md) | `blend views` named shots (upright, include, zoom), matching cameras, live red-capped section cut |
