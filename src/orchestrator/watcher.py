"""
watcher.py — E: drive deletion watch for pipeline completion signal.

Watches E:/CountableLabs/ReportData for deletion of a specific
execution's folder. Deletion signals that the F: drive copy is complete
and it is safe to read result files.

Matches on the pipeline's own timestamped `name` for the execution (the
same string used by orchestrator.find_result_folder() and carried in the
NOTIFY payload's "name" field) rather than experiment_id/run_id. Per
ADR-022 the harness never stamps a run_id anywhere on the pipeline side,
so a run_id-based folder match would almost always find nothing and
silently skip the wait — see ADR-022 for the incident this replaced.

See ADR-019 for the original design reasoning.
"""

import asyncio
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class ReportDataDeletionHandler(FileSystemEventHandler):
    """
    Fires callback when the target execution's folder is deleted from E:.
    Runs in watchdog's OS thread — uses run_coroutine_threadsafe to
    bridge back into the asyncio event loop.
    """

    def __init__(self, name: str,
                 loop: asyncio.AbstractEventLoop, callback):
        self.name = name
        self.loop = loop
        self.callback = callback
        self.fired = False   # prevent multiple triggers

    def on_deleted(self, event):
        if self.fired:
            return
        if event.is_directory:
            folder_name = Path(event.src_path).name
            if folder_name.startswith(self.name):
                self.fired = True
                asyncio.run_coroutine_threadsafe(
                    self.callback(), self.loop
                )


async def wait_for_e_drive_deletion(exp_id: str, run_id: str, name: str,
                                     config: dict) -> bool:
    """
    Wait for the execution's folder to be deleted from E: drive,
    signalling that the F: drive copy is complete.

    `name` is the pipeline's own timestamped identifier for this
    execution (e.g. "JS221N_serial_titration_PSF_260925_1416") — the
    same value orchestrator.find_result_folder() globs on F: with, and
    the same value carried in the NOTIFY payload's "name" field.
    exp_id/run_id are accepted only for logging context.

    Starts the observer first, then checks whether the folder is already
    absent — this eliminates the race window between checking and
    watching if deletion occurred between the DB NOTIFY and this function
    being called. The NOTIFY is the anchor: if the folder is already
    gone once the observer is live, the copy is confirmed complete.

    Returns True if folder was absent when checked after observer startup
    or deletion was detected within the configured timeout. Returns False
    if timeout elapsed.
    """
    watch_dir = config["paths"]["e_drive_report_data"]
    timeout_seconds = config["verification"]["e_drive_deletion_timeout_seconds"]
    label = f"{exp_id}/{run_id} ({name})"

    loop = asyncio.get_running_loop()
    deletion_event = asyncio.Event()

    async def on_deletion():
        deletion_event.set()

    handler = ReportDataDeletionHandler(name, loop, on_deletion)
    observer = Observer()
    observer.schedule(handler, watch_dir, recursive=False)
    observer.start()

    try:
        # Pre-check after the observer is live — eliminates the race window
        # between checking and watching. If the folder is already gone, the
        # copy completed before we started; the NOTIFY is the anchor.
        existing = list(Path(watch_dir).glob(f"{name}*"))
        if not existing:
            print(f"E: folder already absent for {label} — F: copy complete")
            return True

        await asyncio.wait_for(deletion_event.wait(), timeout=timeout_seconds)
        print(f"E: deletion detected for {label} — F: copy complete")
        return True
    except asyncio.TimeoutError:
        print(f"Warning: E: deletion timeout for {label} "
              f"after {timeout_seconds}s — run will not be verified")
        return False
    finally:
        observer.stop()
        await asyncio.to_thread(observer.join)


async def watch_and_confirm(exp_id: str, run_id: str, name: str, config: dict,
                             on_confirmed, on_timeout) -> None:
    """
    Watch E: drive for the execution's folder deletion and dispatch to the
    appropriate callback.

    Calls on_confirmed() if deletion is detected within the configured
    timeout, on_timeout() otherwise.
    """
    if await wait_for_e_drive_deletion(exp_id, run_id, name, config):
        await on_confirmed()
    else:
        await on_timeout()
