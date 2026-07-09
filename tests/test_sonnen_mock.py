from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import json
import runpy
import unittest


ROOT = Path(__file__).resolve().parents[1]
MOCK = runpy.run_path(str(ROOT / "scripts" / "sonnen-mock"))
PROBE = runpy.run_path(str(ROOT / "scripts" / "sonnen-probe"))


class SonnenMockTests(unittest.TestCase):
    def test_status_endpoint_matches_probe_fields(self) -> None:
        state = MOCK["MockState"]()
        handle_mock_request = MOCK["handle_mock_request"]
        summarize_status = PROBE["summarize_status"]
        status, payload = handle_mock_request(state, "GET", "/api/v2/status", "")

        out = StringIO()
        with redirect_stdout(out):
            exit_code = summarize_status(json.dumps(payload))

        self.assertEqual(status, 200)
        self.assertEqual(exit_code, 0)
        text = out.getvalue()
        self.assertIn("soc:", text)
        self.assertIn("production_w:", text)
        self.assertIn("battery_w:", text)

    def test_write_endpoint_is_locked_by_default(self) -> None:
        state = MOCK["MockState"]()
        handle_mock_request = MOCK["handle_mock_request"]

        status, payload = handle_mock_request(
            state, "PUT", "/api/v2/configurations", '{"EM_OperatingMode":"1"}'
        )

        self.assertEqual(status, 423)
        self.assertEqual(payload["error"], "writes_locked")
        self.assertEqual(state.request_log[-1][0], "PUT")

    def test_write_endpoint_can_be_enabled_for_dry_run(self) -> None:
        state = MOCK["MockState"](allow_writes=True)
        handle_mock_request = MOCK["handle_mock_request"]
        status, payload = handle_mock_request(state, "POST", "/api/v2/setpoint/charge/500", "")

        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["path"], "/api/v2/setpoint/charge/500")


if __name__ == "__main__":
    unittest.main()
