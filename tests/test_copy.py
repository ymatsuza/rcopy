from rcopy.copy import Result, execute
from rcopy.plan import Op


def test_execute_copies_files_and_preserves_content(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("hello")
    dst = tmp_path / "out" / "a.txt"
    res = execute([Op(src=src, dst=dst)])
    assert isinstance(res, Result)
    assert res.copied == 1
    assert dst.read_text() == "hello"


def test_execute_dry_run_writes_nothing(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("hello")
    dst = tmp_path / "out" / "a.txt"
    lines = []
    res = execute([Op(src=src, dst=dst)], dry_run=True, echo=lines.append)
    assert res.copied == 0
    assert not dst.exists()
    assert lines == [f"{src} -> {dst}"]


def test_execute_no_clobber_skips_existing(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("new")
    dst = tmp_path / "a_copy.txt"
    dst.write_text("old")
    res = execute([Op(src=src, dst=dst)], no_clobber=True)
    assert res.skipped == 1
    assert res.copied == 0
    assert dst.read_text() == "old"  # untouched


def test_execute_overwrites_by_default(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("new")
    dst = tmp_path / "a_copy.txt"
    dst.write_text("old")
    res = execute([Op(src=src, dst=dst)])
    assert res.copied == 1
    assert dst.read_text() == "new"


def test_execute_collects_errors_and_continues(tmp_path):
    good = tmp_path / "good.txt"
    good.write_text("g")
    missing = tmp_path / "missing.txt"  # does not exist -> copy fails
    ops = [
        Op(src=missing, dst=tmp_path / "out" / "missing.txt"),
        Op(src=good, dst=tmp_path / "out" / "good.txt"),
    ]
    res = execute(ops)
    assert res.copied == 1
    assert len(res.errors) == 1
    assert res.errors[0][0] == missing
