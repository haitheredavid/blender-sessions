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

# --- sessions ----------------------------------------------------------------

# create sessions/YYYY-MM-DD-<name>/ and open it in Blender (--unit m|cm|mm)
new name *flags:
    {{blend}} new "$@"
    {{blend}} open {{name}}

# list sessions
ls:
    {{blend}} ls

# open a session's model.blend (MCP bridge auto-starts)
open session:
    {{blend}} open {{session}}

# mesh health of the Model collection (--strict also fails non-manifold/transforms)
check session *flags:
    {{blend}} check "$@"

# export the Model collection to exports/ (--formats glb,fbx,obj --split)
export session *flags:
    {{blend}} export "$@"

# studio render -> sessions/<s>/render.png + README gallery (--framing fit|wide)
render session *flags:
    {{blend}} render "$@"

# 360° turntable -> sessions/<s>/out/<s>-turntable.mp4 + .gif
turntable session *flags:
    {{blend}} turntable "$@"

# build assets/studio.blend, the scene render/turntable use (--overwrite discards hand edits)
render-scene *flags:
    {{blend}} render-scene "$@"

# rewrite the README gallery from every session's render.png
gallery:
    {{blend}} gallery

# check -> export -> render
wrap session:
    {{blend}} check {{session}}
    {{blend}} export {{session}}
    {{blend}} render {{session}}

# mark a session done and refresh the gallery
done session:
    {{blend}} done {{session}}

# workflows/ docs and the sessions that use each
workflows:
    {{blend}} workflows
