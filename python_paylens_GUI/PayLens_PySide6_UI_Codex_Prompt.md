# Codex implementation prompt — PayLens Simulator UI

You are implementing the desktop USER INTERFACE of **PayLens Simulator**, a Python application using **PySide6 and Qt Widgets**.

Build the runnable interface now. Do not stop at a proposal, wireframe, or architecture document. Use the attached PayLens reference image for visual direction and the event/CSV screenshots for contracts. Read this entire brief before implementation.

## 1. Scope: UI implementation only

Your responsibility is the complete UI and presentation behavior, not the complete simulator.

Implement:

- Navigation, layouts, reusable widgets, forms, dialogs, tables, themes, and useful empty/error/loading states.
- Form-to-JSON synchronization, local presentation validation, selection, editing, filtering, sorting, and an in-memory event stack.
- An in-memory mock history and small, deterministic fixtures that demonstrate the intended workflows.
- Clearly named Qt signals or controller interfaces for future generation, sending, persistence, importing, and exporting services.
- A mock adapter that makes these workflows demonstrable without external infrastructure. Every simulated result must be labeled **SIMULATED**.

Do not implement HTTP clients, Flask, Kafka, databases, durable history, real CSV generation engines, payment processing, reconciliation algorithms, provider retries, or large-scale synthetic-data generators. Do not perform network requests. Export and save buttons should invoke integration hooks and display an honest mock result, not claim files were saved. Copying the current JSON to the clipboard is allowed. Loading bounded local demo fixtures is allowed.

User-selectable output directories, filename previews, autosave preferences, and export dialogs are required UI, even though actual persistence is deferred. All screens should work offline. A visibly configured Mock mode may simulate dispatch; the Real integration option must say **Not implemented** and cannot silently use the mock.

## 2. Visual design

Match the reference image's visual language: dark navy sidebar, light neutral workspace, white cards, teal primary actions, restrained borders, dark JSON editor, and readable typography. Implement an original coherent Qt interface informed by the reference; do not place its screenshot inside the application.

- Application name: **PayLens Simulator**. Main composer title: **Transaction Event Generator**.
- English interface, left-to-right. Clear, professional labels and exact technical field names in previews/tooltips.
- A QMainWindow with persistent sidebar, page header, central workspace, and compact status bar.
- Sidebar: Event Composer, Event Stack, Batch Files, Customers, Merchants, Event History, Settings.
- Header: current page, LOCAL / SIMULATION badge, mock/real adapter state, and no fake connection indicators.
- Use layout managers, QSplitter, scroll areas, stretch factors, and sensible minimum sizes. Do not hard-code absolute positions.
- Target a comfortable 1440 × 900 window. Verify usability at 1280 × 800 and 1920 × 1080. At smaller sizes, scroll relevant panels without hiding essential actions.
- Main composer: editable form on the left and live JSON preview on the right; preserve adjustable proportions.
- Keep primary actions accessible. Use text plus icons for important actions. Avoid emoji icons and color-only status meaning.
- Consistent spacing, card padding, input heights, focus indication, tooltips, keyboard traversal, and visible selection.
- No KPI charts, decorative dashboards, authentication screen, or unrelated features.
- No web frontend, QWebEngine, Electron, Tkinter, PyQt, or QML. Use PySide6 Qt Widgets with a reusable QSS theme.

## 3. Terms and navigation behavior

Keep these concepts distinct:

1. **Single event:** manually configure one payload and request its dispatch.
2. **Event Stack:** collect any practical number of heterogeneous event drafts, reorder them, and request dispatch of the collection with one user action. This is not a LIFO-only data structure.
3. **Batch Files:** configure future generation of the five CSV datasets listed below. This is unrelated to the event stack.
4. **Event History:** read-only snapshots of prepared/dispatched events, grouped and searchable by related business identifiers.

Do not use the word Batch ambiguously in event controls. Switching pages or schemas must preserve drafts and stack contents. Keep prototype data bounded for performance, but do not impose an arbitrary product limit such as 10 stack entries.

