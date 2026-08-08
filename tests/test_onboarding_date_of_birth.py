import os
import tempfile
import unittest
from datetime import date, timedelta
from unittest.mock import patch

from marshmallow import ValidationError

TEST_JWT_SECRET = "test-only-secret-key-with-at-least-32-characters"
os.environ.setdefault("JWT_SECRET_KEY", TEST_JWT_SECRET)

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.user_profile_model import UserProfile
from app.schemas.onboarding_schema import OnboardingSchema, calculate_age


class OnboardingDateOfBirthTest(unittest.TestCase):
    def setUp(self):
        self.today = date(2026, 8, 8)

    def test_calculate_age_uses_whether_birthday_has_occurred(self):
        self.assertEqual(calculate_age(date(2017, 8, 8), self.today), 9)
        self.assertEqual(calculate_age(date(2017, 8, 9), self.today), 8)

    def test_accepts_age_boundaries(self):
        schema = OnboardingSchema()
        for date_of_birth in (date(2017, 8, 8), date(1946, 8, 8)):
            with self.subTest(date_of_birth=date_of_birth):
                with patch("app.schemas.onboarding_schema.date") as mocked_date:
                    mocked_date.today.return_value = self.today
                    schema.validate_date_of_birth(date_of_birth)

    def test_rejects_younger_than_nine_and_older_than_eighty(self):
        schema = OnboardingSchema()
        for date_of_birth in (date(2017, 8, 9), date(1945, 8, 8)):
            with self.subTest(date_of_birth=date_of_birth):
                with patch("app.schemas.onboarding_schema.date") as mocked_date:
                    mocked_date.today.return_value = self.today
                    with self.assertRaisesRegex(ValidationError, "aged 9 to 80"):
                        schema.validate_date_of_birth(date_of_birth)


class OnboardingDateOfBirthEndpointTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        database_path = os.path.join(cls.temp_dir.name, "onboarding-dob.sqlite")
        Config.SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path}"
        Config.SQLALCHEMY_ENGINE_OPTIONS = {}
        Config.JWT_SECRET_KEY = TEST_JWT_SECRET
        Config.ENABLE_SCHEDULER = False

        cls.app = create_app()
        cls.app.config.update(TESTING=True)
        with cls.app.app_context():
            db.create_all()
            user = UserProfile(
                full_name="DOB Test User",
                email="dob@onboarding.test",
                role="user",
                status="active",
                onboarding_completed=False,
            )
            user.set_password("test-password")
            db.session.add(user)
            db.session.commit()
            cls.user_id = user.id

        with cls.app.test_client() as client:
            response = client.post(
                "/api/auth/login",
                json={"email": "dob@onboarding.test", "password": "test-password"},
            )
            cls.token = response.get_json()["access_token"]

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        cls.temp_dir.cleanup()

    def test_complete_endpoint_rejects_age_one_without_mutating_user(self):
        payload = {
            "full_name": "DOB Test User",
            "date_of_birth": (date.today() - timedelta(days=365)).isoformat(),
            "country": "Sri Lanka",
            "height": 160,
            "weight": 55,
            "language_preference": "english",
            "timezone": "Asia/Colombo",
            "period_history": [{"period_start": "2026-07-15", "flow": "medium"}],
            "average_cycle_length": 28,
            "average_period_length": 5,
            "cycle_regularity": "regular",
            "common_symptoms": ["no_symptoms"],
            "health_conditions": ["none"],
            "sleep_hours": 8,
            "water_intake_liters": 2,
            "exercise_frequency": "weekly",
            "stress_level": "low",
            "smoking": False,
            "alcohol": False,
            "is_teenager": False,
            "trying_to_conceive": False,
            "is_pregnant": False,
            "is_breastfeeding": False,
            "using_birth_control": False,
            "birth_control_type": "none",
            "notify_period": True,
            "notify_ovulation": True,
            "notify_medication": False,
            "notify_daily_health": False,
        }

        with self.app.test_client() as client:
            response = client.post(
                "/api/onboarding/complete",
                json=payload,
                headers={"Authorization": f"Bearer {self.token}"},
            )

        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertEqual(body["errors"][0]["code"], "validation.date_of_birth")
        self.assertIn("aged 9 to 80", body["errors"][0]["message"])
        with self.app.app_context():
            user = db.session.get(UserProfile, self.user_id)
            self.assertFalse(user.onboarding_completed)
            self.assertIsNone(user.date_of_birth)


if __name__ == "__main__":
    unittest.main()
