# In-Memory Filesystem

A simplified filesystem that supports files and directories entirely in memory.
Nothing touches disk — the whole tree lives in RAM and is gone when the process
exits. The public surface is the [`FileSystem`](filesystem.py) class, whose
methods mirror familiar shell commands.

## Project structure

```
filesystem.py        # the FileSystem class, Node/File/Directory, and exceptions
test_filesystem.py   # pytest suite: every command, edge cases, prompt walkthrough
README.md            # this file
```

## Requirements

- Python 3.10+ (uses `dict[str, Node]` style type hints)
- `pytest` for the test suite

## Getting it running / tested

```bash
# install the one dev dependency
python -m pip install pytest

# run the test suite
python -m pytest -v
```

There is no CLI — the filesystem is used as a library:

```python
from filesystem import FileSystem

fs = FileSystem()
fs.mkdir("school")
fs.cd("school")
fs.pwd()                 # -> "/school"
fs.touch("essay.txt")
fs.write("essay.txt", "hello world")
fs.read("essay.txt")     # -> "hello world"
fs.find("essay.txt")     # -> ["/school/essay.txt"]
```

## Supported operations

| Command            | Method                  | Notes                                              |
| ------------------ | ----------------------- | -------------------------------------------------- |
| Change directory   | `cd(name)`              | child name, `..` (parent), or `.` (stay)           |
| Print working dir  | `pwd()`                 | absolute path from root, e.g. `/school/homework`   |
| Make directory     | `mkdir(name)`           |                                                    |
| List contents      | `ls()`                  | child names, sorted                                |
| Remove directory   | `rmdir(name)`           | refuses to remove a non-empty directory            |
| Create file        | `touch(name)`           | empty file                                         |
| Write file         | `write(name, content)`  | replaces contents                                  |
| Read file          | `read(name)`            |                                                    |
| Move / rename file | `mv(src, dst)`          | within the current directory (a rename)            |
| Find by name       | `find(name)`            | recursive over the cwd subtree; returns full paths |

All commands operate relative to the current working directory (`cwd`), which
starts at the root `/`.

## Design

The filesystem is a **tree** of `Node` objects:

```
Node (abstract: name, parent)
├── File       (adds: content)
└── Directory  (adds: children)
```

- **`Directory.children` is a `dict` keyed by name.** This is the central
  decision. Every command is fundamentally "find a child by name," so a dict
  gives **O(1)** lookup, insert, and remove, versus **O(n)** for a list that
  must be scanned. Dict keys are also unique, which enforces "no two things with
  the same name in one directory" for free — exactly how real filesystems
  behave. This is what keeps the program fast under moderately high volume.

- **Every node keeps a `parent` pointer.** This makes upward movement cheap:
  `cd ..` is a single pointer hop, and `pwd` is built by walking parent pointers
  from the cwd up to the root, then reversing the collected names.

- **A single `cwd` pointer** tracks the current location so commands can stay
  short and path-free.

- **One "find and validate child" helper layer** (`_get_child`, `_get_file`,
  `_require_absent`) is reused by every command, keeping each command to a few
  lines and removing duplicated lookup/validation logic.

### Error handling

Errors are raised through a small custom exception hierarchy so callers can
catch precisely what they care about:

```
FileSystemError
├── NotFoundError          # no such file or directory
├── AlreadyExistsError     # name already taken in this directory
├── NotADirectoryError     # expected a directory, got a file (or vice versa)
├── DirectoryNotEmptyError # rmdir on a non-empty directory
└── InvalidNameError       # empty name, or contains "/", ".", ".."
```

### Key tradeoffs

- **`rmdir` blocks on a non-empty directory** rather than deleting recursively.
  This mirrors Unix `rmdir` and prevents a single call from silently wiping a
  whole subtree. A recursive `rm -r` is listed below as a future extension.
- **`find` is recursive** over the entire cwd subtree and returns absolute
  paths. It is more useful than a single-level search and demonstrates the tree
  traversal the structure is built for. The cost is **O(n)** in the size of the
  subtree, which is inherent to "find everything named X."
- **`mv` is a same-directory rename.** The prompt scopes moves to the current
  directory, so `mv` removes the old dict key and re-inserts under the new one;
  it refuses to overwrite an existing name.
- **`ls` returns names sorted** for deterministic, predictable output (handy for
  tests and humans). Insertion order would also be reasonable; sorting was the
  more useful default.
- **The name is stored twice** — as the `children` dict key and in the node's
  own `name` field. A deliberate, minor redundancy: the key drives O(1) lookup,
  while the node still knows its own name for path building.

## Future extensions

### 1. Recursive delete (`rm -r`) and a unified path-based API

**Why I picked it:** this is the most obvious real-world gap in the current
design. `rmdir` deliberately refuses non-empty directories, so there is no way
to remove a subtree yet, and every command is currently limited to names in the
cwd rather than full paths like `/school/homework/math`. Closing that gap is the
single change that most moves this toward a usable filesystem.

**Changes:**
- Add a path-resolution helper that walks `/`-separated segments from the root
  (or relative to cwd), handling `.` and `..`, and reuse it across all commands.
- Add `rm(path, recursive=False)`; when `recursive=True`, traverse and detach
  the subtree (Python's garbage collector reclaims the now-unreferenced nodes).
- Generalize `mv` to accept source and destination paths in different
  directories by re-parenting the node (update its `parent` and both directories'
  `children` maps).

### 2. Metadata, permissions, and a thread-safe concurrency layer

**Why I picked it:** I chose this because it is what separates a toy from
something production-ready, which is the bar the assignment sets. Real
filesystems track size, timestamps, and ownership and are hit by many callers at
once; none of that exists yet, and the concurrency angle is the most interesting
design problem of the three.

**Changes:**
- Extend `Node` with `created_at`, `modified_at`, `size`, and an `owner`/`mode`;
  update timestamps on writes and have `ls -l`-style output read from them.
- Add a permission check in the helper layer so reads/writes/deletes can be
  authorized in one place.
- Guard mutating operations with a lock (a single coarse `RLock` to start, or
  per-directory locks for more parallelism) so concurrent callers can't corrupt
  the `children` maps. This becomes important if the filesystem backs a server.

### 3. (Bonus) Symbolic links / hard links

**Why I picked it:** I included this because links are a core filesystem feature
and a genuinely interesting design problem — lazy path resolution and cycle
detection force decisions the current tree never has to make.

**Changes:**
- Add a `SymLink(Node)` type storing a target path string, resolved lazily
  during path resolution (with cycle detection to avoid infinite loops).
- Decide link semantics for `find`, `rm`, and `pwd` (follow vs. report the
  link itself), and document them.

## AI usage

I designed the architecture and made every design decision in this project
myself: modeling the filesystem as a tree, the `Node` / `File` / `Directory`
split, choosing a name-keyed `dict` for a directory's children (O(1) lookups and
unique-name enforcement) over a list, using a `cwd` pointer plus `parent`
pointers to drive `cd`/`pwd`, making `find` recursive, having `rmdir` refuse
non-empty directories, and the custom exception hierarchy.

I used an AI assistant the way I'd normally look things up while working — to get
up to speed on Python tooling and idioms I use less often, for example `pytest`
fixtures and parametrization, `abc.ABC` for the abstract base, and modern
type-hint syntax (`dict[str, Node]`). I read and understand every line in this
repository and can explain and defend each decision.
