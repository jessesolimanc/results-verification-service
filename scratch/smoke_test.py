import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from src.database.db import get_connection
from src.orchestrator.orchestrator import verify_run

# minimal config pointing to your local paths
config = {
    "paths": {
        "database":         "F:/RegressionTesting/verification.db",
        "manifests_dir":    "F:/RegressionTesting/manifests",
        "results_dir":      "F:/RegressionTesting/results",
        "reports_dir":      "F:/RegressionTesting/reports"
    }
}

# use a fake but valid run_id
run_id = "run_20260514_001"

# load the manifest directly
manifest_path = Path(config["paths"]["manifests_dir"]) / f"context_manifest_{run_id}.json"
with open(manifest_path) as f:
    manifest = json.load(f)

conn = get_connection(config["paths"]["database"])

# Wipe any previous smoke test run so the script is safely re-runnable.
# Delete in FK order: reports → sample_results → experiment_results → runs.
with conn:
    conn.execute("DELETE FROM reports WHERE run_id = ?", (run_id,))
    conn.execute(
        "DELETE FROM sample_results WHERE result_id IN "
        "(SELECT result_id FROM experiment_results WHERE run_id = ?)",
        (run_id,),
    )
    conn.execute("DELETE FROM experiment_results WHERE run_id = ?", (run_id,))
    conn.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))

verify_run(conn, config, run_id, manifest)

conn.close()