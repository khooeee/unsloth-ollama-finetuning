#!/usr/bin/env python3
"""Generate readable YAML train sessions and eval cases (run once while scaffolding)."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SESSIONS = ROOT / "data" / "sessions"
CASES = ROOT / "evals" / "cases"


def dump(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )


def plan_session(sid: str, user: str, steps: list[str]) -> dict:
    body = "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
    return {
        "id": sid,
        "messages": [
            {"role": "user", "content": user},
            {
                "role": "assistant",
                "content": (
                    "Here is a tight inspect → edit → verify plan:\n\n"
                    f"{body}\n\n"
                    "Use run_command for each shell step; re-run tests before declaring done."
                ),
            },
        ],
    }


def tool_session(
    sid: str,
    user: str,
    turns: list[dict],
) -> dict:
    """turns: sequence of assistant/tool/assistant messages already shaped for YAML."""
    return {"id": sid, "messages": [{"role": "user", "content": user}, *turns]}


def tc(command: str, call_id: str = "call_1") -> dict:
    return {
        "role": "assistant",
        "tool_calls": [
            {
                "id": call_id,
                "name": "run_command",
                "arguments": {"command": command},
            }
        ],
    }


def tool_result(content: str, call_id: str = "call_1") -> dict:
    return {
        "role": "tool",
        "tool_call_id": call_id,
        "name": "run_command",
        "content": content,
    }


def main() -> None:
    SESSIONS.mkdir(parents=True, exist_ok=True)
    CASES.mkdir(parents=True, exist_ok=True)
    for p in SESSIONS.glob("*.yaml"):
        p.unlink()
    for p in CASES.glob("*.yaml"):
        p.unlink()

    plans: list[dict] = []

    # --- Plan-only sessions (32) ---
    plans.append(
        plan_session(
            "001-fix-floor-divide",
            "tests/test_ops.py fails because divide(5, 2) returns 2 instead of 2.5. Fix it.",
            [
                "Run pytest -q to reproduce the failure",
                "Open calc/ops.py and find divide",
                "Change a // b to a / b",
                "Re-run pytest -q and confirm green",
            ],
        )
    )
    plans.append(
        plan_session(
            "002-rename-helper",
            "Rename helper `parse_line` to `parse_record` across the package and keep tests green.",
            [
                "rg -n 'parse_line' to list call sites",
                "Rename the function definition",
                "Update imports and call sites",
                "Run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "003-add-cli-flag",
            "Add a --verbose flag to cli.py that prints each processed path. Keep existing tests passing and add one new test.",
            [
                "Read cli.py and its tests",
                "Add argparse --verbose",
                "Print paths when the flag is set",
                "Add a test for --verbose",
                "Run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "004-fix-off-by-one",
            "slice_window(xs, n) drops the last element. Fix the off-by-one and verify with tests.",
            [
                "Run the failing test to see expected vs actual",
                "Inspect slice_window in utils.py",
                "Fix the end index",
                "Re-run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "005-fix-import-error",
            "python -m app crashes with ModuleNotFoundError: config_loader. Fix the import.",
            [
                "Run python -m app to reproduce",
                "Find the bad import with rg",
                "Correct the module path",
                "Re-run python -m app and pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "006-type-error-none",
            "format_user(user) TypeErrors when email is None. Make it safe and test it.",
            [
                "Reproduce with a small python snippet or pytest",
                "Guard None email in format_user",
                "Add/adjust a unit test",
                "Run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "007-json-key-typo",
            "load_settings reads 'timout' instead of 'timeout' from settings.json. Fix and verify.",
            [
                "Inspect load_settings and settings.json",
                "Fix the key name",
                "Run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "008-regex-escape",
            "match_version fails on strings with dots because the regex isn't escaped. Fix it.",
            [
                "Run the failing version tests",
                "Use re.escape on the literal parts",
                "Re-run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "009-missing-return",
            "is_palindrome returns None for odd-length strings. Fix the control flow.",
            [
                "Run pytest -q on test_palindrome.py",
                "Add the missing return True/False paths",
                "Re-run tests",
            ],
        )
    )
    plans.append(
        plan_session(
            "010-mutable-default",
            "append_item uses a mutable default list. Fix the classic bug without breaking callers.",
            [
                "Locate append_item",
                "Replace mutable default with None + create list inside",
                "Run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "011-path-join",
            "open_data uses string concat for paths and breaks on Windows-style joins in tests. Use pathlib.",
            [
                "Find open_data",
                "Switch to pathlib.Path",
                "Run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "012-sort-key",
            "sort_people should sort by age ascending then name. Fix the sort key.",
            [
                "Read the failing test expectations",
                "Update sorted(..., key=...)",
                "Run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "013-encode-utf8",
            "write_report crashes on non-ASCII. Open/write with encoding='utf-8'.",
            [
                "Reproduce the UnicodeEncodeError",
                "Set encoding on open()",
                "Re-run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "014-cache-invalidate",
            "get_user caches forever after updates. Invalidate or key the cache correctly.",
            [
                "Read get_user and update_user",
                "Clear or version the cache on update",
                "Run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "015-float-compare",
            "assert nearly_equal(0.1+0.2, 0.3) fails due to float compare. Use a tolerance.",
            [
                "Inspect nearly_equal",
                "Compare with abs(a-b) < eps",
                "Run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "016-http-status",
            "fetch_ok treats any status < 500 as success. Only 2xx should count.",
            [
                "Read fetch_ok",
                "Check 200 <= status < 300",
                "Run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "017-cli-exit-code",
            "CLI returns 0 even when validation fails. Exit non-zero on errors.",
            [
                "Find main() exit paths",
                "sys.exit(1) on validation failure",
                "Run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "018-dedupe-stable",
            "unique_keep_order drops the first occurrence instead of later dupes. Fix it.",
            [
                "Run the unique() tests",
                "Track seen values correctly",
                "Re-run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "019-dataclass-default",
            "Config dataclass shares a mutable dict default across instances. Fix with field(default_factory=dict).",
            [
                "Open Config definition",
                "Use dataclasses.field(default_factory=dict)",
                "Run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "020-logging-level",
            "debug logs always print. Honor LOG_LEVEL from the environment.",
            [
                "Inspect logging setup",
                "Read LOG_LEVEL and setLevel",
                "Run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "021-csv-header",
            "export_csv forgets the header row. Write headers then rows.",
            [
                "Read export_csv and its test",
                "Write header first",
                "Run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "022-retry-backoff",
            "retry_call sleeps 0 between attempts. Use exponential backoff.",
            [
                "Open retry_call",
                "Sleep 2**attempt (or similar) between tries",
                "Run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "023-gitignore-secret",
            "Tests accidentally import a secrets module committed locally. Move sample secrets to fixtures and update imports.",
            [
                "rg secrets",
                "Point tests at fixtures/sample_secrets.py",
                "Run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "024-async-await",
            "get_json is async but callers forget await, so tests get coroutines. Fix call sites.",
            [
                "Reproduce in pytest",
                "Add await at call sites / mark tests async",
                "Run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "025-boundary-empty",
            "median([]) should raise ValueError, but returns 0. Fix empty-list handling.",
            [
                "Run test_stats.py",
                "Raise on empty input",
                "Re-run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "026-strreplace-bug",
            "rewrite_url replaces only the first 'http' occurrence and breaks 'https'. Fix replacement logic.",
            [
                "Inspect rewrite_url",
                "Replace the scheme safely",
                "Run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "027-enum-typo",
            "Status.CANCELLED is misspelled CANCELLED as CANCELED inconsistently. Unify and fix tests.",
            [
                "rg CANCEL",
                "Pick one spelling and update code+tests",
                "Run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "028-fixture-scope",
            "A module-scoped fixture leaks DB rows between tests. Isolate state.",
            [
                "Read conftest.py fixtures",
                "Reset DB per test or narrow fixture scope",
                "Run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "029-version-compare",
            "version_gte('1.10', '1.2') is False because of string compare. Parse properly.",
            [
                "Run version tests",
                "Compare as tuples of ints",
                "Run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "030-close-file",
            "read_blob leaves files open. Use a context manager.",
            [
                "Open read_blob",
                "Wrap open() in with",
                "Run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "031-param-order",
            "connect(host, port) callers pass port, host. Fix signature or call sites consistently.",
            [
                "rg connect(",
                "Align parameters",
                "Run pytest -q",
            ],
        )
    )
    plans.append(
        plan_session(
            "032-test-isolation-tz",
            "Time-based tests fail outside UTC. Freeze time or set TZ in the test.",
            [
                "Identify flaky time test",
                "Pin timezone or mock datetime",
                "Run pytest -q",
            ],
        )
    )

    # --- Tool-use sessions (16) ---
    tool_sessions: list[dict] = []

    tool_sessions.append(
        tool_session(
            "033-tool-fix-divide",
            "calc/ops.py divide is wrong: divide(5,2) should be 2.5. Use the shell to fix and verify.",
            [
                tc("pytest -q", "c1"),
                tool_result(
                    "FAILED tests/test_ops.py::test_divide - AssertionError: assert 2 == 2.5\n1 failed, 1 passed",
                    "c1",
                ),
                tc("sed -n '1,40p' calc/ops.py", "c2"),
                tool_result(
                    "def add(a, b):\n    return a + b\n\ndef divide(a, b):\n    return a // b\n",
                    "c2",
                ),
                tc(
                    "python - <<'PY'\nfrom pathlib import Path\np=Path('calc/ops.py')\np.write_text(p.read_text().replace('return a // b','return a / b'))\nprint('patched')\nPY",
                    "c3",
                ),
                tool_result("patched", "c3"),
                tc("pytest -q", "c4"),
                tool_result("2 passed", "c4"),
                {
                    "role": "assistant",
                    "content": "Fixed `divide` to use true division (`a / b`). pytest is green (2 passed).",
                },
            ],
        )
    )

    tool_sessions.append(
        tool_session(
            "034-tool-rename-function",
            "Rename `add_numbers` to `add` in mathutil.py and update tests.",
            [
                tc("rg -n 'add_numbers' -g '*.py'", "c1"),
                tool_result(
                    "mathutil.py:3:def add_numbers(a, b):\ntests/test_mathutil.py:4:assert add_numbers(1, 2) == 3",
                    "c1",
                ),
                tc(
                    "python - <<'PY'\nfrom pathlib import Path\nfor rel in ['mathutil.py','tests/test_mathutil.py']:\n p=Path(rel)\n p.write_text(p.read_text().replace('add_numbers','add'))\n print('updated', rel)\nPY",
                    "c2",
                ),
                tool_result("updated mathutil.py\nupdated tests/test_mathutil.py", "c2"),
                tc("pytest -q tests/test_mathutil.py", "c3"),
                tool_result("1 passed", "c3"),
                {
                    "role": "assistant",
                    "content": "Renamed `add_numbers` → `add` in code and tests; tests passed.",
                },
            ],
        )
    )

    tool_sessions.append(
        tool_session(
            "035-tool-off-by-one",
            "utils.first_n(xs, n) returns n-1 items. Fix it with the shell.",
            [
                tc("pytest -q tests/test_utils.py", "c1"),
                tool_result(
                    "FAILED tests/test_utils.py::test_first_n - AssertionError: assert [1,2] == [1,2,3]",
                    "c1",
                ),
                tc("sed -n '1,30p' utils.py", "c2"),
                tool_result("def first_n(xs, n):\n    return xs[: n - 1]\n", "c2"),
                tc(
                    "python - <<'PY'\nfrom pathlib import Path\np=Path('utils.py')\np.write_text(p.read_text().replace('xs[: n - 1]','xs[:n]'))\nprint('ok')\nPY",
                    "c3",
                ),
                tool_result("ok", "c3"),
                tc("pytest -q tests/test_utils.py", "c4"),
                tool_result("1 passed", "c4"),
                {"role": "assistant", "content": "Corrected the slice to `xs[:n]`; test_first_n passes."},
            ],
        )
    )

    tool_sessions.append(
        tool_session(
            "036-tool-missing-import",
            "app.py uses json but forgot to import it. Fix and run a smoke command.",
            [
                tc("python app.py", "c1"),
                tool_result("NameError: name 'json' is not defined", "c1"),
                tc(
                    "python - <<'PY'\nfrom pathlib import Path\np=Path('app.py')\nt=p.read_text()\nif 'import json' not in t:\n t='import json\\n'+t\n p.write_text(t)\nprint('added import')\nPY",
                    "c2",
                ),
                tool_result("added import", "c2"),
                tc("python app.py", "c3"),
                tool_result("ok", "c3"),
                {"role": "assistant", "content": "Added `import json` and confirmed `python app.py` runs."},
            ],
        )
    )

    tool_sessions.append(
        tool_session(
            "037-tool-mutable-default",
            "bag.add uses a mutable default. Fix the classic Python bug.",
            [
                tc("pytest -q tests/test_bag.py", "c1"),
                tool_result(
                    "FAILED tests/test_bag.py::test_isolation - AssertionError: lists leaked across calls",
                    "c1",
                ),
                tc("sed -n '1,40p' bag.py", "c2"),
                tool_result(
                    "def add(item, items=[]):\n    items.append(item)\n    return items\n",
                    "c2",
                ),
                tc(
                    "python - <<'PY'\nfrom pathlib import Path\np=Path('bag.py')\np.write_text('''def add(item, items=None):\n    if items is None:\n        items = []\n    items.append(item)\n    return items\n''')\nprint('rewrote bag.add')\nPY",
                    "c3",
                ),
                tool_result("rewrote bag.add", "c3"),
                tc("pytest -q tests/test_bag.py", "c4"),
                tool_result("1 passed", "c4"),
                {
                    "role": "assistant",
                    "content": "Replaced the mutable default with `items=None` and local list creation; tests pass.",
                },
            ],
        )
    )

    tool_sessions.append(
        tool_session(
            "038-tool-json-key",
            "settings loader looks up 'timout'. Fix the typo.",
            [
                tc("rg -n 'timout|timeout' -g '*.py'", "c1"),
                tool_result("settings.py:12:return data['timout']", "c1"),
                tc(
                    "python - <<'PY'\nfrom pathlib import Path\np=Path('settings.py')\np.write_text(p.read_text().replace(\"data['timout']\",\"data['timeout']\"))\nprint('fixed key')\nPY",
                    "c2",
                ),
                tool_result("fixed key", "c2"),
                tc("pytest -q tests/test_settings.py", "c3"),
                tool_result("2 passed", "c3"),
                {"role": "assistant", "content": "Corrected `timout` → `timeout`; settings tests passed."},
            ],
        )
    )

    tool_sessions.append(
        tool_session(
            "039-tool-palindrome",
            "is_palindrome returns None for 'aba'. Fix control flow via shell.",
            [
                tc("pytest -q tests/test_palindrome.py", "c1"),
                tool_result(
                    "FAILED tests/test_palindrome.py::test_odd - AssertionError: assert None is True",
                    "c1",
                ),
                tc("cat palindrome.py", "c2"),
                tool_result(
                    "def is_palindrome(s):\n    if len(s) <= 1:\n        return True\n    if s[0] == s[-1]:\n        is_palindrome(s[1:-1])\n    else:\n        return False\n",
                    "c2",
                ),
                tc(
                    "python - <<'PY'\nfrom pathlib import Path\nPath('palindrome.py').write_text('''def is_palindrome(s):\n    if len(s) <= 1:\n        return True\n    if s[0] == s[-1]:\n        return is_palindrome(s[1:-1])\n    return False\n''')\nprint('fixed return')\nPY",
                    "c3",
                ),
                tool_result("fixed return", "c3"),
                tc("pytest -q tests/test_palindrome.py", "c4"),
                tool_result("3 passed", "c4"),
                {
                    "role": "assistant",
                    "content": "Added the missing `return` on the recursive call; palindrome tests are green.",
                },
            ],
        )
    )

    tool_sessions.append(
        tool_session(
            "040-tool-csv-header",
            "export_csv omits headers. Patch and verify.",
            [
                tc("pytest -q tests/test_export.py", "c1"),
                tool_result(
                    "FAILED tests/test_export.py::test_header - AssertionError: first row was data, not header",
                    "c1",
                ),
                tc("sed -n '1,50p' export_csv.py", "c2"),
                tool_result(
                    "import csv\n\ndef export_csv(path, rows, headers):\n    with open(path, 'w', newline='') as f:\n        w = csv.writer(f)\n        w.writerows(rows)\n",
                    "c2",
                ),
                tc(
                    "python - <<'PY'\nfrom pathlib import Path\nPath('export_csv.py').write_text('''import csv\n\ndef export_csv(path, rows, headers):\n    with open(path, \"w\", newline=\"\") as f:\n        w = csv.writer(f)\n        w.writerow(headers)\n        w.writerows(rows)\n''')\nprint('added header write')\nPY",
                    "c3",
                ),
                tool_result("added header write", "c3"),
                tc("pytest -q tests/test_export.py", "c4"),
                tool_result("1 passed", "c4"),
                {"role": "assistant", "content": "CSV exporter now writes headers before rows; test passed."},
            ],
        )
    )

    tool_sessions.append(
        tool_session(
            "041-tool-version-compare",
            "version_gte string-compares versions. Fix numeric compare.",
            [
                tc("pytest -q tests/test_version.py", "c1"),
                tool_result(
                    "FAILED tests/test_version.py::test_ten - AssertionError: assert False",
                    "c1",
                ),
                tc("cat version.py", "c2"),
                tool_result(
                    "def version_gte(a, b):\n    return a >= b\n",
                    "c2",
                ),
                tc(
                    "python - <<'PY'\nfrom pathlib import Path\nPath('version.py').write_text('''def _parts(v):\n    return tuple(int(x) for x in v.split(\".\"))\n\ndef version_gte(a, b):\n    return _parts(a) >= _parts(b)\n''')\nprint('numeric compare')\nPY",
                    "c3",
                ),
                tool_result("numeric compare", "c3"),
                tc("pytest -q tests/test_version.py", "c4"),
                tool_result("2 passed", "c4"),
                {
                    "role": "assistant",
                    "content": "Switched version compare to integer tuples; `1.10 >= 1.2` works now.",
                },
            ],
        )
    )

    tool_sessions.append(
        tool_session(
            "042-tool-float-eps",
            "nearly_equal uses == on floats. Use an epsilon.",
            [
                tc("pytest -q tests/test_float.py", "c1"),
                tool_result(
                    "FAILED tests/test_float.py::test_sum - AssertionError",
                    "c1",
                ),
                tc(
                    "python - <<'PY'\nfrom pathlib import Path\nPath('floats.py').write_text('''def nearly_equal(a, b, eps=1e-9):\n    return abs(a - b) < eps\n''')\nprint('rewrote nearly_equal')\nPY",
                    "c2",
                ),
                tool_result("rewrote nearly_equal", "c2"),
                tc("pytest -q tests/test_float.py", "c3"),
                tool_result("1 passed", "c3"),
                {"role": "assistant", "content": "Replaced exact float equality with an epsilon check; tests pass."},
            ],
        )
    )

    tool_sessions.append(
        tool_session(
            "043-tool-cli-exit",
            "CLI exits 0 on validation failure. Make it exit 1.",
            [
                tc("pytest -q tests/test_cli.py", "c1"),
                tool_result(
                    "FAILED tests/test_cli.py::test_bad_args_exit_code - AssertionError: assert 0 == 1",
                    "c1",
                ),
                tc("rg -n 'sys.exit|return' cli.py", "c2"),
                tool_result("cli.py:20:    return 0\ncli.py:24:    return 0", "c2"),
                tc(
                    "python - <<'PY'\nfrom pathlib import Path\np=Path('cli.py')\nt=p.read_text().replace('if not args.path:\\n    return 0','if not args.path:\\n    return 1')\np.write_text(t)\nprint('exit code fixed')\nPY",
                    "c3",
                ),
                tool_result("exit code fixed", "c3"),
                tc("pytest -q tests/test_cli.py", "c4"),
                tool_result("2 passed", "c4"),
                {
                    "role": "assistant",
                    "content": "Validation failure now returns exit code 1; CLI tests passed.",
                },
            ],
        )
    )

    tool_sessions.append(
        tool_session(
            "044-tool-pathlib",
            "open_data builds paths with string concat. Switch to pathlib.",
            [
                tc("pytest -q tests/test_paths.py", "c1"),
                tool_result("FAILED tests/test_paths.py::test_join", "c1"),
                tc("cat paths.py", "c2"),
                tool_result(
                    "def open_data(root, name):\n    return open(root + '/' + name)\n",
                    "c2",
                ),
                tc(
                    "python - <<'PY'\nfrom pathlib import Path\nPath('paths.py').write_text('''from pathlib import Path\n\ndef open_data(root, name):\n    return (Path(root) / name).open()\n''')\nprint('pathlib')\nPY",
                    "c3",
                ),
                tool_result("pathlib", "c3"),
                tc("pytest -q tests/test_paths.py", "c4"),
                tool_result("1 passed", "c4"),
                {"role": "assistant", "content": "Updated path joining to pathlib; path tests passed."},
            ],
        )
    )

    tool_sessions.append(
        tool_session(
            "045-tool-empty-median",
            "median([]) should raise ValueError.",
            [
                tc("pytest -q tests/test_stats.py", "c1"),
                tool_result(
                    "FAILED tests/test_stats.py::test_empty - AssertionError: did not raise",
                    "c1",
                ),
                tc(
                    "python - <<'PY'\nfrom pathlib import Path\nPath('stats.py').write_text('''def median(xs):\n    if not xs:\n        raise ValueError(\"empty\")\n    ys = sorted(xs)\n    mid = len(ys) // 2\n    if len(ys) % 2:\n        return ys[mid]\n    return (ys[mid - 1] + ys[mid]) / 2\n''')\nprint('median fixed')\nPY",
                    "c2",
                ),
                tool_result("median fixed", "c2"),
                tc("pytest -q tests/test_stats.py", "c3"),
                tool_result("3 passed", "c3"),
                {"role": "assistant", "content": "Empty input now raises ValueError; stats tests are green."},
            ],
        )
    )

    tool_sessions.append(
        tool_session(
            "046-tool-utf8",
            "write_report fails on non-ASCII. Force utf-8.",
            [
                tc("pytest -q tests/test_report.py", "c1"),
                tool_result("FAILED tests/test_report.py::test_unicode - UnicodeEncodeError", "c1"),
                tc(
                    "python - <<'PY'\nfrom pathlib import Path\np=Path('report.py')\nt=p.read_text().replace(\"open(path, 'w')\",\"open(path, 'w', encoding='utf-8')\")\np.write_text(t)\nprint('encoding set')\nPY",
                    "c2",
                ),
                tool_result("encoding set", "c2"),
                tc("pytest -q tests/test_report.py", "c3"),
                tool_result("1 passed", "c3"),
                {"role": "assistant", "content": "Opened the report file with encoding='utf-8'; unicode test passed."},
            ],
        )
    )

    tool_sessions.append(
        tool_session(
            "047-tool-dedupe",
            "unique_keep_order keeps the last duplicate. Keep the first instead.",
            [
                tc("pytest -q tests/test_unique.py", "c1"),
                tool_result(
                    "FAILED tests/test_unique.py::test_order - AssertionError: assert [2,1] == [1,2]",
                    "c1",
                ),
                tc(
                    "python - <<'PY'\nfrom pathlib import Path\nPath('unique.py').write_text('''def unique_keep_order(xs):\n    seen = set()\n    out = []\n    for x in xs:\n        if x in seen:\n            continue\n        seen.add(x)\n        out.append(x)\n    return out\n''')\nprint('dedupe fixed')\nPY",
                    "c2",
                ),
                tool_result("dedupe fixed", "c2"),
                tc("pytest -q tests/test_unique.py", "c3"),
                tool_result("1 passed", "c3"),
                {
                    "role": "assistant",
                    "content": "Deduper now keeps first occurrences in order; test passed.",
                },
            ],
        )
    )

    tool_sessions.append(
        tool_session(
            "048-tool-status-2xx",
            "fetch_ok should accept only 2xx statuses.",
            [
                tc("pytest -q tests/test_http.py", "c1"),
                tool_result(
                    "FAILED tests/test_http.py::test_404 - AssertionError: 404 treated as ok",
                    "c1",
                ),
                tc("cat httputil.py", "c2"),
                tool_result(
                    "def fetch_ok(status):\n    return status < 500\n",
                    "c2",
                ),
                tc(
                    "python - <<'PY'\nfrom pathlib import Path\nPath('httputil.py').write_text('''def fetch_ok(status):\n    return 200 <= status < 300\n''')\nprint('2xx only')\nPY",
                    "c3",
                ),
                tool_result("2xx only", "c3"),
                tc("pytest -q tests/test_http.py", "c4"),
                tool_result("3 passed", "c4"),
                {
                    "role": "assistant",
                    "content": "Updated fetch_ok to treat only HTTP 2xx as success; tests passed.",
                },
            ],
        )
    )

    all_sessions = plans + tool_sessions
    assert len(all_sessions) == 48, len(all_sessions)

    for i, sess in enumerate(all_sessions, 1):
        dump(SESSIONS / f"{i:03d}-{sess['id'].split('-', 1)[1]}.yaml", sess)

    # --- Eval cases (12) ---
    evals = [
        {
            "id": "e01-divide-fix",
            "prompt": "In this workspace, divide(5, 2) returns 2 but should return 2.5. Find the bug, fix it, and verify with pytest.",
            "requires_tool": True,
            "rubric": {
                "min_steps_or_commands": 2,
                "must_mention_any": ["pytest", "divide", "ops.py", "//", "/"],
                "require_run_command": True,
                "forbidden_substrings": ["rm -rf /", "curl ", "ssh "],
            },
        },
        {
            "id": "e02-rename-plan",
            "prompt": "Plan how you would rename function `load_cfg` to `load_config` across a Python package and keep tests green. Number your steps.",
            "requires_tool": False,
            "rubric": {
                "min_steps_or_commands": 3,
                "must_mention_any": ["rg", "pytest", "rename", "load_cfg", "load_config"],
                "require_run_command": False,
                "expect_ordered_hints": ["rg", "pytest"],
            },
        },
        {
            "id": "e03-mutable-default",
            "prompt": "A function uses `def add(item, items=[]):`. Explain the bug and the shell commands you'd run to fix and test it.",
            "requires_tool": False,
            "rubric": {
                "min_steps_or_commands": 3,
                "must_mention_any": ["None", "mutable", "pytest", "default"],
                "require_run_command": False,
            },
        },
        {
            "id": "e04-off-by-one-tool",
            "prompt": "first_n(xs, n) returns one too few items. Use run_command to inspect, patch, and re-test.",
            "requires_tool": True,
            "rubric": {
                "min_steps_or_commands": 2,
                "must_mention_any": ["pytest", "first_n", "slice", "[:"],
                "require_run_command": True,
            },
        },
        {
            "id": "e05-import-fix",
            "prompt": "python app.py raises NameError for json. Give an inspect → edit → verify command plan.",
            "requires_tool": False,
            "rubric": {
                "min_steps_or_commands": 3,
                "must_mention_any": ["import json", "app.py", "python"],
                "require_run_command": False,
            },
        },
        {
            "id": "e06-version-compare",
            "prompt": "version_gte('1.10','1.2') is False due to string compare. Fix approach and how you'd verify.",
            "requires_tool": False,
            "rubric": {
                "min_steps_or_commands": 3,
                "must_mention_any": ["split", "int", "pytest", "tuple"],
                "require_run_command": False,
            },
        },
        {
            "id": "e07-csv-header-tool",
            "prompt": "CSV export skips the header row. Use run_command style steps to fix export_csv and run tests.",
            "requires_tool": True,
            "rubric": {
                "min_steps_or_commands": 2,
                "must_mention_any": ["header", "writerow", "pytest"],
                "require_run_command": True,
            },
        },
        {
            "id": "e08-utf8",
            "prompt": "write_report hits UnicodeEncodeError. What commands would you run to fix encoding and verify?",
            "requires_tool": False,
            "rubric": {
                "min_steps_or_commands": 2,
                "must_mention_any": ["utf-8", "encoding", "pytest"],
                "require_run_command": False,
            },
        },
        {
            "id": "e09-palindrome-tool",
            "prompt": "is_palindrome('aba') returns None because a recursive call forgets return. Fix it with run_command.",
            "requires_tool": True,
            "rubric": {
                "min_steps_or_commands": 2,
                "must_mention_any": ["return", "palindrome", "pytest"],
                "require_run_command": True,
            },
        },
        {
            "id": "e10-cli-exit",
            "prompt": "CLI returns 0 when args are invalid. Outline inspect → edit → pytest steps.",
            "requires_tool": False,
            "rubric": {
                "min_steps_or_commands": 3,
                "must_mention_any": ["exit", "1", "pytest"],
                "require_run_command": False,
            },
        },
        {
            "id": "e11-http-2xx",
            "prompt": "fetch_ok treats 404 as success. How do you change the status check and verify?",
            "requires_tool": False,
            "rubric": {
                "min_steps_or_commands": 2,
                "must_mention_any": ["200", "300", "2xx", "pytest", "status"],
                "require_run_command": False,
            },
        },
        {
            "id": "e12-dedupe-tool",
            "prompt": "unique_keep_order keeps the last duplicate instead of the first. Use run_command to fix and test.",
            "requires_tool": True,
            "rubric": {
                "min_steps_or_commands": 2,
                "must_mention_any": ["seen", "pytest", "unique"],
                "require_run_command": True,
            },
        },
    ]

    assert len(evals) == 12
    for i, case in enumerate(evals, 1):
        dump(CASES / f"{i:02d}-{case['id']}.yaml", case)

    print(f"Wrote {len(all_sessions)} sessions and {len(evals)} eval cases")


if __name__ == "__main__":
    main()
