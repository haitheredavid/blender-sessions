"""`blend` command line."""

import re
import shutil
import subprocess
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from blend import blender, gallery, session
from blend.config import ROOT, get_settings

app = typer.Typer(no_args_is_help=True, help="Blender modeling sessions.")
console = Console()

README = ROOT / "README.md"
TILES = ROOT / "docs" / "gallery"
UNITS = {
    "m": (1.0, "METERS"),
    "cm": (0.01, "CENTIMETERS"),
    "mm": (0.001, "MILLIMETERS"),
}

SessionArg = Annotated[
    str, typer.Argument(help="Session folder name or unique part of it.")
]


def _session(ref: str) -> session.Session:
    try:
        return session.resolve(ref)
    except LookupError as e:
        console.print(f"[red]{escape(str(e))}[/red]")
        raise typer.Exit(1)


def _need_blend(s: session.Session) -> None:
    if not s.blend.exists():
        console.print(f"[red]{s.blend} does not exist[/red]")
        raise typer.Exit(1)


def _run(script: str, **kwargs) -> dict:
    try:
        return blender.run_script(script, **kwargs)
    except blender.BlenderError as e:
        console.print(f"[red]{escape(str(e))}[/red]")
        raise typer.Exit(1)


def _studio() -> Path:
    path = get_settings().studio_blend
    if not path.exists():
        _run("build_studio.py", args=["--save", str(path)], factory_startup=True)
        console.print(f"[dim]studio -> {path.relative_to(ROOT)}[/dim]")
    return path


def _render_args(s: session.Session, framing: str | None, scene: str | None) -> list:
    try:
        opts = s.render_options()
    except ValueError as e:
        console.print(f"[red]{escape(str(e))}[/red]")
        raise typer.Exit(1)
    framing = framing or opts["framing"]
    if framing not in session.FRAMINGS:
        console.print(
            f"[red]--framing must be one of {', '.join(session.FRAMINGS)}[/red]"
        )
        raise typer.Exit(1)
    scene = scene or opts["scene"]
    return [
        "--studio",
        str(_studio()),
        "--framing",
        framing,
        *(["--scene", scene] if scene else []),
    ]


def _update_gallery() -> None:
    sessions = session.list_all()
    for tile in gallery.write_tiles(sessions, TILES):
        console.print(f"[dim]tile -> {tile.relative_to(ROOT)}[/dim]")
    md = gallery.gallery_markdown(sessions, ROOT, TILES)
    try:
        if gallery.update_readme(README, md):
            console.print("[dim]README gallery updated[/dim]")
    except LookupError as e:
        console.print(f"[yellow]{escape(str(e))}[/yellow]")


# --- sessions ---------------------------------------------------------------


@app.command()
def new(
    name: str,
    unit: Annotated[str, typer.Option(help="Length unit: m, cm or mm.")] = "m",
    no_blend: Annotated[bool, typer.Option(help="Skip creating model.blend.")] = False,
) -> None:
    """Create sessions/YYYY-MM-DD-<name>/ from the template."""
    if unit not in UNITS:
        console.print(f"[red]--unit must be one of {', '.join(UNITS)}[/red]")
        raise typer.Exit(1)
    s = session.create(name)
    scale, length_unit = UNITS[unit]
    s.toml.write_text(
        s.toml.read_text()
        .replace("scale_length = 1.0", f"scale_length = {scale}", 1)
        .replace('length_unit = "METERS"', f'length_unit = "{length_unit}"', 1)
    )
    if not no_blend:
        try:
            blender.run_script(
                "setup_scene.py",
                args=[
                    "--save",
                    str(s.blend),
                    "--scale-length",
                    str(scale),
                    "--length-unit",
                    length_unit,
                ],
                factory_startup=True,
            )
        except blender.BlenderError as e:
            console.print(f"[yellow]couldn't create model.blend:[/yellow] {e}")
    console.print(f"[green]created[/green] {s.path}")


@app.command("ls")
def list_sessions() -> None:
    """List sessions and how far along each is."""
    table = Table("session", "status", "exports", "workflows")
    for s in session.list_all():
        table.add_row(
            s.name, s.status(), str(len(s.export_files())), ", ".join(s.workflows)
        )
    console.print(table)


@app.command("open")
def open_cmd(ref: SessionArg) -> None:
    """Open the session's model.blend in the Blender GUI (MCP bridge auto-starts)."""
    s = _session(ref)
    _need_blend(s)
    blender.open_gui(s.blend)
    console.print(f"opened {s.blend}")


@app.command()
def latest() -> None:
    """Print the newest active session's folder name."""
    try:
        print(session.latest().name)
    except LookupError as e:
        console.print(f"[red]{escape(str(e))}[/red]")
        raise typer.Exit(1)


