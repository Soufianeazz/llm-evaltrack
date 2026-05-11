import unittest

from scripts import set_api_key_expiry_remote


class SetApiKeyExpiryRemoteTests(unittest.TestCase):
    def test_payload_uses_trial_days(self):
        self.assertEqual(set_api_key_expiry_remote.build_payload(days=14, expires_at=None), {"trial_days": 14})

    def test_payload_rejects_non_positive_days(self):
        with self.assertRaises(ValueError):
            set_api_key_expiry_remote.build_payload(days=0, expires_at=None)

    def test_explicit_expires_at_overrides_days(self):
        self.assertEqual(
            set_api_key_expiry_remote.build_payload(days=14, expires_at=1_779_750_000.0),
            {"expires_at": 1_779_750_000.0},
        )


if __name__ == "__main__":
    unittest.main()
