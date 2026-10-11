set dotenv-load := false
# pass recipe args through as "$@" so quoted values stay intact
set positional-arguments

blend := "uv run blend"

# list recipes
default:
    @just --list --unsorted

# --- setup / dev -------------------------------------------------------------

# install deps, create .env if missing
setup:
    uv sync
    test -f .env || cp .env.example .env

# install/update the MCP for Blender add-on (then restart Blender)
addon:
    uvx mcp-for-blender install-addon

# run tests
test *args:
    uv run pytest "$@"

# lint + format check
lint:
    uv run ruff check .
    uv run ruff format --check .

# auto-fix lint + format
fmt:
    uv run ruff check --fix .
    uv run ruff format .

# lint + tests
ci: lint test

# --- models and sessions -----------------------------------------------------

# create models/<name>/ and open it in Blender (--unit m|cm|mm)
new name *flags:
    {{blend}} model new "$@"
    {{blend}} open {{name}}

# list models
ls:
    {{blend}} model ls

# open a model's model.blend (MCP bridge auto-starts)
open model:
    {{blend}} open {{model}}

# start a session note for a model (--goal "...")
session model name *flags:
    {{blend}} session new "$@"

# a model's step timeline (--last N)
history model *flags:
    {{blend}} history "$@"

# --- outputs -------------------------------------------------------------------

# mesh health of the Model collection (--strict also fails non-manifold/transforms)
check model *flags:
    {{blend}} check "$@"

# export the Model collection to exports/ (--formats glb,fbx,obj,stl,3mf --split)
export model *flags:
    {{blend}} export "$@"

# studio render -> models/<m>/render.png + README gallery (--framing fit|wide)
render model *flags:
    {{blend}} render "$@"

# 360° turntable -> models/<m>/out/<m>-turntable.mp4 + .gif
turntable model *flags:
    {{blend}} turntable "$@"

# render the scene's own animation (kit.anim keys) -> models/<m>/out/animation.mp4 + .gif
animate model *flags:
    {{blend}} animate "$@"

# render the model's [[views]] studio shots -> models/<m>/out/views/ (--only NAME)
views model *flags:
    {{blend}} views "$@"

# render every params.toml variant with one shot -> models/<m>/out/variants.png (--view NAME)
variants model *flags:
    {{blend}} variants "$@"

# build lib/patterns into assets/patterns.blend (GN groups as assets)
patterns-lib:
    {{blend}} patterns-lib

# build assets/studio.blend, the scene render/turntable use (--overwrite discards hand edits)
render-scene *flags:
    {{blend}} render-scene "$@"

# rewrite the README gallery from every model's render.png
gallery:
    {{blend}} gallery

# check -> export -> render
wrap model:
    {{blend}} check {{model}}
    {{blend}} export {{model}}
    {{blend}} render {{model}}

# mark a model done and refresh the gallery
done model:
    {{blend}} model done {{model}}

# workflows/ docs and the models that use each
workflows:
    {{blend}} workflows
