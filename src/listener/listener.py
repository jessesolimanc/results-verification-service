"""
listener.py — PostgreSQL NOTIFY/LISTEN listener for the verification service.

Listens on the reports_table_changes channel. When a notification arrives,
calls the on_notification callback with the raw JSON payload string.

Use listen_async_mock() during development (no pipeline DB required).
Use listen_async() in production.
"""

import asyncio
import json

import asyncpg

CHANNEL = "reports_table_changes"
RETRY_DELAY_SECONDS = 5


def parse_experiment_notification(experiment_id_field: str) -> tuple[str, str]:
    """Split {exp_id}_run_{YYYYMMDD}_{NNN}_{timestamp} into (exp_id, run_id)."""
    exp_id, tail = experiment_id_field.split("_run_", 1)
    run_id = "_".join(["run"] + tail.split("_")[:2])
    return exp_id, run_id


async def listen_async_mock(config: dict, on_notification) -> None:
    """Simulate a single NOTIFY event then sleep indefinitely."""
    payload = {
        "schema": "public",
        "op": "insert",
        "experimentId": "T087_run3_compressed_1_run_20260514_001_20260514_1504",
        "name": "mock_report",
        "user": "mock_user",
    }
    await on_notification(json.dumps(payload))
    await asyncio.sleep(float("inf"))


async def listen_async(config: dict, token: asyncio.Event, on_notification) -> None:
    """Listen on reports_table_changes and call on_notification for INSERT events."""
    db_url = config["pipeline"]["database_connection"]

    while not token.is_set():
        try:
            conn = await asyncpg.connect(db_url)
            try:
                async def _handler(conn, pid, channel, payload):
                    try:
                        data = json.loads(payload)
                        if data.get("op") == "insert":
                            await on_notification(payload)
                    except Exception as e:
                        print(f"Notification handler error: {e}")

                await conn.add_listener(CHANNEL, _handler)
                await token.wait()
                await conn.remove_listener(CHANNEL, _handler)
            finally:
                await conn.close()

        except asyncio.CancelledError:
            raise
        except Exception as e:
            if token.is_set():
                break
            print(f"Listener error: {e}. Retrying in {RETRY_DELAY_SECONDS}s...")
            await asyncio.sleep(RETRY_DELAY_SECONDS)