## 4. Event Composer: six schema families

Provide a schema selector with friendly labels and these exact event_type mappings:

| UI schema family | Actual event_type |
| --- | --- |
| Authorization Request | authorization_requested |
| Authorization Response | authorization_result |
| Capture Expectation | capture_expected |
| Capture Result | capture_result |
| Order Fulfillment | order_fulfillment_updated |
| Refund | refund.updated |

Correct spelling in UI labels: Authorization, not Autherization. Preserve the exact contract keys, values, nesting, capitalization, and types in Appendix A. Do not rename payload fields to match friendly labels. These are supplied examples, not complete JSON Schema specifications; do not invent authoritative status enums or conditional requirements from a single sample. Unknown enum values should remain representable, particularly in testing mode. Record assumptions explicitly.

Composer requirements:

- Group fields logically into Identity, Business Details, Provider/Outcome, and Event Metadata as appropriate for the selected schema.
- Use searchable merchant/customer selectors wherever the contract supports the relevant identifier. Do not add customer_id to event contracts that do not contain it.
- All contract fields must be editable or have an explicit intentional fixed/read-only explanation. A disabled hidden field must not erase its existing value.
- Provide defaults, Reset current draft, Load sample, Copy JSON, Import JSON hook, Export JSON hook, Add to Stack, and Send Single Event.
- Generate/new-ID and Now UTC actions are presentation helpers, not business simulation. IDs and timestamps must not regenerate on every repaint or field change.
- Amounts in *_minor are integers. Display a separate friendly monetary equivalent; never replace the integer payload with a formatted float. The supplied EGP example maps 100000 to EGP 1,000.00. Do not assume every currency has two decimal places.
- Integer amount inputs must support large values beyond a normal 32-bit spin box's range, and deliberate negative values in testing mode.
- Preserve UTC/timezone information. Keep event_time, provider_event_time, follow_up_at, expected_capture_at, fulfillment_occurred_at, emitted_at, and refund timestamps distinct.
- Explicit controls for null vs a value; where contracts permit it, also support omitted optional fields. Empty string, null, zero, false, and missing must remain distinct.
- Nested objects need usable editors. Known nested sections get structured controls; unspecified action/error object shapes get a bounded JSON object editor instead of invented subfields.
- Preserve schema_version as integer 1 for the authorization/capture/fulfillment examples and string "1.0" for the refund example.
- The refund contract uses emitted_at, update_source, a nested data object, order_id, and uppercase statuses. Do not normalize it into the other event envelope.
- Capture Expectation must carry a short explanatory hint: internal notification of an expected automatic capture; not a command to charge a customer.
- Keep automatic capture as the scope; do not add a manual-capture payment workflow. Raw test edits may still demonstrate malformed values.
- Order fulfillment originates from the merchant system; do not infer delivery from successful authorization/capture.

### JSON preview and testing mode

- Pretty-printed, syntax-highlighted JSON in a monospace QPlainTextEdit with copy action, validation summary, and no truncation of the payload.
- Default preview is read-only. An explicit Raw JSON mode permits controlled payload editing.
- Applying raw JSON synchronizes known fields, preserves unknown fields, and displays parse/type issues. No recursive signal loops or silent field loss.
- Strict mode: validate known structural/types requirements, prevent dispatch of demonstrably invalid payloads, and show field-level messages. Do not call this an official full-schema validation when complete contracts were not supplied.
- Testing mode: permit deliberate contract violations with a visible warning, scenario label, and confirmation at dispatch. Malformed JSON cannot be treated as a valid event object; represent it separately as a raw test payload if supported, clearly marked.
- Cover payload-test cases through presets or editing controls: null/omitted fields, mismatched IDs, abnormal amounts, duplicate event IDs, alternate status, old timestamps, and malformed fields. Do not expand the allowed payment business scope to partial refunds; refunds remain full-order refunds.

