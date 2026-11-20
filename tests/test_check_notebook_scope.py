"""``scripts/check_notebook_scope.py``: plan tags, restricted data, S&P 500 scope, output hygiene.

Fixtures are small hand-built notebooks written to ``tmp_path``; membership is injected, so no
network and no ``valuein_sdk`` is needed.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import check_notebook_scope as scope
import pytest

ROOT = Path(__file__).resolve().parent.parent
MEMBERS = {"AAPL", "MSFT", "KO", "0000806085", "0000320193"}


def member(identifier: str) -> bool:
    """Fake membership: a fixed set of tickers and CIKs."""
    return identifier in MEMBERS


def code(source: str, outputs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Build a code cell."""
    return {
        "cell_type": "code",
        "execution_count": 1,
        "metadata": {},
        "outputs": outputs or [],
        "source": source.splitlines(keepends=True),
    }


def write(
    tmp_path: Path, cells: list[dict[str, Any]], valuein: Any, name: str = "nb.ipynb"
) -> Path:
    """Write a notebook with the given cells and ``metadata.valuein``."""
    metadata = {} if valuein is None else {"valuein": valuein}
    path = tmp_path / name
    path.write_text(
        json.dumps({"cells": cells, "metadata": metadata, "nbformat": 4, "nbformat_minor": 5}),
        encoding="utf-8",
    )
    return path


def stream(text: str) -> dict[str, Any]:
    """Build a stdout stream output."""
    return {"output_type": "stream", "name": "stdout", "text": [text]}


GOOD = {"plan": "benchmark", "executed_at": "2026-11-20T00:00:00Z"}


def messages(path: Path, secret: str = "") -> list[str]:
    """Return the finding messages for one notebook using the fake membership."""
    return [str(f) for f in scope.check_notebook(path, member, secret)]


def test_clean_benchmark_notebook_passes(tmp_path: Path) -> None:
    """A free-data notebook with member tickers and clean output has no findings."""
    cells = [code('client.resolve("KO")\nfin = client.financials("AAPL")', [stream("ok 1.2\n")])]
    assert messages(write(tmp_path, cells, GOOD)) == []


@pytest.mark.parametrize("bad", [None, {}, {"plan": "pro", "executed_at": "x"}])
def test_missing_or_unknown_plan_fails(tmp_path: Path, bad: Any) -> None:
    """The plan tag is required and must be benchmark or institutional."""
    found = messages(write(tmp_path, [], bad))
    assert any("metadata.valuein.plan" in m for m in found)


def test_missing_executed_at_fails(tmp_path: Path) -> None:
    """A notebook with no execution timestamp fails."""
    found = messages(write(tmp_path, [], {"plan": "benchmark"}))
    assert any("executed_at" in m for m in found)


@pytest.mark.parametrize(
    "snippet",
    [
        'client.insider_transactions("NVDA")',
        'client.run_query("SELECT * FROM institutional_holding")',
        'client.read_table("investment_adviser")',
        'mcp_call("get_smart_money_flow", {})',
        'mcp_call("get_price_history", {})',
        "# 13F-HR positions\nx = 1",
        'client.run_query("select * from Stock_Price_Daily")',
        'q = "Form ADV"',
    ],
)
def test_benchmark_notebook_may_not_touch_restricted_data(tmp_path: Path, snippet: str) -> None:
    """Institutional/Pro-only tables, methods and filing families fail a benchmark notebook."""
    found = messages(write(tmp_path, [code("x = 1"), code(snippet)], GOOD))
    assert any("Institutional/Pro-only" in m and "cell 1" in m for m in found), found


def test_institutional_notebook_may_use_restricted_data(tmp_path: Path) -> None:
    """The restricted-data rule only binds benchmark notebooks."""
    cells = [code('client.insider_transactions("NVDA")')]
    meta = {"plan": "institutional", "executed_at": "2026-11-20T00:00:00Z"}
    assert messages(write(tmp_path, cells, meta)) == []


def test_substring_of_a_longer_name_is_not_restricted(tmp_path: Path) -> None:
    """``advisers`` inside another identifier does not trip the word-boundary match."""
    cells = [code("my_advisers_note = 1\nreinsider_transactions_x = 2")]
    assert messages(write(tmp_path, cells, GOOD)) == []


