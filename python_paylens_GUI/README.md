# PayLens Simulator

A **PySide6 / Qt Widgets** desktop application with Event Composer, Event Stack, Batch Files, Customers, Merchants, Event History, and Settings. Event publishing connects to Kafka using `python_paylens_GUI/.env`; CSV generation/upload and several other service hooks remain UI previews until their Azure Blob/service integrations are implemented. The original `main_window.ui` and brief are preserved as references.

## Run

From the repository root, with Python 3.11 or newer:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r python_paylens_GUI\requirements.txt
.venv\Scripts\python.exe python_paylens_GUI\main.py
```

If the repository environment already exists, use its Python directly. On macOS/Linux, use `.venv/bin/python` in place of `.venv\Scripts\python.exe`. The UI opens without a broker connection; publishing requires network access to the Kafka broker configured in `.env`.

## Try the workflows

- Select any of the six schema families. Each starts with its **exact supplied sample**, including the distinct refund envelope. Edit fields or use Raw JSON mode and Apply. Unknown fields survive form edits. Use the presence selector for Value, Null, or Omitted; empty strings, zero, and false stay distinct. IDs and Now UTC helpers only change values when clicked.
- Add several schemas to Event Stack. Select an item to inspect or edit its independent snapshot. Clone as new event changes only the event ID; Duplicate for testing retains the exact payload and ID. Move controls use the underlying dispatch order even after table sorting. Sequential dispatch sends to Kafka; delay, reversal, explicit duplicate delivery, stop-on-error, and cancellation controls apply to that publish run. Bulk transport remains unimplemented.
- Event Stack publishes events sequentially to their configured Kafka topics. The application reuses one producer per dispatch run in a worker thread, waits for each delivery callback, and reports broker acknowledgements, failures, and cancellations per event. A broker acknowledgement confirms Kafka accepted the record; it does not confirm that a consumer processed it. Retry failed preserves the event ID and payload. The Consumer subscription is not yet connected to a UI workflow.
- History records immutable prepared/dispatched payload snapshots and separate attempt metadata. Search includes all identifiers, scenario, stack, and run. Family/outcome/date filters, a business timeline, export hooks, save-failure demonstrations, and Load as new draft are available. The latter explicitly assigns a new event ID. Load demo history shows the independent supplied examples; it does not claim they form a successful payment journey.
- Batch Files contains all five ordered column contracts, editable bounded samples, per-file settings, exception configurations, column notes, and generation/export review dialogs. Scroll inside each tab to reach exception controls and type notes. Enter `<null>` in a sample cell for null; empty cells are empty strings. Modified rows are marked `*`. Approximate scale, seed, output directory, CSV delimiter, and encoding are configured in Settings and passed to future generation/export services; they do not silently rewrite the explicit reference previews. Approximate counts never allocate large datasets.
- Customers and Merchants provide searchable lists, manual strict/testing editors, clone/disable/remove, synthetic auto-generation previews, and import/export hooks. Referenced entity removal requires confirmation; existing event snapshots keep their IDs. Merchant selectors support typing and substring completion; manual event overrides remain intact.
- Settings apply only to the current session. Kafka credentials and per-family topic names are read from `.env`; broker connectivity is checked during publish. Output/history directories and export filename previews still configure future persistence services.

## Boundaries and assumptions

Kafka publish performs a real network operation when the user sends an event. The GUI validates the full selected set and resolves every event type to a topic before starting the worker. Producer creation, delivery polling, and flush run off the UI thread. Failed/unknown delivery outcomes are reported per item. The app still has no Azure Blob upload, durable history, CSV generation engine, financial lifecycle/reconciliation logic, or complete authoritative event schemas. CSV generation/export/save hooks remain visibly simulated; clipboard copying is local. Closing during a Kafka run requests cancellation for unsent events and lets the in-flight publish finish.

`paylens_ui/contracts.json` transcribes all six event objects and all five CSV column lists from `PayLens_PySide6_UI_Codex_Prompt.md`. The supplied examples are not full JSON Schemas. Local strict checks conservatively require the non-null sample fields and their demonstrated types; null sample fields are assumed nullable/omittable, with `_minor` values interpreted as integers and unspecified `action`/`error` values as bounded objects. These assumptions are isolated in `domain.py` for replacement. Alternate status strings and unknown fields remain representable. Negative amounts, missing non-null sample fields, malformed known types, timezone-free timestamps, and nonautomatic capture mode require testing mode. Raw JSON must parse to an object; malformed raw transport is not supported. Testing-mode payloads still pass the same publish validation; invalid payloads are blocked before Kafka. No partial-refund business workflow is introduced.

Customer/merchant records are explicitly a **proposed UI model**, not an authoritative contract. No supplied event has `customer_id`, so no customer selector or identifier is injected into these payloads. Common currency exponents are explicitly listed for display only (including EGP 2, JPY 0, KWD/BHD 3); unknown currencies receive no assumed conversion. Amount fields preserve Python integers, and CSV monetary fixtures use decimal text.

The linked CSV fixture uses `provider_demo / pa_demo / mer_001`, one successful capture for 1000.00, a 20.00 fee, a provider-supplied 980.00 allocation/payout, and a matching bank credit. Pending and failed capture attempts also remain visible. This simple convention is a fixture, not a general provider balance rule. Allocation-unavailable mode performs no derivation. Requested scales, seeds, distributions, target identifiers, and exception counts are future-service configuration; bounded examples illustrate them without a large generator. The event `processor` and CSV `provider_id` contracts remain separate.

## Integration seams

`services.IntegrationHooks` exposes UI signals for event publishing and future services. `KafkaDispatchWorker` owns one producer for a run and emits per-item delivery outcomes, progress, and completion from a `QThread`. `kafka_IO.produce_kafka_message` queues a record on that caller-owned producer; delivery polling and the run-level flush are handled by the worker. Topic routing follows the six exact `event_type` values. Kafka subscription still needs a managed worker, start/stop controls, message-handling policy, and offset-commit behavior before it can be used by the GUI.

## Verification

```powershell
.venv\Scripts\python.exe -m compileall -q python_paylens_GUI
.venv\Scripts\python.exe python_paylens_GUI\tests\smoke_ui.py
.venv\Scripts\python.exe python_paylens_GUI\tests\smoke_ui.py --screenshots
```

Earlier offscreen checks cover the presentation prototype. The Kafka worker now requires a live broker for end-to-end delivery verification; no messages were sent during this code change.

## Source layout

`main.py` launches the application. `window.py` composes navigation and dispatch signals. `KafkaDispatchWorker` in `services.py` owns per-run producer delivery handling in a `QThread`. Composer, stack/history, CSV, entity, and settings pages are split into modules. `widgets.py` contains reusable JSON/field/model-view components, `theme.py` contains QSS, and `domain.py` isolates fixtures and presentation checks.
