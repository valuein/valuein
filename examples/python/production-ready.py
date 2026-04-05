"""Valuein US Core Fundamentals — Production Service Pattern

This module demonstrates how to integrate the Valuein SDK into a
production environment (e.g., a FastAPI backend, Celery worker, or Airflow DAG).

It abstracts the raw SDK behind a 'Service Gateway', ensuring the database
connection is initialized only once and resources are strictly managed.
"""

import logging
import os
import sys

import pandas as pd
from keyring.core import load_env

from valuein_sdk import ValueinClient, ValueinConfig
from valuein_sdk.exceptions import ValueinAuthError, ValueinPlanError

# 1. Standardize Logging for Observability
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("market_data_service")
load_env()


class MarketDataGateway:
    """
    A unified data gateway that safely wraps the ValueinClient.
    This class handles configuration, logging, and error translation.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize the gateway with hardware-specific constraints."""

        # In production, data pipelines should explicitly constrain memory
        # to prevent out-of-memory (OOM) kills on cloud containers.
        self.config = ValueinConfig(memory_limit="4GB", max_temp_directory_size="20GB", threads=4)

        # Load the heavy tables ONCE during initialization
        self.required_tables = ["entity", "security", "filing", "fact"]
        self.api_key = api_key or os.getenv("VALUEIN_API_KEY")

    def run_pipeline(self, target_ticker: str) -> None:
        """
        The main business logic executor.
        Demonstrates the safe use of the SDK via a context manager.
        """
        logger.info("Initializing Valuein Engine...")

        try:
            # 2. Use the Context Manager for guaranteed teardown
            with ValueinClient(
                api_key=self.api_key, tables=self.required_tables, config=self.config
            ) as client:
                # Step A: Introspection & Health Check
                self._log_system_health(client)

                # Step B: Execute Business Logic (Aggregation)
                top_filers = self._get_top_filers(client, limit=5)
                logger.info(f"Top Filers by Volume:\n{top_filers.to_string(index=False)}")

                # Step C: Execute Template Logic (Time-Series)
                fundamentals = self._get_fundamentals(client, target_ticker)
                if not fundamentals.empty:
                    logger.info(
                        f"Found {len(fundamentals)} fundamental records for {target_ticker}. "
                        f"Latest Revenue: {fundamentals['Revenues'].iloc[0] if 'Revenues' in fundamentals.columns else 'N/A'}"
                    )

        except ValueinAuthError:
            logger.critical("Authentication failed. Check VALUEIN_API_KEY vault/secrets.")
            sys.exit(1)
        except ValueinPlanError as e:
            logger.error(f"Plan permission denied: {e}")
        except Exception as e:
            logger.exception(f"Unexpected pipeline failure: {e}")
            raise

    # ── Internal Class Methods (Hiding the SQL from the Application) ───────

    def _log_system_health(self, client: ValueinClient) -> None:
        manifest = client.manifest()
        me = client.me()
        logger.info(f"Connected to Valuein Gateway | Plan: {me.get('plan')}")
        logger.info(
            f"Using Snapshot: {manifest.get('snapshot')} (Updated: {manifest.get('last_updated')})"
        )

    def _get_top_filers(self, client: ValueinClient, limit: int = 10) -> pd.DataFrame:
        """Example of a complex analytical query joining multiple tables."""
        query = f"""
            SELECT e.name, e.sector, count(f.accession_id) AS filings
            FROM   entity   e
            JOIN   security s ON s.entity_id = e.cik AND s.is_active = TRUE
            JOIN   filing   f ON f.entity_id = e.cik
            GROUP  BY e.name, e.sector
            ORDER  BY filings DESC
            LIMIT  {limit}
        """
        return client.query(query)

    def _get_fundamentals(self, client: ValueinClient, ticker: str) -> pd.DataFrame:
        """Example of safely invoking a bundled SQL template."""
        try:
            return client.run_template(
                "fundamentals_by_ticker",
                ticker=ticker,
                form_types=["10-K", "10-Q"],
                start_date="2020-01-01",
                end_date="2026-12-31",
                metrics=["Revenues", "NetIncomeLoss"],
            )
        except FileNotFoundError as e:
            logger.error(f"Template execution failed: {e}")
            return pd.DataFrame()


if __name__ == "__main__":
    # 3. Application Entry Point
    logger.info("Starting Daily Fundamental Aggregation Job...")

    # The application instantiates the gateway, completely detached from SDK internals
    gateway = MarketDataGateway()

    # Run the pipeline for a specific asset
    gateway.run_pipeline(target_ticker="NVDA")

    logger.info("Job completed successfully.")
