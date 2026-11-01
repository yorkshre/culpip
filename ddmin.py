"""Delta debugging (ddmin): shrink a failing set of changes to a minimal one."""

from __future__ import annotations

from typing import Callable, Sequence, TypeVar

T = TypeVar("T")


def ddmin(items: Sequence[T], fails: Callable[[list[T]], bool]) -> list[T]:
    """Return a 1-minimal subset of ``items`` for which ``fails`` is True.

    Assumes ``fails(list(items))`` is True and ``fails([])`` is False.
    Handles culprits that only fail together (e.g. two packages that are
    each fine alone), unlike a plain binary search.
    """
    items = list(items)
    n = 2
    while len(items) >= 2:
        size = -(-len(items) // n)  # ceil division
        chunks = [items[i : i + size] for i in range(0, len(items), size)]
        reduced = False

        for chunk in chunks:
            if fails(chunk):
                items, n, reduced = chunk, 2, True
                break

        if not reduced:
            for chunk in chunks:
                complement = [x for x in items if x not in chunk]
                if complement and fails(complement):
                    items, n, reduced = complement, max(n - 1, 2), True
                    break

        if not reduced:
            if n >= len(items):
                break
            n = min(len(items), n * 2)
    return items
