from datetime import timedelta
import os
import re
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


def _split_host_port(host, default_port="3306"):
    host = (host or "").strip()
    if not host:
        return host, default_port

    if host.startswith("["):
        closing = host.find("]")
        if closing != -1:
            hostname = host[: closing + 1]
            remainder = host[closing + 1 :]
            if remainder.startswith(":") and remainder[1:].isdigit():
                return hostname, remainder[1:]
            return hostname, default_port

    if host.count(":") == 1:
        hostname, port = host.rsplit(":", 1)
        if port.isdigit():
            return hostname, port

    return host, default_port


def _fix_double_port_url(url):
    return re.sub(r"(@[^/@]+:\d+):(\d+)(?=/|$)", r"\1", url, count=1)


def _normalize_database_url(url):
    if not url:
        return None

    url = _fix_double_port_url(url.strip())
    if url.startswith("mysql://"):
        url = url.replace("mysql://", "mysql+pymysql://", 1)
    elif url.startswith("mysql2://"):
        url = url.replace("mysql2://", "mysql+pymysql://", 1)

    return url


def _build_database_uri():
    database_url = (
        os.getenv("DATABASE_URL")
        or os.getenv("MYSQL_URL")
        or os.getenv("MYSQL_PUBLIC_URL")
    )
    if database_url:
        return _normalize_database_url(database_url)

    db_user = os.getenv("DB_USER") or os.getenv("MYSQLUSER")
    db_password = os.getenv("DB_PASSWORD") or os.getenv("MYSQLPASSWORD")
    db_host = os.getenv("DB_HOST") or os.getenv("MYSQLHOST")
    db_port = os.getenv("DB_PORT") or os.getenv("MYSQLPORT") or "3306"
    db_name = os.getenv("DB_NAME") or os.getenv("MYSQLDATABASE")

    if not all([db_user, db_password, db_host, db_name]):
        return None

    hostname, port = _split_host_port(db_host, db_port)

    return (
        f"mysql+pymysql://{quote_plus(db_user)}:{quote_plus(db_password)}"
        f"@{hostname}:{port}/{db_name}"
    )


class Config:
    DB_USER = os.getenv("DB_USER") or os.getenv("MYSQLUSER")
    DB_PASSWORD = os.getenv("DB_PASSWORD") or os.getenv("MYSQLPASSWORD")
    DB_HOST = os.getenv("DB_HOST") or os.getenv("MYSQLHOST")
    DB_PORT = os.getenv("DB_PORT") or os.getenv("MYSQLPORT") or "3306"
    DB_NAME = os.getenv("DB_NAME") or os.getenv("MYSQLDATABASE")

    SQLALCHEMY_DATABASE_URI = _build_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-key-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "1440"))
    )

    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

    @staticmethod
    def validate():
        if not Config.SQLALCHEMY_DATABASE_URI:
            raise RuntimeError(
                "Database is not configured. Link a Railway MySQL service or set "
                "DB_USER, DB_PASSWORD, DB_HOST, DB_NAME (or MYSQLUSER, MYSQLPASSWORD, "
                "MYSQLHOST, MYSQLPORT, MYSQLDATABASE / MYSQL_URL)."
            )

        try:
            from sqlalchemy.engine import make_url

            make_url(Config.SQLALCHEMY_DATABASE_URI)
        except ValueError as exc:
            raise RuntimeError(
                f"Invalid database URL: {exc}. Check DB_HOST/MYSQLHOST does not "
                "already include a port if MYSQLPORT is also set."
            ) from exc
