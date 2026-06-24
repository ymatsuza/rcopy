# rcopy

Cross-platform recursive copy with **gitignore-style excludes** and a `--dry-run`
preview. Fills the gap left by Windows `Copy-Item -Recurse -Exclude` (broken on
subdirectories), `robocopy` (Windows-only, archaic `/XF /XD`), and
`rsync --exclude` (not on Windows / complex). Local-only, dependency: `typer` only.

## Install

```bash
uv sync
uv run rcopy --help
```

## Usage

```bash
# Copy a directory, excluding patterns (gitignore-style, work the same on every OS)
rcopy myproject backup --exclude node_modules --exclude "*.log" --exclude build/

# Preview first — prints "src -> dst" for every planned copy, writes nothing
rcopy myproject backup -e node_modules --dry-run

# Re-include something that an exclude would drop
rcopy src dst -e "*.log" -i important.log

# Read patterns from a file (like .gitignore: one per line, # comments)
rcopy myproject backup --exclude-from .gitignore

# Don't overwrite existing files
rcopy src dst --no-clobber

# Top-level files only (no recursion)
rcopy src dst --no-recurse

# Multiple sources into a directory
rcopy a.txt b.txt out/
```

## Pattern semantics (gitignore-style)

- `*.log` (no slash) — matches that basename at **any depth**.
- `build/` (trailing slash) — matches **directories** only.
- `src/*.tmp` or `/dist` (contains/leads with slash) — **anchored** to the source root.
- `**` crosses directories; `*` and `?` do not cross `/`.
- An excluded directory is **pruned** (its whole subtree is skipped).
- `--include` overrides `--exclude` for matching files (but cannot re-include inside a pruned directory — same limitation as gitignore).

## Exit codes

`0` success (copying nothing because everything was excluded is still success) ·
`1` some files failed to copy (others still copied) · `2` usage error (missing
SRC/DST, source not found, multiple sources with a file destination, unreadable
`--exclude-from`).
