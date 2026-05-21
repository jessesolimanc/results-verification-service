"""
watcher.py — E: drive deletion watch for pipeline completion signal.

Watches E:/CountableLabs/ReportData for deletion of a specific
experiment folder. Deletion signals that the F: drive copy is complete
and it is safe to read result files.

See ADR-019 for design reasoning.
"""

import asyncio
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class ReportDataDeletionHandler(FileSystemEventHandler):
    """
    Fires callback when the target experiment folder is deleted from E:.
    Runs in watchdog's OS thread — uses run_coroutine_threadsafe to
    bridge back into the asyncio event loop.
    """

    def __init__(self, exp_id: str, run_id: str,
                 loop: asyncio.AbstractEventLoop, callback):
        self.exp_id = exp_id
        self.run_id = run_id
        self.loop = loop
        self.callback = callback
        self.fired = False   # prevent multiple triggers

    def on_deleted(self, event):
        if self.fired:
            return
        if event.is_directory:
            folder_name = Path(event.src_path).name
            if folder_name.startswith(f"{self.exp_id}_{self.run_id}_"):
                self.fired = True
                asyncio.run_coroutine_threadsafe(
                    self.callback(), self.loop
                )


async def wait_for_e_drive_deletion(exp_id: str, run_id: str,
                                     config: dict) -> bool:
    """
    Wait for the experiment folder to be deleted from E: drive,
    signalling that the F: drive copy is complete.

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

    loop = asyncio.get_running_loop()
    deletion_event = asyncio.Event()

    async def on_deletion():
        deletion_event.set()

    handler = ReportDataDeletionHandler(exp_id, run_id, loop, on_deletion)
    observer = Observer()
    observer.schedule(handler, watch_dir, recursive=False)
    observer.start()

    try:
        # Pre-check after the observer is live — eliminates the race window
        # between checking and watching. If the folder is already gone, the
        # copy completed before we started; the NOTIFY is the anchor.
        existing = list(Path(watch_dir).glob(f"{exp_id}_{run_id}_*"))
        if not existing:
            print(f"E: folder already absent for {exp_id}/{run_id} — F: copy complete")
            return True

        await asyncio.wait_for(deletion_event.wait(), timeout=timeout_seconds)
        print(f"E: deletion detected for {exp_id}/{run_id} — F: copy complete")
        return True
    except asyncio.TimeoutError:
        print(f"Warning: E: deletion timeout for {exp_id}/{run_id} "
              f"after {timeout_seconds}s — run will not be verified")
        return False
    finally:
        observer.stop()
        await asyncio.to_thread(observer.join)


async def watch_and_confirm(exp_id: str, run_id: str, config: dict,
                             on_confirmed, on_timeout) -> None:
    """
    Watch E: drive for experiment folder deletion and dispatch to the
    appropriate callback.

    Calls on_confirmed() if deletion is detected within the configured
    timeout, on_timeout() otherwise.
    """
    if await wait_for_e_drive_deletion(exp_id, run_id, config):
        await on_confirmed()
    else:
        await on_timeout()
