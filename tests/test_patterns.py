from rcopy import patterns
from rcopy.patterns import match_pattern


def test_basename_pattern_matches_any_depth():
    # no slash -> matches any path segment (gitignore behavior)
    assert match_pattern("*.log", "a/b/c.log", is_dir=False)
    assert match_pattern("*.log", "c.log", is_dir=False)
    assert match_pattern("node_modules", "x/node_modules", is_dir=True)
    assert not match_pattern("*.log", "a/b/c.txt", is_dir=False)


def test_dir_only_trailing_slash():
    assert match_pattern("build/", "src/build", is_dir=True)
    assert not match_pattern("build/", "src/build", is_dir=False)  # not a dir


def test_anchored_slash_pattern():
    # contains a slash -> anchored to relpath root
    assert match_pattern("src/*.tmp", "src/a.tmp", is_dir=False)
    assert not match_pattern("src/*.tmp", "x/src/a.tmp", is_dir=False)
    # leading slash -> anchored
    assert match_pattern("/dist", "dist", is_dir=True)
    assert not match_pattern("/dist", "a/dist", is_dir=True)


def test_double_star():
    assert match_pattern("**/*.tmp", "a/b/c.tmp", is_dir=False)
    assert match_pattern("**/*.tmp", "c.tmp", is_dir=False)  # zero dirs
    assert match_pattern("a/**/b", "a/x/y/b", is_dir=False)
    assert match_pattern("a/**/b", "a/b", is_dir=False)


def test_question_mark():
    assert match_pattern("file?.txt", "file1.txt", is_dir=False)
    assert not match_pattern("file?.txt", "file12.txt", is_dir=False)


def test_glob_to_regex_anchored():
    import re
    rx = patterns._glob_to_regex("*.log")
    assert re.match(rx, "a.log")
    assert not re.match(rx, "a/b.log")  # * does not cross /


from rcopy.patterns import Matcher, parse_pattern_file


def test_matcher_exclude_and_include_override():
    m = Matcher(excludes=["*.log", "node_modules"], includes=["keep.log"])
    assert m.is_excluded("a/x.log", is_dir=False)
    assert m.is_excluded("node_modules", is_dir=True)
    assert not m.is_excluded("a/x.txt", is_dir=False)
    assert m.is_included("keep.log", is_dir=False)
    assert not m.is_included("x.log", is_dir=False)


def test_matcher_empty_patterns_ignored():
    m = Matcher(excludes=["", "  "], includes=None)
    assert not m.is_excluded("anything", is_dir=False)


def test_parse_pattern_file_skips_comments_and_blanks():
    text = "# comment\n\n*.log\n  build/  \n# another\nnode_modules\n"
    assert parse_pattern_file(text) == ["*.log", "build/", "node_modules"]
