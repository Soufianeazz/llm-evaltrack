import time
import unittest
from types import SimpleNamespace

from api.auth import is_api_key_expired
from api.routes import admin


class ApiKeyExpiryTests(unittest.TestCase):
    def test_api_key_without_expiry_is_not_expired(self):
        key = SimpleNamespace(expires_at=None)

        self.assertFalse(is_api_key_expired(key, now=1_000_000.0))

    def test_api_key_with_future_expiry_is_not_expired(self):
        key = SimpleNamespace(expires_at=1_000_100.0)

        self.assertFalse(is_api_key_expired(key, now=1_000_000.0))

    def test_api_key_with_past_expiry_is_expired(self):
        key = SimpleNamespace(expires_at=999_999.0)

        self.assertTrue(is_api_key_expired(key, now=1_000_000.0))

    def test_pilot_expiry_defaults_to_14_days(self):
        now = 1_000_000.0

        self.assertEqual(
            admin.resolve_key_expiry(plan="pilot", trial_days=None, expires_at=None, now=now),
            now + 14 * 24 * 60 * 60,
        )

    def test_explicit_expiry_overrides_pilot_default(self):
        now = time.time()
        explicit = now + 3 * 24 * 60 * 60

        self.assertEqual(
            admin.resolve_key_expiry(plan="pilot", trial_days=None, expires_at=explicit, now=now),
            explicit,
        )

    def test_non_pilot_key_without_trial_has_no_expiry(self):
        self.assertIsNone(
            admin.resolve_key_expiry(plan="team", trial_days=None, expires_at=None, now=1_000_000.0)
        )

    def test_expiry_days_must_be_positive(self):
        with self.assertRaises(ValueError):
            admin.resolve_key_expiry(plan="pilot", trial_days=0, expires_at=None, now=1_000_000.0)


if __name__ == "__main__":
    unittest.main()
