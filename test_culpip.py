import unittest

from culpip.core import BaselineError, Outcome, diff, find_culprits
from culpip.ddmin import ddmin
from culpip.parse import load, parse_requirements, parse_uv_lock

GOOD = "a==1.0\nb==1.0\nc==1.0\nd==1.0\ne==1.0\nf==1.0\n"
BAD = "a==2.0\nb==2.0\nc==2.0\nd==2.0\ne==2.0\nf==2.0\n"


def fake_trial(broken_sets):
    """Fails if every (name, version) of any set in ``broken_sets`` is installed."""

    def trial(lines):
        installed = {tuple(l.split("==")) for l in lines}
        bad = any(s <= installed for s in broken_sets)
        return Outcome.FAIL if bad else Outcome.PASS

    return trial


class TestParse(unittest.TestCase):
    def test_basic(self):
        r = parse_requirements("# c\nFoo_Bar[x]==1.2 ; python_version>'3'\n-r other.txt\n")
        self.assertEqual(r["foo-bar"].version, "1.2")
        self.assertIn("python_version", r["foo-bar"].line)

    def test_hashes_dropped(self):
        r = parse_requirements("x==1 \\\n    --hash=sha256:abc\n")
        self.assertEqual(r["x"].line, "x==1")

    def test_unpinned_rejected(self):
        with self.assertRaises(ValueError):
            parse_requirements("x>=1\n")


LOCK_OLD = """
version = 1
requires-python = ">=3.9"

[[package]]
name = "myproj"
version = "0.1.0"
source = { editable = "." }
dependencies = [{ name = "Foo_Bar" }]

[[package]]
name = "foo-bar"
version = "1.0"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "baz"
version = "2.0"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "gitdep"
version = "0.1"
source = { git = "https://example.com/x.git?rev=abc#abc" }
"""
LOCK_NEW = LOCK_OLD.replace('version = "1.0"', 'version = "1.1"')


class TestUvLock(unittest.TestCase):
    def test_parse(self):
        with self.assertWarns(UserWarning):
            r = parse_uv_lock(LOCK_OLD)
        self.assertEqual(sorted(r), ["baz", "foo-bar"])
        self.assertEqual(r["foo-bar"].line, "foo-bar==1.0")

    def test_autodetect_and_diff(self):
        with self.assertWarns(UserWarning):
            good, bad = load(LOCK_OLD, "uv.lock.old"), load(LOCK_NEW, "uv.lock")
        self.assertEqual([str(c) for c in diff(good, bad)], ["foo-bar 1.0 -> 1.1"])

    def test_multiple_versions_rejected(self):
        dup = LOCK_OLD + """
[[package]]
name = "baz"
version = "3.0"
source = { registry = "https://pypi.org/simple" }
"""
        with self.assertRaises(ValueError), self.assertWarns(UserWarning):
            parse_uv_lock(dup)


class TestDdmin(unittest.TestCase):
    def test_single(self):
        self.assertEqual(ddmin(list(range(10)), lambda s: 7 in s), [7])

    def test_pair(self):
        out = ddmin(list(range(10)), lambda s: 2 in s and 8 in s)
        self.assertEqual(sorted(out), [2, 8])


class TestFind(unittest.TestCase):
    def setUp(self):
        self.good = parse_requirements(GOOD)
        self.bad = parse_requirements(BAD)

    def test_single_culprit(self):
        res = find_culprits(self.good, self.bad, fake_trial([{("c", "2.0")}]))
        self.assertEqual([c.name for c in res.culprits], ["c"])

    def test_pair_culprit(self):
        res = find_culprits(
            self.good, self.bad, fake_trial([{("b", "2.0"), ("e", "2.0")}])
        )
        self.assertEqual(sorted(c.name for c in res.culprits), ["b", "e"])

    def test_added_and_removed(self):
        good = parse_requirements("a==1\nold==1\n")
        bad = parse_requirements("a==1\nnew==1\n")
        self.assertEqual(len(diff(good, bad)), 2)
        res = find_culprits(good, bad, fake_trial([{("new", "1")}]))
        self.assertEqual([c.name for c in res.culprits], ["new"])

    def test_baseline_checks(self):
        with self.assertRaises(BaselineError):
            find_culprits(self.good, self.bad, lambda _l: Outcome.PASS)
        with self.assertRaises(BaselineError):
            find_culprits(self.good, self.bad, lambda _l: Outcome.FAIL)

    def test_identical(self):
        with self.assertRaises(BaselineError):
            find_culprits(self.good, self.good, lambda _l: Outcome.PASS)


if __name__ == "__main__":
    unittest.main()
