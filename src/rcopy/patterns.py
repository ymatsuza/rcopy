from __future__ import annotations

import re


def _glob_to_regex(glob: str) -> str:
    """Translate a glob (with **, *, ?) into an anchored regex string."""
    out = ["^"]
    i, n = 0, len(glob)
    while i < n:
        c = glob[i]
        if c == "*":
            if glob[i : i + 3] == "**/":
                out.append("(?:.*/)?")  # ** plus slash = zero or more dirs
                i += 3
            elif glob[i : i + 2] == "**":
                out.append(".*")
                i += 2
            else:
                out.append("[^/]*")
                i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    out.append("$")
    return "".join(out)


def match_pattern(pattern: str, relpath: str, is_dir: bool) -> bool:
    relpath = relpath.replace("\\", "/").strip("/")
    p = pattern.strip()
    if not p:
        return False
    if p.endswith("/"):
        if not is_dir:
            return False
        p = p.rstrip("/")
    leading = p.startswith("/")
    if leading:
        p = p[1:]
    anchored = leading or ("/" in p)
    rx = _glob_to_regex(p)
    if anchored:
        # anchored to the relpath root; ** in the pattern still allows any depth
        return re.match(rx, relpath) is not None
    # no slash anywhere: match against any path segment (basename at any depth)
    return any(re.match(rx, seg) is not None for seg in relpath.split("/"))


class Matcher:
    def __init__(self, excludes, includes):
        self.excludes = [p for p in (excludes or []) if p.strip()]
        self.includes = [p for p in (includes or []) if p.strip()]

    def is_excluded(self, relpath: str, is_dir: bool = False) -> bool:
        return any(match_pattern(p, relpath, is_dir) for p in self.excludes)

    def is_included(self, relpath: str, is_dir: bool = False) -> bool:
        return any(match_pattern(p, relpath, is_dir) for p in self.includes)


def parse_pattern_file(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out.append(s)
    return out
