from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from rcopy.plan import Op


@dataclass
class Result:
    copied: int = 0
    skipped: int = 0
    errors: list[tuple[Path, str]] = field(default_factory=list)


def execute(
    ops: list[Op],
    dry_run: bool = False,
    no_clobber: bool = False,
    verbose: bool = False,
    echo=print,
) -> Result:
    res = Result()
    for op in ops:
        if dry_run:
            echo(f"{op.src} -> {op.dst}")
            continue
        if no_clobber and op.dst.exists():
            res.skipped += 1
            if verbose:
                echo(f"skip (exists): {op.dst}")
            continue
        try:
            op.dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(op.src, op.dst)
            res.copied += 1
            if verbose:
                echo(f"{op.src} -> {op.dst}")
        except OSError as exc:
            res.errors.append((op.src, str(exc)))
    return res
