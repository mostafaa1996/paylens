import json
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, patch

from Transactions_tests.generate_Auth_req import generate_auth_request_payload
from Transactions_tests.generate_Auth_res import generate_auth_response_payload
from Transactions_tests.generate_capture_exp import generate_capture_exp_payload
from Transactions_tests.generate_capture_res import generate_capture_res_payload
from Transactions_tests.generate_order_fulfillment import generate_order_fulfillment_payload


class TransactionPayloadTests(unittest.TestCase):
    def test_full_sequence_keeps_correlations_and_fresh_events(self):
        request = json.loads(generate_auth_request_payload({"merchant_id": 21}))
        response = json.loads(generate_auth_response_payload(None, request))
        expected = json.loads(generate_capture_exp_payload(None, request, response))
        captured = json.loads(generate_capture_res_payload(None, request, response, expected))
        fulfillment = json.loads(generate_order_fulfillment_payload(None, request, response, expected, captured))
        events = [request, response, expected, captured, fulfillment]
        for event in events:
            for key in ("payment_id", "merchant_id", "order_reference"):
                self.assertEqual(event[key], request[key])
        self.assertEqual(len({event["event_id"] for event in events}), 5)
        self.assertEqual(response["authorized_amount_minor"], request["requested_amount_minor"])
        self.assertIsNotNone(response["authorization_code"])
        self.assertEqual(captured["capture_id"], expected["capture_id"])
        self.assertEqual(captured["authorization_reference"], response["processor_reference"])
        self.assertEqual(captured["captured_amount_minor"], expected["expected_amount_minor"])

    def test_template_overrides_nulls_nested_fields_and_falsy_values(self):
        previous = {"payment_id": "old", "merchant_id": 9, "payment_method": {"token": "existing"}}
        template = {
            "payment_id": "custom", "merchant_id": None,
            "requested_amount_minor": 0, "channel": "web", "ip_address": "",
            "payment_method": {"token": None, "type": "custom"},
            "custom": {"enabled": False},
        }
        original = deepcopy(template)
        cursor = Mock()
        result = json.loads(generate_auth_request_payload(template, previous, cursor=cursor))
        self.assertEqual(result["payment_id"], "custom")
        self.assertEqual(result["merchant_id"], 9)
        self.assertEqual(result["requested_amount_minor"], 0)
        self.assertEqual(result["ip_address"], "")
        self.assertEqual(result["payment_method"]["token"], "existing")
        self.assertEqual(result["payment_method"]["type"], "custom")
        self.assertEqual(result["payment_method"]["entry_mode"], "online")
        self.assertIs(result["custom"]["enabled"], False)
        self.assertEqual(template, original)
        cursor.execute.assert_not_called()

    def test_latest_non_null_predecessor_and_amount_aliases(self):
        result = json.loads(generate_capture_res_payload(
            {"payment_id": None, "captured_amount_minor": None},
            {"payment_id": "older", "processor_reference": "auth", "requested_amount_minor": 100},
            None,
            json.dumps({"payment_id": "latest", "capture_id": "capture", "expected_amount_minor": 20, "authorization_reference": "auth"}),
            {"payment_id": None},
        ))
        self.assertEqual(result["payment_id"], "latest")
        self.assertEqual(result["capture_id"], "capture")
        self.assertEqual(result["authorization_reference"], "auth")
        self.assertEqual(result["captured_amount_minor"], 20)

    def test_nested_null_in_latest_predecessor_uses_older_value(self):
        result = json.loads(generate_auth_request_payload(
            {"payment_method": {"token": None}},
            {"payment_method": {"token": "older", "type": "card"}},
            {"payment_method": {"token": None, "type": "latest"}},
        ))
        self.assertEqual(result["payment_method"]["token"], "older")
        self.assertEqual(result["payment_method"]["type"], "latest")
        # Templates may intentionally carry unusual values for negative tests.
        result = json.loads(generate_auth_request_payload({"payment_method": False}))
        self.assertIs(result["payment_method"], False)

    def test_no_predecessors_generates_consistent_defaults(self):
        for generator in (generate_auth_request_payload, generate_auth_response_payload,
                          generate_capture_exp_payload, generate_capture_res_payload,
                          generate_order_fulfillment_payload):
            with self.subTest(generator=generator.__name__):
                event = json.loads(generator(None, None))
                self.assertTrue(event["payment_id"].startswith("pay_"))
                self.assertTrue(event["order_reference"].startswith("ord_"))
                self.assertTrue(event["event_id"].startswith("evt_"))
        with patch("Transactions_tests.generate_Auth_req.generate_payment_id", return_value="one-payment") as generate_id:
            result = json.loads(generate_capture_res_payload())
            self.assertEqual(result["payment_id"], "one-payment")
            generate_id.assert_called_once()

    def test_database_defaults_use_selected_merchant(self):
        cursor = Mock()
        cursor.fetchall.return_value = [SimpleNamespace(customer_id=7)]
        cursor.fetchone.return_value = SimpleNamespace(payment_token="token")
        result = json.loads(generate_auth_request_payload(None, cursor=cursor, merchant=SimpleNamespace(merchant_id=42)))
        self.assertEqual(result["payment_method"]["token"], "token")
        self.assertEqual(cursor.execute.call_args_list[0].args, ("SELECT * FROM customers where merchant_id = ?", 42))

    def test_status_and_nested_decline_defaults(self):
        result = json.loads(generate_auth_response_payload(
            {"status": "declined", "decline": {"reason": "insufficient_funds"}},
            {"status": "requested", "requested_amount_minor": 25}, status="authorized",
        ))
        self.assertEqual(result["status"], "declined")
        self.assertIsNone(result["authorization_code"])
        self.assertIsNone(result["authorized_amount_minor"])
        self.assertEqual(result["decline"], {"reason": "insufficient_funds", "provider_code": None, "provider_reason": None})

    def test_complete_template_avoids_generation_and_database_queries(self):
        template = json.loads(generate_auth_response_payload({"merchant_id": 21, "processor": "processor"}))
        cursor = Mock()
        with patch("Transactions_tests.generate_Auth_res.generate_auth_request_payload", side_effect=AssertionError("Unexpected generation")):
            self.assertEqual(json.loads(generate_auth_response_payload(template, cursor=cursor)), template)
        cursor.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
