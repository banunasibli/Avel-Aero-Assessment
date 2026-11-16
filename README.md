# Charter Quote Workflow Engine

A small execution engine that reliably runs a four-step workflow for a fictional charter inquiry (`REQ-1042`). All outside services are mocked; no messages are actually sent.

1. Check aircraft availability
2. Prepare a quote
3. Wait for human approval
4. Send the approved quote (mock)

I used Python 3, the only standard library. There should be nothing to install.

## Run it

```bash
python3 main.py                  # normal run: one simulated timeout, retry succeeds, pause, approval, send
python3 main.py --fail-times 3   # every attempt fails, workflow ends FAILED
python3 -m unittest -v           # run the tests
```

At the approval prompt, we should type `y` (or `yes`) to approve. Anything else rejects the quote and nothing is sent.

## Architecture

```
main.py         command-line program: runs the engine, shows the draft, asks the human
workflow.py     defines the four steps and the fictional request
tools.py        mocked tools (hardcoded aircraft, simulated timeout, fake "outbox")
engine.py       the engine: step order, retry, pause for approval, status, history
test_engine.py  tests for the behaviors above
```

- **Steps and data passing.** A step is a small object with a name, a log label, and a function. The function receives a shared `context` dictionary and returns a result. The engine stores each result in the context under the step's name. So "prepare quote" reads the aircraft list from `context["check_availability"]`, and "send quote" sends `context["prepare_quote"]`. That is how data moves from one step to the next.
- **Status.** The engine is always in one of these states: `PENDING`, `RUNNING`, `PAUSED`, `COMPLETED`, `FAILED`, `REJECTED`.
- **History.** Every event (`START`, `RUNNING`, `FAILED`, `RETRY`, `SUCCESS`, `PAUSED`, `APPROVED`, `REJECTED`, `COMPLETE`) is added to a list of `(label, message)` entries and printed in the same format as the assessment's example. The log comes from what the code actually did, not from print statements scattered around.
- **Retry.** If a tool raises `ToolError`, the engine tries the step again, up to 3 attempts in total. If every attempt fails, the workflow ends as `FAILED` and the later steps never run (so nothing can be sent).

## One key decision: the approval pause is a state, not a prompt

When the engine reaches the approval step, `run()` sets the status to `PAUSED` and **returns**. It does not wait on `input()` inside the engine. The only way past that step is a separate call to `approve()`, which logs the approval, moves the engine forward, and lets `run()` continue. Calling `run()` again while paused does nothing, and `reject()` ends the workflow without the send step ever being reached. This is covered by tests (nothing is sent while paused, nothing is sent after a rejection).

I debated a little with Claude and chose this over a simple "type y to continue" inside the engine because in a real system humans do not decide instantly, it might take some time. "Waiting for a human" should be something the engine can represent as a state, with the decision coming in from outside. It also means the send step cannot run by accident: there is no code path from the pause to the send except  `approve()`.

**Side improvement:** I worked with Claude to add one small side improvement. As mentioned in the document, after failure, we should implement a sensible retry or recovery path. So the engine waits before each retry and doubles the wait every time (0.5s before attempt 2, 1s before attempt 3). The wait is written into the log line, e.g. `[RETRY] Attempt 2 (after 0.5s backoff)`. The delay is a single parameter (`retry_delay`), and the tests set it to 0 so they run instantly. One test checks the waits are 0.5s and 1s by replacing `time.sleep` with a fake.

## One limitation

Everything is stored in memory. A real version must save the status, context, and history to storage after every step. However, if my program is closed while a workflow is `PAUSED`, the workflow and its draft are lost; there is no way to resume it later. 


## Evidence of execution

### Success, with a simulated failure and retry (`python3 main.py`)

```
[START]     Workflow REQ-1042
[RUNNING]   Check availability
[FAILED]    Temporary API timeout
[RETRY]     Attempt 2 (after 0.5s backoff)
[SUCCESS]   Aircraft availability received
[RUNNING]   Prepare quote
[SUCCESS]   Draft prepared
[PAUSED]    Waiting for human approval

  Draft: Gojo Satoru, Tokyo to Osaka, Phenom 300, $8,000

Approve sending this quote? (y/n): y
[APPROVED]  Human approves draft
[RUNNING]   Send quote (mock)
[SUCCESS]   Mock send completed
[COMPLETE]  Workflow finished

Final status: COMPLETED
```

### Every attempt fails (`python3 main.py --fail-times 3`)

```
[START]     Workflow REQ-1042
[RUNNING]   Check availability
[FAILED]    Temporary API timeout
[RETRY]     Attempt 2 (after 0.5s backoff)
[FAILED]    Temporary API timeout
[RETRY]     Attempt 3 (after 1s backoff)
[FAILED]    Temporary API timeout
[FAILED]    Check availability failed after 3 attempts

Final status: FAILED
```

### Human rejects the draft (type `n` at the prompt)

```
[PAUSED]    Waiting for human approval

  Draft: Gojo Satoru, Tokyo to Osaka, Phenom 300, $8,000

Approve sending this quote? (y/n): n
[REJECTED]  Human rejected draft, nothing was sent

Final status: REJECTED
```

(The lines before `[PAUSED]` are the same as in the first run.)

### Tests

`python3 -m unittest -v` runs 7 tests: steps run in order and pass data, a failed step is retried, retries stop after the maximum attempts, waits grow before each retry, nothing is sent while paused, rejection sends nothing, and approving when nothing is waiting raises an error.

## AI use

I built this project with help from an AI assistant (Claude). I gave the description of the project, including keeping it as simple as possible. It suggested the delay side improvement for the recovery path after failure, and I added it after slight changes. I asked for simplifications along the way, like creating a single approving gate and a simpler fictional scenario. AI also helped me in creating this document and designing the simulations in the document. However, I understand the whole process and code and can explain it if needed. 
