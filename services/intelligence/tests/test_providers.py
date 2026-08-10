import unittest

from app.providers import provider_failure


class ProviderContractTests(unittest.TestCase):
    def test_failure_contract_marks_transient_errors_retryable(self) -> None:
        failure = provider_failure("weather", TimeoutError("timed out"))

        self.assertEqual(failure["code"], "upstream_unavailable")
        self.assertTrue(failure["retryable"])
        self.assertEqual(failure["source"], "weather")


if __name__ == "__main__":
    unittest.main()
