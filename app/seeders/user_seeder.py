from datetime import date

from app.extensions import db
from app.models.educational_resource_model import EducationalResource
from app.models.health_profile_model import HealthProfile
from app.models.pcos_disorder_status_model import PCOSDisorderStatus
from app.models.user_profile_model import UserProfile


def seed_users():
    admin_email = "admin@penmozhi.com"
    if not UserProfile.query.filter_by(email=admin_email).first():
        admin = UserProfile(
            full_name="Penmozhi Admin",
            date_of_birth=date(1990, 1, 1),
            email=admin_email,
            language_preference="english",
            role="admin",
        )
        admin.set_password("Admin123!")
        db.session.add(admin)
        db.session.flush()
        print(f"  Created admin: {admin_email}")
    else:
        print(f"  Skipped admin (exists): {admin_email}")

    user_email = "user@penmozhi.com"
    if not UserProfile.query.filter_by(email=user_email).first():
        user = UserProfile(
            full_name="Demo User",
            date_of_birth=date(1998, 5, 15),
            email=user_email,
            language_preference="tamil",
            role="user",
        )
        user.set_password("User123!")
        db.session.add(user)
        db.session.flush()

        health = HealthProfile(profile_id=user.id)
        db.session.add(health)
        db.session.flush()

        pcos = PCOSDisorderStatus(
            health_profile_id=health.id,
            disorder_type="none",
            diagnosis_status="not_diagnosed",
        )
        db.session.add(pcos)
        print(f"  Created user: {user_email}")
    else:
        print(f"  Skipped user (exists): {user_email}")

    db.session.commit()


def seed_education():
    if EducationalResource.query.first():
        print("  Skipped education resources (already present).")
        return

    resources = [
        EducationalResource(
            article_title="Understanding Your Menstrual Cycle",
            content_category="cycle",
            content_body=(
                "A typical menstrual cycle lasts 21–35 days. Tracking start and end "
                "dates helps predict your next period and spot irregularities."
            ),
            publication_date=date(2026, 1, 10),
        ),
        EducationalResource(
            article_title="PCOS: Signs and Support",
            content_category="pcos",
            content_body=(
                "Polycystic ovary syndrome can cause irregular cycles, acne, and "
                "weight changes. Early logging of symptoms supports conversations "
                "with a clinician."
            ),
            publication_date=date(2026, 2, 1),
        ),
        EducationalResource(
            article_title="Nutrition for Hormonal Balance",
            content_category="nutrition",
            content_body=(
                "Balanced meals with fiber, protein, and healthy fats can support "
                "energy and mood across the cycle. Stay hydrated and limit excess sugar."
            ),
            publication_date=date(2026, 3, 5),
        ),
    ]
    db.session.add_all(resources)
    db.session.commit()
    print(f"  Created {len(resources)} educational resources.")