## 5. Event Stack

Support mixed schema families in one stack. Show a table with Enabled, Position, Event Type, Event ID, Merchant, Payment/Order, Event Time, Scenario, Validation, and UI Dispatch State. Handle different envelope paths correctly, e.g. refund data.payment_id.

- Add current draft, edit selected item, remove, duplicate, move up/down, optional drag reorder, select all, enable/disable, clear stack, and inspect payload.
- Support two explicit duplication actions: **Clone as new event** generates a new event ID; **Duplicate for testing** preserves the exact payload/ID and is visibly labeled. Neither silently changes payment_id/attempt_id.
- Editing a stack item updates that draft only. Later composer edits cannot mutate previously captured snapshots by shared object reference.
- Stack selection opens a detail preview. Display entry count and enabled/invalid counts.
- Send Stack is one user action. Expose a future transport choice: sequential dispatch, or one bulk request if supported. Do not assume the future API supports arrays, atomic delivery, or a transaction spanning the stack.
- Expose UI controls for ordering, inter-event delay, intentional duplicate dispatch, delayed arrival, out-of-order dispatch, and stop-on-error vs continue-on-error.
- Keep transport options separate from payload JSON; do not inject UI metadata into payment contracts.
- Include start/stop/progress/cancel states in the mock adapter. Cancellation affects items not yet simulated; it does not undo completed dispatches.
- Distinguish queued, dispatching, accepted, failed, cancelled, and simulated states from business payload status. A declined authorization event can be successfully transported.
- Show partial dispatch results and retry failed/selected hooks. Exact resend preserves event ID and the snapshot; a new business event requires explicit cloning/editing.
- Label multi-event dispatch outcomes per item. Never show complete success before the adapter reports it, or imply API acceptance guarantees downstream Kafka processing.
- Use a small UI-safe mock sequence with QTimer when needed, never time.sleep on the GUI thread.

## 6. Event History and planned JSON persistence

Design for saving **each event in its own JSON file**, including single and stack actions. Provide an Autosave after dispatch preference and configurable history/output directories. These controls are contracts for later persistence services, not permission to implement durable storage now.

Preserve each event as its original raw payload. Keep UI metadata such as stack_id, run_id, scenario, dispatch attempts, timestamps, and transport outcome separate, for example in a sidecar/index. Do not wrap or rewrite event contracts without explicit user choice.

Suggested future output paths, shown as previews:

- history/<run_id>/authorization/<event_id>.json
- history/<run_id>/capture/<event_id>.json
- history/<run_id>/refund/<event_id>.json
- history/<run_id>/fulfillment/<event_id>.json

Map authorization_requested and authorization_result into Authorization; capture_expected and capture_result into Capture. The same payment can have multiple immutable events in both families. Provide a business-grouped history view as well, using payment/attempt/capture/refund identifiers or merchant + order where appropriate. Order fulfillment does not contain payment_id; do not invent one to make grouping work.

Never overwrite events in duplicate/replay tests: design collision-safe filename suggestions and separate dispatch-attempt records. Repeated dispatch of an event must retain the original payload and event ID while recording each attempt independently.

History UI:

- Search and filter by schema family, event ID, merchant, payment/attempt/capture/refund/order, date range, scenario, stack/run, and transport outcome.
- Read-only payload/details pane, chronological business timeline, copy, export hooks, and **Load as new draft**.
- History snapshots remain unchanged after edits elsewhere.
- Separate transport failure from planned file-save failure; provide UI for pending/save failed/retry save without inventing disk success.
- Include honest empty, loading, error, and demo-populated states.

## 7. Batch Files workspace: five CSV datasets

Build a complete configuration and preview UI for:

1. settlement_entries_DATE.csv
2. payouts_DATE.csv
3. payout_allocations_DATE.csv
4. bank_statement_ACCOUNT_DATE.csv
5. capture_ledger_DATE.csv — an internal PayLens backend export, not an external provider settlement report.

