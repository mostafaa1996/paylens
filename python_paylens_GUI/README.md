# PayLens Simulator

A **PySide6 / Qt Widgets** desktop application with Test Cases, Event Stack, Batch Files, Event History, and Settings. Event publishing uses the existing Azure Event Hubs sender with `python_paylens_GUI/.env`; CSV generation/upload and several other service hooks remain UI previews until their Azure Blob/service integrations are implemented. The original `main_window.ui` and brief are preserved as references.

## Run

From the repository root, with Python 3.11 or newer:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r python_paylens_GUI\requirements.txt
.venv\Scripts\python.exe python_paylens_GUI\main.py
```

If the repository environment already exists, use its Python directly. On macOS/Linux, use `.venv/bin/python` in place of `.venv\Scripts\python.exe`. The UI opens without a network connection. Sending requires `EVENTHUB_CONNECTION_STRING` in `.env` with Send permission for `auth_req`, the hub selected by `utils/EventHubs_interface.py`. All event families use that existing sender; no per-family topics or Kafka credentials are required.

## Try the workflows

- Test Cases displays only Case ID, Transaction journey, Description, Expected, and Num of Steps. `TestCasesFromExcelReader.read_test_cases()` and `read_test_steps()` read the workbook. Each case is instantiated with the existing `TestCaseClass` and an empty step list at startup; the table displays its metadata without opening SQL connections or generating payloads.
- Selecting a case captures the Merchant selection and runs `CasePreparationWorker` in a background QThread. It looks up that merchant, then uses the unchanged `TestCaseClass` constructor to build only the selected case's steps from the reader's stored rows. Generated payloads (including merchant ID and available payment tokens) then appear in Event Stack without publishing. Double-click payload or timing cells to edit them; use `<null>` for JSON null. Edit selected opens the complete JSON editor. Remove, Clear stack, and Export all as JSON retain their behavior. Export contains the currently displayed generated/edited payloads; send results refresh those payloads with the actual transmitted content.
- Terminal choices load from `terminal_machines` for the selected merchant in a background thread, showing each ID and location alongside Online. Selection is captured when adding a case or starting a stream; existing stack cases and active streams retain their selection. Online forces `channel=web`, `payment_method.card_presence=CNP`, `payment_method.entry_mode=online`, `terminal_id=null`, and the default IP address. A terminal forces `channel=pos`, `card_presence=CP`, `entry_mode=offline`, its terminal ID, and `ip_address=null`. These overrides apply only to authorization requests, including when Excel contains conflicting values. Other generators keep their current behavior. Outside the UI, omitting `terminal_id` retains the existing generator defaults; use `terminal_id='online'` to explicitly select online mode.
- Each stack item contains only `payload`, `step`, `action`, `dispatch_seconds`, `token`, `case_run`, `merchant`, and `terminal_id`. Original case objects are kept separately by `case_run`. Send results are separate logger snapshots; they never add execution metadata to the stack items.
- Send Stack creates a fresh `TestCaseClass` from the edited rows for each case run and calls its unchanged `run_test_case()` in the background worker. The class owns ordering, generation, previous-dispatch state and all step delays; the worker has no separate step scheduler or timer. Its sender callback sends the generated payload, records the result and updates progress. CLOCK rows remain in the original runner sequence as observation checkpoints. Their callbacks do not serialize or send a message, create an Event Hubs producer, or increase the sent/total event count. The logger records them as Observation checkpoint. This records reaching the checkpoint, not a pass/fail assertion about downstream processing. Repeated copies of a case have independent run state.
- Start normal stream constructs a fresh first-case instance from the original reader rows with the captured merchant, then calls its original zero-argument `run_test_case()` method. Each cycle generates new identifiers and gets the correct merchant before step creation. The class's own delays and generation behavior apply exactly as implemented. The configurable interval controls the start of another case, allowing overlapping runs. Up to 64 cases execute concurrently; starts are skipped at capacity instead of creating an unbounded queue.
- Each active case runs on its own execution thread and owns an independent Event Hubs producer. The manual stack worker remains separate and available while streaming. Stop prevents new cases only. Every already-started case continues through all remaining steps, including its final capture response, before its producer closes. Manual stack sends also finish every queued event; there is no dispatch cancellation path. Closing waits for the stack and active stream cases to finish sending.
- Generation requires `SQL_CONNECTION_STRING`, pyodbc and the appropriate installed SQL Server ODBC driver. The Merchant selector in Event Stack offers Nile Electronics (21), Alex Fashion (22), Delta Market (23), Cairo Home (24), and Red Sea Sports (25), defaulting to 21. Each stack send or stream captures its selected ID at startup and looks up that merchant in SQL when the case does not supply a merchant. Changing the selector affects subsequent runs; explicit non-null payload values retain their existing precedence. Browsing the catalog does not open SQL connections; selecting a case performs its SQL-backed generation in a background thread. Re-selecting generates a fresh case with the current merchant while previously stacked runs remain independent. The original `TestCaseClass.py` is preserved unchanged; no `prepare_steps`, `use_database` or new cancellation parameters are required from it.
- Event History is a read-only session logger for actual stack/streaming send outcomes. Its table shows time, source, case ID, event type, event ID, result and any error. Selecting a row displays the payload JSON. Draft preparation is not logged. There are no search/filter/demo controls, replay-to-stack actions, exports, save requests or timeline views; logs remain in memory until the app closes.
- Batch Files contains all five ordered column contracts, editable bounded samples, per-file settings, exception configurations, column notes, and generation/export review dialogs. Scroll inside each tab to reach exception controls and type notes. Enter `<null>` in a sample cell for null; empty cells are empty strings. Modified rows are marked `*`. Approximate scale, seed, output directory, CSV delimiter, and encoding are configured in Settings and passed to future generation/export services; they do not silently rewrite the explicit reference previews. Approximate counts never allocate large datasets.
- Customers and merchants are fixed reference data maintained in SQL outside this tool. Enter existing merchant IDs in event fields or raw JSON and batch samples. The tool has no customer/merchant generation or management pages; execution uses the SQL-backed lookups already provided by the test runner.
- Settings apply only to the current session. `EVENTHUB_CONNECTION_STRING` is read from `.env`; connectivity is checked when sending. JSON indentation controls stack export. Batch scale, seed, delimiter, encoding and null/header settings feed the active batch preview workflow; Event History stays in memory and has no persistence controls. Unused HTTP routes, timeouts and composer preferences have been removed.

## Boundaries and assumptions

Event Hubs sending performs a real network operation only when Send Stack or Start normal stream is used. JSON serialization, client creation, sends, and client cleanup run off the UI thread. A successful return from `send_event_hubs_message` is counted as sent; exceptions are reported as failures. This does not confirm consumer processing. Stop prevents new stream cases; active cases and manual stack sends finish every remaining step. Close waits for that work, including the original runner delays, before exiting. Batch generation/upload remains a preview. Event History is an in-memory logger.

`paylens_ui/contracts.json` contains the five CSV column contracts used by Batch Files. Event payload generation uses the provided `TestCaseClass`/`TestStepClass` and their generators. The UI only checks that a payload is a JSON object before dispatch; the retired sample-schema validator and testing-mode flags are removed, so intentional invalid values can be sent for test cases.

No supplied event has `customer_id`, so no customer identifier is injected into these payloads. Supplied event and CSV examples retain their reference merchant IDs; replace them with IDs from SQL when preparing events for your environment. Amount fields preserve Python integers, and CSV monetary fixtures use decimal text.

The linked CSV fixture uses `provider_demo / pa_demo / mer_001`, one successful capture for 1000.00, a 20.00 fee, a provider-supplied 980.00 allocation/payout, and a matching bank credit. Pending and failed capture attempts also remain visible. This simple convention is a fixture, not a general provider balance rule. Requested scales, seeds, distributions, target identifiers, and exception counts are future-service configuration; bounded examples illustrate them without a large generator. The event `processor` and CSV `provider_id` contracts remain separate.

## Integration seams

`services.IntegrationHooks` supplies feedback and the active batch integration hooks. `EventHubDispatchWorker` sends the manual stack and `NormalStreamWorker` schedules the baseline stream. Both call `send_event_hubs_message` directly from `utils/EventHubs_interface.py`. The manual stack worker and each overlapping normal-case execution create separate producers on their first send, reuse them for that run, and close them in `finally`, after completion or failure. Cleanup errors are reported through feedback.

The sender has no module-global producer and does not create a client or load settings at import time. `create_event_hub_producer()` creates a client for the calling thread. `send_event_hubs_message(message, producer=producer)` borrows that client without closing it; the caller owns its lifetime. Never share the same client between threads. All events go to the existing `auth_req` hub, partitioned by `payment_id`.

The existing one-argument `send_event_hubs_message(message)` call remains supported for standalone scripts: it creates a temporary producer and closes it after that send. For multiple messages, create one client in the sending thread and use it for the whole sequence:

```python
from utils.EventHubs_interface import create_event_hub_producer, send_event_hubs_message

