"""
main.py — entry point for the results verification service.

Usage:
    python -m src.main --init      Initialise the database
    python -m src.main --register  Run the gold standard registration tool
    python -m src.main --run       Start the verification service
"""

import argparse
import asyncio
import json
import shutil
import yaml
from pathlib import Path

from src.database.db import get_connection, initialise_database
from src.database.models import get_all_processed_run_ids
from src.listener.listener import listen_async, listen_async_mock
from src.orchestrator.orchestrator import verify_run
from src.orchestrator.watcher import watch_and_confirm
from src.orchestrator.manifest_watcher import watch_manifests_dir
from src.registration.registrar import register_gold_standard

# Manifest read retry: watchdog's on_created/on_moved can fire before a
# writer has finished flushing the file (or mid-rename on some
# filesystems). Retry with backoff rather than giving up on the first
# read — see ADR-022 / Copilot review, ticket for manifest_watcher.py.
MANIFEST_READ_RETRY_DELAYS = (0.1, 0.2, 0.4, 0.8, 1.6)


def load_config() -> dict:
    """Load configuration from local_config.yaml if it exists, else config.yaml."""
    config_dir = Path(__file__).parent.parent / "config"
    local = config_dir / "local_config.yaml"
    default = config_dir / "config.yaml"
    config_path = local if local.exists() else default
    with open(config_path) as f:
        return yaml.safe_load(f)


def init(config: dict) -> None:
    """Initialise the SQLite database from the schema DDL."""
    db_path = config["paths"]["database"]
    schema_path = Path(__file__).parent.parent / "schema" / "verification_schema.sql"
    print("Initialising database...")
    initialise_database(db_path, str(schema_path))
    print("Done.")


def register(config: dict) -> None:
    """Run the interactive gold standard registration tool."""
    print("Starting registration tool...")
    experiment_id = input("Experiment ID: ")

    while True:
        gold_standard_csv_path = input("Gold standard CSV path: ")
        path = Path(gold_standard_csv_path)
        if not path.exists():
            print(f"Error: file not found at {gold_standard_csv_path}")
        elif path.suffix.lower() != ".csv":
            print(f"Error: expected a .csv file, got '{path.suffix}'")
        else:
            break

    registered_by = input("Registered by: ")
    reason = input("Reason: ")

    try:
        with get_connection(config["paths"]["database"]) as conn:
            new_gs_exp_version_id = register_gold_standard(conn, experiment_id,
                                                        gold_standard_csv_path,
                                                        registered_by, reason)
            print("Registered new gold standard version:", new_gs_exp_version_id)
    except Exception as e:
        print(f"Registration failed: {e}")
        return


def run(config: dict) -> None:
    """Start the verification service listener loop."""
    token = asyncio.Event()
    asyncio.run(run_service(config, token))