@app.command()
def done(ref: SessionArg) -> None:
    """Mark a session done and refresh the README gallery."""
    s = _session(ref)
    s.set_field("status", "done")
    console.print(f"[green]done[/green] {s.name}")
    _update_gallery()


# --- outputs ----------------------------------------------------------------


def _flag(o: dict) -> list[str]:
    issues = []
    for key, label in (
        ("non_manifold_edges", "non-manifold"),
        ("loose_verts", "loose verts"),
        ("loose_edges", "loose edges"),
        ("degenerate_faces", "degenerate"),
        ("flipped_edges", "flipped normals"),
    ):
        if o[key]:
            issues.append(f"{o[key]} {label}")
    if o["negative_scale"]:
        issues.append("negative scale")
    return issues


@app.command()
def check(
    ref: SessionArg,
    strict: Annotated[
        bool, typer.Option(help="Also fail on non-manifold / unapplied transforms.")
    ] = False,
) -> None:
    """Mesh health of the Model collection: topology, normals, transforms, size."""
    s = _session(ref)
    _need_blend(s)
    res = _run("check_mesh.py", blend=s.blend)
    if not res["objects"]:
        console.print("[yellow]no visible mesh objects in Model[/yellow]")
        raise typer.Exit(1)
    table = Table(
        "object", "size", "faces", "tris", "ngons", "issues", "transforms",
        title=f"{s.name} (unit scale {res['unit_scale']:g})",
    )  # fmt: skip
    failed = False
    for o in res["objects"]:
        issues = _flag(o)
        if not strict:  # open surfaces are often intentional (planes, cloth, shells)
            issues = [i for i in issues if "non-manifold" not in i]
        failed |= bool(issues)
        tf = [
            n for n, k in (("scale", "unapplied_scale"), ("rot", "unapplied_rotation"))
            if o[k]
        ]  # fmt: skip
        failed |= strict and bool(tf)
        table.add_row(
            o["name"],
            " x ".join(f"{v:.3g}" for v in o["size"]),
            str(o["faces"]),
            str(o["tris"]),
            str(o["ngons"]),
            f"[red]{', '.join(_flag(o))}[/red]" if _flag(o) else "-",
            f"[yellow]{', '.join(tf)}[/yellow]" if tf else "-",
        )
    console.print(table)
    if failed:
        raise typer.Exit(1)


@app.command()
def export(
    ref: SessionArg,
    formats: Annotated[
        str | None,
        typer.Option(help="Comma-separated glb,fbx,obj (default: [export] formats)."),
    ] = None,
    split: Annotated[
        bool | None, typer.Option(help="One file per Model object.")
    ] = None,
) -> None:
    """Export the Model collection to exports/."""
    s = _session(ref)
    _need_blend(s)
    try:
        fmts = formats.split(",") if formats else s.export_formats()
    except ValueError as e:
        console.print(f"[red]{escape(str(e))}[/red]")
        raise typer.Exit(1)
    if bad := [f for f in fmts if f not in session.EXPORT_FORMATS]:
        console.print(f"[red]unknown formats: {', '.join(bad)}[/red]")
        raise typer.Exit(1)
    if split is None:
        split = bool(s.config.get("export", {}).get("split", False))
    slug = s.name[11:] if re.match(r"\d{4}-\d{2}-\d{2}-", s.name) else s.name
    args = ["--outdir", str(s.exports), "--name", slug, "--formats", ",".join(fmts)]
    res = _run("export.py", blend=s.blend, args=args + (["--split"] if split else []))
    for path in res["written"]:
        console.print(f"[green]wrote[/green] {Path(path).relative_to(s.path)}")
    if not res["written"]:
        console.print("[yellow]nothing in Model to export[/yellow]")
        raise typer.Exit(1)


@app.command()
def render(
    ref: SessionArg,
    framing: Annotated[
        str | None,
        typer.Option(help="fit or wide (default: [render] framing, else fit)."),
    ] = None,
    scene: Annotated[
        str | None,
        typer.Option(help="Scene to render (default: [render] scene, else saved)."),
    ] = None,
) -> None:
    """Studio render of the Model collection to render.png; refreshes the gallery."""
    s = _session(ref)
    _need_blend(s)
    args = _render_args(s, framing, scene)
    res = _run("render_studio.py", blend=s.blend, args=[*args, "--out", str(s.render)])
    console.print(
        f"[green]rendered[/green] {s.render.relative_to(ROOT)} "
        f"({res['objects']} objects, {res['framing']}, {res['engine']})"
    )
    _update_gallery()


