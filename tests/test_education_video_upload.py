import os
import tempfile
import unittest

import cloudinary.utils
from cloudinary.exceptions import AuthorizationRequired
from flask_jwt_extended import create_access_token

TEST_JWT_SECRET = "test-only-video-upload-secret-with-32-characters"
TEST_CLOUDINARY_SECRET = "test-cloudinary-secret"
os.environ.setdefault("JWT_SECRET_KEY", TEST_JWT_SECRET)

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.education_video_model import EducationVideo
from app.models.user_profile_model import UserProfile
from app.services.cloudinary_service import (
    EDUCATION_VIDEO_FOLDER,
    classify_cloudinary_upload_error,
)


class EducationVideoUploadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        database_path = os.path.join(cls.temp_dir.name, "education-video.sqlite")
        Config.SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path}"
        Config.SQLALCHEMY_ENGINE_OPTIONS = {}
        Config.JWT_SECRET_KEY = TEST_JWT_SECRET
        Config.ENABLE_SCHEDULER = False
        Config.CLOUDINARY_CLOUD_NAME = "test-cloud"
        Config.CLOUDINARY_API_KEY = "test-key"
        Config.CLOUDINARY_API_SECRET = TEST_CLOUDINARY_SECRET

        cls.app = create_app()
        cls.app.config.update(TESTING=True)
        with cls.app.app_context():
            db.create_all()
            admin = UserProfile(
                full_name="Upload Admin",
                email="upload-admin@test.invalid",
                role="admin",
                status="active",
                onboarding_completed=True,
            )
            admin.set_password("test-password")
            db.session.add(admin)
            db.session.commit()
            cls.admin_id = admin.id
            cls.token = create_access_token(identity=str(admin.id))

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        cls.temp_dir.cleanup()

    @property
    def auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def test_signature_endpoint_never_returns_api_secret(self):
        with self.app.test_client() as client:
            response = client.post(
                "/admin/education/videos/upload-signature",
                headers=self.auth_headers,
            )

        self.assertEqual(response.status_code, 200)
        upload = response.get_json()["upload"]
        self.assertEqual(upload["cloud_name"], "test-cloud")
        self.assertEqual(upload["api_key"], "test-key")
        self.assertEqual(upload["folder"], EDUCATION_VIDEO_FOLDER)
        self.assertTrue(upload["signature"])
        self.assertNotIn("api_secret", upload)
        self.assertNotIn(TEST_CLOUDINARY_SECRET, response.get_data(as_text=True))

    def test_signed_direct_upload_result_creates_video_record(self):
        public_id = f"{EDUCATION_VIDEO_FOLDER}/verified-test-video"
        version = 1234567890
        response_signature = cloudinary.utils.api_sign_request(
            {"public_id": public_id, "version": version},
            TEST_CLOUDINARY_SECRET,
        )
        payload = {
            "title": "Verified video",
            "description": "Created from a signed direct upload response",
            "category": "Cycle Health",
            "upload": {
                "bytes": 1024,
                "public_id": public_id,
                "resource_type": "video",
                "secure_url": (
                    "https://res.cloudinary.com/test-cloud/video/upload/"
                    f"v{version}/{public_id}.mp4"
                ),
                "signature": response_signature,
                "version": version,
            },
        }

        with self.app.test_client() as client:
            response = client.post(
                "/admin/education/videos",
                headers=self.auth_headers,
                json=payload,
            )

        self.assertEqual(response.status_code, 201)
        body = response.get_json()
        self.assertEqual(body["education_video"]["video_public_id"], public_id)
        with self.app.app_context():
            record = EducationVideo.query.filter_by(video_public_id=public_id).one()
            self.assertEqual(record.created_by_admin_id, self.admin_id)

    def test_tampered_direct_upload_result_is_rejected(self):
        payload = {
            "title": "Tampered video",
            "category": "Cycle Health",
            "upload": {
                "bytes": 1024,
                "public_id": f"{EDUCATION_VIDEO_FOLDER}/tampered",
                "resource_type": "video",
                "secure_url": "https://res.cloudinary.com/test-cloud/video/upload/tampered.mp4",
                "signature": "not-a-valid-signature",
                "version": 123,
            },
        }

        with self.app.test_client() as client:
            response = client.post(
                "/admin/education/videos",
                headers=self.auth_headers,
                json=payload,
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["error_code"],
            "education.video_invalid_response",
        )

    def test_cloudinary_auth_failure_has_specific_safe_error(self):
        code, message, status = classify_cloudinary_upload_error(
            AuthorizationRequired("invalid credentials")
        )
        self.assertEqual(code, "education.cloudinary_auth_failed")
        self.assertEqual(status, 502)
        self.assertIn("Railway", message)

    def test_request_too_large_is_json_413(self):
        previous_limit = self.app.config["MAX_CONTENT_LENGTH"]
        self.app.config["MAX_CONTENT_LENGTH"] = 128
        try:
            with self.app.test_client() as client:
                response = client.post(
                    "/admin/education/videos",
                    headers=self.auth_headers,
                    json={"padding": "x" * 1000},
                )
        finally:
            self.app.config["MAX_CONTENT_LENGTH"] = previous_limit

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(response.get_json()["error_code"], "validation.video_too_large")


if __name__ == "__main__":
    unittest.main()
