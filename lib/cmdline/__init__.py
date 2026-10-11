"""cmdline: the Blender side of `blend repl` (src/blend/repl.py), a Rhino-style command
prompt in the terminal for the live Blender.

Modules: commands (the command functions, e.g. `gn Frame Depth 0.4`), remote (runs each
REPL input in a namespace that persists between inputs). Both run inside Blender, reached
through the blender-mcp socket.
"""
