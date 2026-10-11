"""Report the saved scene's frame range and fps.

Usage: blender -b model.blend -P scene_info.py -- [--scene NAME] --result r.json
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import bpy
from _common import parse, write_result

parser = argparse.ArgumentParser()
parser.add_argument("--scene", default="")
opts = parse(parser)
sc = bpy.data.scenes[opts.scene] if opts.scene else bpy.context.scene
write_result(
    opts.result,
    {"frame_start": sc.frame_start, "frame_end": sc.frame_end, "fps": sc.render.fps},
)
