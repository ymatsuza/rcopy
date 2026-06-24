from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from rcopy import __version__
from rcopy.copy import execute
from rcopy.patterns import Matcher, parse_pattern_file
from rcopy.plan import build_plan

app = typer.Typer(add_completion=False)


def _die(msg: str, code: int = 2) -> None:
    typer.echo(f"rcopy: {msg}", err=True)
    raise typer.Exit(code)


def _version_cb(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.command()
def copy(
    paths: list[str] = typer.Argument(..., help="SRC... DST（最後が宛先）"),
    exclude: Optional[list[str]] = typer.Option(None, "--exclude", "-e", help="除外パターン（繰り返し可）"),
    include: Optional[list[str]] = typer.Option(None, "--include", "-i", help="再包含パターン（繰り返し可）"),
    exclude_from: Optional[list[str]] = typer.Option(None, "--exclude-from", help="パターンファイル（繰り返し可）"),
    dry_run: bool = typer.Option(False, "--dry-run", help="コピーせず src -> dst を列挙"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    no_recurse: bool = typer.Option(False, "--no-recurse", help="トップレベルのみ"),
    no_clobber: bool = typer.Option(False, "--no-clobber", help="既存を上書きしない"),
    version: bool = typer.Option(
        False, "--version", callback=_version_cb, is_eager=True, help="バージョン表示"
    ),
) -> None:
    """rcopy: 除外付きクロスプラットフォーム・コピー（gitignore 風 --exclude ＋ --dry-run）。"""
    if len(paths) < 2:
        _die("need at least SRC and DST")
    *src_args, dst_arg = paths
    sources = [Path(s) for s in src_args]
    dst = Path(dst_arg)

    for s in sources:
        if not s.exists():
            _die(f"source not found: {s}")

    excludes = list(exclude or [])
    for ef in exclude_from or []:
        try:
            excludes.extend(parse_pattern_file(Path(ef).read_text(encoding="utf-8")))
        except OSError as exc:
            _die(f"cannot read --exclude-from {ef}: {exc}")

    matcher = Matcher(excludes, list(include or []))

    if len(sources) > 1:
        if dst.exists() and not dst.is_dir():
            _die(f"destination is not a directory: {dst}")
        dst_is_dir = True
    else:
        dst_is_dir = dst.is_dir()

    ops = build_plan(sources, dst, matcher, recurse=not no_recurse, dst_is_dir=dst_is_dir)
    res = execute(ops, dry_run=dry_run, no_clobber=no_clobber, verbose=verbose, echo=typer.echo)

    for src, msg in res.errors:
        typer.echo(f"rcopy: {src}: {msg}", err=True)
    if not dry_run:
        typer.echo(f"copied {res.copied}, skipped {res.skipped}, errors {len(res.errors)}")
    if res.errors:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
