from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from rcopy.patterns import Matcher


@dataclass
class Op:
    src: Path
    dst: Path


def _walk_dir(root: Path, dest_root: Path, matcher: Matcher, recurse: bool, ops: list[Op]) -> None:
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        dp = Path(dirpath)
        rel_dir = dp.relative_to(root)
        kept = []
        for d in sorted(dirnames):
            rel = (rel_dir / d).as_posix()
            if matcher.is_excluded(rel, is_dir=True) and not matcher.is_included(rel, is_dir=True):
                continue
            kept.append(d)
        dirnames[:] = kept if recurse else []
        for f in sorted(filenames):
            rel = (rel_dir / f).as_posix()
            if matcher.is_excluded(rel, is_dir=False) and not matcher.is_included(rel, is_dir=False):
                continue
            ops.append(Op(src=dp / f, dst=dest_root / rel))


def build_plan(
    sources: list[Path],
    dst: Path,
    matcher: Matcher,
    recurse: bool = True,
    dst_is_dir: bool = False,
) -> list[Op]:
    ops: list[Op] = []
    for src in sources:
        src = Path(src)
        if src.is_file():
            target = (dst / src.name) if dst_is_dir else dst
            ops.append(Op(src=src, dst=target))
        else:
            dest_root = (dst / src.name) if dst_is_dir else dst
            _walk_dir(src, dest_root, matcher, recurse, ops)
    return ops
