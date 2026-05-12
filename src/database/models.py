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
    # TODO: implement
    pass


def insert_gs_sample(conn, record: dict) -> None:
    """Insert a single gold standard sample expected value."""
    # TODO: implement
    pass


def get_active_gs_version(conn, experiment_id: str) -> dict | None:
    """Return the currently active gold standard version for an experiment."""
    # TODO: implement
    pass


def retire_gs_version(conn, gs_exp_version_id: str, superseded_at: str) -> None:
    """Set superseded_at on an existing gold standard version."""
    # TODO: implement
    pass


# ---------------------------------------------------------------
# Run tracking
# ---------------------------------------------------------------

def insert_run(conn, record: dict) -> None:
    """Insert a new run record."""
    # TODO: implement
    pass


def get_unprocessed_runs(conn) -> list[dict]:
    """Return runs that have not yet been picked up by the verification service."""
    # TODO: implement
    pass


# ---------------------------------------------------------------
# Results
# ---------------------------------------------------------------

def insert_experiment_result(conn, record: dict) -> str:
    """Insert an experiment result. Returns result_id."""
    # TODO: implement
    pass


def insert_sample_result(conn, record: dict) -> None:
    """Insert a single sample result."""
    # TODO: implement
    pass


# ---------------------------------------------------------------
# Reports
# ---------------------------------------------------------------

def insert_report(conn, record: dict) -> None:
    """Insert a report record."""
    # TODO: implement
    pass
