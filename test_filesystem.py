"""Tests for the in-memory filesystem. Run with: pytest"""

import pytest

from filesystem import (
    AlreadyExistsError,
    Directory,
    DirectoryNotEmptyError,
    File,
    FileSystem,
    InvalidNameError,
    NotADirectoryError,
    NotFoundError,
)


@pytest.fixture
def fs() -> FileSystem:
    return FileSystem()


# Navigation: cd / pwd
def test_starts_at_root(fs: FileSystem) -> None:
    assert fs.pwd() == "/"


def test_cd_into_child_and_pwd(fs: FileSystem) -> None:
    fs.mkdir("school")
    fs.cd("school")
    assert fs.pwd() == "/school"


def test_cd_parent_returns_up_one_level(fs: FileSystem) -> None:
    fs.mkdir("school")
    fs.cd("school")
    fs.mkdir("homework")
    fs.cd("homework")
    assert fs.pwd() == "/school/homework"
    fs.cd("..")
    assert fs.pwd() == "/school"


def test_cd_parent_from_root_is_noop(fs: FileSystem) -> None:
    fs.cd("..")
    assert fs.pwd() == "/"


def test_cd_dot_stays_put(fs: FileSystem) -> None:
    fs.mkdir("school")
    fs.cd("school")
    fs.cd(".")
    assert fs.pwd() == "/school"


def test_cd_missing_directory_raises(fs: FileSystem) -> None:
    with pytest.raises(NotFoundError):
        fs.cd("nope")


def test_cd_into_a_file_raises(fs: FileSystem) -> None:
    fs.touch("notes.txt")
    with pytest.raises(NotADirectoryError):
        fs.cd("notes.txt")


def test_cd_dot_at_root_stays_at_root(fs: FileSystem) -> None:
    fs.cd(".")
    assert fs.pwd() == "/"


def test_pwd_reports_deep_nesting(fs: FileSystem) -> None:
    for name in ("a", "b", "c", "d"):
        fs.mkdir(name)
        fs.cd(name)
    assert fs.pwd() == "/a/b/c/d"


def test_cd_parent_walks_all_the_way_to_root(fs: FileSystem) -> None:
    for name in ("a", "b", "c"):
        fs.mkdir(name)
        fs.cd(name)
    for _ in range(3):
        fs.cd("..")
    assert fs.pwd() == "/"
    fs.cd("..")  # extra is a no-op
    assert fs.pwd() == "/"


def test_directory_contents_survive_navigation(fs: FileSystem) -> None:
    fs.mkdir("docs")
    fs.cd("docs")
    fs.touch("note.txt")
    fs.write("note.txt", "kept")
    fs.cd("..")
    fs.cd("docs")
    assert fs.read("note.txt") == "kept"


# Directories: mkdir / ls / rmdir
def test_mkdir_and_ls(fs: FileSystem) -> None:
    fs.mkdir("math")
    fs.mkdir("history")
    assert fs.ls() == ["history", "math"]


def test_mkdir_duplicate_raises(fs: FileSystem) -> None:
    fs.mkdir("math")
    with pytest.raises(AlreadyExistsError):
        fs.mkdir("math")


def test_rmdir_removes_empty_directory(fs: FileSystem) -> None:
    fs.mkdir("lunch")
    fs.rmdir("lunch")
    assert fs.ls() == []


def test_rmdir_missing_raises(fs: FileSystem) -> None:
    with pytest.raises(NotFoundError):
        fs.rmdir("ghost")


def test_rmdir_nonempty_raises(fs: FileSystem) -> None:
    fs.mkdir("school")
    fs.cd("school")
    fs.mkdir("homework")
    fs.cd("..")
    with pytest.raises(DirectoryNotEmptyError):
        fs.rmdir("school")


def test_rmdir_on_a_file_raises(fs: FileSystem) -> None:
    fs.touch("notes.txt")
    with pytest.raises(NotADirectoryError):
        fs.rmdir("notes.txt")


