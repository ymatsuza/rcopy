from typer.testing import CliRunner

from rcopy.cli import app

runner = CliRunner()


def _text(res):
    parts = [res.output or ""]
    try:
        if res.stderr:
            parts.append(res.stderr)
    except ValueError:
        pass
    return "".join(parts)


def _proj(root):
    (root / "src").mkdir(parents=True)
    (root / "src" / "a.py").write_text("a")
    (root / "src" / "b.log").write_text("b")
    (root / "node_modules").mkdir()
    (root / "node_modules" / "junk.js").write_text("j")


def test_version():
    res = runner.invoke(app, ["--version"])
    assert res.exit_code == 0
    assert res.output.strip()


def test_copy_with_excludes_end_to_end(tmp_path):
    proj = tmp_path / "proj"
    _proj(proj)
    out = tmp_path / "out"
    res = runner.invoke(app, [str(proj), str(out), "-e", "node_modules", "-e", "*.log"])
    assert res.exit_code == 0, _text(res)
    assert (out / "src" / "a.py").exists()
    assert not (out / "src" / "b.log").exists()
    assert not (out / "node_modules").exists()


def test_dry_run_writes_nothing(tmp_path):
    proj = tmp_path / "proj"
    _proj(proj)
    out = tmp_path / "out"
    res = runner.invoke(app, [str(proj), str(out), "--dry-run"])
    assert res.exit_code == 0
    assert not out.exists()
    assert "a.py" in res.output  # planned op printed


def test_exclude_from_file(tmp_path):
    proj = tmp_path / "proj"
    _proj(proj)
    patt = tmp_path / "ignore.txt"
    patt.write_text("# ignore\nnode_modules\n*.log\n")
    out = tmp_path / "out"
    res = runner.invoke(app, [str(proj), str(out), "--exclude-from", str(patt)])
    assert res.exit_code == 0, _text(res)
    assert (out / "src" / "a.py").exists()
    assert not (out / "src" / "b.log").exists()


def test_no_clobber_skips_existing(tmp_path):
    src = tmp_path / "proj"
    src.mkdir()
    (src / "a.txt").write_text("new")
    out = tmp_path / "out"
    out.mkdir()
    (out / "a.txt").write_text("old")
    res = runner.invoke(app, [str(src), str(out), "--no-clobber"])
    assert res.exit_code == 0
    # dst_is_dir=True because out exists -> copies under out/proj, not out/a.txt
    assert (out / "proj" / "a.txt").read_text() == "new"
    assert (out / "a.txt").read_text() == "old"  # untouched


def test_missing_source_exit_2(tmp_path):
    res = runner.invoke(app, [str(tmp_path / "nope"), str(tmp_path / "out")])
    assert res.exit_code == 2
    assert "not found" in _text(res)


def test_too_few_args_exit_2(tmp_path):
    res = runner.invoke(app, [str(tmp_path)])
    assert res.exit_code == 2


def test_multiple_sources_into_dir(tmp_path):
    f1 = tmp_path / "x.txt"
    f1.write_text("1")
    f2 = tmp_path / "y.txt"
    f2.write_text("2")
    out = tmp_path / "out"
    res = runner.invoke(app, [str(f1), str(f2), str(out)])
    assert res.exit_code == 0, _text(res)
    assert (out / "x.txt").read_text() == "1"
    assert (out / "y.txt").read_text() == "2"


def test_multiple_sources_with_file_dst_exit_2(tmp_path):
    f1 = tmp_path / "x.txt"
    f1.write_text("1")
    f2 = tmp_path / "y.txt"
    f2.write_text("2")
    dstfile = tmp_path / "dst.txt"
    dstfile.write_text("z")
    res = runner.invoke(app, [str(f1), str(f2), str(dstfile)])
    assert res.exit_code == 2
