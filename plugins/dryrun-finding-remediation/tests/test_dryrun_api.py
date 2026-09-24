import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch
import urllib.error


SCRIPT = Path(__file__).resolve().parents[1] / "skills/dryrun-finding-remediation/scripts/dryrun_api.py"
SPEC = importlib.util.spec_from_file_location("dryrun_api", SCRIPT)
api = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(api)
ACCOUNT = "22222222-2222-4222-8222-222222222222"
FINDING = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


class FindingCommandTests(unittest.TestCase):
    def run_cli(self, arguments):
        output = io.StringIO()
        with patch.object(sys, "argv", [str(SCRIPT), *arguments]), contextlib.redirect_stdout(output):
            api.main()
        return json.loads(output.getvalue())

    def test_exact_lookup_normalizes_uuid_and_preserves_nulls(self):
        payload = {"data": {"id": FINDING, "finding_type": "sca", "branch": None,
                            "package_version": None, "version_occurrences": [
                                {"package_version": "1.0", "locations": None},
                                {"package_version": "2.0", "locations": []}]}}
        with patch.object(api, "make_request", return_value=payload) as request:
            actual = self.run_cli(["get-finding", "--account-id", ACCOUNT,
                                   "--finding-id", FINDING.upper()])
        self.assertEqual(actual, payload)
        request.assert_called_once_with(f"/v1/accounts/{ACCOUNT}/findings/{FINDING}", None)

    def test_supported_type_filters(self):
        for finding_type in ("pullrequest", "deepscan", "sca"):
            with self.subTest(finding_type=finding_type), patch.object(api, "make_request", return_value={"data": {}}) as request:
                self.run_cli(["get-finding", "--account-id", ACCOUNT,
                              "--finding-id", FINDING, "--finding-type", finding_type])
                request.assert_called_once_with(f"/v1/accounts/{ACCOUNT}/findings/{FINDING}",
                                                {"finding_type": finding_type})

    def test_invalid_ids_are_rejected_without_network(self):
        for flag in ("--account-id", "--finding-id"):
            for invalid in ("not-a-uuid", "../accounts", FINDING.replace("-", ""), "{" + FINDING + "}"):
                args = ["get-finding", "--account-id", ACCOUNT, "--finding-id", FINDING]
                args[args.index(flag) + 1] = invalid
                with self.subTest(flag=flag, invalid=invalid), patch.object(api, "make_request") as request:
                    with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                        self.run_cli(args)
                    self.assertEqual(error.exception.code, 2)
                    request.assert_not_called()

    def test_invalid_types_are_rejected_without_network(self):
        for invalid in ("pr", "all", "code_policy", "", "SCA"):
            with self.subTest(finding_type=invalid), patch.object(api, "make_request") as request:
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                    self.run_cli(["get-finding", "--account-id", ACCOUNT,
                                  "--finding-id", FINDING, "--finding-type", invalid])
                self.assertEqual(error.exception.code, 2)
                request.assert_not_called()

    def test_existing_commands_keep_their_routes(self):
        cases = [
            (["list-accounts"], "/v1/accounts", {"data": []}),
            (["list-repos", "--account-id", ACCOUNT], f"/v1/accounts/{ACCOUNT}/repositories", {"data": []}),
            (["list-scans", "--account-id", ACCOUNT, "--repo-id", "repo"],
             f"/v1/accounts/{ACCOUNT}/repositories/repo/scans", {"data": []}),
            (["get-scan", "--account-id", ACCOUNT, "--repo-id", "repo", "--scan-id", "scan"],
             f"/v1/accounts/{ACCOUNT}/repositories/repo/scans/scan", {"findings": []}),
            (["list-deepscans", "--account-id", ACCOUNT, "--repo-id", "repo"],
             f"/v1/accounts/{ACCOUNT}/repositories/repo/deepscans", {"data": [{"id": "scan"}]}),
            (["get-deepscan-results", "--account-id", ACCOUNT, "--repo-id", "repo", "--deepscan-id", "scan"],
             f"/v1/accounts/{ACCOUNT}/repositories/repo/deepscans/scan/results", {"data": []}),
            (["get-sca-results", "--account-id", ACCOUNT, "--repo-id", "repo", "--deepscan-id", "scan"],
             f"/v1/accounts/{ACCOUNT}/repositories/repo/deepscans/scan/sca_results", {"data": []}),
        ]
        for arguments, expected_path, payload in cases:
            with self.subTest(command=arguments[0]), patch.object(api, "make_request", return_value=payload) as request:
                self.run_cli(arguments)
                self.assertEqual(request.call_args.args[0], expected_path)


class RequestTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {"DRYRUN_API_KEY": "test-key"}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_default_and_overridden_origins(self):
        for base in (None, "https://simple-api.sb.dryrun.security", "https://simple-api.sb.dryrun.security/"):
            with self.subTest(base=base):
                if base is None:
                    os.environ.pop("DRYRUN_API_BASE_URL", None)
                else:
                    os.environ["DRYRUN_API_BASE_URL"] = base
                response = MagicMock()
                response.__enter__.return_value.read.return_value = b'{"data": {"branch": null}}'
                with patch.object(api.urllib.request, "build_opener") as build:
                    build.return_value.open.return_value = response
                    result = api.make_request("/v1/accounts", {"finding_type": "sca"})
                self.assertEqual(result, {"data": {"branch": None}})
                request = build.return_value.open.call_args.args[0]
                self.assertEqual(request.full_url,
                                 (base or api.BASE_URL).rstrip("/") + "/v1/accounts?finding_type=sca")
                self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
                self.assertEqual(build.return_value.open.call_args.kwargs, {"timeout": 30})
                self.assertIsInstance(build.call_args.args[0], api.NoRedirect)

    def test_unsafe_origins_are_rejected_before_network(self):
        for base in ("", "http://simple-api.sb.dryrun.security", "https://user:pass@example.com",
                     "https://example.com/v1", "https://example.com?token=x", "https://example.com#fragment",
                     "https://", "https://example.com:invalid", "https://example.com\n",
                     "https://example.com?", "https://example.com#", "\x01https://example.com",
                     "https://example.com\x7f", "https://example.com\\other"):
            with self.subTest(base=base), patch.dict(os.environ, {"DRYRUN_API_BASE_URL": base}):
                with patch.object(api.urllib.request, "build_opener") as build, contextlib.redirect_stdout(io.StringIO()) as output:
                    with self.assertRaises(SystemExit) as error:
                        api.make_request("/v1/accounts")
                    self.assertEqual(error.exception.code, 1)
                    self.assertIn("HTTPS origin", json.loads(output.getvalue())["error"])
                    build.assert_not_called()

    def test_missing_key_is_rejected(self):
        os.environ.pop("DRYRUN_API_KEY")
        with patch.object(api.urllib.request, "build_opener") as build, contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit) as error:
                api.make_request("/v1/accounts")
            self.assertEqual(error.exception.code, 1)
            self.assertIn("DRYRUN_API_KEY", json.loads(output.getvalue())["error"])
            build.assert_not_called()

    def test_http_errors_preserve_status_and_body(self):
        for status in (400, 401, 403, 404, 409, 500):
            with self.subTest(status=status):
                error = urllib.error.HTTPError("https://example.com", status, "failure", {},
                                               io.BytesIO(b'{"error": "server error"}'))
                with patch.object(api.urllib.request, "build_opener") as build, contextlib.redirect_stdout(io.StringIO()) as output:
                    build.return_value.open.side_effect = error
                    with self.assertRaises(SystemExit) as exit_error:
                        api.make_request(f"/v1/accounts/{ACCOUNT}/findings/{FINDING}")
                self.assertEqual(exit_error.exception.code, 1)
                result = json.loads(output.getvalue())
                self.assertEqual(result["status_code"], status)
                self.assertEqual(result["response_body"], {"error": "server error"})
                if status == 404:
                    self.assertIn("finding_id", result["message"])
                if status == 409:
                    self.assertIn("--finding-type", result["message"])
                self.assertNotIn("test-key", output.getvalue())

    def test_non_json_http_errors(self):
        error = urllib.error.HTTPError("https://example.com", 502, "failure", {}, io.BytesIO(b"upstream failure"))
        with patch.object(api.urllib.request, "build_opener") as build, contextlib.redirect_stdout(io.StringIO()) as output:
            build.return_value.open.side_effect = error
            with self.assertRaises(SystemExit):
                api.make_request("/v1/accounts")
        self.assertEqual(json.loads(output.getvalue())["response_body"], "upstream failure")

    def test_connection_errors(self):
        for error in (urllib.error.URLError("unavailable"), TimeoutError("timed out")):
            with self.subTest(error=error), patch.object(api.urllib.request, "build_opener") as build:
                build.return_value.open.side_effect = error
                with contextlib.redirect_stdout(io.StringIO()) as output, self.assertRaises(SystemExit):
                    api.make_request("/v1/accounts")
                self.assertEqual(json.loads(output.getvalue())["error"], "Connection error")

    def test_redirects_are_not_followed(self):
        self.assertIsNone(api.NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://other.example"))


if __name__ == "__main__":
    unittest.main()