def test_mkdir_returns_the_directory(fs: FileSystem) -> None:
    created = fs.mkdir("school")
    assert isinstance(created, Directory)
    assert created.name == "school"


def test_ls_on_empty_directory_is_empty(fs: FileSystem) -> None:
    assert fs.ls() == []


def test_rmdir_then_recreate(fs: FileSystem) -> None:
    fs.mkdir("tmp")
    fs.rmdir("tmp")
    fs.mkdir("tmp")
    assert fs.ls() == ["tmp"]


def test_mkdir_then_file_with_same_name_raises(fs: FileSystem) -> None:
    fs.mkdir("data")
    with pytest.raises(AlreadyExistsError):
        fs.touch("data")


def test_sibling_directories_do_not_share_contents(fs: FileSystem) -> None:
    fs.mkdir("a")
    fs.mkdir("b")
    fs.cd("a")
    fs.mkdir("only_in_a")
    fs.cd("..")
    fs.cd("b")
    assert fs.ls() == []


# Files: touch / write / read / mv
def test_touch_creates_empty_file(fs: FileSystem) -> None:
    fs.touch("essay.txt")
    assert fs.read("essay.txt") == ""


def test_touch_duplicate_raises(fs: FileSystem) -> None:
    fs.touch("essay.txt")
    with pytest.raises(AlreadyExistsError):
        fs.touch("essay.txt")


def test_write_then_read(fs: FileSystem) -> None:
    fs.touch("essay.txt")
    fs.write("essay.txt", "hello world")
    assert fs.read("essay.txt") == "hello world"


def test_write_overwrites(fs: FileSystem) -> None:
    fs.touch("essay.txt")
    fs.write("essay.txt", "first")
    fs.write("essay.txt", "second")
    assert fs.read("essay.txt") == "second"


def test_read_missing_raises(fs: FileSystem) -> None:
    with pytest.raises(NotFoundError):
        fs.read("missing.txt")


def test_write_to_directory_raises(fs: FileSystem) -> None:
    fs.mkdir("folder")
    with pytest.raises(NotADirectoryError):
        fs.write("folder", "nope")


def test_mv_renames_file(fs: FileSystem) -> None:
    fs.touch("old.txt")
    fs.write("old.txt", "data")
    fs.mv("old.txt", "new.txt")
    assert fs.ls() == ["new.txt"]
    assert fs.read("new.txt") == "data"


def test_mv_missing_source_raises(fs: FileSystem) -> None:
    with pytest.raises(NotFoundError):
        fs.mv("nope.txt", "new.txt")


def test_mv_onto_existing_name_raises(fs: FileSystem) -> None:
    fs.touch("a.txt")
    fs.touch("b.txt")
    with pytest.raises(AlreadyExistsError):
        fs.mv("a.txt", "b.txt")


def test_touch_returns_the_file(fs: FileSystem) -> None:
    created = fs.touch("essay.txt")
    assert isinstance(created, File)
    assert created.name == "essay.txt"


def test_touch_invalid_name_raises(fs: FileSystem) -> None:
    with pytest.raises(InvalidNameError):
        fs.touch("bad/name")


def test_read_on_a_directory_raises(fs: FileSystem) -> None:
    fs.mkdir("folder")
    with pytest.raises(NotADirectoryError):
        fs.read("folder")


def test_write_accepts_empty_content(fs: FileSystem) -> None:
    fs.touch("f.txt")
    fs.write("f.txt", "data")
    fs.write("f.txt", "")
    assert fs.read("f.txt") == ""


def test_write_preserves_newlines_and_unicode(fs: FileSystem) -> None:
    fs.touch("f.txt")
    content = "line 1\nline 2\n\ttab\némoji 🚀"
    fs.write("f.txt", content)
    assert fs.read("f.txt") == content


def test_file_then_directory_with_same_name_raises(fs: FileSystem) -> None:
    fs.touch("data")
    with pytest.raises(AlreadyExistsError):
        fs.mkdir("data")


def test_mv_on_a_directory_raises(fs: FileSystem) -> None:
    fs.mkdir("folder")
    with pytest.raises(NotADirectoryError):
        fs.mv("folder", "renamed")


