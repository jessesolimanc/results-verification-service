# asyncio — reference guide

A practical reference for understanding and working with Python's asyncio
framework, written in the context of the results verification service.

---

## The core problem asyncio solves

Normal Python code is **synchronous** — one line finishes before the next
starts. This works fine until you need to wait for something external (a
database, a network response, a file). While waiting, the entire program
is frozen. This is called **blocking**.

asyncio solves this by letting Python say:
> "I'm waiting for X — go do something else and come back when X is ready."

This is called **asynchronous** or **non-blocking** execution.

---

## Key concepts

### Coroutine
A function defined with `async def`. It can be paused and resumed, unlike
a normal function which runs to completion without stopping.

```python
async def my_coroutine():
    await asyncio.sleep(1)   # paused here for 1 second
    print("done")            # resumes after 1 second
```

A coroutine doesn't run when you call it — it returns a coroutine object.
You need to either `await` it or run it with `asyncio.run()`.

### `await`
Pauses the current coroutine and gives control back to the event loop
until the awaited thing is ready. Only valid inside `async def` functions.

```python
result = await some_coroutine()   # pause until done, then get result
```

### Event loop
The engine that drives all async code. It runs coroutines, switches
between them when they hit `await`, and manages callbacks. You never
interact with it directly in most cases — `asyncio.run()` handles it.

```python
asyncio.run(my_coroutine())   # creates event loop, runs coroutine, closes loop
```

### Task
A coroutine scheduled to run concurrently on the event loop. Unlike
`await` which runs one thing at a time, tasks let multiple coroutines
run "simultaneously" (taking turns at each `await`).

```python
task = asyncio.create_task(my_coroutine())   # schedules it to run
await task                                    # wait for it to finish
```

---

## asyncio.Queue — coroutine-safe data passing

A queue designed for passing data between coroutines safely within the
same event loop. Useful when one coroutine produces data and another
consumes it asynchronously.

```python
queue = asyncio.Queue()

# Producer coroutine
async def producer():
    await queue.put(item)

# Consumer coroutine
async def consumer():
    item = await queue.get()
```

**Important:** `asyncio.Queue` is safe across coroutines in the same
event loop but is NOT thread-safe across OS threads. If you need to
pass data from a true OS thread into the event loop, use
`loop.call_soon_threadsafe()` instead.

**Note on the verification service listener:** The actual listener
implementation does NOT use a queue. asyncpg calls the notification
handler as a native async coroutine directly within the event loop,
so no thread bridge is needed. See the listener pattern section below.

---

## asyncio.Event — signalling between coroutines

A simple flag that coroutines can check or wait on. Used for two
purposes in the verification service:

**Cancellation token** — signals the listener to shut down gracefully:

```python
token = asyncio.Event()

while not token.is_set():
    ...   # keep running

# from outside, to stop:
token.set()
```

**Connection termination detection** — asyncpg fires a termination
listener when a connection drops. Wrapping it in an `asyncio.Event`
lets the async code wait on it cleanly:

```python
conn_terminated = asyncio.Event()
conn.add_termination_listener(lambda _: conn_terminated.set())

# wait for shutdown OR connection drop — whichever comes first
done, pending = await asyncio.wait(
    [
        asyncio.ensure_future(token.wait()),
        asyncio.ensure_future(conn_terminated.wait()),
    ],
    return_when=asyncio.FIRST_COMPLETED,
)
```

This is more responsive than a polling timeout loop — the service
reacts immediately to a dropped connection rather than waiting for
the next poll interval.

---

## The actual listener pattern

The verification service listener uses asyncpg's native async callback
support — no queue needed. asyncpg calls the notification handler
directly as a coroutine within the event loop:

```python
async def listen_async(config, token, on_notification):
    while not token.is_set():
        conn = await asyncpg.connect(db_url)

        # async handler — called directly by asyncpg within the event loop
        async def _handler(conn, pid, channel, payload):
            data = json.loads(payload)
            if data.get("op") == "insert":
                await on_notification(payload)

        # detect connection drop immediately
        conn_terminated = asyncio.Event()
        conn.add_termination_listener(lambda _: conn_terminated.set())

        await conn.add_listener("reports_table_changes", _handler)

        # wait for shutdown OR connection drop — whichever comes first
        done, pending = await asyncio.wait(
            [
                asyncio.ensure_future(token.wait()),
                asyncio.ensure_future(conn_terminated.wait()),
            ],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()

        await conn.close()
```

**Why no queue?** asyncpg's `add_listener` accepts both sync and async
callbacks. When given an async callback, it schedules it on the event
loop directly — no thread boundary is crossed and no bridge is needed.

**Why `asyncio.wait(FIRST_COMPLETED)`?** The listener needs to exit
cleanly on either a deliberate shutdown (`token.set()`) or an unexpected
connection drop (`conn_terminated`). Waiting on both simultaneously means
the service reacts immediately to either event rather than being stuck
waiting for a timeout.

