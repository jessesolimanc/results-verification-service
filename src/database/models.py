"""
models.py — all database insert and query functions.

No other module writes SQL directly. All database interaction
goes through functions defined here.
"""


# ---------------------------------------------------------------
# Gold standard registration
# ---------------------------------------------------------------

def insert_gs_exp_version(conn, record: dict) -> str:
    """Insert a new gold standard experiment version. Returns gs_exp_version_id."""
    conn.execute(
        """
        INSERT INTO gold_standard_exp_versions
            (gs_exp_version_id, experiment_id, version_number, checksum_hash,
             file_path, registered_at, registered_by, reason, superseded_at)
        VALUES
            (:gs_exp_version_id, :experiment_id, :version_number, :checksum_hash,
             :file_path, :registered_at, :registered_by, :reason, :superseded_at)
        """,
        record,
    )
    return record["gs_exp_version_id"]


def insert_gs_sample(conn, record: dict) -> None:
    """Insert a single gold standard sample expected value."""
    conn.execute(
        """
        INSERT INTO gold_standard_samples
            (gs_sample_id, gs_exp_version_id, sample_id, primary_metric,
             primary_metric_value, full_metrics, notes)
        VALUES
            (:gs_sample_id, :gs_exp_version_id, :sample_id, :primary_metric,
             :primary_metric_value, :full_metrics, :notes)
        """,
        record,
    )


def get_active_gs_version(conn, experiment_id: str) -> dict | None:
    """Return the currently active gold standard version for an experiment."""
    row = conn.execute(
        """
        SELECT * FROM gold_standard_exp_versions
        WHERE experiment_id = ? AND superseded_at IS NULL
        """,
        (experiment_id,),
    ).fetchone()
    return dict(row) if row else None


def retire_gs_version(conn, gs_exp_version_id: str, superseded_at: str) -> None:
    """Set superseded_at on an existing gold standard version."""
    conn.execute(
        """
        UPDATE gold_standard_exp_versions
        SET superseded_at = ?
        WHERE gs_exp_version_id = ?
        """,
        (superseded_at, gs_exp_version_id),
    )


def get_gs_samples(conn, gs_exp_version_id: str) -> list[dict]:
    """Return all samples for a gold standard experiment version."""
    rows = conn.execute(
        """
        SELECT gs_sample_id, sample_id, primary_metric, primary_metric_value, full_metrics
        FROM gold_standard_samples
        WHERE gs_exp_version_id = ?
        """,
        (gs_exp_version_id,),
    ).fetchall()
    return [dict(row) for row in rows]


# ---------------------------------------------------------------
# Run tracking
# ---------------------------------------------------------------

def get_all_processed_run_ids(conn) -> set:
    """Return the set of all run_ids already recorded in the verification DB."""
    rows = conn.execute("SELECT run_id FROM runs").fetchall()
    return {row["run_id"] for row in rows}


def insert_run(conn, record: dict) -> None:
    """Insert a new run record."""
    try:
        conn.execute(
            """
            INSERT INTO runs
                (run_id, triggered_at, pipeline_build, scenario, manifest_path, verdict)
            VALUES
                (:run_id, :triggered_at, :pipeline_build, :scenario, :manifest_path, :verdict)
            """,
            record,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to insert run '{record['run_id']}': {e}") from e


# ---------------------------------------------------------------
# Results
# ---------------------------------------------------------------

def insert_experiment_result(conn, record: dict) -> str:
    """Insert an experiment result. Returns result_id."""
    try:
        conn.execute(
            """
            INSERT INTO experiment_results
                (result_id, run_id, gs_exp_version_id, experiment_id, feature_set,
                 classification, pre_verify_status, verdict, verified_at)
            VALUES
                (:result_id, :run_id, :gs_exp_version_id, :experiment_id, :feature_set,
                 :classification, :pre_verify_status, :verdict, :verified_at)
            """,
            record,
        )
    except Exception as e:
        raise RuntimeError(
            f"Failed to insert experiment result for '{record['experiment_id']}': {e}"
        ) from e
    return record["result_id"]


def insert_sample_result(conn, record: dict) -> None:
    """Insert a single sample result."""
    try:
        conn.execute(
            """
            INSERT INTO sample_results
                (sample_result_id, result_id, gs_sample_id, sample_id, primary_metric,
                 actual_value, expected_value, deviation_percent,
                 full_actual_metrics, full_expected_metrics, verdict)
            VALUES
                (:sample_result_id, :result_id, :gs_sample_id, :sample_id, :primary_metric,
                 :actual_value, :expected_value, :deviation_percent,
                 :full_actual_metrics, :full_expected_metrics, :verdict)
            """,
            record,
        )
    except Exception as e:
        raise RuntimeError(
            f"Failed to insert sample result for '{record['sample_id']}': {e}"
        ) from e


# ---------------------------------------------------------------
# Reports
# ---------------------------------------------------------------

def insert_report(conn, record: dict) -> None:
    """Insert a report record."""
    try:
        conn.execute(
            """
            INSERT INTO reports
                (report_id, run_id, result_id, llm_narrative, overall_verdict, generated_at)
            VALUES
                (:report_id, :run_id, :result_id, :llm_narrative, :overall_verdict, :generated_at)
            """,
            record,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to insert report for run '{record['run_id']}': {e}") from e