with create_event_hub_producer() as producer:
    for message in messages:
        send_event_hubs_message(message, producer=producer)
```

No receiver is needed to report successful sending. Observing received events would require a separate consumer with Listen permission and its own consumer group on the same hub; it does not require another Event Hub. Verifying downstream processing would additionally require a result channel or consumer acknowledgement contract.

## Verification

```powershell
.venv\Scripts\python.exe -m compileall -q python_paylens_GUI
.venv\Scripts\python.exe -m unittest discover -s python_paylens_GUI/tests -p 'test_*.py' -v
```

The offscreen catalog/stack tests mock Event Hubs sending and verify editing, workbook preparation, schedules, concurrent stream/manual sends, graceful stream stopping, and shutdown after all events finish. Sender tests use mocked Azure SDK clients and verify repeated sends, independent client ownership across threads, cleanup, standalone-call compatibility, and import without client initialization. End-to-end verification requires a live Event Hub; no messages were sent during this code change.

## Source layout

`main.py` launches the application. `window.py` composes navigation and dispatch signals. `EventHubDispatchWorker` in `services.py` calls the original `TestCaseClass.run_test_case()` in a `QThread`, with a send/progress callback and no independent step schedule. `TestCasesFromExcelReader` owns workbook reading, and the unchanged `TestCaseClass`/`TestStepClass` provide execution and generation. `test_cases.py` displays their attributes and serializes the generated step payloads for the UI, `stack_model.py` provides typed inline payload edits, and stack/history, CSV, and settings pages are split into modules. `NormalStreamWorker` schedules the baseline stream independently. `widgets.py` contains reusable JSON/field/model-view components, `theme.py` contains QSS, and `domain.py` contains shared helpers and CSV preview fixtures.
