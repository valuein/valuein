"""Proof kit (examples/proof): pure-logic tests on fixtures recorded from the sample tier."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")

ROOT = Path(__file__).resolve().parent.parent
FIX = Path(__file__).resolve().parent / "fixtures" / "proof"
sys.path.insert(0, str(ROOT / "examples" / "proof"))

import _common
import look_ahead_audit as audit_mod
import survivorship_check as surv
import verify_lineage as lineage


@pytest.fixture(scope="module")
def versions() -> pd.DataFrame:
    """Annual metric versions for MPWR and GE recorded from the sample tier."""
    return pd.read_csv(FIX / "versions_fixture.csv", dtype={"cik": str})


def test_audit_finds_the_known_mpwr_net_income_revision(versions) -> None:
    """MPWR fiscal-2024 net income was first filed higher than its latest value."""
    res = audit_mod.audit(versions)
    row = res[
        (res["cik"] == "0001280452")
        & (res["standard_concept"] == "NetIncome")
        & (res["period_end"].astype(str).str[:10] == "2024-12-31")
    ].iloc[0]
    assert row["changed"]
    assert row["first_value"] == pytest.approx(1.7867e9)
    assert row["latest_value"] == pytest.approx(1.592058e9, rel=1e-6)
    assert row["first_accepted_at"] < row["changed_at"]
    assert row["window_days"] > 0
    assert len(row["first_fact_id"]) == 64 and row["first_fact_id"] != row["latest_fact_id"]


def test_min_change_filters_rounding(versions) -> None:
    """A higher threshold can only shrink the changed set."""
    assert (
        audit_mod.audit(versions, 0.5)["changed"].sum()
        <= audit_mod.audit(versions, 0.001)["changed"].sum()
    )


def test_distribution_sums_to_changed(versions) -> None:
    """Every changed company-period lands in exactly one size bucket."""
    res = audit_mod.audit(versions)
    assert audit_mod.magnitude_distribution(res)["company_periods"].sum() == res["changed"].sum()


def test_point_in_time_hides_later_restatement(versions) -> None:
    """On the day before the changing filing, the PIT view still holds the first value."""
    res = audit_mod.audit(versions)
    row = res[res["changed"]].iloc[0]
    day_before = (row["changed_at"] - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    pit = audit_mod.point_in_time(versions, day_before)
    key = (
        (pit["cik"] == row["cik"])
        & (pit["standard_concept"] == row["standard_concept"])
        & (pit["period_end"].astype(str) == str(row["period_end"]))
    )
    seen = pit[key]["numeric_value"].iloc[0]
    assert seen == pytest.approx(row["first_value"], rel=0.001)
    assert seen != pytest.approx(row["latest_value"], rel=0.001)


def test_biggest_excludes_per_share(versions) -> None:
    """The top list never contains EPS (split-prone) rows."""
    assert "EPSDiluted" not in set(audit_mod.biggest(audit_mod.audit(versions))["standard_concept"])


def test_survivorship_classifies_by_filing_items() -> None:
    """Bankrupt and acquired registrants get the matching 8-K item; ACTIVE ones are not listed."""
    companies = pd.read_csv(FIX / "companies_fixture.csv", dtype=str)
    evidence = pd.read_csv(FIX / "evidence_fixture.csv", dtype={"cik": str, "item": str})
    gone = surv.classify(companies, evidence)
    assert "0000320193" not in set(gone["cik"])
    reasons = dict(zip(gone["cik"], gone["reason"], strict=True))
    assert reasons["0001418091"].startswith("acquisition completed")
    assert all(
        u.startswith("https://www.sec.gov/Archives/edgar/data/") for u in gone["evidence_url"] if u
    )


def test_index_choice_rejected_when_unknown() -> None:
    """Only known index keys reach the SQL."""
    with pytest.raises(ValueError):
        surv.index_view(None, "NOPE", "2021-01-01", "2022-01-01")


def test_sql_list_rejects_injection() -> None:
    """Identifiers with quotes or spaces never reach SQL."""
    with pytest.raises(ValueError):
        _common.sql_list(["AAPL'; DROP"])


def test_fact_ids_read_from_audit_csv(tmp_path: Path, versions) -> None:
    """verify_lineage collects the *_fact_id columns of an audit CSV, de-duplicated."""
    res = audit_mod.audit(versions)
    path = tmp_path / "a.csv"
    res.to_csv(path, index=False)
    ids = lineage.ids_from_csv(path)
    assert ids and all(lineage.FACT_ID.match(i) for i in ids)
    assert len(ids) == len(set(ids))


def test_sec_folder_url_strips_zero_padding() -> None:
    """EDGAR folders use the integer CIK and the dashless accession."""
    assert (
        _common.sec_folder_url("0000320193", "0000320193-24-000123")
        == "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/"
    )


def test_kit_names_index_only_with_notice() -> None:
    """Any proof file that names an index carries the non-affiliation notice, and none sells prices."""
    for path in (ROOT / "examples" / "proof").glob("*"):
        if path.suffix not in {".py", ".md"}:
            continue
        text = path.read_text(encoding="utf-8")
        if "S&P 500" in text or "Russell" in text:
            assert (
                "not affiliated with or endorsed by any index provider" in text
                or "INDEX_NOTICE" in text
            )
        assert "silent" not in text.lower() and "hidden" not in text.lower() or path.suffix == ".py"


def test_as_of_drift_counts_numbers_that_later_changed(versions) -> None:
    """As of a date inside a revision window, at least one visible number differs from today's."""
    res = audit_mod.audit(versions)
    row = res[res["changed"]].iloc[0]
    day = (row["changed_at"] - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    text = audit_mod.as_of_drift(versions, day)
    assert not text.startswith("0 of")
