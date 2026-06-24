from pathlib import Path

from rcopy.patterns import Matcher
from rcopy.plan import Op, build_plan


def _tree(root: Path):
    (root / "src").mkdir(parents=True)
    (root / "src" / "a.py").write_text("a")
    (root / "src" / "b.log").write_text("b")
    (root / "node_modules").mkdir()
    (root / "node_modules" / "junk.js").write_text("j")
    (root / "keep.log").write_text("k")


def _rel(ops, base: Path):
    return sorted(op.src.relative_to(base).as_posix() for op in ops)


def test_plan_copies_all_without_patterns(tmp_path):
    proj = tmp_path / "proj"
    _tree(proj)
    dst = tmp_path / "out"
    ops = build_plan([proj], dst, Matcher([], []), recurse=True, dst_is_dir=False)
    assert _rel(ops, proj) == ["keep.log", "node_modules/junk.js", "src/a.py", "src/b.log"]
    # mirror into dst (dst did not exist)
    a = next(o for o in ops if o.src.name == "a.py")
    assert a.dst == dst / "src" / "a.py"


def test_plan_prunes_excluded_dir_and_files(tmp_path):
    proj = tmp_path / "proj"
    _tree(proj)
    m = Matcher(excludes=["node_modules", "*.log"], includes=[])
    ops = build_plan([proj], tmp_path / "out", m, recurse=True, dst_is_dir=False)
    assert _rel(ops, proj) == ["src/a.py"]  # node_modules pruned, *.log excluded


def test_plan_include_overrides_exclude(tmp_path):
    proj = tmp_path / "proj"
    _tree(proj)
    m = Matcher(excludes=["*.log"], includes=["keep.log"])
    ops = build_plan([proj], tmp_path / "out", m, recurse=True, dst_is_dir=False)
    # only *.log is excluded, so junk.js stays; keep.log survives via include override
    assert _rel(ops, proj) == ["keep.log", "node_modules/junk.js", "src/a.py"]


def test_plan_no_recurse_top_level_only(tmp_path):
    proj = tmp_path / "proj"
    _tree(proj)
    ops = build_plan([proj], tmp_path / "out", Matcher([], []), recurse=False, dst_is_dir=False)
    assert _rel(ops, proj) == ["keep.log"]  # only top-level files


def test_plan_dst_is_dir_places_under_basename(tmp_path):
    proj = tmp_path / "proj"
    _tree(proj)
    dst = tmp_path / "out"
    dst.mkdir()
    ops = build_plan([proj], dst, Matcher([], []), recurse=True, dst_is_dir=True)
    a = next(o for o in ops if o.src.name == "a.py")
    assert a.dst == dst / "proj" / "src" / "a.py"


def test_plan_single_file_source(tmp_path):
    f = tmp_path / "one.txt"
    f.write_text("x")
    # dst not a dir -> dst is the name
    ops = build_plan([f], tmp_path / "copy.txt", Matcher([], []), recurse=True, dst_is_dir=False)
    assert ops == [Op(src=f, dst=tmp_path / "copy.txt")]
    # dst is a dir -> under dir
    d = tmp_path / "dir"
    d.mkdir()
    ops = build_plan([f], d, Matcher([], []), recurse=True, dst_is_dir=True)
    assert ops == [Op(src=f, dst=d / "one.txt")]
