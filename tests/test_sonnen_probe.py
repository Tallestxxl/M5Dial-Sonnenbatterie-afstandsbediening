from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import runpy
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PROBE = runpy.run_path(str(ROOT / "scripts" / "sonnen-probe"))


class SonnenProbeTests(unittest.TestCase):
    def test_build_url_adds_scheme_port_and_path_slash(self) -> None:
        build_url = PROBE["build_url"]

        self.assertEqual(
            build_url("192.168.1.50", 8080, "api/v2/status"),
            "http://192.168.1.50:8080/api/v2/status",
        )
        self.assertEqual(
            build_url("http://192.168.1.50:9000", 80, "/api/v2/status"),
            "http://192.168.1.50:9000/api/v2/status",
        )

    def test_summarize_status_prints_known_fields(self) -> None:
        summarize_status = PROBE["summarize_status"]
        out = StringIO()

        with redirect_stdout(out):
            exit_code = summarize_status(
                '{"RSOC":77,"Production_W":1234,"Consumption_W":456,'
                '"GridFeedIn_W":-50,"Pac_total_W":200,'
                '"OperatingMode":"2","Timestamp":"2026-07-01T12:00:00Z"}'
            )

        self.assertEqual(exit_code, 0)
        self.assertIn("soc: 77", out.getvalue())
        self.assertIn("battery_w: 200", out.getvalue())

    def test_summarize_status_prefers_user_soc(self) -> None:
        summarize_status = PROBE["summarize_status"]
        out = StringIO()

        with redirect_stdout(out):
            exit_code = summarize_status('{"USOC":51,"RSOC":55}')

        self.assertEqual(exit_code, 0)
        self.assertIn("soc: 51", out.getvalue())

    def test_make_config_escapes_values_and_keeps_writes_disabled(self) -> None:
        parser = PROBE["make_parser"]()
        render_config = PROBE["render_config"]
        args = parser.parse_args(
            [
                "make-config",
                "--wifi-ssid",
                "TestWifi",
                "--wifi-password",
                'quote"slash\\end',
                "--host",
                "192.168.1.50",
                "--token",
                'tok"en',
            ]
        )

        config = render_config(args)

        self.assertIn('static const char WIFI_PASSWORD[] = "quote\\"slash\\\\end";', config)
        self.assertIn('static const char SONNEN_AUTH_TOKEN[] = "tok\\"en";', config)
        self.assertIn("#define SONNEN_ALLOW_WRITES 0", config)
        self.assertIn("#define SONNEN_WIFI_OFF_AFTER_REQUEST 1", config)
        self.assertIn("#define SONNEN_MAX_SETPOINT_W 3600", config)
        self.assertIn("#define SONNEN_SETPOINT_STEP_W 100", config)
        self.assertIn("#define SONNEN_ACTIVE_REFRESH_MS 10000", config)
        self.assertIn("#define SONNEN_IDLE_REFRESH_MS 60000", config)
        self.assertIn("#define SONNEN_ERROR_REFRESH_MS 20000", config)
        self.assertIn("#define SONNEN_ACTIVE_POWER_THRESHOLD_W 100", config)

    def test_make_config_refuses_to_overwrite_without_force(self) -> None:
        parser = PROBE["make_parser"]()
        run_make_config = PROBE["run_make_config"]

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "config.h"
            output.write_text("existing", encoding="utf-8")
            args = parser.parse_args(
                [
                    "make-config",
                    "--output",
                    str(output),
                    "--wifi-ssid",
                    "TestWifi",
                    "--wifi-password",
                    "pw",
                    "--host",
                    "192.168.1.50",
                ]
            )

            err = StringIO()
            with redirect_stderr(err):
                exit_code = run_make_config(args)

            self.assertEqual(exit_code, 2)
            self.assertEqual(output.read_text(encoding="utf-8"), "existing")
            self.assertIn("Refusing to overwrite", err.getvalue())

    def test_non_get_request_requires_explicit_write_confirmation(self) -> None:
        parser = PROBE["make_parser"]()
        run_request = PROBE["run_request"]
        args = parser.parse_args(
            [
                "request",
                "--host",
                "127.0.0.1",
                "--path",
                "/api/v2/configurations",
                "--method",
                "PUT",
                "--body",
                "{}",
            ]
        )

        err = StringIO()
        with redirect_stderr(err):
            exit_code = run_request(args)

        self.assertEqual(exit_code, 2)
        self.assertIn("Refusing non-GET request", err.getvalue())


if __name__ == "__main__":
    unittest.main()
