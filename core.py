"""Core logic: diff two pinned states and find the culprit change(s)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

from .ddmin import ddmin
from .parse import Req


class Outcome(Enum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"  # environment could not be built; treated as "not failing"


@dataclass(frozen=True)
class Change:
    name: str
    old: str | None  # None -> package was added
    new: str | None  # None -> package was removed

    def __str__(self) -> str:
        if self.old is None:
            return f"{self.name} (added {self.new})"
        if self.new is None:
            return f"{self.name} (removed {self.old})"
        return f"{self.name} {self.old} -> {self.new}"


@dataclass
class Result:
    culprits: list[Change]
    trials: int
    errors: int


class BaselineError(Exception):
    pass


def diff(good: dict[str, Req], bad: dict[str, Req]) -> list[Change]:
    changes = []
    for name in sorted(set(good) | set(bad)):
        g, b = good.get(name), bad.get(name)
        if (g and g.version) != (b and b.version):
            changes.append(Change(name, g.version if g else None, b.version if b else None))
    return changes


def apply(good: dict[str, Req], bad: dict[str, Req], subset: list[Change]) -> list[str]:
    """Requirement lines: the good state with only ``subset`` of changes applied."""
    state = dict(good)
    for ch in subset:
        if ch.new is None:
            state.pop(ch.name, None)
        else:
            state[ch.name] = bad[ch.name]
    return [state[name].line for name in sorted(state)]


def find_culprits(
    good: dict[str, Req],
    bad: dict[str, Req],
    trial: Callable[[list[str]], Outcome],
    log: Callable[[str], None] = lambda _msg: None,
) -> Result:
    changes = diff(good, bad)
    if not changes:
        raise BaselineError("The two states are identical: nothing to bisect.")

    cache: dict[frozenset[Change], Outcome] = {}

    def outcome(subset: list[Change]) -> Outcome:
        key = frozenset(subset)
        if key not in cache:
            names = ", ".join(c.name for c in subset) or "(none)"
            log(f"trial {len(cache) + 1}: applying {len(subset)} change(s): {names}")
            cache[key] = trial(apply(good, bad, subset))
            log(f"  -> {cache[key].value}")
        return cache[key]

    if outcome([]) is not Outcome.PASS:
        raise BaselineError("The 'good' state does not pass. Check --good and --test.")
    if outcome(changes) is not Outcome.FAIL:
        raise BaselineError("The 'bad' state does not fail. Check --bad and --test.")

    culprits = ddmin(changes, lambda s: outcome(s) is Outcome.FAIL)
    errors = sum(1 for o in cache.values() if o is Outcome.ERROR)
    return Result(culprits, len(cache), errors)
