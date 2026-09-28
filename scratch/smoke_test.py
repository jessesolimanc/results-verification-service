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

conn.close()

# experiment_names would normally be collected live from NOTIFY payloads
# as they arrive; for a smoke test we don't have real notifications, so
# fall back to each experiment_id itself as a stand-in "name" — fine as
# long as your local results_dir has a folder actually named that way.
experiment_names = {e["experiment_id"]: e["experiment_id"] for e in manifest["experiments"]}

# In the real service this is computed as processed_dir / manifest's
# current filename (see main.py); here we just point it at the manifest's
# current location since this script doesn't archive anything.
manifest_record_path = str(manifest_path)

verify_run(config, run_id, manifest, experiment_names, manifest_record_path)