---

## Callbacks

A function passed as a parameter to another function, to be called when
something happens. The caller doesn't know what the callback does — it
just knows to call it.

```python
# callback defined elsewhere
async def handle_notification(payload: str):
    print(f"Got: {payload}")

# passed into the listener
await listen_async(config, token, on_notification=handle_notification)

# listener calls it internally when a notification arrives
await on_notification(payload)   # calls handle_notification
```

The listener has no knowledge of what `on_notification` does. It just
calls it. This keeps the listener and orchestrator decoupled.

---

## How the verification service uses asyncio

### One event loop, one extra thread

The entire verification service runs on **one event loop**, started by
`asyncio.run()` in `main.py`. There is no second event loop.

The only extra thread is the `watchdog` observer — a separate OS thread
that watches the filesystem. It communicates back to the event loop via
`asyncio.run_coroutine_threadsafe()`. Everything else runs on the single
event loop, taking turns at each `await`.

```
ONE event loop (main thread)
  ├── run_service
  ├── listen_async
  ├── _watch_experiment (EXP_1)   ← scheduled by create_task()
  ├── _watch_experiment (EXP_2)   ← scheduled by create_task()
  └── watch_and_confirm (EXP_1)   ← awaited by _watch_experiment

watchdog OS thread (separate thread)
  └── bridges back via run_coroutine_threadsafe()
```

### `asyncio.create_task()` vs `await`

```python
# await — sequential, blocks until done
await some_coroutine()

# create_task — concurrent, schedules and returns immediately
asyncio.create_task(some_coroutine())
```

`create_task()` is used in `handle_notification()` to start a
`_watch_experiment` task without waiting for it. This means
`handle_notification()` returns immediately and the event loop can
receive the next notification while the watch runs in the background.

### The full run_service pattern

```python
# main.py — entry point
def run(config: dict) -> None:
    token = asyncio.Event()
    asyncio.run(run_service(config, token))   # ONE event loop starts here

async def run_service(config: dict, token: asyncio.Event) -> None:
    conn = get_connection(config["paths"]["database"])
    processed_run_ids = get_all_processed_run_ids(conn)
    in_progress = {}       # {run_id: set of exp_ids notified}
    confirmed_ready = {}   # {run_id: set of exp_ids confirmed on F:}
    manifests = {}

    async def handle_notification(payload: str) -> None:
        data = json.loads(payload)
        result = parse_experiment_notification(data.get("experimentId", ""))
        if result is None:
            return   # malformed or missing experimentId — discard
        exp_id, run_id = result

        if run_id in processed_run_ids:
            return

        if run_id not in in_progress:
            manifest = load_manifest(run_id, config)
            manifests[run_id] = manifest
            in_progress[run_id] = set()
            confirmed_ready[run_id] = set()

        expected = {e["experiment_id"] for e in manifests[run_id]["experiments"]}

        if exp_id not in expected:
            print(f"Warning: unexpected experiment '{exp_id}' — ignoring")
            return

        in_progress[run_id].add(exp_id)

        # fire and forget — starts concurrent watch, returns immediately
        asyncio.create_task(
            _watch_experiment(exp_id, run_id, expected, ...)
        )
        # handle_notification returns HERE without waiting for the watch

    async def _watch_experiment(exp_id, run_id, expected, ...):
        """Defines callbacks and delegates to watch_and_confirm."""

        async def on_confirmed():
            confirmed_ready[run_id].add(exp_id)
            if expected.issubset(confirmed_ready[run_id]):
                await asyncio.to_thread(verify_run, config, run_id, manifests[run_id])
                processed_run_ids.add(run_id)
                in_progress.pop(run_id, None)
                confirmed_ready.pop(run_id, None)
                manifests.pop(run_id, None)

        async def on_timeout():
            print(f"Run {run_id}: {exp_id} timed out")

        await watch_and_confirm(exp_id, run_id, config,
                                on_confirmed, on_timeout)

    if config["listener"]["use_mock"]:
        await listen_async_mock(config, handle_notification)
    else:
        await listen_async(config, token, handle_notification)
```

**Note on `verify_run`:** a regular synchronous `def`, not `async def`.
All its internal operations (SQLite writes, file I/O) are synchronous and
have no awaitable equivalents to use. It is run via
`asyncio.to_thread(verify_run, ...)` so the event loop is not blocked
while it executes. Making it `async def` would only matter if it
internally used `await` — it does not.

---

## watchdog and asyncio — OS thread boundary

The `watchdog` library runs its filesystem observer in a separate OS
thread. You cannot call `await` from inside a watchdog callback because
it runs outside the event loop. The correct bridge is
`asyncio.run_coroutine_threadsafe()`:

