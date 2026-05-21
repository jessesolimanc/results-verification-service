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
import yaml
from pathlib import Path

from src.database.db import get_connection, initialise_database
from src.database.models import get_all_processed_run_ids
from src.listener.listener import listen_async, listen_async_mock, parse_experiment_notification
from src.orchestrator.orchestrator import load_manifest, verify_run
from src.orchestrator.watcher import watch_and_confirm
from src.registration.registrar import register_gold_standard


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
    """Async service loop — listens for notifications and coordinates verification."""
    with get_connection(config["paths"]["database"]) as conn:
        processed_run_ids = get_all_processed_run_ids(conn)
    in_progress = {}       # {run_id: set of exp_ids notified}
    confirmed_ready = {}   # {run_id: set of exp_ids confirmed on F:}
    manifests = {}

    async def handle_notification(payload: str) -> None:
        data = json.loads(payload)
        result = parse_experiment_notification(data.get("experimentId", ""))
        if result is None:
            return
        exp_id, run_id = result

        if run_id in processed_run_ids:
            print(f"Run {run_id} already processed — ignoring")
            return

        if run_id not in in_progress:
            try:
                manifest = load_manifest(run_id, config)
            except FileNotFoundError as e:
                print(f"Warning: {e}")
                return
            manifests[run_id] = manifest
            in_progress[run_id] = set()
            confirmed_ready[run_id] = set()

        expected = {e["experiment_id"] for e in manifests[run_id]["experiments"]}

        if exp_id not in expected:
            print(f"Warning: unexpected experiment '{exp_id}' "
                  f"for run '{run_id}' — ignoring")
            return

        in_progress[run_id].add(exp_id)
        print(f"Run {run_id}: notification received for {exp_id}")

        asyncio.create_task(
            _watch_experiment(exp_id, run_id, expected, config,
                              manifests, confirmed_ready,
                              processed_run_ids, in_progress)
        )

    async def _watch_experiment(exp_id, run_id, expected, config,
                                manifests, confirmed_ready,
                                processed_run_ids, in_progress):
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
                await asyncio.to_thread(
                    verify_run, config, run_id, manifests[run_id]
                )
                processed_run_ids.add(run_id)
                in_progress.pop(run_id, None)
                confirmed_ready.pop(run_id, None)
                manifests.pop(run_id, None)

        async def on_timeout():
            print(f"Run {run_id}: experiment {exp_id} timed out — "
                  f"run will not be verified")

        await watch_and_confirm(exp_id, run_id, config, on_confirmed, on_timeout)

    if config["listener"]["use_mock"]:
        await listen_async_mock(config, handle_notification)
    else:
        await listen_async(config, token, handle_notification)


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
