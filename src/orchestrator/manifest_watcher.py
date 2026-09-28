"""
manifest_watcher.py — watches manifests_dir for new context manifests.

This is the explicit hand-off: a context_manifest_*.json file appearing
in manifests_dir is the signal that a run's experiments are about to
start reporting results. The service registers every experiment the
manifest declares as "expected" the moment the file appears, so a later
pipeline notification only needs a plain dictionary lookup to find which
run it belongs to — no parsing a run_id out of the notification payload.

Mirrors the same "start the observer, then check for what's already
there" pattern used in orchestrator/watcher.py for the E: drive deletion
watch, so a manifest dropped before the service starts isn't missed.
"""

import asyncio
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

MANIFEST_PREFIX = "context_manifest_"
MANIFEST_SUFFIX = ".json"


class ManifestCreatedHandler(FileSystemEventHandler):
    """
    Fires callback for each new context_manifest_*.json file created.
    Runs in watchdog's OS thread — uses run_coroutine_threadsafe to
    bridge back into the asyncio event loop.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop, callback):
        self.loop = loop
        self.callback = callback

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.name.startswith(MANIFEST_PREFIX) and path.suffix == MANIFEST_SUFFIX:
            asyncio.run_coroutine_threadsafe(self.callback(path), self.loop)


async def watch_manifests_dir(config: dict, on_new_manifest) -> None:
    """
    Watch manifests_dir for new manifest files and call on_new_manifest(path)
    for each one — including any already sitting there when this starts.

    Runs until cancelled. on_new_manifest must be idempotent: a manifest
    dropped right around startup may be seen both by the catch-up scan
    below and by the live watch.
    """
    watch_dir = Path(config["paths"]["manifests_dir"])
    watch_dir.mkdir(parents=True, exist_ok=True)
    loop = asyncio.get_running_loop()

    async def _on_created(path: Path):
        await on_new_manifest(path)

    handler = ManifestCreatedHandler(loop, _on_created)
    observer = Observer()
    observer.schedule(handler, str(watch_dir), recursive=False)
    observer.start()

    try:
        # Catch up on manifests already present before the observer started —
        # same reasoning as watcher.py's pre-check for E: drive deletion:
        # starting the observer first eliminates the race window.
        for path in sorted(watch_dir.glob(f"{MANIFEST_PREFIX}*{MANIFEST_SUFFIX}")):
            await on_new_manifest(path)

        await asyncio.Event().wait()  # run until cancelled by the caller
    finally:
        observer.stop()
        await asyncio.to_thread(observer.join)
