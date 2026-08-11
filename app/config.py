from datetime import timedelta
import hashlib
import os
import re
import secrets
from urllib.parse import quote_plus, urlparse, urlunparse, parse_qsl, urlencode

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


def _ensure_pymysql_charset(url):
    """Ensure utf8mb4 charset is set for MySQL URLs."""
    if not url or "charset=" in url:
        return url
    if "mysql" not in url.split("://", 1)[0]:
        return url
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.setdefault("charset", "utf8mb4")
    return urlunparse(parsed._replace(query=urlencode(query)))


def _normalize_database_url(url):
    if not url:
        return None

    url = _fix_double_port_url(url.strip())
    if url.startswith("mysql://"):
        url = url.replace("mysql://", "mysql+pymysql://", 1)
    elif url.startswith("mysql2://"):
        url = url.replace("mysql2://", "mysql+pymysql://", 1)

    return _ensure_pymysql_charset(url)


def _is_private_mysql_host(host: str | None) -> bool:
    if not host:
        return False
    hostname = host.strip().lower().split(":")[0]
    return (
        hostname.endswith(".railway.internal")
        or hostname.endswith(".rlwy.internal")
        or hostname in {"mysql", "mysql.railway.internal"}
    )


def _from_discrete_vars(prefer_mysql=False):
    if prefer_mysql:
        db_user = os.getenv("MYSQLUSER") or os.getenv("DB_USER")
        db_password = os.getenv("MYSQLPASSWORD") or os.getenv("DB_PASSWORD")
        db_host = os.getenv("MYSQLHOST") or os.getenv("DB_HOST")
        db_port = os.getenv("MYSQLPORT") or os.getenv("DB_PORT") or "3306"
        db_name = os.getenv("MYSQLDATABASE") or os.getenv("DB_NAME")
    else:
        db_user = os.getenv("DB_USER") or os.getenv("MYSQLUSER")
        db_password = os.getenv("DB_PASSWORD") or os.getenv("MYSQLPASSWORD")
        db_host = os.getenv("DB_HOST") or os.getenv("MYSQLHOST")
        db_port = os.getenv("DB_PORT") or os.getenv("MYSQLPORT") or "3306"
        db_name = os.getenv("DB_NAME") or os.getenv("MYSQLDATABASE")

    if not all([db_user, db_password, db_host, db_name]):
        return None

    hostname, port = _split_host_port(db_host, db_port)
    return _ensure_pymysql_charset(
        f"mysql+pymysql://{quote_plus(db_user)}:{quote_plus(db_password)}"
        f"@{hostname}:{port}/{db_name}"
    )


def _build_database_uri():
    """
    Build SQLAlchemy URI with Railway-safe preference order:
    1. Private discrete MYSQL* / DB_* vars when on Railway (internal network)
    2. DATABASE_URL / MYSQL_URL
    3. Remaining discrete vars
    4. MYSQL_PUBLIC_URL (TCP proxy — last resort)
    """
    on_railway = bool(
        os.getenv("RAILWAY_ENVIRONMENT")
        or os.getenv("RAILWAY_SERVICE_NAME")
        or os.getenv("RAILWAY_PROJECT_ID")
    )
    private_discrete = _from_discrete_vars(prefer_mysql=True)
    private_host = os.getenv("MYSQLHOST")
    if private_discrete and _is_private_mysql_host(private_host):
        return private_discrete

    discrete = _from_discrete_vars()
    host = os.getenv("DB_HOST") or private_host

    if on_railway and discrete and _is_private_mysql_host(host):
        return discrete

    for key in ("DATABASE_URL", "MYSQL_URL"):
        value = os.getenv(key)
        if value:
            return _normalize_database_url(value)

    if discrete:
        return discrete

    public_url = os.getenv("MYSQL_PUBLIC_URL")
    if public_url:
        return _normalize_database_url(public_url)

    return None


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
        "pool_size": 5,
        "max_overflow": 10,
    }

    _CONFIGURED_JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_SECRET_KEY_IS_EPHEMERAL = not bool(_CONFIGURED_JWT_SECRET_KEY)
    JWT_SECRET_KEY_WAS_DERIVED = bool(_CONFIGURED_JWT_SECRET_KEY) and len(
        _CONFIGURED_JWT_SECRET_KEY
    ) < 32
    # A random process-local fallback keeps a misconfigured deployment secure and
    # available. Configure JWT_SECRET_KEY in production so sessions survive restarts.
    if JWT_SECRET_KEY_WAS_DERIVED:
        JWT_SECRET_KEY = hashlib.sha256(
            b"penmozhi-jwt-v1\0" + _CONFIGURED_JWT_SECRET_KEY.encode("utf-8")
        ).hexdigest()
    else:
        JWT_SECRET_KEY = _CONFIGURED_JWT_SECRET_KEY or secrets.token_urlsafe(48)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "1440"))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES_DAYS", "30"))
    )

    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")
    ADMIN_NAME = os.getenv("ADMIN_NAME")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

    CLIENT_APP_URL = os.getenv("CLIENT_APP_URL", "http://localhost:3000")
    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    SMTP_FROM = os.getenv("SMTP_FROM")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
    BREVO_API_KEY = os.getenv("BREVO_API_KEY")
    BREVO_FROM_EMAIL = os.getenv("BREVO_FROM_EMAIL")
    BREVO_FROM_NAME = os.getenv("BREVO_FROM_NAME", "Penmozhi")

    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    # Prefer flash-lite — gemini-flash-latest maps to gemini-3.6-flash with a tiny free-tier cap.
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
    AI_PROVIDER = os.getenv("AI_PROVIDER", "auto")

    VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
    VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")
    VAPID_CLAIMS_EMAIL = os.getenv("VAPID_CLAIMS_EMAIL", "mailto:admin@penmozhi.com")

    ENABLE_SCHEDULER = os.getenv("ENABLE_SCHEDULER", "false").lower() in ("true", "1", "yes")

    CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
    # Keep transport overhead outside the 200 MB video-file allowance. Direct
    # browser-to-Cloudinary uploads normally send only small JSON requests here,
    # while this limit protects the legacy multipart endpoint.
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(210 * 1024 * 1024)))

    @staticmethod
    def validate():
        if (
            Config._CONFIGURED_JWT_SECRET_KEY
            and len(Config._CONFIGURED_JWT_SECRET_KEY) < 16
        ):
            raise RuntimeError(
                "JWT_SECRET_KEY must be configured with at least 16 characters."
            )
        if len(Config.JWT_SECRET_KEY) < 32:
            raise RuntimeError("Effective JWT signing key must be at least 32 characters.")

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