```python
class ReportDataDeletionHandler(FileSystemEventHandler):
    def __init__(self, ..., loop, callback):
        self.loop = loop         # captured from async context before observer starts
        self.callback = callback # an async coroutine

    def on_deleted(self, event):
        # running in watchdog's OS thread — cannot await directly
        asyncio.run_coroutine_threadsafe(
            self.callback(), self.loop
        )
```

The `loop` reference must be captured **before** the observer starts,
while still in the async context:

```python
async def watch_and_confirm(...):
    loop = asyncio.get_running_loop()  # capture here, in async context
    deletion_event = asyncio.Event()

    async def on_deletion():
        deletion_event.set()          # this runs on the event loop

    handler = DeletionHandler(..., loop=loop, callback=on_deletion)
    observer = Observer()
    observer.start()                  # watchdog OS thread starts here

    await deletion_event.wait()       # event loop free while waiting
```

**Observer-first pattern:** Always start the observer before checking
whether the watched condition already exists. This prevents missed
events — if the deletion occurs between the existence check and the
observer starting, it would be missed. Starting the observer first
guarantees any deletion after that point is caught. If the condition
is already true when you check, set the event manually and proceed.

---

## Full notification flow (with E: drive watch)

```
PostgreSQL fires NOTIFY on reports_table_changes
        ↓
asyncpg calls _handler() on the event loop
        ↓
_handler() checks op == "insert" — ignores updates/deletes
        ↓
await handle_notification(payload)
        ↓
parse_experiment_notification() → (exp_id, run_id) or None (malformed — discarded)
        ↓
manifest loaded, in_progress and confirmed_ready initialised
        ↓
asyncio.create_task(_watch_experiment(exp_id, run_id))
  ← handle_notification returns immediately
  ← event loop free to receive next notification
        ↓
_watch_experiment runs concurrently:
  defines on_confirmed() and on_timeout()
  await watch_and_confirm(exp_id, run_id, ...)
        ↓
watch_and_confirm:
  STEP 1: start watchdog observer (OS thread starts)
  STEP 2: check if E: folder already gone
    → already gone: set deletion_event manually
    → still present: wait for watchdog to fire
  STEP 3: await deletion_event.wait()
    ← event loop FREE while waiting
    ← other notifications handled, other watches run concurrently
        ↓
E: deletion occurs (watchdog OS thread detects it)
  run_coroutine_threadsafe(on_deletion(), loop)
  deletion_event.set()
  deletion_event.wait() unblocks
        ↓
await on_confirmed()
  confirmed_ready[run_id].add(exp_id)
  if all expected experiments confirmed:
    await asyncio.to_thread(verify_run, config, run_id, manifests[run_id])
    clean up state
        ↓
listener goes back to waiting...
```

Note: if the DB connection drops at any point, `conn_terminated` is set,
`asyncio.wait` unblocks, and the outer `while` loop in `listen_async`
reconnects automatically.

---

## Common patterns quick reference

| Pattern | What it does |
|---|---|
| `async def f():` | Declares a coroutine |
| `await f()` | Runs coroutine, pauses until done — sequential |
| `asyncio.run(f())` | Starts the ONE event loop and runs coroutine |
| `asyncio.create_task(f())` | Schedules coroutine concurrently — returns immediately |
| `asyncio.Queue()` | Coroutine-safe data passing within event loop (not OS-thread-safe) |
| `asyncio.Event()` | Cancellation/signalling flag between coroutines |
| `await asyncio.sleep(n)` | Pause for n seconds without blocking |
| `await asyncio.wait_for(f(), timeout=n)` | Run with a timeout |
| `await asyncio.wait([...], FIRST_COMPLETED)` | Wait for whichever of N events fires first |
| `asyncio.run_coroutine_threadsafe(f(), loop)` | Schedule coroutine from an OS thread onto the event loop |
| `loop = asyncio.get_running_loop()` | Capture the currently running loop for use in OS threads |

---

## Things to watch out for

**Never call `await` outside an async function.**
You'll get a `SyntaxError`. If you need to call async code from sync
code, use `asyncio.run()`.

**Never block inside an async function.**
Calling a slow synchronous function (e.g. reading a large file with no
async equivalent) inside an async function blocks the entire event loop.
Use `asyncio.to_thread()` to run blocking code in a thread pool.

```python
# bad — blocks the event loop
result = slow_synchronous_function()

# good — runs in a thread, doesn't block
result = await asyncio.to_thread(slow_synchronous_function)
```

**`asyncio.run()` can only be called once per thread.**
It creates and closes the event loop. Don't call it inside an async
function — use `await` instead.

---

## Further reading

- Python asyncio docs: https://docs.python.org/3/library/asyncio.html
- asyncpg docs: https://magicstack.github.io/asyncpg/current/
- watchdog docs: https://python-watchdog.readthedocs.io/en/stable/
