import unittest

from scripts import set_api_key_expiry


class SetApiKeyExpiryTests(unittest.TestCase):
    def test_resolve_expiry_adds_days_to_now(self):
        self.assertEqual(
            set_api_key_expiry.resolve_expiry(now=1_000_000.0, days=14),
            1_000_000.0 + 14 * 24 * 60 * 60,
        )

    def test_mask_key_does_not_expose_full_key(self):
        masked = set_api_key_expiry.mask_key("al_abcdefghijklmnopqrstuvwxyz")

        self.assertEqual(masked, "al_abc...wxyz")
        self.assertNotIn("defghijklmnopqrstuv", masked)


if __name__ == "__main__":
    unittest.main()
