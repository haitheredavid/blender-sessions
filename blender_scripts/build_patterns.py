"""Build every lib/patterns node group into an asset library .blend.

Usage: blender -b --factory-startup -P build_patterns.py -- --save assets/patterns.blend --result r.json

Each GN_<Pattern> group is marked as an asset (catalog-free), so the user can drag it into
any file from the Asset Browser once assets/ is added as an asset library.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

import bpy
import patterns
from _common import parse, write_result

parser = argparse.ArgumentParser()
parser.add_argument("--save", required=True)
opts = parse(parser)

for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
built = []
for pattern in patterns.ALL:
    group = pattern.build(reset=True)
    group.asset_mark()
    group.asset_data.description = (pattern.__doc__ or "").strip().splitlines()[0]
    group.use_fake_user = True
    built.append(group.name)

Path(opts.save).parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(Path(opts.save).resolve()))
write_result(opts.result, {"saved": opts.save, "groups": built})