def test_non_member_ticker_fails_with_cell_index(tmp_path: Path) -> None:
    """A ticker that is not an S&P 500 member names the notebook and the cell."""
    cells = [code("pass"), code('client.resolve("ZZZZ")')]
    found = messages(write(tmp_path, cells, GOOD, "x.ipynb"))
    assert any(m.startswith("x.ipynb cell 1:") and "'ZZZZ'" in m for m in found)


def test_identifier_forms_are_all_collected(tmp_path: Path) -> None:
    """Keyword args, lists, constants, int CIKs and MCP dict keys are all judged."""
    src = (
        'TICKER = "BAD1"\n'
        "client.financials(TICKER)\n"
        'client.read_table("fact", tickers=["AAPL", "BAD2"])\n'
        "client.restatements(cik=320193, limit=5)\n"
        'mcp_call("t", {"ticker": "BAD3", "limit": 1})\n'
        'client.resolve(["MSFT", 99])\n'
    )
    notebook = json.loads(write(tmp_path, [code(src)], GOOD).read_text())
    got = {i for _, i in scope.identifier_literals(notebook)}
    assert got == {"BAD1", "AAPL", "BAD2", "320193", "BAD3", "MSFT", "99"}


def test_cik_literals_are_zero_padded_before_the_lookup(tmp_path: Path) -> None:
    """An int CIK is judged as its 10-digit form."""
    ok = messages(write(tmp_path, [code("client.resolve(320193)")], GOOD))
    bad = messages(write(tmp_path, [code("client.resolve(12345)")], GOOD))
    assert ok == [] and any("'12345'" in m for m in bad)


def test_messy_notebook_reports_every_problem(tmp_path: Path) -> None:
    """Magics, a syntax-broken cell, string-list sources and several faults at once."""
    cells = [
        {"cell_type": "markdown", "metadata": {}, "source": "client.resolve('NOPE')"},
        code('%pip install -q "valuein-sdk"\n!ls /home/runner\nclient.resolve("KO")'),
        code("def broken(:\n    pass"),
        code(
            'client.institutional_holdings(issuer="NVDA")\nclient.resolve("NOPE")',
            [
                stream("saved to /home/runner/work/x.csv\n"),
                {"output_type": "error", "ename": "E", "evalue": "/Users/me/k", "traceback": []},
                {
                    "output_type": "display_data",
                    "metadata": {},
                    "data": {"text/plain": ["VALUEIN_API_KEY=abc"], "image/png": "/mnt/xx"},
                },
            ],
        ),
    ]
    found = messages(write(tmp_path, cells, {"plan": "benchmark"}))
    text = "\n".join(found)
    assert "executed_at" in text
    assert "institutional_holdings" in text
    assert "'NOPE'" in text and text.count("'NOPE'") == 1  # markdown cell is not code
    assert "local path" in text and "API key assignment" in text
    assert "cell 3" in text and "cell 2" not in text  # the syntax error is skipped, not fatal
    assert "/mnt/xx" not in text  # image payloads are not scanned


@pytest.mark.parametrize(
    "leak",
    [
        "see /home/valuein/x",
        "path /mnt/raw_storage",
        "/Users/jane/Desktop",
        "VALUEIN_API_KEY=abcdef",
        "Authorization: Bearer abcdefghijklmnopqrstuvwxyz012345",
        "vi_abcdefghijklmnopqrstuvwx",
    ],
)
def test_output_leaks_fail(tmp_path: Path, leak: str) -> None:
    """Paths, key assignments, bearer tokens and key-shaped strings in outputs fail."""
    found = messages(write(tmp_path, [code("x = 1", [stream(leak)])], GOOD))
    assert any("output contains" in m for m in found), leak


def test_placeholder_bearer_and_prose_are_not_leaks(tmp_path: Path) -> None:
    """The documented placeholder and an env var NAME are fine."""
    out = [stream("Bearer YOUR_VALUEIN_API_KEY\nset VALUEIN_API_KEY to your key\n")]
    assert messages(write(tmp_path, [code("x = 1", out)], GOOD)) == []


def test_the_real_key_value_in_an_output_fails(tmp_path: Path) -> None:
    """Whatever shape the key has, its exact value must not appear in an output."""
    path = write(tmp_path, [code("x = 1", [stream("token is s3cr3tvalue here")])], GOOD)
    assert any("API key value" in m for m in messages(path, secret="s3cr3tvalue"))


