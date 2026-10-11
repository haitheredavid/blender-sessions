import json
import socket
import threading
from types import SimpleNamespace

import pytest

from blend import model as models
from blend import repl
from blend.bridge import Bridge, BridgeError

NAMES = {"gn", "ls", "sel", "log", "help"}


def test_command_lines_become_calls():
    def call(line):
        return repl.to_python(*repl.parse(line, NAMES))

    assert call("gn Frame Depth 0.4") == 'gn("Frame", "Depth", 0.4)'
    assert call("ls") == "ls()"
    assert call("sel Clip_* Key_N") == 'sel("Clip_*", "Key_N")'
    assert call('gn Frame "Wall Height" 3') == 'gn("Frame", "Wall Height", 3)'
    assert call("log wider-rim make it wider") == (
        'log("wider-rim", "make", "it", "wider")'
    )


def test_values_are_typed():
    assert repl.parse("gn Frame Count 12", NAMES) == ("gn", ["Frame", "Count", 12])
    assert repl.parse("gn Frame Flip true", NAMES) == ("gn", ["Frame", "Flip", True])
    assert repl.parse("gn F Size 1,2,3", NAMES) == ("gn", ["F", "Size", (1, 2, 3)])
    assert repl.parse("sel None", NAMES) == ("sel", ["None"])  # stays a string


def test_python_passes_through():
    for line in ["gn('F')", "ls = 3", "x = 1", "D.objects", "help(bpy)", "gn.x", ""]:
        assert repl.parse(line, NAMES) is None
    assert repl.parse('gn Frame "unclosed', NAMES) is None
    assert repl.parse("ls\nls", NAMES) is None  # multi-line input is Python


def test_enter_runs_complete_input_and_continues_blocks():
    assert repl.is_complete("gn Frame Depth 40")
    assert repl.is_complete("x = 1")
    assert repl.is_complete("1 +")  # syntax error: run it, Blender reports it
    assert not repl.is_complete("f(1,")
    assert not repl.is_complete("for o in D.objects:")
    assert not repl.is_complete("for o in D.objects:\n    print(o)")
    assert repl.is_complete("for o in D.objects:\n    print(o)\n")
    assert repl._indent("for o in D.objects:") == "    "
    assert repl._indent("for o in x:\n    if o:") == "        "


def test_changes_model():
    assert repl.changes_model(("gn", ["F", "Depth", 4]), "")
    assert not repl.changes_model(("gn", ["F", "Depth"]), "")
    assert not repl.changes_model(("ls", []), "")
    assert not repl.changes_model(None, 'D.objects["F"].location')
    assert repl.changes_model(None, 'D.objects["F"].location.z = 1')
    assert repl.changes_model(None, "kit.params.apply('base')")


def test_remote_code_quotes_input():
    code = repl.remote_code('print("hi")\nx = 1')
    assert "remote.run('print(\"hi\")\\nx = 1', reset=False)" in code
    assert "importlib.reload" in repl.remote_code("", reset=True)


def serve(replies):
    """A one-connection fake add-on: answers each request with the next reply, the
    first one split in two chunks."""
    srv = socket.socket()
    srv.bind(("localhost", 0))
    srv.listen(1)
    seen = []

    def loop():
        conn, _ = srv.accept()
        for i, reply in enumerate(replies):
            seen.append(json.loads(conn.recv(65536)))
            data = json.dumps(reply).encode()
            if i == 0:
                conn.sendall(data[:7])
                conn.sendall(data[7:])
            else:
                conn.sendall(data)
        conn.close()
        srv.close()

    threading.Thread(target=loop, daemon=True).start()
    return srv.getsockname()[1], seen


def test_bridge_reads_split_replies_and_errors():
    port, seen = serve(
        [
            {"status": "success", "result": {"executed": True, "result": "hi\n"}},
            {"status": "error", "message": "boom"},
        ]
    )
    b = Bridge(port=port, timeout=5)
    assert b.execute("print('hi')") == "hi\n"
    with pytest.raises(BridgeError, match="boom"):
        b.send("get_scene_info")
    assert seen[0] == {"type": "execute_code", "params": {"code": "print('hi')"}}
    b.close()


class FakeBridge:
    """Answers execute() like lib/cmdline/remote.py would."""

    def __init__(self, file, ok=True):
        self.file, self.ok, self.sent = file, ok, []

    def execute(self, code):
        self.sent.append(code)
        info = {
            "ok": self.ok,
            "error": None if self.ok else "Traceback...\nKeyError: 'x'",
            "file": str(self.file),
            "commands": ["gn", "help", "ls"],
            "objects": ["Frame"],
            "gn": {"Frame": ["Depth"]},
        }
        return "out\n" + repl.MARK + json.dumps(info)


def test_repl_runs_commands_and_logs_steps(models_dir, monkeypatch, capsys):
    m = models.create("frame", base=models_dir)
    monkeypatch.setattr(
        repl,
        "get_settings",
        lambda: SimpleNamespace(models_dir=models_dir, lib_dir="L"),
    )
    r = repl.Repl(FakeBridge(m.blend))
    r.connect()
    assert r.prompt() == "frame> " and "gn" in r.commands

    r.handle("gn Frame Depth 40")
    r.handle("ls")
    r.handle("D.objects['Frame'].location")
    assert 'remote.run(\'gn("Frame", "Depth", 40)\'' in r.bridge.sent[-3]
    assert r.pending == ['gn("Frame", "Depth", 40)']

    r.handle("log deeper make it deeper")
    assert r.pending == []
    code = (m.log_dir / "001-deeper.py").read_text()
    assert (
        'gn("Frame", "Depth", 40)' in code and "from cmdline.commands import *" in code
    )

    r.bridge.ok = False
    r.handle("gn Frame Depth 50")
    assert r.pending == []  # failed input is not kept
    assert "KeyError" in capsys.readouterr().out