The reference summary also mentions recon_settlement/recon_payout. These are downstream reconciliation outputs, NOT additional source-generator files in this scope. Do not implement reconciliation logic.

### Layout and controls

- Shared configuration card: reporting date/date range, timezone/cutoff, merchant selection, provider/provider account, bank/beneficiary account, currency, approximate scale, optional seed, and output-directory selector.
- Enable/disable each dataset. Clearly show dependencies and whether payout allocations are available from the simulated provider.
- Per-file tabs/cards with settings, ordered column list, sample row grid, column type hints, row count, null formatting, filename preview, and mock generation state.
- Table preview must support selecting and manually editing sample cells, adding/deleting sample rows, and clearly marking modified rows.
- Proposed configuration may support counts and distribution controls, but the prototype generates only small deterministic demo previews. Never allocate a huge dataset just because a user enters a large requested count.
- Buttons: Preview sample, Generate selected files, Export selected, Export all five. Generation/export invoke mock hooks and show SIMULATED results; no real files or generation engine.
- Provide explicit settings for delimiter, encoding, header inclusion, and null representation. Monetary decimal values must be displayed without binary floating-point artifacts.
- Show a dependency/relationship explanation panel or compact text list; do not claim payout_allocations exist for every integration, and never invent an unsupported allocation derivation.

### Related-data design

Normal fixture previews should visibly demonstrate consistent merchant/provider/provider-account scopes; capture/payment references linking ledger and settlement; entry_id linking settlement and allocations; payout_id linking allocations and payouts; and beneficiary_account_id matching bank_account_id where appropriate. Use explicit future mapping boundaries for processor/provider naming differences between event and CSV contracts. Do not rename either source contract.

Amounts: event *_minor fields are integer minor units, while the supplied CSV monetary columns are decimal major-unit amounts. Use explicit conversion only when a future adapter needs it; never label them as the same representation. Settlement net_amount = gross_settlement_amount - fee_amount for the supplied convention. Use a transparent simple fixture for payout totals rather than silently assuming all providers' balance rules are identical.

Capture ledger contains capture attempts. Reconciliation eligibility uses SUCCEEDED records; do not silently exclude all PENDING/FAILED rows from the dataset or build a reconciliation engine.

### Exception/testing panel

Allow per-file exception enablement, count or percentage, seed, target identifiers, preset selection, and a description of expected inconsistency. Keep normal preview and intentionally invalid preview distinguishable. Example UI presets:

- Ledger capture missing from settlement; settlement entry without ledger match.
- Amount mismatch, wrong currency, wrong merchant/provider scope, missing or duplicate stable identifier.
- Repeated report, corrected report version, older snapshot arriving after a newer one.
- Missing/incorrect allocation, allocation amount mismatch, absent provider allocation report.
- Payout SCHEDULED/SENT/FAILED/RETURNED snapshot examples; missing or delayed bank credit; unmatched bank credit; mismatched transfer reference/account.
- Empty file, missing column, invalid date/decimal, null in required column, duplicate row.

These are UI test configuration presets and bounded mock examples. Do not implement financial inference, fraud models, or automatic validation of complete cross-file financial rules. Do not edit history/events as a side effect of CSV test configuration.

Use the exact ordered columns and known type/enum notes from Appendix B. Show row counts, selected files, intended exception counts, output filenames, and a summary before future generation.

## 8. Customers and Merchants workspaces

Each gets a dedicated page with a searchable/filterable table, details pane, automatic-generation configuration dialog, manual-add/edit dialog, import/export hooks, and mock records.

