"""
main.py — entry point for the results verification service.

Usage:
    python src/main.py --init      Initialise the database
    python src/main.py --register  Run the gold standard registration tool
    python src/main.py --run       Start the verification service
"""

import argparse
import yaml
from pathlib import Path

from database.db import (
    initialise_database,
    get_connection
)
from registration.registrar import register_gold_standard


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
    # TODO: implement service loop
    print("Starting verification service...")


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
