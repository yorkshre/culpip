# culpip

Find which dependency update broke your tests.

You upgraded 30 packages and the tests went red. `culpip` bisects the change
between two pinned states (`requirements.txt` or `uv.lock`) and points at the
culprit, including packages that only break *together* (delta debugging).
Each trial runs your tests in a throwaway venv.

## Usage

```
culpip --good requirements.old.txt --bad requirements.txt --test "pytest -x"
```

```
culpip --good uv.lock.old --bad uv.lock --test "pytest -x"
```

Inputs can be fully pinned requirements (`name==version`, e.g. from
`uv pip compile` or `pip freeze`) or `uv.lock` files (detected automatically).
Get the old lockfile with e.g. `git show HEAD~1:uv.lock > uv.lock.old`. Each trial builds a throwaway venv (using `uv` if available,
otherwise `venv` + `pip`) and runs your test command in it.

Add `--editable` if your tests need the project itself installed.

## Status

Alpha (0.0.1). Supported: pinned `requirements.txt` and `uv.lock`
(registry packages only; git/path/url dependencies are ignored with a
warning; lockfiles that pin one package at several versions via resolution
markers are rejected for now).
Planned: `poetry.lock`, `pylock.toml`, git refs, grouping by
direct dependency, finding the first bad version inside one package.
