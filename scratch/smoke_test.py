import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
print(f"Path added: {sys.path[0]}")  # add this temporarily

import sqlite3
import json
from src.database.db import get_connection
from src.gate.gate import run_gate
from src.comparator.comparator import compare_experiment

config = {
    "paths": {
        "database": "F:/RegressionTesting/verification.db"
    }
}

# minimal experiment dict — just what gate and comparator need
experiment = {
    "experiment_id": "T087_run3_compressed_1",  # whatever is registered
    "comparisons": [
        {"type": "count_tolerance", "tolerance_percent": 10.0}
    ]
}

result_csv_path = "F:\CountableLabs\metadata\T078_run3_260408_1743\T078_run3\T078_run3_260408_1743_CountableDataSummary.csv"

conn = get_connection(config["paths"]["database"])

# test the gate
passed, status = run_gate(conn, experiment)
print(f"Gate: {status}")

# test the comparator
if passed:
    results = compare_experiment(conn, experiment, result_csv_path)
    for r in results["comparison_results"]:
        print(r)

conn.close()