- Automatic-generation UI: count, optional seed, ID prefix, and relevant distribution/default settings. Counts configure a future service; prototype fixtures stay small.
- Manual additions must support deliberate test cases: custom/duplicate IDs, missing fields, unusual values, and inactive entities, with strict/testing mode clearly distinguished.
- Add/Edit/Clone/Disable and remove-from-demo actions; warn about drafts/stack references before removing a referenced record. Never silently cascade changes into existing event snapshots.
- Selecting an entity in the composer can populate relevant defaults, but manual overrides remain possible and visible. Do not overwrite them unexpectedly.
- As no authoritative customer/merchant schemas were supplied, define a small clearly marked **proposed UI model**, isolated for later replacement. Do not present invented fields as established PayLens contracts.
- Suggested customer fields: customer_id, synthetic display name, optional synthetic email, country, status, optional scenario tags. No real identities or payment-card data.
- Suggested merchant fields: merchant_id, display name, status, default currency, provider_id/provider_account_id, and beneficiary-account references with synthetic bank/account IDs. Support multiple account references in the proposed UI model if useful.
- Customer records are useful simulation fixtures, but do not force a customer_id into supplied events that lack it. No real card numbers, CVV, or bank credentials.

## 9. Settings and future integration boundaries

Settings UI should include mock/real adapter selection, API base URL, schema-family route mapping, request timeout, optional safe authentication placeholder, defaults, timestamp/timezone options, history/export directories, JSON/CSV preferences, autosave preference, strict/testing default, and theme preference if implemented.

Do not hard-code an assumption that all six schemas share one endpoint. Do not implement authentication or store credentials. Test Connection in Mock mode returns clearly simulated feedback; Real mode says not implemented.

Expose small, readable integration seams such as:

- request_send_event(payload, dispatch_options)
- request_send_stack(items, dispatch_options)
- request_generate_batch_files(config)
- request_generate_customers(config), request_generate_merchants(config)
- request_import(kind), request_export(kind, selection, options)
- request_save_history(snapshot, metadata), request_test_connection(settings)

Actual method/signal names may follow repository conventions. UI-facing DTOs/view models and mock adapters must remain separate from event payloads. Future asynchronous services can report per-item status/progress/errors without rewriting the widgets.

## 10. Implementation structure and usability

- Inspect the repository and applicable instructions first; extend existing structure when possible and preserve unrelated code.
- Use ordinary PySide6 signals/slots and a modest page/controller/view-model organization. Avoid a giant monolithic main.py and unnecessary framework layers.
- Suggested separation: app entry point; main window; pages; shared form/JSON/table widgets; theme; schema field definitions; UI view models; mock adapters; fixtures.
- Use model/view tables for stack, history, and entity lists so larger future lists do not require widget-per-cell designs.
- Preserve form state during navigation. Show unsaved draft indicators and protect against accidental replacement/reset.
- Keyboard support: tab traversal, standard copy/paste, Ctrl+Enter for Add to Stack, Delete only when the stack/list has focus. Do not make Enter in a text field accidentally send financial events.
- No blocking work on the GUI thread. Use bounded mock data and QTimer for simulated operations.
- Tooltips and inline messages should explain product behavior, not implementation internals. Keep technical contract names in developer-oriented previews where useful.
- No broad refactoring, deployment, actual payment integrations, packaged installers, or persistence work beyond this UI scope.

## 11. Acceptance checklist

Complete the UI, then verify these behaviors:

1. Application launches offline with documented commands and no external service.
2. All seven sidebar pages are implemented and usable, not empty placeholders.
3. Every supplied event sample loads with all fields/nesting/types preserved.
4. The request's payment_method, response's decline, capture result's failure/retry, and refund's data objects are editable.
5. Form changes update JSON; applying valid raw JSON updates the form without losing unknown fields.
6. Null, omitted, empty, zero, false, UTC timestamps, and large integer amounts remain distinguishable.
7. Mixed event types can be added, edited, reordered, duplicated, and dispatched through the explicit mock adapter.
8. One event and stack dispatch have honest per-item progress/error/cancel states and never imply atomic delivery.
9. History snapshots remain immutable and support Authorization/Capture family views plus correct refund/fulfillment linking.
10. Every CSV tab contains its exact columns, a useful editable demo preview, configuration controls, and exception settings.
11. All five datasets are selectable together; Capture Ledger is labeled internal; reconciliation outputs stay out of scope.
12. Customer/merchant auto-generation configurations and manual test-record forms work with demo state.
13. UI resizing remains usable at the three target resolutions, including keyboard access and scrollable long forms.
14. External actions remain mock/stubbed and clearly labeled; no real network, disk-save, CSV engine, or financial success is fabricated.

