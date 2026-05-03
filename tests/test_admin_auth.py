import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from api import admin_auth


class AdminAuthTests(unittest.TestCase):
    def test_extract_bearer_token_accepts_case_insensitive_prefix(self):
        self.assertEqual(
            admin_auth.extract_bearer_token("Bearer super-secret"),
            "super-secret",
        )
        self.assertEqual(
            admin_auth.extract_bearer_token("bearer another-secret"),
            "another-secret",
        )

    def test_extract_bearer_token_rejects_other_schemes(self):
        self.assertIsNone(admin_auth.extract_bearer_token(None))
        self.assertIsNone(admin_auth.extract_bearer_token("Basic abc123"))
        self.assertIsNone(admin_auth.extract_bearer_token("Bearer"))

    def test_resolve_admin_token_prefers_header_then_bearer_then_query(self):
        self.assertEqual(
            admin_auth.resolve_admin_token(
                x_admin_token="header-token",
                authorization="Bearer bearer-token",
                token="query-token",
            ),
            "header-token",
        )
        self.assertEqual(
            admin_auth.resolve_admin_token(
                x_admin_token=None,
                authorization="Bearer bearer-token",
                token="query-token",
            ),
            "bearer-token",
        )
        self.assertEqual(
            admin_auth.resolve_admin_token(
                x_admin_token=None,
                authorization=None,
                token="query-token",
            ),
            "query-token",
        )

    def test_verify_admin_token_requires_configured_secret(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HTTPException) as ctx:
                admin_auth.verify_admin_token("anything")
        self.assertEqual(ctx.exception.status_code, 503)

    def test_verify_admin_token_rejects_invalid_secret(self):
        with patch.dict(os.environ, {"ADMIN_TOKEN": "expected"}, clear=True):
            with self.assertRaises(HTTPException) as ctx:
                admin_auth.verify_admin_token("wrong")
        self.assertEqual(ctx.exception.status_code, 403)

    def test_verify_admin_token_accepts_matching_secret(self):
        with patch.dict(os.environ, {"ADMIN_TOKEN": "expected"}, clear=True):
            admin_auth.verify_admin_token("expected")


if __name__ == "__main__":
    unittest.main()