def test_mv_onto_a_directory_name_raises(fs: FileSystem) -> None:
    fs.touch("a.txt")
    fs.mkdir("dir")
    with pytest.raises(AlreadyExistsError):
        fs.mv("a.txt", "dir")


def test_mv_invalid_destination_raises(fs: FileSystem) -> None:
    fs.touch("a.txt")
    with pytest.raises(InvalidNameError):
        fs.mv("a.txt", "bad/name")


def test_mv_keeps_the_file_findable_under_the_new_name(fs: FileSystem) -> None:
    fs.touch("old.txt")
    fs.mv("old.txt", "new.txt")
    with pytest.raises(NotFoundError):
        fs.read("old.txt")
    assert fs.read("new.txt") == ""


# Name validation
@pytest.mark.parametrize("bad_name", ["", ".", "..", "a/b"])
def test_invalid_names_rejected(fs: FileSystem, bad_name: str) -> None:
    with pytest.raises(InvalidNameError):
        fs.mkdir(bad_name)


# Search: find (recursive)
def test_find_searches_recursively(fs: FileSystem) -> None:
    fs.mkdir("school")
    fs.cd("school")
    fs.mkdir("homework")
    fs.mkdir("notes")
    fs.cd("homework")
    fs.mkdir("math")
    fs.cd("..")
    fs.cd("notes")
    fs.mkdir("math")
    fs.cd("..")
    assert sorted(fs.find("math")) == [
        "/school/homework/math",
        "/school/notes/math",
    ]


def test_find_no_match_returns_empty(fs: FileSystem) -> None:
    fs.mkdir("school")
    assert fs.find("missing") == []


def test_find_matches_files_and_directories(fs: FileSystem) -> None:
    fs.mkdir("target")
    fs.mkdir("sub")
    fs.cd("sub")
    fs.touch("target")
    fs.cd("..")
    assert sorted(fs.find("target")) == ["/sub/target", "/target"]


def test_find_from_root_searches_the_whole_tree(fs: FileSystem) -> None:
    fs.mkdir("a")
    fs.cd("a")
    fs.mkdir("hit")
    fs.cd("..")
    fs.mkdir("b")
    fs.cd("b")
    fs.mkdir("hit")
    fs.cd("..")  # back at root
    assert sorted(fs.find("hit")) == ["/a/hit", "/b/hit"]


def test_find_excludes_the_current_directory_itself(fs: FileSystem) -> None:
    fs.mkdir("school")
    fs.cd("school")
    # "school" is the cwd, not part of its own subtree
    assert fs.find("school") == []


def test_find_in_empty_directory_returns_empty(fs: FileSystem) -> None:
    assert fs.find("anything") == []


def test_find_returns_an_independent_list(fs: FileSystem) -> None:
    fs.mkdir("x")
    result = fs.find("x")
    result.append("/tampered")
    assert fs.find("x") == ["/x"]


def test_node_repr(fs: FileSystem) -> None:
    directory = fs.mkdir("school")
    file = fs.touch("essay.txt")
    assert repr(directory) == "Directory('school')"
    assert repr(file) == "File('essay.txt')"


# End-to-end: the exact scenario from the assignment prompt
def test_assignment_prompt_walkthrough(fs: FileSystem) -> None:
    fs.mkdir("school")
    fs.cd("school")
    assert fs.pwd() == "/school"

    fs.mkdir("homework")
    fs.cd("homework")

    fs.mkdir("math")
    fs.mkdir("lunch")
    fs.mkdir("history")
    fs.mkdir("spanish")
    fs.rmdir("lunch")

    assert fs.ls() == ["history", "math", "spanish"]
    assert fs.pwd() == "/school/homework"

    fs.cd("..")
    fs.mkdir("cheatsheet")
    assert fs.ls() == ["cheatsheet", "homework"]

    fs.rmdir("cheatsheet")
    fs.cd("..")
    assert fs.pwd() == "/"
