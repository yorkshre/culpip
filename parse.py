"""Parse pinned requirements files (``name==version``)."""

from __future__ import annotations

import re
from dataclasses import dataclass

_REQ = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?==(?P<version>[^\s;#]+)"
)


@dataclass(frozen=True)
class Req:
    name: str  # normalised (PEP 503 style)
    version: str
    line: str  # the line to pass to the installer


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_requirements(text: str) -> dict[str, Req]:
    """Parse pinned requirements. Options (``--hash`` etc.) are dropped."""
    text = text.replace("\\\r\n", " ").replace("\\\n", " ")
    reqs: dict[str, Req] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "-")):
            continue
        m = _REQ.match(line)
        if not m:
            raise ValueError(
                f"Unsupported line (only pinned 'name==version' is supported): {line!r}"
            )
        # drop trailing options such as --hash=..., keep environment markers
        line = re.split(r"\s+--", line)[0].split(" #")[0].strip()
        name = normalize(m["name"])
        reqs[name] = Req(name, m["version"], line)
    return reqs


def parse_uv_lock(text: str) -> dict[str, Req]:
    """Parse a ``uv.lock``: registry packages only (the project itself is skipped)."""
    try:
        import tomllib  # Python 3.11+
    except ModuleNotFoundError:  # pragma: no cover
        import tomli as tomllib

    data = tomllib.loads(text)
    reqs: dict[str, Req] = {}
    skipped: list[str] = []
    for pkg in data.get("package", []):
        name = normalize(pkg["name"])
        source = pkg.get("source", {})
        if "registry" not in source:
            # the project itself (virtual/editable) or git/path/url dependencies
            if not ({"virtual", "editable"} & source.keys()):
                skipped.append(name)
            continue
        version = pkg.get("version")
        if version is None:
            continue
        if name in reqs:
            raise ValueError(
                f"{name!r} appears with multiple versions (resolution markers); "
                "this is not supported yet."
            )
        reqs[name] = Req(name, version, f"{name}=={version}")
    if skipped:
        import warnings

        warnings.warn(
            "Ignoring non-registry packages (git/path/url): " + ", ".join(sorted(skipped)),
            stacklevel=2,
        )
    return reqs


def load(text: str, filename: str = "") -> dict[str, Req]:
    """Parse a requirements file or a uv.lock, detected by name or content."""
    if filename.endswith(".lock") or "[[package]]" in text:
        return parse_uv_lock(text)
    return parse_requirements(text)
