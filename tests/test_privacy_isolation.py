import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time

TEST_JWT_SECRET = "test-only-secret-key-with-at-least-32-characters"
os.environ.setdefault("JWT_SECRET_KEY", TEST_JWT_SECRET)

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.health_profile_model import HealthProfile
from app.models.medication_supplement_reminder_model import MedicationSupplementReminder
from app.models.symptom_tracking_log_model import SymptomTrackingLog
from app.models.user_profile_model import UserProfile


class PrivacyIsolationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        database_path = os.path.join(cls.temp_dir.name, "privacy-isolation.sqlite")
        Config.SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path}"
        Config.SQLALCHEMY_ENGINE_OPTIONS = {}
        Config.JWT_SECRET_KEY = TEST_JWT_SECRET
        Config.ENABLE_SCHEDULER = False

        cls.app = create_app()
        cls.app.config.update(TESTING=True)

        with cls.app.app_context():
            db.create_all()
            cls.user_ids = {}
            for marker in ("alpha", "beta"):
                user = UserProfile(
                    full_name=f"{marker.title()} User",
                    email=f"{marker}@privacy.test",
                    role="user",
                    status="active",
                    onboarding_completed=True,
                )
                user.set_password(f"{marker}-password")
                db.session.add(user)
                db.session.flush()
                cls.user_ids[marker] = user.id
                db.session.add(HealthProfile(profile_id=user.id))
                db.session.add(
                    SymptomTrackingLog(
                        profile_id=user.id,
                        date_time=datetime.now(),
                        category=f"{marker}-only-symptom",
                        pain_severity=1,
                    )
                )
                db.session.add(
                    MedicationSupplementReminder(
                        profile_id=user.id,
                        item_name=f"{marker}-only-reminder",
                        reminder_type="medication",
                        scheduled_time=time(9, 0),
                    )
                )
            db.session.commit()

        cls.tokens = {}
        with cls.app.test_client() as client:
            for marker in ("alpha", "beta"):
                response = client.post(
                    "/api/auth/login",
                    json={
                        "email": f"{marker}@privacy.test",
                        "password": f"{marker}-password",
                    },
                )
                cls.tokens[marker] = response.get_json()["access_token"]

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        cls.temp_dir.cleanup()

    def _request_summary(self, marker):
        with self.app.test_client() as client:
            response = client.get(
                "/api/dashboard/summary",
                headers={"Authorization": f"Bearer {self.tokens[marker]}"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.headers["Cache-Control"],
                "private, no-store, no-cache, max-age=0, must-revalidate",
            )
            self.assertIn("Authorization", response.headers["Vary"])
            return response.get_json()

    def test_two_accounts_never_receive_each_others_dashboard_data(self):
        requests = ["alpha", "beta"] * 25
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(self._request_summary, requests))

        for marker, payload in zip(requests, results):
            other = "beta" if marker == "alpha" else "alpha"
            serialized = str(payload)
            self.assertIn(f"{marker}-only-symptom", serialized)
            self.assertIn(f"{marker}-only-reminder", serialized)
            self.assertNotIn(f"{other}-only-symptom", serialized)
            self.assertNotIn(f"{other}-only-reminder", serialized)

    def test_fresh_unauthenticated_client_cannot_read_dashboard(self):
        with self.app.test_client() as client:
            response = client.get("/api/dashboard/summary")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.headers["Cache-Control"],
            "private, no-store, no-cache, max-age=0, must-revalidate",
        )


if __name__ == "__main__":
    unittest.main()