async def run_service(config: dict, token: asyncio.Event) -> None:
    """
    Async service loop.

    Two watchers run side by side:
      - watch_manifests_dir: the explicit hand-off. A new manifest file
        is the signal that a run's experiments are about to start
        reporting; its experiments are registered as "expected"
        immediately, before any notification for them ever arrives.
      - listen_async / listen_async_mock: the pipeline's Postgres NOTIFY
        stream. Each notification's experiment_id is looked up against
        what's expected — a plain dictionary lookup, replacing the old
        approach of trying to parse a run_id out of the payload itself.

    The manifest watcher's initial catch-up scan must finish before the
    listener starts consuming notifications: otherwise a notification for
    a manifest that's already sitting in manifests_dir at startup can
    arrive (or, for the mock listener, fire immediately) before that
    manifest has been registered, and gets dropped as "no pending
    manifest". manifest_watcher_ready is the barrier for that.
    """
    with get_connection(config["paths"]["database"]) as conn:
        processed_run_ids = get_all_processed_run_ids(conn)

    in_progress = {}                 # {run_id: set of exp_ids notified}
    confirmed_ready = {}             # {run_id: set of exp_ids confirmed on F:}
    manifests = {}                   # {run_id: manifest dict}
    manifest_paths = {}              # {run_id: Path — for archiving once done}
    experiment_names = {}            # {run_id: {experiment_id: pipeline's timestamped name}}
    expected_experiment_to_run = {}  # {experiment_id: run_id} — the explicit contract

    manifests_dir = Path(config["paths"]["manifests_dir"])
    processed_dir = manifests_dir / "processed"
    timed_out_dir = manifests_dir / "timed_out"
    failed_dir = manifests_dir / "failed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    timed_out_dir.mkdir(parents=True, exist_ok=True)
    failed_dir.mkdir(parents=True, exist_ok=True)

    def _archive(run_id: str, destination: Path) -> None:
        """Drop a finished run's in-memory state and move its manifest aside."""
        in_progress.pop(run_id, None)
        confirmed_ready.pop(run_id, None)
        manifest = manifests.pop(run_id, None)
        path = manifest_paths.pop(run_id, None)
        experiment_names.pop(run_id, None)

        if manifest is not None:
            for exp_id in {e["experiment_id"] for e in manifest["experiments"]}:
                if expected_experiment_to_run.get(exp_id) == run_id:
                    expected_experiment_to_run.pop(exp_id, None)

        if path is not None and path.exists():
            try:
                shutil.move(str(path), str(destination / path.name))
                print(f"Run {run_id}: manifest archived to {destination / path.name}")
            except OSError as e:
                print(f"Warning: could not archive manifest {path}: {e}")

    async def handle_new_manifest(path: Path) -> None:
        """Register a manifest's experiments as soon as the file appears.

        Retries the read with backoff: a filesystem event can fire before
        the writer has finished flushing (or mid atomic-rename), so a
        JSONDecodeError or a transient OSError on the first attempt
        doesn't necessarily mean the manifest is bad.
        """
        manifest = None
        last_error = None
        for delay in MANIFEST_READ_RETRY_DELAYS:
            try:
                manifest = json.loads(path.read_text())
                break
            except (json.JSONDecodeError, OSError) as e:
                last_error = e
                await asyncio.sleep(delay)
        else:
            print(f"Warning: could not read manifest {path} after "
                  f"{len(MANIFEST_READ_RETRY_DELAYS)} attempts: {last_error}")
            return

        run_id = manifest["run"]["run_id"]

        if run_id in processed_run_ids or run_id in manifests:
            return  # already verified, or already registered

        expected = {e["experiment_id"] for e in manifest["experiments"]}

        conflicts = expected & expected_experiment_to_run.keys()
        if conflicts:
            conflicting_runs = sorted({expected_experiment_to_run[c] for c in conflicts})
            print(f"Warning: manifest {path.name} (run {run_id}) declares "
                  f"experiment(s) {sorted(conflicts)} already pending under "
                  f"run(s) {conflicting_runs} — skipping registration. This "
                  f"usually means a prior run never finished and its manifest "
                  f"was never archived. Resolve the stuck run (or move its "
                  f"manifest out of {path.parent}) and re-drop this manifest "
                  f"to retry.")
            return

        manifests[run_id] = manifest
        manifest_paths[run_id] = path
        in_progress[run_id] = set()
        confirmed_ready[run_id] = set()
        experiment_names[run_id] = {}
        for exp_id in expected:
            expected_experiment_to_run[exp_id] = run_id

        print(f"Manifest registered: run {run_id} — expecting {len(expected)} experiment(s)")

    async def handle_notification(payload: str) -> None:
        data = json.loads(payload)
        exp_id = data.get("experimentId", "")
        name = data.get("name", "")

        run_id = expected_experiment_to_run.get(exp_id)
        if run_id is None:
            print(f"Warning: notification for experiment '{exp_id}' with no "
                  f"pending manifest — ignoring")
            return

        if run_id in processed_run_ids:
            print(f"Run {run_id} already processed — ignoring")
            return

        expected = {e["experiment_id"] for e in manifests[run_id]["experiments"]}

        in_progress[run_id].add(exp_id)
        experiment_names[run_id][exp_id] = name
        print(f"Run {run_id}: notification received for {exp_id} (name={name!r})")

        asyncio.create_task(_watch_experiment(exp_id, run_id, name, expected, config))

    async def _watch_experiment(exp_id, run_id, name, expected, config):
        """Watch E: for this experiment and trigger verify_run when all ready."""

        async def on_confirmed():
            if run_id not in confirmed_ready:
                return
            confirmed_ready[run_id].add(exp_id)
            print(f"Run {run_id}: {len(confirmed_ready[run_id])}/"
                  f"{len(expected)} experiments confirmed on F:")

            if expected.issubset(confirmed_ready[run_id]):
                print(f"Run {run_id}: all experiments confirmed — "
                      f"starting verification")
                # The manifest is only archived to processed/ once
                # verify_run() succeeds (see except branch below), so this
                # is a true prediction of where it will live — that's what
                # gets recorded in runs.manifest_path.
                manifest_record_path = str(processed_dir / manifest_paths[run_id].name)
                try:
                    await asyncio.to_thread(
                        verify_run, config, run_id, manifests[run_id],
                        experiment_names[run_id], manifest_record_path,
                    )
                except Exception as e:
                    print(f"Error: verification failed for run {run_id}: "
                          f"{e!r} — archiving manifest to {failed_dir} and "
                          f"freeing state so later runs aren't blocked")
                    _archive(run_id, failed_dir)
                else:
                    processed_run_ids.add(run_id)
                    _archive(run_id, processed_dir)

        async def on_timeout():
            if run_id not in confirmed_ready:
                return  # another experiment already triggered cleanup for this run
            print(f"Run {run_id}: experiment {exp_id} timed out — "
                  f"run will not be verified")
            _archive(run_id, timed_out_dir)

        await watch_and_confirm(exp_id, run_id, name, config, on_confirmed, on_timeout)

    manifest_watcher_ready = asyncio.Event()
    manifest_watch_task = asyncio.create_task(
        watch_manifests_dir(config, handle_new_manifest, manifest_watcher_ready)
    )
    await manifest_watcher_ready.wait()

    try:
        if config["listener"]["use_mock"]:
            await listen_async_mock(config, handle_notification)
        else:
            await listen_async(config, token, handle_notification)
    finally:
        manifest_watch_task.cancel()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Results verification service")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--init", action="store_true", help="Initialise the database")
    group.add_argument("--register", action="store_true", help="Register gold standards")
    group.add_argument("--run", action="store_true", help="Start the service")
    args = parser.parse_args()

    config = load_config()

    if args.init:
        init(config)
    elif args.register:
        register(config)
    elif args.run:
        run(config)
