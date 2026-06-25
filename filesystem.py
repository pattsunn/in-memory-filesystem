"""In-memory filesystem with files, directories, and a current working directory.

See README.md for design rationale and tradeoffs.
"""

from __future__ import annotations

from abc import ABC


# Errors
class FileSystemError(Exception):
    """Base class for filesystem errors."""


class NotFoundError(FileSystemError):
    """No file or directory with that name."""


class AlreadyExistsError(FileSystemError):
    """A file or directory with that name already exists."""


class NotADirectoryError(FileSystemError):
    """Expected a directory but found a file, or vice versa."""


class DirectoryNotEmptyError(FileSystemError):
    """Cannot remove a directory that still has children."""


class InvalidNameError(FileSystemError):
    """Name is empty or contains a reserved character."""


# Tree nodes
class Node(ABC):
    """A file or directory: a name and a parent (None only for the root)."""

    def __init__(self, name: str, parent: Directory | None) -> None:
        self.name = name
        self.parent = parent

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.name!r})"


class File(Node):
    def __init__(self, name: str, parent: Directory | None, content: str = "") -> None:
        super().__init__(name, parent)
        self.content = content


class Directory(Node):
    def __init__(self, name: str, parent: Directory | None) -> None:
        super().__init__(name, parent)
        self.children: dict[str, Node] = {}


# The filesystem
_RESERVED_NAMES = {"", ".", ".."}  # reserved during navigation; "/" is the separator


class FileSystem:
    """A filesystem rooted at '/' with a current working directory."""

    def __init__(self) -> None:
        self._root = Directory("/", parent=None)
        self._cwd = self._root

    # Internal helpers
    @staticmethod
    def _validate_name(name: str) -> None:
        if name in _RESERVED_NAMES or "/" in name:
            raise InvalidNameError(f"invalid name: {name!r}")

    def _get_child(self, name: str) -> Node:
        try:
            return self._cwd.children[name]
        except KeyError:
            raise NotFoundError(f"no such file or directory: {name!r}") from None

    def _require_absent(self, name: str) -> None:
        if name in self._cwd.children:
            raise AlreadyExistsError(f"already exists: {name!r}")

    def _get_file(self, name: str) -> File:
        node = self._get_child(name)
        if not isinstance(node, File):
            raise NotADirectoryError(f"not a file: {name!r}")
        return node

    @staticmethod
    def _path_of(node: Node) -> str:
        parts: list[str] = []
        current: Node | None = node
        while current is not None and current.parent is not None:
            parts.append(current.name)
            current = current.parent
        return "/" + "/".join(reversed(parts))

    # Navigation
    def cd(self, name: str) -> None:
        """Move into a child directory, or '..' for the parent / '.' to stay."""
        if name == ".":
            return
        if name == "..":
            self._cwd = self._cwd.parent or self._cwd  # no-op at root
            return

        node = self._get_child(name)
        if not isinstance(node, Directory):
            raise NotADirectoryError(f"not a directory: {name!r}")
        self._cwd = node

    def pwd(self) -> str:
        """Absolute path of the current working directory."""
        return self._path_of(self._cwd)

    # Directory operations
    def mkdir(self, name: str) -> Directory:
        """Create an empty directory in the current working directory."""
        self._validate_name(name)
        self._require_absent(name)
        directory = Directory(name, parent=self._cwd)
        self._cwd.children[name] = directory
        return directory

    def ls(self) -> list[str]:
        """Names of the current directory's children, sorted."""
        return sorted(self._cwd.children)

    def rmdir(self, name: str) -> None:
        """Remove an empty child directory; refuse if it has children."""
        node = self._get_child(name)
        if not isinstance(node, Directory):
            raise NotADirectoryError(f"not a directory: {name!r}")
        if node.children:
            raise DirectoryNotEmptyError(f"directory not empty: {name!r}")
        del self._cwd.children[name]

    # File operations
    def touch(self, name: str) -> File:
        """Create an empty file in the current working directory."""
        self._validate_name(name)
        self._require_absent(name)
        file = File(name, parent=self._cwd)
        self._cwd.children[name] = file
        return file

    def write(self, name: str, content: str) -> None:
        """Replace a file's contents."""
        self._get_file(name).content = content

    def read(self, name: str) -> str:
        """Return a file's contents."""
        return self._get_file(name).content

    def mv(self, src: str, dst: str) -> None:
        """Rename a file within the current directory; dst must be free."""
        self._validate_name(dst)
        file = self._get_file(src)
        self._require_absent(dst)
        del self._cwd.children[src]
        file.name = dst
        self._cwd.children[dst] = file

    # Search
    def find(self, name: str) -> list[str]:
        """Absolute paths of every match named 'name' in the cwd subtree, sorted."""
        matches: list[str] = []

        def walk(directory: Directory) -> None:
            for child in directory.children.values():
                if child.name == name:
                    matches.append(self._path_of(child))
                if isinstance(child, Directory):
                    walk(child)

        walk(self._cwd)
        return sorted(matches)
