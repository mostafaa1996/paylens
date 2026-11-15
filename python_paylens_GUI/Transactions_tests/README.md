# Payload generators

All generators use the same argument pattern:

```python
generate_...(template=None, *previous_payloads, cursor=None, merchant=None)
```

The first positional argument is a template for the output event, or `None`.
The argument is named `payload` in Python. Templates and earlier payloads can
be dictionaries or JSON object strings. Return values remain JSON strings.

Non-null template fields win, including `0`, `False`, and empty strings.
Missing/null fields inherit relevant correlation fields from earlier payloads,
passed in dispatch order (oldest first, newest last). Remaining fields use the
existing random ID, timestamp, amount, and database generators. Nested objects
are filled recursively. Inputs are not modified.

Event-specific fields such as event ID, event type, timestamps, status, and
source are generated for the current event rather than copied from a previous
event. Supply those fields in the template to override them. Capture events
map the authorization processor reference into `authorization_reference`, and
capture responses use the expected capture amount when available.

```python
request = generate_auth_request_payload(
    {"requested_amount_minor": 10000}, cursor=cursor, merchant=merchant
)
response = generate_auth_response_payload(
    {"status": "authorized", "payment_id": None}, request, cursor=cursor
)
expected = generate_capture_exp_payload(None, request, response)
captured = generate_capture_res_payload(
    {"captured_amount_minor": None}, request, response, expected
)
```

`cursor` and `merchant` are keyword-only context arguments; callers using the
old positional signatures must update their calls as shown in `main.py`.
Without database context, unavailable merchant IDs, payment tokens and
processor codes remain `null`; no database connection is opened implicitly.
Provide them in templates/previous payloads or pass the database context.
