"""`blend repl`: a Rhino-style command prompt in the terminal for the live Blender.

A line whose first word is a command runs as a call (`gn Frame Depth 0.4` ->
`gn("Frame", "Depth", 0.4)`); anything else is Python. Both run inside Blender through the
blender-mcp socket (blend.bridge) in a namespace that persists between inputs
(lib/cmdline/remote.py). Blender commands live in lib/cmdline/commands.py; the host
commands below (log, look, reset, exit) need the repo or the terminal.
"""

import ast
import codeop
import json
import shlex
from pathlib import Path

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers.python import PythonLexer
from rich.console import Console

from blend import model as models
from blend.bridge import Bridge, BridgeError
from blend.config import get_settings
from blend.steplog import StepLog

MARK = "\x00blend-repl\x00"  # matches lib/cmdline/remote.py
HISTORY = Path.home() / ".cache" / "blend" / "repl_history"
# Blender commands that never change the model, so `log` leaves them out.
READONLY = {"help", "ls", "sel", "zoom", "save"}
HOST_HELP = {
    "log": "log [slug intent...]: save model-changing input since the last log as a step",
    "look": "look [size]: viewport screenshot, opened in your image viewer",
    "reset": "reset: fresh namespace, reload lib/cmdline commands",
    "exit": "exit (or Ctrl-D)",
}
# A command word followed by one of these is Python using that name (`ls = 3`, `gn(...)`).
_PYTHON_AFTER = "=([.,:"

console = Console()


# --- parsing --------------------------------------------------------------------


def _value(token: str):
    """Numbers, booleans and number tuples as such; everything else stays a string."""
    if token.lower() in ("true", "false"):
        return token.lower() == "true"
    try:
        v = ast.literal_eval(token)
    except (ValueError, SyntaxError, MemoryError, RecursionError):
        return token
    if isinstance(v, bool | int | float):
        return v
    if isinstance(v, tuple | list) and all(isinstance(x, int | float) for x in v):
        return v
    return token


def parse(line: str, names) -> tuple[str, list] | None:
    """(command, args) when the line's first word is a command, else None (Python)."""
    if "\n" in line.strip():
        return None
    words = line.strip().split(None, 1)
    if not words or words[0] not in names:
        return None
    rest = words[1] if len(words) > 1 else ""
    if rest and rest[0] in _PYTHON_AFTER:
        return None
    try:
        tokens = shlex.split(rest)
    except ValueError:  # unbalanced quote: let Python report it
        return None
    return words[0], [_value(t) for t in tokens]


def to_python(name: str, args: list) -> str:
    def lit(v):
        return json.dumps(v) if isinstance(v, str) else repr(v)

    return f"{name}({', '.join(lit(a) for a in args)})"


def is_complete(text: str) -> bool:
    """Whether Enter should run the input (else it adds a line, like the Python REPL)."""
    if not text.strip():
        return True
    lines = text.split("\n")
    last = lines[-1]
    if len(lines) > 1 and not last.strip():
        return True  # a blank line ends a block
    if last.rstrip().endswith(":") or (len(lines) > 1 and last[:1] in " \t"):
        return False
    try:
        return codeop.compile_command(text, "<repl>", "exec") is not None
    except (SyntaxError, ValueError, OverflowError):
        return True  # commands, or Python errors Blender will report


def _indent(text: str) -> str:
    last = text.split("\n")[-1]
    pad = last[: len(last) - len(last.lstrip())]
    return pad + "    " if last.rstrip().endswith(":") else pad


def changes_model(call: tuple[str, list] | None, src: str) -> bool:
    """Worth logging: not a read-only command, and not a bare non-call expression."""
    if call is not None:
        name, args = call
        return not (name in READONLY or (name == "gn" and len(args) < 3))
    try:
        body = ast.parse(src).body
    except SyntaxError:
        return False
    return not (
        len(body) == 1
        and isinstance(body[0], ast.Expr)
        and not isinstance(body[0].value, ast.Call)
    )


def remote_code(src: str, reset: bool = False) -> str:
    lib = str(get_settings().lib_dir)
    pre = f"import sys\nif {lib!r} not in sys.path:\n    sys.path.insert(0, {lib!r})\n"
    if reset:
        pre += (
            "import importlib, cmdline.commands, cmdline.remote\n"
            "importlib.reload(cmdline.commands)\nimportlib.reload(cmdline.remote)\n"
        )
    return pre + f"from cmdline import remote\nremote.run({src!r}, reset={reset})\n"


# --- session --------------------------------------------------------------------