Run available syntax/import checks and meaningful UI smoke checks. If a GUI environment is available, launch and inspect representative screens; otherwise use a feasible offscreen check and report visual inspection limitations honestly. Do not claim a screenshot review that did not occur. Do not spend this task building an exhaustive business test suite.

Deliver the implementation, minimal dependencies, a concise README with run instructions and mock/integration boundaries, and screenshots of the composer, stack, CSV workspace, and entity management if capture is possible. Explain any assumptions or missing contract definitions. Proceed with reasonable UI choices without stopping for routine confirmation.

---

## Appendix A — Exact supplied event examples

These examples are the transcription of the attached contract screenshots. Preserve differences between contracts. They do not constitute an exhaustive enum/rules specification.

### Authorization Request

```json
{
  "schema_version": 1,
  "event_id": "evt_001",
  "event_type": "authorization_requested",
  "event_time": "2026-10-08T09:00:00.000Z",
  "source": "backend",
  "payment_id": "pay_001",
  "attempt_id": "attempt_001",
  "merchant_id": "mer_001",
  "order_reference": "order_145",
  "requested_amount_minor": 100000,
  "currency": "EGP",
  "channel": "web",
  "payment_method": {
    "type": "card",
    "card_presence": "CNP",
    "entry_mode": "online"
  },
  "terminal_id": null,
  "ip_address": "192.0.2.10",
  "idempotency_key": "auth_attempt_001"
}
```

### Authorization Response

```json
{
  "schema_version": 1,
  "event_id": "evt_002",
  "event_type": "authorization_result",
  "event_time": "2026-10-08T09:00:02.350Z",
  "source": "api_response",
  "payment_id": "pay_001",
  "attempt_id": "attempt_001",
  "merchant_id": "mer_001",
  "order_reference": "order_145",
  "processor": "adyen",
  "processor_reference": "8812345678901234",
  "provider_event_time": null,
  "status": "declined",
  "provider_status": "Refused",
  "requested_amount_minor": 100000,
  "authorized_amount_minor": null,
  "currency": "EGP",
  "authorization_code": null,
  "decline": {
    "provider_code": "12",
    "provider_reason": "Not enough balance",
    "reason": "insufficient_funds"
  },
  "action": null,
  "error": null
}
```

### Capture Expectation

```json
{
  "schema_version": 1,
  "event_id": "evt_cap_001",
  "event_type": "capture_expected",
  "event_time": "2026-10-08T09:00:02.000Z",
  "source": "backend",
  "capture_id": "cap_001",
  "payment_id": "pay_001",
  "attempt_id": "attempt_001",
  "merchant_id": "mer_001",
  "order_reference": "order_145",
  "capture_mode": "automatic",
  "processor": "provider_demo",
  "authorization_reference": "auth_ref_001",
  "expected_amount_minor": 100000,
  "currency": "EGP",
  "expected_capture_at": "2026-10-08T09:00:02.000Z",
  "follow_up_at": "2026-10-08T09:10:02.000Z"
}
```

### Capture Result

