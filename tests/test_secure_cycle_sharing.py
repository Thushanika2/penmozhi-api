import os
import tempfile
import unittest
from datetime import date, timedelta
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-key-with-at-least-32-characters")
TEST_JWT_SECRET = "test-only-secret-key-with-at-least-32-characters"

from app import create_app
from app.config import Config
from app.extensions import db, limiter
from app.models.cycle_history_log_model import CycleHistoryLog
from app.models.sharing_model import SharingInvite
from app.models.user_consent_model import UserConsent
from app.models.user_profile_model import UserProfile
from app.utils import utc_now
from app.services.email_service import send_cycle_invitation_email
from werkzeug.security import check_password_hash


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
                user = UserProfile(
                    full_name=marker.title(), email=f"{marker}@test.local", role="user",
                    status="active", onboarding_completed=True,
                )
                user.set_password("password")
                db.session.add(user)
            db.session.commit()
            sharer = UserProfile.query.filter_by(email="sharer@test.local").one()
            db.session.add(CycleHistoryLog(
                profile_id=sharer.id, cycle_start_date=date(2026, 7, 1),
                cycle_end_date=date(2026, 7, 5), flow_intensity="medium", notes="SECRET NOTE",
            ))
            db.session.commit()
        cls.tokens = {}
        with cls.app.test_client() as client:
            for marker in ("sharer", "viewer", "other"):
                response = client.post("/api/auth/login", json={
                    "email": f"{marker}@test.local", "password": "password",
                })
                cls.tokens[marker] = response.get_json()["access_token"]

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove(); db.drop_all(); db.engine.dispose()
        cls.temp_dir.cleanup()

    def auth(self, marker):
        return {"Authorization": f"Bearer {self.tokens[marker]}"}

    def setUp(self):
        limiter.reset()

    def test_email_invitation_verification_scope_and_disconnect(self):
        delivered = []
        with patch(
            "app.controllers.cycle_share_controller.send_cycle_invitation_email",
            side_effect=lambda email, code: delivered.append((email, code)) or True,
        ):
            with self.app.test_client() as client:
                invalid = client.post("/api/invitations/send", json={"email": "bad", "consent": True}, headers=self.auth("sharer"))
                self.assertEqual(invalid.status_code, 400)
                denied = client.post("/api/invitations/send", json={"email": "viewer@test.local", "consent": False}, headers=self.auth("sharer"))
                self.assertEqual(denied.status_code, 400)
                sent = client.post("/api/invitations/send", json={"email": " VIEWER@Test.Local ", "consent": True}, headers=self.auth("sharer"))
                self.assertEqual(sent.status_code, 200)
                self.assertEqual(set(sent.get_json()), {"message", "expires_in", "resend_after"})
                self.assertNotIn(delivered[0][1], str(sent.get_json()))
                code = delivered[0][1]
                self.assertRegex(code, r"^\d{6}$")

                with self.app.app_context():
                    invite = SharingInvite.query.filter_by(status="active").one()
                    self.assertEqual(invite.invited_email, "viewer@test.local")
                    self.assertNotEqual(invite.code_hash, code)
                    self.assertTrue(check_password_hash(invite.code_hash, code))
                    self.assertLessEqual(invite.expires_at - invite.created_at, timedelta(minutes=10, seconds=1))

                cooldown = client.post("/api/invitations/send", json={"email": "viewer@test.local", "consent": True}, headers=self.auth("sharer"))
                self.assertEqual(cooldown.status_code, 429)
                wrong_user = client.post("/api/invitations/verify", json={"email": "viewer@test.local", "code": code}, headers=self.auth("other"))
                self.assertEqual(wrong_user.status_code, 400)
                wrong_code = client.post("/api/invitations/verify", json={"email": "viewer@test.local", "code": "000000"}, headers=self.auth("viewer"))
                self.assertEqual(wrong_code.status_code, 400)
                connected = client.post("/api/invitations/verify", json={"email": "VIEWER@test.local", "code": code}, headers=self.auth("viewer"))
                self.assertEqual(connected.status_code, 201)
                connection_id = connected.get_json()["connection"]["id"]
                reused = client.post("/api/invitations/verify", json={"email": "viewer@test.local", "code": code}, headers=self.auth("viewer"))
                self.assertEqual(reused.status_code, 400)
                self.assertIn("Invalid or expired", str(reused.get_json()))

                viewed = client.get(f"/api/cycle-shares/connections/{connection_id}/view", headers=self.auth("viewer"))
                self.assertEqual(viewed.status_code, 200)
                serialized = str(viewed.get_json()).lower()
                for forbidden in ("symptom", "mood", "energy", "pain", "sexual", "weight", "notes", "secret note", "chat", "flow_intensity"):
                    self.assertNotIn(forbidden, serialized)
                ended = client.post(f"/api/cycle-shares/connections/{connection_id}/disconnect", headers=self.auth("viewer"))
                self.assertEqual(ended.status_code, 200)
                blocked = client.get(f"/api/cycle-shares/connections/{connection_id}/view", headers=self.auth("viewer"))
                self.assertEqual(blocked.status_code, 403)
                with self.app.app_context():
                    self.assertEqual(UserConsent.query.filter_by(consent_type="cycle_date_sharing").count(), 1)

    def test_expired_and_resend_codes_are_rejected_safely(self):
        delivered = []
        with patch(
            "app.controllers.cycle_share_controller.send_cycle_invitation_email",
            side_effect=lambda email, code: delivered.append(code) or True,
        ):
            with self.app.test_client() as client:
                client.post("/api/invitations/send", json={"email": "other@test.local", "consent": True}, headers=self.auth("sharer"))
                old_code = delivered[-1]
                with self.app.app_context():
                    invite = SharingInvite.query.filter_by(invited_email="other@test.local", status="active").one()
                    invite.created_at = utc_now() - timedelta(seconds=61)
                    db.session.commit()
                resent = client.post("/api/invitations/resend", json={"email": "other@test.local"}, headers=self.auth("other"))
                self.assertEqual(resent.status_code, 200)
                new_code = delivered[-1]
                self.assertNotEqual(old_code, new_code)
                old_rejected = client.post("/api/invitations/verify", json={"email": "other@test.local", "code": old_code}, headers=self.auth("other"))
                self.assertEqual(old_rejected.status_code, 400)
                with self.app.app_context():
                    active = SharingInvite.query.filter_by(invited_email="other@test.local", status="active").one()
                    active.expires_at = utc_now() - timedelta(seconds=1)
                    db.session.commit()
                expired = client.post("/api/invitations/verify", json={"email": "other@test.local", "code": new_code}, headers=self.auth("other"))
                self.assertEqual(expired.status_code, 400)
                self.assertIn("Invalid or expired", str(expired.get_json()))

    def test_brevo_failure_rolls_back_invitation(self):
        with patch("app.controllers.cycle_share_controller.send_cycle_invitation_email", return_value=False):
            with self.app.test_client() as client:
                response = client.post("/api/invitations/send", json={"email": "nobody@example.com", "consent": True}, headers=self.auth("sharer"))
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("BREVO", str(response.get_json()).upper())
        with self.app.app_context():
            self.assertIsNone(SharingInvite.query.filter_by(invited_email="nobody@example.com").first())

    def test_brevo_message_uses_configured_sender_and_branded_content(self):
        class FakeTransactionalEmails:
            def __init__(self):
                self.kwargs = None

            def send_transac_email(self, **kwargs):
                self.kwargs = kwargs

        transactional = FakeTransactionalEmails()

        class FakeBrevo:
            def __init__(self, **kwargs):
                self.api_key = kwargs["api_key"]
                self.transactional_emails = transactional

        with self.app.app_context():
            self.app.config.update(
                BREVO_API_KEY="test-secret-not-for-production",
                BREVO_FROM_EMAIL="verified@penmozhi.test",
                BREVO_FROM_NAME="Penmozhi Team",
            )
            with patch("brevo.Brevo", FakeBrevo):
                sent = send_cycle_invitation_email("friend@example.com", "123456")
        self.assertTrue(sent)
        self.assertEqual(transactional.kwargs["sender"].email, "verified@penmozhi.test")
        self.assertEqual(transactional.kwargs["sender"].name, "Penmozhi Team")
        self.assertEqual(transactional.kwargs["to"][0].email, "friend@example.com")
        self.assertEqual(transactional.kwargs["subject"], "You’ve been invited to Penmozhi")
        self.assertIn("123456", transactional.kwargs["html_content"])
        self.assertIn("10 minutes", transactional.kwargs["html_content"])


if __name__ == "__main__":
    unittest.main()