class Repl:
    def __init__(self, bridge: Bridge):
        self.bridge = bridge
        self.commands: set[str] = set()
        self.state: dict = {"file": "", "objects": [], "gn": {}}
        self.pending: list[str] = []

    @property
    def names(self) -> set[str]:
        return self.commands | HOST_HELP.keys() | {"quit"}

    def model(self) -> models.Model | None:
        path = Path(self.state["file"]) if self.state["file"] else None
        if path and path.parent.parent == get_settings().models_dir.resolve():
            return models.Model(path.parent)
        return None

    def prompt(self) -> str:
        m = self.model()
        if m:
            return f"{m.name}> "
        return f"{Path(self.state['file']).stem or 'blender'}> "

    def remote(self, src: str, reset: bool = False) -> tuple[str, bool]:
        """Run src in Blender; print its output; return (output, ok)."""
        out = self.bridge.execute(remote_code(src, reset))
        text, found, trailer = out.rpartition(MARK)
        if not found:
            raise BridgeError(out)
        info = json.loads(trailer)
        self.state = {k: info[k] for k in ("file", "objects", "gn")}
        self.commands = set(info["commands"])
        if text:
            print(text, end="" if text.endswith("\n") else "\n")
        if info["error"]:
            console.print(
                info["error"].rstrip(), style="red", markup=False, soft_wrap=True
            )
        return text, info["ok"]

    def connect(self) -> None:
        self.remote("")

    def handle(self, text: str) -> None:
        text = text.rstrip()
        if not text.strip():
            return
        call = parse(text, self.names)
        if call and call[0] in HOST_HELP.keys() | {"quit"}:
            getattr(self, f"cmd_{'exit' if call[0] == 'quit' else call[0]}")(*call[1])
            return
        src = to_python(*call) if call else text
        _, ok = self.remote(src)
        if call == ("help", []):
            for line in HOST_HELP.values():
                print(line)
        if ok and changes_model(call, src):
            self.pending.append(src)

    # host commands

    def cmd_exit(self) -> None:
        raise EOFError

    def cmd_reset(self) -> None:
        self.remote("", reset=True)
        self.pending.clear()
        print("namespace reset, commands reloaded")

    def cmd_look(self, size: int = 1200) -> None:
        m = self.model()
        out = m.out if m else Path.home() / ".cache" / "blend"
        out.mkdir(parents=True, exist_ok=True)
        path = out / "repl_look.png"
        result = self.bridge.send(
            "get_viewport_screenshot", max_size=int(size), filepath=str(path)
        )
        if isinstance(result, dict) and result.get("error"):
            console.print(result["error"], style="red", markup=False, soft_wrap=True)
            return
        typer.launch(str(path))

    def cmd_log(self, slug=None, *intent) -> None:
        if slug is None:
            print("\n".join(self.pending) if self.pending else "nothing to log yet")
            return
        if not self.pending:
            print("nothing to log: no model-changing input since the last log")
            return
        m = self.model()
        if m is None:
            console.print(
                f"not a repo model: {self.state['file'] or '(unsaved)'}", style="red"
            )
            return
        code = "from cmdline.commands import *  # blend repl commands\n\n"
        st = StepLog(m).append(
            str(slug),
            intent=" ".join(map(str, intent)),
            code=code + "\n".join(self.pending) + "\n",
        )
        self.pending.clear()
        console.print(f"[green]step {st.n}[/green] {st.slug} -> {st.code}")


class _Completer(Completer):
    """Command names first; then object names, or GN input names after `gn <obj>`."""

    def __init__(self, repl: Repl):
        self.repl = repl

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if "\n" in text:
            return
        words = text.split(" ")
        word = words[-1].strip('"')
        if len(words) == 1:
            options = sorted(self.repl.names)
        elif words[0] in self.repl.names:
            gn = self.repl.state["gn"]
            if words[0] == "gn" and len(words) == 3 and words[1] in gn:
                options = gn[words[1]]
            else:
                options = self.repl.state["objects"]
        else:
            return
        for o in options:
            if o.lower().startswith(word.lower()):
                yield Completion(
                    f'"{o}"' if " " in o else o, start_position=-len(words[-1])
                )


def _keys() -> KeyBindings:
    kb = KeyBindings()

    @kb.add("enter")
    def _(event):
        buf = event.current_buffer
        if is_complete(buf.text):
            buf.validate_and_handle()
        else:
            buf.insert_text("\n" + _indent(buf.text))

    @kb.add("escape", "enter")  # Alt/Esc-Enter runs the input as it stands
    def _(event):
        event.current_buffer.validate_and_handle()

    return kb


def run(bridge: Bridge, expect: models.Model | None = None) -> None:
    repl = Repl(bridge)
    try:
        repl.connect()
    except BridgeError as e:
        console.print(
            f"could not start the REPL in Blender:\n{e}", style="red", markup=False
        )
        raise typer.Exit(1)
    if expect and Path(repl.state["file"]) != expect.blend.resolve():
        console.print(
            f"[yellow]Blender has {repl.state['file'] or 'an unsaved file'} open, "
            f"not {expect.name}[/yellow]"
        )
    console.print(
        "[dim]Commands like `gn Frame Depth 40`, Python otherwise. "
        "`help` lists commands. Ctrl-D exits.[/dim]"
    )
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    session = PromptSession(
        history=FileHistory(str(HISTORY)),
        lexer=PygmentsLexer(PythonLexer),
        completer=_Completer(repl),
        key_bindings=_keys(),
        multiline=True,
        prompt_continuation=lambda width, n, soft: "... ".rjust(width),
    )
    while True:
        try:
            text = session.prompt(repl.prompt())
        except KeyboardInterrupt:
            continue
        except EOFError:
            break
        try:
            repl.handle(text)
        except EOFError:
            break
        except KeyboardInterrupt:
            console.print(
                "[yellow]interrupted; Blender may still be running it[/yellow]"
            )
        except BridgeError as e:
            console.print(str(e), style="red", markup=False, soft_wrap=True)
        except Exception as e:  # noqa: BLE001 - keep the prompt alive on bad input
            console.print(
                f"{type(e).__name__}: {e}", style="red", markup=False, soft_wrap=True
            )
    bridge.close()
    if repl.pending:
        console.print(
            f"[yellow]{len(repl.pending)} unlogged input(s) dropped "
            "(use `log <slug>` before exiting to keep them)[/yellow]"
        )
