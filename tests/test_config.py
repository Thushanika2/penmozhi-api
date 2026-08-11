import unittest
from unittest.mock import patch

from app.config import Config, _build_database_uri


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

    def test_railway_prefers_private_mysql_variables_over_public_db_variables(self):
        env = {
            "DB_USER": "root",
            "DB_PASSWORD": "public-password",
            "DB_HOST": "public.proxy.rlwy.net",
            "DB_PORT": "12345",
            "DB_NAME": "railway",
            "MYSQLUSER": "root",
            "MYSQLPASSWORD": "private-password",
            "MYSQLHOST": "mysql.railway.internal",
            "MYSQLPORT": "3306",
            "MYSQLDATABASE": "railway",
            "RAILWAY_ENVIRONMENT": "production",
        }
        with patch.dict("os.environ", env, clear=True):
            uri = _build_database_uri()

        self.assertIn("@mysql.railway.internal:3306/railway", uri)
        self.assertIn("root:private-password", uri)
        self.assertNotIn("public.proxy.rlwy.net", uri)


if __name__ == "__main__":
    unittest.main()
