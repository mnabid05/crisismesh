import unittest
from unittest.mock import MagicMock, patch

from app.providers import fetch_provider_json, provider_failure


class ProviderContractTests(unittest.TestCase):
    def test_failure_contract_marks_transient_errors_retryable(self) -> None:
        failure = provider_failure("weather", TimeoutError("timed out"))

        self.assertEqual(failure["code"], "upstream_unavailable")
        self.assertTrue(failure["retryable"])
        self.assertEqual(failure["source"], "weather")

    @patch("app.providers.time.sleep")
    @patch("app.providers.urlopen")
    def test_fetch_retries_a_transient_failure(self, urlopen: MagicMock, sleep: MagicMock) -> None:
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"ok": true}'
        urlopen.side_effect = [TimeoutError("slow"), response]

        payload = fetch_provider_json("https://example.test", source="test", timeout=1)

        self.assertEqual(payload, {"ok": True})
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once()


if __name__ == "__main__":
    unittest.main()