```json
{
  "schema_version": 1,
  "event_id": "evt_cap_002",
  "event_type": "capture_result",
  "event_time": "2026-10-08T09:00:04.000Z",
  "source": "webhook",
  "capture_id": "cap_001",
  "payment_id": "pay_001",
  "attempt_id": "attempt_001",
  "merchant_id": "mer_001",
  "order_reference": "order_145",
  "capture_mode": "automatic",
  "processor": "provider_demo",
  "authorization_reference": "auth_ref_001",
  "processor_capture_reference": "cap_ref_001",
  "provider_event_time": "2026-10-08T09:00:03.800Z",
  "status": "failed",
  "provider_status": "CAPTURE_FAILED",
  "captured_amount_minor": null,
  "currency": "EGP",
  "failure": {
    "code": "technical_issue",
    "provider_code": null,
    "provider_reason": "Temporary processing issue",
    "retryable": true
  },
  "retry": {
    "owner": "provider",
    "state": "scheduled",
    "next_retry_at": null
  },
  "follow_up_at": "2026-10-08T09:15:04.000Z"
}
```

### Order Fulfillment

```json
{
  "schema_version": 1,
  "event_id": "evt_order_003",
  "event_type": "order_fulfillment_updated",
  "event_time": "2026-10-08T09:02:00.000Z",
  "source": "merchant_update",
  "merchant_id": "mer_001",
  "order_reference": "order_145",
  "fulfillment_status": "delivered",
  "fulfillment_version": 3,
  "fulfillment_occurred_at": "2026-10-08T09:01:30.000Z"
}
```

### Refund

```json
{
  "schema_version": "1.0",
  "event_id": "evt_r100_v3",
  "event_type": "refund.updated",
  "refund_version": 3,
  "emitted_at": "2026-10-12T10:02:01Z",
  "update_source": "PROVIDER_WEBHOOK",
  "provider_event_id": "pevt_903",
  "data": {
    "refund_id": "ref_100",
    "merchant_id": "mer_001",
    "order_id": "ord_7001",
    "payment_id": "pay_9001",
    "provider": "DEMO_PROVIDER",
    "provider_payment_id": "ppay_551",
    "provider_refund_id": "pref_801",
    "request_idempotency_key": "mer001_ord7001_full_refund_1",
    "retry_of_refund_id": null,
    "refund_amount_minor": 100000,
    "currency": "EGP",
    "refund_reason": "CUSTOMER_REQUEST",
    "status": "PENDING_FUNDS",
    "status_reason_code": "INSUFFICIENT_FUNDS",
    "status_reason_message": "Waiting for refundable balance.",
    "provider_status": "pending",
    "requested_at": "2026-10-12T10:00:00Z",
    "status_updated_at": "2026-10-12T10:02:00Z",
    "provider_updated_at": "2026-10-12T10:01:58Z",
    "refund_reference": null
  }
}
```

The independent examples are not one coherent successful payment journey: the authorization example is declined, capture examples use a different provider value, and the refund refers to another order/payment. Preserve them as separate samples. If demonstrating a linked normal journey, use a clearly labeled separate fixture with consistent identifiers, an authorized result, and suitable timestamps; do not silently alter the supplied samples or implement a lifecycle engine.

## Appendix B — CSV column contracts

Preserve each list's column order. Required = known requirement in supplied screenshots; optional = nullable/absent value according to the later export convention; conditional = explain the known rule. For screenshots that do not fully define a condition, annotate it rather than inventing one. All CSV schemas below are reference contracts for the UI, not a request to build the export engine.

### B1. settlement_entries_DATE.csv

| Column | Type / known requirement |
| --- | --- |
| report_id | string, required |
| report_version | integer, required; corrected-report versions |
| entry_id | string, required; stable within provider/account scope |
| provider_id | string, required |
| provider_account_id | string, required |
| merchant_id | string, required; may require source mapping |
| settlement_batch_id | string, required |
| entry_type | enum, required: SALE / REFUND / CHARGEBACK / FEE / RESERVE_HOLD / RESERVE_RELEASE / ADJUSTMENT |
| provider_payment_id | string, conditional for payment-linked movements |
| provider_capture_id | string, conditional where capture-level linking is available |
| original_entry_id | string, optional |
| event_time | timezone-aware timestamp, required |
| settlement_date | date, required |
| record_status | enum, required: POSTED / PENDING / REVERSED |
| gross_amount | decimal(18,2), required; signed amount in transaction currency |
| transaction_currency | char(3), required |
| settlement_currency | char(3), required |
| fx_rate | decimal(18,8), conditional for currency conversion; 1 when same currency under agreed convention |
| gross_settlement_amount | decimal(18,2), required; signed settlement-currency amount |
| fee_amount | decimal(18,2), required; positive deduction, negative fee reversal under this convention |
| net_amount | decimal(18,2), required; gross_settlement_amount - fee_amount |
| source_reference | string, optional |

