import logging
import os

from flask_cors import CORS

from app import create_app
from app.config import Config

app = create_app()

_cors_origins = Config.CORS_ORIGINS
if _cors_origins and _cors_origins != "*":
    _cors_origins = [origin.strip() for origin in _cors_origins.split(",") if origin.strip()]

CORS(
    app,
    origins=_cors_origins,
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", 5000)))
