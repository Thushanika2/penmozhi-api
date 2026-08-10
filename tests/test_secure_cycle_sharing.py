import os
import tempfile
import unittest
from datetime import date, timedelta

os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-key-with-at-least-32-characters")
TEST_JWT_SECRET = "test-only-secret-key-with-at-least-32-characters"

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.cycle_history_log_model import CycleHistoryLog
from app.models.sharing_model import SharingInvite
from app.models.user_consent_model import UserConsent
from app.models.user_profile_model import UserProfile
from app.utils import utc_now


class SecureCycleSharingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        Config.SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(cls.temp_dir.name, 'sharing.sqlite')}"
        Config.SQLALCHEMY_ENGINE_OPTIONS = {}
        Config.JWT_SECRET_KEY = TEST_JWT_SECRET
        Config.ENABLE_SCHEDULER = False
        cls.app = create_app()
        cls.app.config.update(TESTING=True)
        with cls.app.app_context():
            db.create_all()
            for marker in ("sharer", "viewer", "other"):
                user = UserProfile(full_name=marker.title(), email=f"{marker}@test.local", role="user", status="active", onboarding_completed=True)
                user.set_password("password")
                db.session.add(user)
            db.session.commit()
            sharer = UserProfile.query.filter_by(email="sharer@test.local").one()
            db.session.add(CycleHistoryLog(profile_id=sharer.id, cycle_start_date=date(2026, 7, 1), cycle_end_date=date(2026, 7, 5), flow_intensity="medium", notes="SECRET NOTE"))
            db.session.commit()
        cls.tokens = {}
        with cls.app.test_client() as client:
            for marker in ("sharer", "viewer", "other"):
                response = client.post("/api/auth/login", json={"email": f"{marker}@test.local", "password": "password"})
                cls.tokens[marker] = response.get_json()["access_token"]

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        cls.temp_dir.cleanup()

    def auth(self, marker):
        return {"Authorization": f"Bearer {self.tokens[marker]}"}

    def test_consent_single_use_scope_and_disconnect(self):
        with self.app.test_client() as client:
            denied = client.post("/api/cycle-shares/invites", json={"consent": False}, headers=self.auth("sharer"))
            self.assertEqual(denied.status_code, 400)
            created = client.post("/api/cycle-shares/invites", json={"consent": True}, headers=self.auth("sharer"))
            self.assertEqual(created.status_code, 201)
            code = created.get_json()["invite"]["code"]
            connected = client.post("/api/cycle-shares/connect", json={"code": code}, headers=self.auth("viewer"))
            self.assertEqual(connected.status_code, 201)
            connection_id = connected.get_json()["connection"]["id"]
            reused = client.post("/api/cycle-shares/connect", json={"code": code}, headers=self.auth("other"))
            self.assertEqual(reused.status_code, 409)

            viewed = client.get(f"/api/cycle-shares/connections/{connection_id}/view", headers=self.auth("viewer"))
            self.assertEqual(viewed.status_code, 200)
            payload = viewed.get_json()
            self.assertEqual(set(payload), {"connection", "periods", "predictions"})
            self.assertEqual(set(payload["periods"][0]), {"period_start_date", "period_end_date"})
            serialized = str(payload).lower()
            for forbidden in ("symptom", "mood", "energy", "pain", "sexual", "weight", "notes", "secret note", "chat", "flow_intensity"):
                self.assertNotIn(forbidden, serialized)

            ended = client.post(f"/api/cycle-shares/connections/{connection_id}/disconnect", headers=self.auth("viewer"))
            self.assertEqual(ended.status_code, 200)
            blocked = client.get(f"/api/cycle-shares/connections/{connection_id}/view", headers=self.auth("viewer"))
            self.assertEqual(blocked.status_code, 403)
            replacement = client.post("/api/cycle-shares/invites", json={"consent": True}, headers=self.auth("sharer"))
            self.assertEqual(replacement.status_code, 201)
            replacement_code = replacement.get_json()["invite"]["code"]
            reconnected = client.post("/api/cycle-shares/connect", json={"code": replacement_code}, headers=self.auth("viewer"))
            self.assertEqual(reconnected.status_code, 201)
            replacement_id = reconnected.get_json()["connection"]["id"]
            client.post(f"/api/cycle-shares/connections/{replacement_id}/disconnect", headers=self.auth("sharer"))
            with self.app.app_context():
                self.assertEqual(UserConsent.query.filter_by(consent_type="cycle_date_sharing").count(), 2)

    def test_expired_code_has_clear_error(self):
        with self.app.app_context():
            sharer = UserProfile.query.filter_by(email="sharer@test.local").one()
            invite = SharingInvite(code="expired-code", sharer_user_id=sharer.id, expires_at=utc_now() - timedelta(seconds=1))
            db.session.add(invite)
            db.session.commit()
        with self.app.test_client() as client:
            response = client.post("/api/cycle-shares/connect", json={"code": "expired-code"}, headers=self.auth("other"))
        self.assertEqual(response.status_code, 410)
        self.assertIn("expired", str(response.get_json()).lower())


if __name__ == "__main__":
    unittest.main()