def test_scrub_redacts_and_the_result_passes(tmp_path: Path) -> None:
    """After ``scrub_notebook`` the leaks are gone, images and other cells are untouched."""
    out = [
        stream("wrote /home/runner/a.csv and /mnt/x/y\nVALUEIN_API_KEY=zzz\nkey=s3cr3tvalue\n"),
        {"output_type": "display_data", "metadata": {}, "data": {"image/png": "/mnt/raw"}},
    ]
    path = write(tmp_path, [code("x = 1", out), code("print('/mnt/in-source')")], GOOD)
    assert scope.scrub_notebook(path, "s3cr3tvalue") is True
    assert messages(path, "s3cr3tvalue") == []
    notebook = json.loads(path.read_text())
    assert "<path>" in "".join(notebook["cells"][0]["outputs"][0]["text"])
    assert notebook["cells"][0]["outputs"][1]["data"]["image/png"] == "/mnt/raw"
    assert "/mnt/in-source" in "".join(notebook["cells"][1]["source"])
    assert scope.scrub_notebook(path, "s3cr3tvalue") is False


def test_stamp_sets_executed_at_and_keeps_the_plan(tmp_path: Path) -> None:
    """``stamp_notebook`` writes the UTC time and leaves the plan alone."""
    path = write(tmp_path, [], GOOD)
    scope.stamp_notebook(path, datetime(2030, 1, 2, 3, 4, 5, tzinfo=UTC))
    meta = json.loads(path.read_text())["metadata"]["valuein"]
    assert meta == {"plan": "benchmark", "executed_at": "2030-01-02T03:04:05Z"}


def test_unreadable_notebook_is_a_finding_not_a_crash(tmp_path: Path) -> None:
    """Invalid JSON fails cleanly."""
    path = tmp_path / "bad.ipynb"
    path.write_text("{nope", encoding="utf-8")
    assert any("not a readable notebook" in m for m in messages(path))


def test_main_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Exit 1 with a FAIL line on a finding; exit 0 on a clean notebook that needs no lookup."""
    bad = write(tmp_path, [], None, "bad.ipynb")
    good = write(tmp_path, [code("x = 1")], GOOD, "good.ipynb")
    assert scope.main([str(good)]) == 0
    assert scope.main([str(bad)]) == 1
    assert "FAIL bad.ipynb" in capsys.readouterr().out
    assert scope.main(["--stamp", "--scrub", str(good)]) == 0


def test_membership_failure_fails_closed(tmp_path: Path) -> None:
    """If membership cannot be loaded the check fails instead of skipping (c)."""

    def boom(_: str) -> bool:
        """Simulate the sample being unreachable."""
        raise OSError("offline")

    path = write(tmp_path, [code('client.resolve("KO")')], GOOD)
    found = [str(f) for f in scope.check_notebook(path, boom)]
    assert any("cannot load sample membership" in m for m in found)


def test_restricted_tables_cover_every_full_tier_table_in_the_public_schema() -> None:
    """A new full-tier table in ``docs/schema.json`` must be added to ``RESTRICTED_TABLES``."""
    schema = json.loads((ROOT / "docs" / "schema.json").read_text(encoding="utf-8"))
    gated = {
        name
        for name, table in schema["tables"].items()
        if "(full) tier only" in table["description"] or "FULL bucket only" in table["description"]
    }
    assert gated, "schema no longer marks full-tier tables: update this test and the constant"
    assert gated <= set(scope.RESTRICTED_TABLES), gated - set(scope.RESTRICTED_TABLES)
    assert set(scope.RESTRICTED_TABLES) - gated <= {"price_daily", "stock_price_daily"}


def test_restricted_mcp_tools_exist_in_the_published_tool_reference() -> None:
    """Every restricted ``get_*`` name is a real tool in ``docs/MCP_TOOLS.md``."""
    tools = (ROOT / "docs" / "MCP_TOOLS.md").read_text(encoding="utf-8")
    for name in scope.RESTRICTED_METHODS:
        if name.startswith("get_"):
            assert f"`{name}`" in tools, name


def test_committed_playbooks_are_tagged_and_clean() -> None:
    """The six shipped notebooks pass the static checks (membership stubbed)."""
    paths = sorted((ROOT / "examples" / "playbooks").glob("*.ipynb"))
    assert len(paths) == 6
    for path in paths:
        found = [f for f in scope.check_notebook(path, lambda _: True)]
        assert found == [], [str(f) for f in found]