@app.command()
def views(
    ref: SessionArg,
    only: Annotated[
        list[str] | None, typer.Option(help="Render just these view names.")
    ] = None,
) -> None:
    """Render the session's [[views]] studio shots to out/views/<name>.png."""
    s = _session(ref)
    _need_blend(s)
    try:
        shots = s.views()
    except ValueError as e:
        console.print(f"[red]{escape(str(e))}[/red]")
        raise typer.Exit(1)
    if only:
        if missing := set(only) - {v["name"] for v in shots}:
            console.print(f"[red]no such view(s): {', '.join(sorted(missing))}[/red]")
            raise typer.Exit(1)
        shots = [v for v in shots if v["name"] in only]
    if not shots:
        console.print("[yellow]no [[views]] in session.toml[/yellow]")
        raise typer.Exit(1)
    out_dir = s.out / "views"
    for v in shots:
        args = _render_args(s, v["framing"], None)
        args += ["--azimuth", str(v["azimuth"]), "--elevation", str(v["elevation"])]
        args += ["--size", str(v["size"]), "--zoom", str(v["zoom"])]
        args += ["--upright"] if v["upright"] else []
        args += [a for c in v["include"] for a in ("--include", c)]
        args += ["--target", *map(str, v["target"])] if v["target"] else []
        out = out_dir / f"{v['name']}.png"
        _run("render_studio.py", blend=s.blend, args=[*args, "--out", str(out)])
        console.print(f"[green]rendered[/green] {out.relative_to(ROOT)}")


@app.command()
def turntable(
    ref: SessionArg,
    frames: Annotated[int | None, typer.Option(help="Default: [turntable].")] = None,
    fps: Annotated[int | None, typer.Option(help="Default: [turntable].")] = None,
    framing: Annotated[str | None, typer.Option(help="fit or wide.")] = None,
    size: Annotated[int, typer.Option(help="Frame size in px.")] = 720,
) -> None:
    """360° studio turntable -> out/<session>-turntable.mp4 + .gif (needs ffmpeg)."""
    s = _session(ref)
    _need_blend(s)
    ffmpeg = get_settings().ffmpeg_bin
    if not shutil.which(ffmpeg):
        console.print(f"[red]{ffmpeg} not found (brew install ffmpeg)[/red]")
        raise typer.Exit(1)
    opts = s.turntable_options()
    frames, fps = frames or opts["frames"], fps or opts["fps"]
    frames_dir = s.out / "turntable"
    shutil.rmtree(frames_dir, ignore_errors=True)
    args = _render_args(s, framing, None)
    args += ["--out", str(frames_dir), "--frames", str(frames), "--fps", str(fps)]
    _run("render_studio.py", blend=s.blend, args=[*args, "--size", str(size)])
    mp4 = s.out / f"{s.name}-turntable.mp4"
    gif = mp4.with_suffix(".gif")
    pattern = str(frames_dir / "f%04d.png")
    for cmd in (
        [ffmpeg, "-y", "-loglevel", "error", "-framerate", str(fps), "-i", pattern,
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(mp4)],
        [ffmpeg, "-y", "-loglevel", "error", "-i", str(mp4), "-vf",
         "fps=15,scale=480:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse",
         "-loop", "0", str(gif)],
    ):  # fmt: skip
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode:
            console.print(f"[red]ffmpeg failed:[/red] {escape(proc.stderr.strip())}")
            raise typer.Exit(1)
    console.print(
        f"[green]wrote[/green] {mp4.relative_to(ROOT)}, {gif.name} ({frames} frames)"
    )


@app.command("render-scene")
def render_scene(
    overwrite: Annotated[
        bool, typer.Option(help="Replace it, discarding hand edits.")
    ] = False,
) -> None:
    """Build the studio .blend `blend render` uses (cyclorama, lights, camera)."""
    path = get_settings().studio_blend
    if path.exists() and not overwrite:
        console.print(
            f"[yellow]{path.relative_to(ROOT)} exists[/yellow] (--overwrite to rebuild)"
        )
        raise typer.Exit(1)
    _run("build_studio.py", args=["--save", str(path)], factory_startup=True)
    console.print(f"[green]built[/green] {path.relative_to(ROOT)}")


@app.command("gallery")
def gallery_cmd() -> None:
    """Rewrite the gallery tiles and the README grid from every session's render.png."""
    _update_gallery()


# --- workflows --------------------------------------------------------------


@app.command()
def workflows() -> None:
    """List workflows/ docs and the sessions that use each."""
    wdir = get_settings().workflows_dir
    used: dict[str, list[str]] = {}
    for s in session.list_all():
        for w in s.workflows:
            used.setdefault(w, []).append(s.name)
    table = Table("workflow", "summary", "sessions")
    docs = sorted(
        p for p in wdir.glob("*.md") if not p.name.startswith(("_", "README"))
    )
    for doc in docs:
        summary = next(
            (ln.strip() for ln in doc.read_text().splitlines()[1:] if ln.strip()), ""
        )
        table.add_row(doc.stem, summary, ", ".join(used.pop(doc.stem, [])) or "-")
    for missing, names in sorted(used.items()):
        table.add_row(f"[red]{missing}[/red]", "[red]no doc[/red]", ", ".join(names))
    console.print(table)
