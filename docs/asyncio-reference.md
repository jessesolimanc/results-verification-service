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

## asyncio.Queue — the thread-safe bridge

A queue designed for passing data between coroutines safely. Also serves
as a bridge between non-async code (like asyncpg's internal thread) and
the async event loop.

```python
queue = asyncio.Queue()

# Producer — puts items in (can be called from non-async context)
queue.put_nowait(item)

# Consumer — waits until something is available
item = await queue.get()
```

**Why it matters in the listener:**
asyncpg calls its notification callback from its own internal thread,
outside the event loop. You can't `await` from there. The queue acts as
a safe handoff point — asyncpg drops the payload in, the event loop
picks it up.

```
asyncpg thread          event loop
──────────────          ──────────────────
_on_notify() called
queue.put_nowait()  →   await queue.get() unblocks
                        await on_notification(payload)
```

---

## asyncio.Event — the cancellation token

A simple flag that coroutines can check to know when to stop.

```python
token = asyncio.Event()

# In the listener loop:
while not token.is_set():
    ...   # keep running

# From outside, to stop the service:
token.set()   # all loops checking token.is_set() will exit
```

Used in the verification service to allow graceful shutdown — the listener
keeps running until someone calls `token.set()`.

---

## The producer-consumer pattern

A common async pattern where one part of the code **produces** data and
another **consumes** it, decoupled by a queue.

```
Producer                    Queue               Consumer
────────                    ─────               ────────
generates data    →    put_nowait()    →    await get()
                                             processes data
```

In the verification service:
- **Producer** — asyncpg receives PostgreSQL NOTIFY, calls `_on_notify()`
- **Queue** — `asyncio.Queue()` bridges the thread boundary
- **Consumer** — event loop calls `on_notification()` with the payload

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

```python
# main.py — entry point
def run(config: dict) -> None:
    token = asyncio.Event()
    asyncio.run(run_service(config, token))   # start the event loop

# run_service — async entry point
async def run_service(config: dict, token: asyncio.Event) -> None:

    # callback — will eventually call the orchestrator
    async def handle_notification(payload: str):
        data = json.loads(payload)
        exp_id, run_id = parse_experiment_notification(data["experimentId"])
        await orchestrator.verify_run(run_id, exp_id)

    # start the appropriate listener
    if config["listener"]["use_mock"]:
        await listen_async_mock(config, handle_notification)
    else:
        await listen_async(config, token, handle_notification)
```

---

## Full notification flow

```
PostgreSQL fires NOTIFY on reports_table_changes
        ↓
asyncpg receives it on its internal thread
        ↓
asyncpg calls _on_notify(connection, pid, channel, payload)
        ↓
_on_notify calls queue.put_nowait(payload)
        ↓
event loop: await queue.get() unblocks
        ↓
listen_async calls await on_notification(payload)
        ↓
handle_notification() in run_service runs
        ↓
parse_experiment_notification() extracts exp_id and run_id
        ↓
orchestrator.verify_run() is called
        ↓
listen_async goes back to waiting...
```

---

## Common patterns quick reference

| Pattern | What it does |
|---|---|
| `async def f():` | Declares a coroutine |
| `await f()` | Runs coroutine, pauses until done |
| `asyncio.run(f())` | Starts event loop and runs coroutine |
| `asyncio.create_task(f())` | Runs coroutine concurrently |
| `asyncio.Queue()` | Thread-safe data bridge |
| `asyncio.Event()` | Cancellation/signalling flag |
| `await asyncio.sleep(n)` | Pause for n seconds without blocking |
| `await asyncio.wait_for(f(), timeout=n)` | Run with a timeout |

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

- Python docs: https://docs.python.org/3/library/asyncio.html
- asyncpg docs: https://magicstack.github.io/asyncpg/current/
