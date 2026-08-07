import unittest

from app.config import Config


class ConfigTest(unittest.TestCase):
    def test_runtime_jwt_secret_meets_minimum_length(self):
        self.assertGreaterEqual(len(Config.JWT_SECRET_KEY), 32)

    def test_short_explicit_jwt_secret_is_rejected(self):
        original_secret = Config.JWT_SECRET_KEY
        original_configured_secret = Config._CONFIGURED_JWT_SECRET_KEY
        try:
            Config._CONFIGURED_JWT_SECRET_KEY = "too-short"
            Config.JWT_SECRET_KEY = "too-short"
            with self.assertRaisesRegex(RuntimeError, "at least 16 characters"):
                Config.validate()
        finally:
            Config._CONFIGURED_JWT_SECRET_KEY = original_configured_secret
            Config.JWT_SECRET_KEY = original_secret


if __name__ == "__main__":
    unittest.main()
