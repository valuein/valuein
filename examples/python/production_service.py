"""Production pattern: a scheduled job that extracts a point-in-time dataset to Parquet.

What it does: wraps the SDK the way a data pipeline (Airflow, Dagster, cron, a Celery worker)
should: explicit resource limits, one client per run inside a context manager, a fixed
point-in-time cutoff so a re-run reproduces the same data, typed errors mapped to exit codes,
logging instead of prints, and a Parquet output with a small manifest of what was read.
Who it is for: data engineers putting Valuein data into a warehouse or a feature store.
Plan: none. Runs on the free sample tier with no API key; set VALUEIN_API_KEY (from your secret
store, never in code) to extract your plan's data.
SDK methods: ValueinConfig, ValueinClient(as_of=..., config=...), ValueinClient.run_query,
ValueinClient.manifest, exceptions ValueinAuthError / ValueinPlanError / ValueinError.
Tables: references, fact.

Run:
    pip install valuein-sdk pyarrow
    python examples/python/production_service.py --as-of 2026-06-30 --out ./extract
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from valuein_sdk import (
    ValueinAuthError,
    ValueinClient,
    ValueinConfig,
    ValueinError,
    ValueinPlanError,
)

logger = logging.getLogger("valuein_extract")
CONCEPTS = ["TotalRevenue", "NetIncome", "OperatingCashFlow", "TotalAssets"]

EXTRACT_SQL = """
    SELECT f.entity_id AS cik, r.symbol, f.standard_concept, f.period_end, f.fiscal_period,
           f.numeric_value, f.unit, f.accession_id, f.accepted_at, f.fact_id
    FROM fact f
    JOIN (SELECT cik, any_value(symbol) AS symbol FROM "references"
          WHERE is_primary_ticker GROUP BY cik) r ON r.cik = f.entity_id
    WHERE f.standard_concept IN ({concepts}) AND f.fiscal_period = 'FY'
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY f.entity_id, f.standard_concept, f.period_end
        ORDER BY f.accepted_at DESC, f.priority DESC) = 1
"""


def extract(as_of: datetime, out_dir: Path) -> int:
    """Write facts known at `as_of` to Parquet plus a manifest; return a process exit status."""
    # Bound DuckDB so the job cannot exhaust a shared worker; size these to your container.
    config = ValueinConfig(memory_limit="4GB", threads=4)
    try:
        with ValueinClient(as_of=as_of, config=config) as client:
            manifest = client.manifest()
            logger.info(
                "plan=%s snapshot=%s as_of=%s",
                client.plan,
                manifest.get("snapshot"),
                as_of.isoformat(),
            )
            concepts = ", ".join(f"'{c}'" for c in CONCEPTS)
            frame = client.run_query(EXTRACT_SQL.format(concepts=concepts))
            plan = client.plan
    except ValueinAuthError:
        logger.error("authentication failed: check the VALUEIN_API_KEY secret")
        return 3
    except ValueinPlanError as exc:
        logger.error("plan does not include this data: %s", exc)
        return 4
    except ValueinError as exc:  # every other SDK error carries an actionable message
        logger.error("extract failed: %s", exc)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    data_path = out_dir / f"fundamentals_{as_of:%Y%m%d}.parquet"
    frame.to_parquet(data_path, index=False)
    record = {
        "as_of": as_of.isoformat(),
        "plan": plan,
        "snapshot": manifest.get("snapshot"),
        "rows": len(frame),
        "concepts": CONCEPTS,
        "file": data_path.name,
    }
    (out_dir / f"fundamentals_{as_of:%Y%m%d}.json").write_text(json.dumps(record, indent=2))
    logger.info("wrote %s rows to %s", len(frame), data_path)
    return 0


def main() -> int:
    """Parse arguments, configure logging and run one extract."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--as-of",
        default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        help="point-in-time cutoff, YYYY-MM-DD (default: today)",
    )
    parser.add_argument("--out", type=Path, default=Path("extract"), help="output directory")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    # End of the given day in UTC: everything accepted that day is included.
    as_of = datetime.strptime(args.as_of, "%Y-%m-%d").replace(
        hour=23, minute=59, second=59, tzinfo=timezone.utc
    )
    as_of = min(as_of, datetime.now(timezone.utc))  # nothing after "now" can be known yet
    return extract(as_of, args.out)


if __name__ == "__main__":
    sys.exit(main())