One row is a financial movement, not necessarily one purchase. Only POSTED affects the balance in the supplied model. A settlement batch is distinct from a payout batch.

### B2. payouts_DATE.csv

| Column | Type / known requirement |
| --- | --- |
| report_id | string, required |
| provider_id | string, required |
| provider_account_id | string, required |
| payout_id | string, required; stable across status snapshots |
| merchant_id | string, required |
| beneficiary_account_id | string, required; internal synthetic reference, not full IBAN |
| currency | char(3), required |
| payout_amount | decimal(18,2), required; positive |
| status | enum, required: SCHEDULED / SENT / FAILED / RETURNED |
| scheduled_at | timestamp, optional |
| sent_at | timestamp, conditional when SENT; dispatch time, not bank deposit time |
| expected_arrival_date | date, optional |
| bank_transfer_reference | string, conditional where available for matching |
| updated_at | timestamp, required |
| failure_code | string, optional |

A row is a payout status snapshot; an updated snapshot does not create a new transfer identity.

### B3. payout_allocations_DATE.csv

| Column | Type / known requirement |
| --- | --- |
| allocation_id | string, required; stable allocation identity |
| provider_id | string, required |
| provider_account_id | string, required |
| payout_id | string, required |
| entry_id | string, required; settlement movement reference |
| merchant_id | string, required |
| currency | char(3), required |
| allocated_net_amount | decimal(18,2), required; signed allocated portion |
| allocation_source | enum, required: PROVIDER / DERIVED |
| created_at | timestamp, required |

The provider may not supply this dataset. DERIVED is a contract value, not permission to implement undocumented allocation inference. A normal preview should use an explicit simple provider-supplied fixture; an unavailable state must be supported.

### B4. bank_statement_ACCOUNT_DATE.csv

| Column | Type / known requirement |
| --- | --- |
| statement_id | string, required |
| bank_id | string, required |
| bank_account_id | string, required; matches beneficiary_account_id where applicable |
| merchant_id | string, required; may be enriched from account ownership |
| bank_entry_id | string, required; stable bank-entry identity |
| booking_date | date, required |
| value_date | date, optional |
| currency | char(3), required |
| credit_amount | decimal(18,2), required; positive credit, zero for debit-only row |
| debit_amount | decimal(18,2), required; positive debit, zero for credit-only row |
| transfer_reference | string, optional |
| description | string, optional |
| counterparty_name | string, optional |
| balance_after | decimal(18,2), optional; reference only, not matching key |

One row is a bank ledger entry, not a payout status message.

### B5. capture_ledger_DATE.csv — internal

| Column | Type / known requirement |
| --- | --- |
| payment_id | string, required |
| order_id | string, required; not sufficient alone as a financial key |
| merchant_id | string, required |
| provider_id | string, required |
| provider_account_id | string, required |
| provider_payment_id | string, required |
| provider_capture_id | string, optional; preferred link when supplied |
| capture_attempt_id | string, required; distinct retry attempt identity |
| capture_status | enum, required: PENDING / SUCCEEDED / FAILED |
| captured_amount | decimal(18,2), conditional; final successful capture amount |
| currency | char(3), required |
| captured_at | timestamp, conditional on successful capture |
| expected_settlement_date | date, conditional; future provider/cutoff/business-day policy |
| updated_at | timestamp, required |

This is an internal source/export. Do not relabel it as a provider statement, derive it live from event history in this UI task, or introduce unsupported status case conversions without an explicit future mapping.
